# Requirements Document

## Introduction

This feature adds a POP3 inbound mail retrieval adapter to the PSense Mail Python backend (FastAPI + Beanie). The adapter implements the existing `InboundAdapter` protocol using Python's `poplib` module wrapped in an asyncio thread executor (or `aiopoplib` if available), enabling the `InboundPollerWorker` to retrieve messages from any POP3-compliant server — including Mailpit's built-in POP3 server for local development and real POP3 providers in production.

The adapter is registered under `provider.active = "pop3"` and is wired into the existing `AdapterRegistry`. A new `Pop3Config` Pydantic model is added to `settings.py` and `default.yaml`. The Mailpit docker-compose service is updated to expose its optional POP3 port. Deduplication is handled via a persistent seen-IDs store so messages are not re-ingested across poller cycles.

## Glossary

- **POP3_Adapter**: The `POP3InboundAdapter` class that implements the `InboundAdapter` protocol using POP3.
- **InboundAdapter**: The existing protocol in `app/adapters/protocols.py` that all inbound mail adapters must satisfy (`fetch_new_messages`, `acknowledge`, `health_check`).
- **InboundPollerWorker**: The existing background worker in `app/workers/inbound_poller.py` that calls `InboundAdapter.fetch_new_messages` on a configurable interval.
- **AdapterRegistry**: The existing factory class in `app/adapters/registry.py` that instantiates adapters from config.
- **Pop3Config**: The new Pydantic model that holds all POP3 connection parameters.
- **Seen_ID_Store**: The in-process set (or persistent MongoDB collection) that tracks provider message UIDs already ingested, preventing duplicate processing.
- **Provider_Message_UID**: The unique identifier assigned by the POP3 server to each message (UIDL response), used as `provider_message_id` in `InboundMessage`.
- **UIDL**: POP3 command that returns a unique identifier listing for messages on the server; used for deduplication.
- **MIME_Parser**: The component responsible for parsing raw RFC 2822 message bytes into structured `InboundMessage` fields (headers, body parts, attachments).
- **TLS_Mode**: The connection security mode — `none` (plain), `ssl` (implicit TLS on connect), or `starttls` (upgrade after connect).
- **Mailpit**: The local development mail sandbox (`axllent/mailpit`) that provides an optional built-in POP3 server on port 1110.

---

## Requirements

### Requirement 1: POP3 Connection and Authentication

**User Story:** As a backend operator, I want the POP3 adapter to establish authenticated connections to a POP3 server, so that the system can retrieve inbound mail from any standards-compliant POP3 provider.

#### Acceptance Criteria

1. WHEN `provider.active` is set to `"pop3"`, THE `AdapterRegistry` SHALL instantiate a `POP3_Adapter` using the parameters from `provider.pop3` in settings.
2. THE `POP3_Adapter` SHALL support `tls_mode` values of `"none"`, `"ssl"`, and `"starttls"` for connection security.
3. WHEN `tls_mode` is `"ssl"`, THE `POP3_Adapter` SHALL connect using `poplib.POP3_SSL` on the configured `port`.
4. WHEN `tls_mode` is `"starttls"`, THE `POP3_Adapter` SHALL connect using `poplib.POP3` and issue the `STLS` command before authenticating.
5. WHEN `tls_mode` is `"none"`, THE `POP3_Adapter` SHALL connect using `poplib.POP3` without TLS negotiation.
6. THE `POP3_Adapter` SHALL authenticate using the `USER` / `PASS` POP3 commands with the configured `username` and `password`.
7. WHEN authentication fails, THE `POP3_Adapter` SHALL raise `ProviderUnavailableError` with provider name `"pop3"` and the server's error message.
8. THE `POP3_Adapter` SHALL execute all blocking `poplib` calls inside `asyncio.get_event_loop().run_in_executor(None, ...)` to avoid blocking the event loop.
9. THE `POP3_Adapter` SHALL close the POP3 connection with a `QUIT` command after each fetch or health-check operation, whether the operation succeeds or fails.
10. WHEN a network-level error occurs during connection, THE `POP3_Adapter` SHALL raise `ProviderUnavailableError` with provider name `"pop3"` and the underlying exception message.

---

### Requirement 2: Message Fetching and Deduplication

**User Story:** As a backend operator, I want the POP3 adapter to fetch only new, previously unseen messages on each poll cycle, so that the `InboundPollerWorker` does not re-ingest messages that have already been processed.

#### Acceptance Criteria

1. WHEN `fetch_new_messages` is called, THE `POP3_Adapter` SHALL issue the `UIDL` command to retrieve the unique identifier listing from the server.
2. WHEN the POP3 server does not support `UIDL`, THE `POP3_Adapter` SHALL fall back to using the message sequence number prefixed with the server hostname as the provider message UID.
3. THE `POP3_Adapter` SHALL maintain a `Seen_ID_Store` that persists the set of `Provider_Message_UID` values already returned to the caller.
4. WHEN `fetch_new_messages` is called, THE `POP3_Adapter` SHALL return only messages whose `Provider_Message_UID` is not present in the `Seen_ID_Store`.
5. THE `POP3_Adapter` SHALL add newly fetched message UIDs to the `Seen_ID_Store` before returning the message list to the caller.
6. THE `Seen_ID_Store` SHALL be backed by an in-memory set by default, with an optional MongoDB collection (`pop3_seen_ids`) when `database.backend` is `"mongo"`.
7. WHEN `fetch_new_messages` is called and the server has no new messages, THE `POP3_Adapter` SHALL return an empty list without raising an error.
8. THE `POP3_Adapter` SHALL respect the `since` parameter of `fetch_new_messages` by filtering out messages whose parsed `Date` header is earlier than `since`, when `since` is not `None`.
9. WHEN the server exposes more than 100 messages (Mailpit's POP3 limit), THE `POP3_Adapter` SHALL process only the messages available in the current UIDL listing without error.

---

### Requirement 3: MIME Parsing and InboundMessage Construction

**User Story:** As a backend developer, I want the POP3 adapter to produce fully populated `InboundMessage` objects from raw POP3 message bytes, so that the `InboundPollerWorker` can store and process messages without any POP3-specific knowledge.

#### Acceptance Criteria

1. WHEN a message is retrieved via `RETR`, THE `MIME_Parser` SHALL parse the raw RFC 2822 bytes using Python's `email.message_from_bytes` with `policy=email.policy.default`.
2. THE `MIME_Parser` SHALL populate `InboundMessage.from_address` and `InboundMessage.from_name` from the `From` header, using `email.utils.parseaddr`.
3. THE `MIME_Parser` SHALL populate `InboundMessage.to` as a list of `MailRecipient` objects parsed from the `To` header.
4. THE `MIME_Parser` SHALL populate `InboundMessage.cc` as a list of `MailRecipient` objects parsed from the `Cc` header, defaulting to an empty list when the header is absent.
5. THE `MIME_Parser` SHALL populate `InboundMessage.subject` by decoding RFC 2047 encoded-word sequences using `email.header.decode_header`.
6. THE `MIME_Parser` SHALL populate `InboundMessage.received_at` by parsing the `Date` header using `email.utils.parsedate_to_datetime`, defaulting to `datetime.now(timezone.utc)` when the header is absent or unparseable.
7. THE `MIME_Parser` SHALL populate `InboundMessage.body_text` from the first `text/plain` MIME part and `InboundMessage.body_html` from the first `text/html` MIME part.
8. THE `MIME_Parser` SHALL populate `InboundMessage.raw_headers` as a dict of all header names to their decoded string values, preserving `Message-ID`, `In-Reply-To`, and `References` headers for thread resolution by the `InboundPollerWorker`.
9. THE `MIME_Parser` SHALL populate `InboundMessage.attachments` with one entry per non-inline attachment part, including `name`, `mime`, `size`, and `content` (raw bytes) fields.
10. WHEN a MIME part's charset cannot be decoded, THE `MIME_Parser` SHALL fall back to `latin-1` decoding with `errors="replace"` rather than raising an exception.
11. FOR ALL valid RFC 2822 message byte sequences, parsing the raw bytes into an `InboundMessage` and re-serializing the key fields SHALL produce values semantically equivalent to the original headers (round-trip property).

---

### Requirement 4: Acknowledge (Delete from Server)

**User Story:** As a backend operator, I want the POP3 adapter to delete acknowledged messages from the POP3 server, so that the server mailbox does not grow unboundedly and messages are not re-fetched after a process restart when the Seen_ID_Store is cleared.

#### Acceptance Criteria

1. WHEN `acknowledge` is called with a non-empty list of `Provider_Message_UID` values, THE `POP3_Adapter` SHALL connect to the POP3 server, issue `DELE` for each message whose UID matches a current server message, and then issue `QUIT` to commit the deletions.
2. WHEN `acknowledge` is called with an empty list, THE `POP3_Adapter` SHALL return immediately without opening a connection.
3. WHEN a UID passed to `acknowledge` is no longer present on the server (already deleted), THE `POP3_Adapter` SHALL skip that UID without raising an error.
4. WHEN the `DELE` command fails for a specific message, THE `POP3_Adapter` SHALL log a warning with the UID and continue processing the remaining UIDs.
5. WHEN the POP3 connection fails during `acknowledge`, THE `POP3_Adapter` SHALL raise `ProviderUnavailableError` with provider name `"pop3"`.
6. THE `POP3_Adapter` SHALL remove successfully acknowledged UIDs from the `Seen_ID_Store` after the `QUIT` command completes, so that if the server re-delivers a message (e.g., after a failed delete), it will be fetched again.

---

### Requirement 5: Health Check

**User Story:** As a backend operator, I want the POP3 adapter to expose a health check, so that the `/health` endpoint and monitoring systems can report the status of the POP3 connection.

#### Acceptance Criteria

1. WHEN `health_check` is called, THE `POP3_Adapter` SHALL open a POP3 connection, issue the `NOOP` command, record the round-trip latency in milliseconds, and close the connection.
2. WHEN the `NOOP` command succeeds, THE `POP3_Adapter` SHALL return an `AdapterHealthStatus` with `name="pop3-inbound"`, `status="ok"`, and `latency_ms` set to the measured round-trip time.
3. WHEN the POP3 connection or `NOOP` command fails, THE `POP3_Adapter` SHALL return an `AdapterHealthStatus` with `name="pop3-inbound"`, `status="down"`, and `details={"error": <exception message>}` without raising an exception.
4. THE `POP3_Adapter` SHALL complete the `health_check` operation within the configured `connect_timeout_seconds` value.

---

### Requirement 6: Configuration Model

**User Story:** As a backend operator, I want all POP3 connection parameters to be declared in a typed Pydantic model and configurable via YAML and environment variables, so that the adapter can be deployed to any POP3 provider without code changes.

#### Acceptance Criteria

1. THE `Pop3Config` Pydantic model SHALL declare the following fields: `host` (str), `port` (int), `username` (str), `password` (str), `tls_mode` (Literal["none", "ssl", "starttls"]), `connect_timeout_seconds` (int), and `max_messages_per_poll` (int).
2. THE `Pop3Config` SHALL use the following defaults: `host="localhost"`, `port=1110`, `username=""`, `password=""`, `tls_mode="none"`, `connect_timeout_seconds=10`, `max_messages_per_poll=50`.
3. THE `ProviderConfig` Pydantic model in `settings.py` SHALL include a `pop3` field of type `Pop3Config` with a default factory.
4. THE `default.yaml` configuration file SHALL include a `provider.pop3` section with all fields from `Pop3Config` set to their default values.
5. WHEN the environment variable `PSENSE_MAIL__PROVIDER__POP3__HOST` is set, THE `Settings` loader SHALL override `provider.pop3.host` with the environment variable value.
6. WHEN `provider.active` is `"pop3"` and `provider.pop3.username` is an empty string, THE `AdapterRegistry` SHALL raise `ValueError` with a message indicating that `provider.pop3.username` is required.
7. THE `Pop3Config` SHALL validate that `port` is in the range 1–65535, raising `ValidationError` for values outside this range.
8. THE `Pop3Config` SHALL validate that `connect_timeout_seconds` is greater than 0, raising `ValidationError` for values of 0 or below.
9. THE `Pop3Config` SHALL validate that `max_messages_per_poll` is in the range 1–500, raising `ValidationError` for values outside this range.

---

### Requirement 7: AdapterRegistry Wiring

**User Story:** As a backend developer, I want the `AdapterRegistry` to instantiate the `POP3_Adapter` when `provider.active = "pop3"`, so that the `InboundPollerWorker` receives the correct adapter without any changes to the worker or service layer.

#### Acceptance Criteria

1. THE `AdapterRegistry` SHALL expose an `inbound` cached property that returns an `InboundAdapter`-compatible instance.
2. WHEN `provider.active` is `"pop3"`, THE `AdapterRegistry.inbound` property SHALL instantiate and return a `POP3InboundAdapter` configured from `settings.provider.pop3`.
3. WHEN `provider.active` is `"mailpit"`, THE `AdapterRegistry.inbound` property SHALL instantiate and return a `MailPitInboundAdapter` configured from `settings.provider.mailpit`.
4. WHEN `provider.active` is `"gmail"`, THE `AdapterRegistry.inbound` property SHALL instantiate and return a `GmailInboundAdapter` configured from `settings.provider.gmail`.
5. WHEN `provider.active` is `"memory"` or any unrecognized value, THE `AdapterRegistry.inbound` property SHALL instantiate and return a `MemoryInboundAdapter` that returns an empty message list.
6. THE `AdapterRegistry.inbound` property SHALL be decorated with `@cached_property` so the adapter is instantiated at most once per registry instance.
7. WHEN the `AdapterRegistry` instantiates the `POP3InboundAdapter`, THE `AdapterRegistry` SHALL log the message `"Initialising inbound adapter: pop3"` at INFO level.

---

### Requirement 8: Mailpit Docker Compose POP3 Configuration

**User Story:** As a developer, I want the Mailpit service in docker-compose to expose its POP3 server, so that I can test the POP3 adapter end-to-end in the local development environment without any additional infrastructure.

#### Acceptance Criteria

1. THE `docker-compose.yaml` Mailpit service SHALL expose port `1110` on the host mapped to container port `1110` for POP3 access.
2. THE `docker-compose.yaml` Mailpit service SHALL set the environment variable `MP_POP3_AUTH` to a value of the form `<username>:<password>` to enable Mailpit's built-in POP3 server.
3. THE `docker-compose.yaml` `api` service SHALL set `PSENSE_MAIL__PROVIDER__POP3__HOST` to `"mailpit"`, `PSENSE_MAIL__PROVIDER__POP3__PORT` to `"1110"`, `PSENSE_MAIL__PROVIDER__POP3__USERNAME` to the same username used in `MP_POP3_AUTH`, and `PSENSE_MAIL__PROVIDER__POP3__PASSWORD` to the same password used in `MP_POP3_AUTH`.
4. THE `docker-compose.yaml` SHALL NOT change `PSENSE_MAIL__PROVIDER__ACTIVE` from `"mailpit"` by default, so that the existing Mailpit REST API inbound adapter remains the default and POP3 is opt-in.

---

### Requirement 9: Memory Inbound Adapter (Test Stub)

**User Story:** As a backend developer, I want a `MemoryInboundAdapter` that satisfies the `InboundAdapter` protocol and returns a configurable list of messages, so that unit tests and the `memory` provider mode do not require a live POP3 server.

#### Acceptance Criteria

1. THE `MemoryInboundAdapter` SHALL implement `fetch_new_messages`, `acknowledge`, and `health_check` as defined by the `InboundAdapter` protocol.
2. WHEN `fetch_new_messages` is called on a `MemoryInboundAdapter`, THE `MemoryInboundAdapter` SHALL return the list of `InboundMessage` objects injected at construction time.
3. WHEN `acknowledge` is called on a `MemoryInboundAdapter`, THE `MemoryInboundAdapter` SHALL remove the acknowledged message IDs from its internal message list.
4. WHEN `health_check` is called on a `MemoryInboundAdapter`, THE `MemoryInboundAdapter` SHALL return `AdapterHealthStatus(name="memory-inbound", status="ok", latency_ms=0.0)`.
5. THE `MemoryInboundAdapter` SHALL be importable from `app.adapters.inbound.memory`.

---

### Requirement 10: Unit and Integration Tests

**User Story:** As a backend developer, I want comprehensive tests for the POP3 adapter and its supporting components, so that regressions are caught before deployment and the adapter's correctness can be verified without a live POP3 server.

#### Acceptance Criteria

1. THE test suite SHALL include a unit test that mocks `poplib.POP3` and verifies that `POP3InboundAdapter.fetch_new_messages` returns an empty list when the server reports zero messages.
2. THE test suite SHALL include a unit test that mocks `poplib.POP3` with two messages and verifies that `fetch_new_messages` returns two `InboundMessage` objects with correctly parsed `from_address`, `subject`, `body_text`, and `received_at` fields.
3. THE test suite SHALL include a unit test that calls `fetch_new_messages` twice with the same mocked server state and verifies that the second call returns an empty list (deduplication via `Seen_ID_Store`).
4. THE test suite SHALL include a unit test that verifies `acknowledge` issues `DELE` commands for each provided UID and then issues `QUIT`.
5. THE test suite SHALL include a unit test that verifies `health_check` returns `status="ok"` when `NOOP` succeeds and `status="down"` when the connection raises an exception.
6. THE test suite SHALL include a unit test that verifies `Pop3Config` raises `ValidationError` for `port=0`, `connect_timeout_seconds=0`, and `max_messages_per_poll=0`.
7. THE test suite SHALL include a unit test that verifies `AdapterRegistry.inbound` returns a `POP3InboundAdapter` instance when `provider.active = "pop3"`.
8. THE test suite SHALL include a property-based test using `hypothesis` that generates arbitrary valid RFC 2822 message bytes and verifies that the `MIME_Parser` always produces an `InboundMessage` without raising an exception (robustness property).
9. THE test suite SHALL include a round-trip property test that generates `InboundMessage` instances with arbitrary `from_address`, `subject`, and `body_text` values, serializes them to RFC 2822 format, parses them back, and asserts that `from_address`, `subject`, and `body_text` are preserved (round-trip property).
10. WHEN all tests are run with `pytest` in `runtime/mail_api/`, THE test suite SHALL pass with zero failures and zero errors.

---

### Requirement 11: Account Settings — POP3 Configuration UI

**User Story:** As a user, I want a dedicated "Accounts & Sync" settings page where I can configure my POP3 server credentials and see the connection status, so that I can set up inbound mail retrieval without touching config files or environment variables.

#### Acceptance Criteria

1. A new route `/_app/settings/accounts` SHALL be added to the TanStack Start file-based router at `webmail_ui/src/routes/_app.settings.accounts.tsx`.
2. THE settings page SHALL be accessible from the account dropdown menu in `AppHeader` (the `DropdownMenu` that currently shows "Preferences", "Mail settings", "Signatures") as a new item labeled "Accounts & sync".
3. THE settings page SHALL render a `Card` component (matching the pattern in `_app.settings.mail.tsx`) with title "Incoming mail (POP3)" and description "Connect a POP3 server to receive mail in PSense."
4. THE POP3 configuration card SHALL contain form fields for: Server host (`Input`), Port (`Input` type="number"), Username (`Input`), Password (`Input` type="password"), and Security (`Select` with options "None", "SSL/TLS", "STARTTLS").
5. THE POP3 configuration card SHALL contain a "Test connection" `Button` that calls `POST /api/v1/accounts/pop3/test` and displays a success toast ("Connection successful") or error toast with the server's error message.
6. THE POP3 configuration card SHALL contain a "Save" `Button` that calls `PATCH /api/v1/accounts/pop3` with the form values and displays a success toast ("POP3 settings saved").
7. WHEN the page loads, THE form SHALL be pre-populated with the current POP3 settings fetched from `GET /api/v1/accounts/pop3`.
8. THE Password field SHALL render as `type="password"` with a toggle button (Eye / EyeOff lucide icon) to reveal/hide the value.
9. THE settings page SHALL use `ScrollArea`, `Card`, `CardHeader`, `CardTitle`, `CardDescription`, `CardContent`, `Label`, `Input`, `Select`, and `Button` from `@/components/ui/` — no custom primitives.
10. THE settings page SHALL display a sync status indicator showing the last successful poll time and the number of messages fetched in the last cycle, fetched from `GET /api/v1/accounts/pop3/status`.

---

### Requirement 12: Sync Status Indicator in Mail Sidebar

**User Story:** As a user, I want to see a subtle sync status indicator in the mail sidebar so that I know whether the POP3 poller is actively fetching mail or has encountered an error.

#### Acceptance Criteria

1. THE `MailSidebar` component SHALL display a sync status row at the bottom of the sidebar (above the storage bar) when `provider.active` is `"pop3"`.
2. WHEN the poller is idle (last poll succeeded), THE sync status row SHALL show a green dot and the text "Synced · <relative time>" (e.g., "Synced · 2 min ago").
3. WHEN the poller is actively fetching, THE sync status row SHALL show a spinning `Loader2` lucide icon and the text "Syncing…".
4. WHEN the last poll failed, THE sync status row SHALL show a red dot and the text "Sync error" with a "Retry" button that triggers an immediate poll via `POST /api/v1/accounts/pop3/sync`.
5. THE sync status data SHALL be fetched from `GET /api/v1/accounts/pop3/status` using TanStack Query with a 30-second refetch interval.
6. THE sync status row SHALL be hidden when `provider.active` is not `"pop3"` (i.e., when using the Mailpit REST API or memory adapter).

---

### Requirement 13: Backend API Endpoints for POP3 Settings and Status

**User Story:** As a frontend developer, I want REST API endpoints to read/write POP3 configuration and query sync status, so that the settings UI can operate without direct access to the server's config files.

#### Acceptance Criteria

1. `GET /api/v1/accounts/pop3` SHALL return the current POP3 configuration (host, port, username, tls_mode, connect_timeout_seconds, max_messages_per_poll) — the password field SHALL be omitted from the response.
2. `PATCH /api/v1/accounts/pop3` SHALL accept a JSON body with any subset of the POP3 config fields (excluding password from the response) and persist the changes to the running settings; the password field SHALL be accepted in the request body but never returned.
3. `POST /api/v1/accounts/pop3/test` SHALL attempt a POP3 `NOOP` health check using the credentials in the request body (or current settings if body is empty) and return `{"status": "ok", "latency_ms": <float>}` on success or `{"status": "error", "message": "<string>"}` on failure.
4. `POST /api/v1/accounts/pop3/sync` SHALL trigger an immediate out-of-cycle poll on the `InboundPollerWorker` and return `{"triggered": true}`.
5. `GET /api/v1/accounts/pop3/status` SHALL return `{"last_poll_at": "<ISO datetime or null>", "last_poll_status": "ok|error|never", "last_error": "<string or null>", "messages_last_cycle": <int>, "is_polling": <bool>}`.
6. ALL five endpoints SHALL be protected by the existing auth middleware and SHALL return `401` when `auth.enabled` is `true` and no valid token is provided.
7. THE `InboundPollerWorker` SHALL expose a `trigger_immediate_poll()` method that can be called by the `POST /api/v1/accounts/pop3/sync` endpoint to initiate an out-of-cycle fetch.
8. THE `InboundPollerWorker` SHALL maintain `last_poll_at`, `last_poll_status`, `last_error`, `messages_last_cycle`, and `is_polling` attributes that are read by the `GET /api/v1/accounts/pop3/status` endpoint.
