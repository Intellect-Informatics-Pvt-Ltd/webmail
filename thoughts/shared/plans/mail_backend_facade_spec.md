# Python FastAPI Mail Backend – Developer Handoff

## Purpose
This document provides a **developer-facing façade contract** for a Python mail backend that can power an Outlook-style web UI while remaining easy to run in a **MailPit-like local mode**.

## Design principles
- **Async-first**
- **Provider-agnostic**
- **Typed and testable**
- **Idempotent on risky writes**
- **Resilient under partial outages**
- **Separation of HTTP layer and domain layer**

## Recommended package layout

```text
app/
  api/
    routers/
      mailbox.py
      messages.py
      drafts.py
      search.py
      attachments.py
      admin.py
  domain/
    enums.py
    errors.py
    models.py
    requests.py
    responses.py
    protocols.py
  services/
    mail_facade.py
    compose_facade.py
    search_facade.py
    attachment_facade.py
    admin_facade.py
  adapters/
    storage/
    search/
    transport/
    events/
    policy/
  workers/
    send_worker.py
    index_worker.py
    retention_worker.py
  main.py
```

## Core domain states

### DeliveryState
- `draft`
- `queued`
- `sending`
- `sent`
- `failed_retryable`
- `failed_permanent`
- `scheduled`
- `cancelled`

### Folder kinds
- `inbox`
- `focused`
- `other`
- `drafts`
- `sent`
- `archive`
- `snoozed`
- `flagged`
- `deleted`
- `junk`
- `custom`

### Message actions
- archive
- delete
- restore
- move
- mark_read
- mark_unread
- flag
- unflag
- pin
- unpin
- snooze
- unsnooze
- categorize
- uncategorize

## Reliability requirements
- Every mutating façade method accepts an optional `idempotency_key`.
- Updates support optimistic concurrency via `expected_version`.
- Domain services raise **structured domain exceptions**, not raw adapter exceptions.
- Search/index/transport outages degrade into typed `ProviderUnavailableError` or `RetryableDeliveryError`.
- Failed sends preserve original draft/message intent for replay and inspection.

## Façade interfaces

### MailFacade
Responsibilities:
- list folders
- list threads
- fetch message/thread
- move/archive/delete/restore
- mark read/unread
- flag/pin/snooze/categorize
- bulk actions

### ComposeFacade
Responsibilities:
- create draft
- patch draft
- validate recipients/body/attachments
- send draft
- retry failed send
- schedule send placeholder

### SearchFacade
Responsibilities:
- structured search
- suggestions
- facets
- recent searches placeholder

### AttachmentFacade
Responsibilities:
- initialize upload
- finalize upload
- read metadata
- authorize download

### AdminFacade
Responsibilities:
- health report
- seed demo data
- replay failed sends
- reindex
- purge test data
- diagnostics

## Domain exceptions

```python
class MailDomainError(Exception): ...
class NotFoundError(MailDomainError): ...
class ValidationError(MailDomainError): ...
class ConflictError(MailDomainError): ...
class ConcurrencyError(MailDomainError): ...
class PolicyDeniedError(MailDomainError): ...
class ProviderUnavailableError(MailDomainError): ...
class RateLimitedError(MailDomainError): ...
class RetryableDeliveryError(MailDomainError): ...
class PermanentDeliveryError(MailDomainError): ...
```

## Example FastAPI route mapping

- `GET /mailboxes/{mailbox_id}/folders`
- `GET /folders/{folder_id}/threads`
- `GET /threads/{thread_id}`
- `GET /messages/{message_id}`
- `POST /drafts`
- `PATCH /drafts/{draft_id}`
- `POST /drafts/{draft_id}/send`
- `POST /messages/actions`
- `POST /search/messages`
- `POST /attachments/init`
- `POST /attachments/{upload_id}/finalize`
- `GET /health`

## Data contracts to model
- `MailRecipient`
- `MailAttachment`
- `MailMessage`
- `MailThread`
- `MailFolder`
- `MailCategory`
- `ComposeDraft`
- `DeliveryReceipt`
- `SearchRequest`
- `SearchResponse`
- `HealthReport`

## Operational guidance
- Keep **provider-specific** fields under `adapter_meta`.
- Use a local transport adapter in development that can feed MailPit or an in-memory sink.
- Add contract tests for façade behavior before wiring full adapters.
- Prefer cursor pagination for thread/message list APIs.
- Expose correlation IDs in route responses and logs for troubleshooting.
