from enum import StrEnum


class ErrorCategory(StrEnum):
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    BUSINESS_RULE = "business_rule"
    FORBIDDEN = "forbidden"
    VALIDATION = "validation"
    UNAUTHENTICATED = "unauthenticated"
    PAYLOAD_TOO_LARGE = "payload_too_large"
    RATE_LIMITED = "rate_limited"
    NOT_IMPLEMENTED = "not_implemented"
    UNAVAILABLE = "unavailable"
    INTERNAL = "internal"
