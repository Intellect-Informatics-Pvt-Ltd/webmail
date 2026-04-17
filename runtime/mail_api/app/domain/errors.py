"""PSense Mail — Domain exception hierarchy.

Every domain service raises these structured exceptions. The error_handler
middleware maps them to appropriate HTTP status codes. Adapter-level
exceptions (e.g., pymongo errors) are caught in services and re-raised as
domain exceptions — callers never see raw driver errors.
"""
from __future__ import annotations

from typing import Any


class MailDomainError(Exception):
    """Base domain error for all PSense Mail operations."""

    def __init__(self, message: str = "", *, code: str = "DOMAIN_ERROR", details: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.details = details or {}


class NotFoundError(MailDomainError):
    """Requested resource does not exist."""

    def __init__(self, resource: str, resource_id: str):
        super().__init__(
            f"{resource} '{resource_id}' not found",
            code="NOT_FOUND",
            details={"resource": resource, "id": resource_id},
        )


class ValidationError(MailDomainError):
    """Input validation failed."""

    def __init__(self, message: str, *, field: str | None = None):
        super().__init__(message, code="VALIDATION_ERROR", details={"field": field} if field else {})


class ConflictError(MailDomainError):
    """Resource already exists or state conflict."""

    def __init__(self, message: str = "Resource conflict"):
        super().__init__(message, code="CONFLICT")


class ConcurrencyError(MailDomainError):
    """Optimistic concurrency check failed (version mismatch)."""

    def __init__(self, resource: str, resource_id: str, expected_version: str):
        super().__init__(
            f"Concurrency conflict on {resource} '{resource_id}' — expected version '{expected_version}'",
            code="CONCURRENCY_ERROR",
            details={"resource": resource, "id": resource_id, "expected_version": expected_version},
        )


class PolicyDeniedError(MailDomainError):
    """Action denied by business policy (not auth — that's AuthorizationError)."""

    def __init__(self, message: str = "Action denied by policy"):
        super().__init__(message, code="POLICY_DENIED")


class ProviderUnavailableError(MailDomainError):
    """Upstream mail provider is unreachable or returned an error."""

    def __init__(self, provider: str, message: str = ""):
        super().__init__(
            f"Provider '{provider}' unavailable: {message}" if message else f"Provider '{provider}' unavailable",
            code="PROVIDER_UNAVAILABLE",
            details={"provider": provider},
        )


class RateLimitedError(MailDomainError):
    """Rate limit exceeded (upstream provider or internal)."""

    def __init__(self, retry_after_seconds: int | None = None):
        msg = "Rate limit exceeded"
        if retry_after_seconds:
            msg += f" — retry after {retry_after_seconds}s"
        super().__init__(msg, code="RATE_LIMITED", details={"retry_after_seconds": retry_after_seconds})


class RetryableDeliveryError(MailDomainError):
    """Send failed but can be retried."""

    def __init__(self, message_id: str, reason: str):
        super().__init__(
            f"Delivery failed (retryable) for message '{message_id}': {reason}",
            code="DELIVERY_RETRYABLE",
            details={"message_id": message_id, "reason": reason},
        )


class PermanentDeliveryError(MailDomainError):
    """Send failed permanently — do not retry."""

    def __init__(self, message_id: str, reason: str):
        super().__init__(
            f"Delivery failed (permanent) for message '{message_id}': {reason}",
            code="DELIVERY_PERMANENT",
            details={"message_id": message_id, "reason": reason},
        )


class AuthenticationError(MailDomainError):
    """Missing or invalid authentication credentials."""

    def __init__(self, message: str = "Authentication required"):
        super().__init__(message, code="UNAUTHENTICATED")


class AuthorizationError(MailDomainError):
    """Authenticated user lacks permission for the requested action."""

    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message, code="UNAUTHORIZED")
