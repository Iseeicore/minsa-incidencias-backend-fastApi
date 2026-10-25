from enum import StrEnum


class ErrorCategory(StrEnum):
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    BUSINESS_RULE = "business_rule"
    FORBIDDEN = "forbidden"
    VALIDATION = "validation"
    UNAVAILABLE = "unavailable"
    TIMEOUT = "timeout"
    INTERNAL = "internal"
