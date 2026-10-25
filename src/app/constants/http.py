ORIGIN_SCHEMES = ("http", "https")
CORS_ALLOWED_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE"]
CORS_ALLOWED_HEADERS = ["Content-Type"]
CORS_EXPOSED_HEADERS = ["Retry-After", "RateLimit-Limit", "RateLimit-Remaining"]
DOCS_PATH = "/docs"
REDOC_PATH = "/redoc"
OPENAPI_PATH = "/openapi.json"
JSON_MEDIA_TYPE = "application/json"
LOCATION_HEADER = "Location"
CONTENT_LENGTH_HEADER = "content-length"
CONTENT_SECURITY_POLICY_HEADER = "Content-Security-Policy"
SECURITY_HEADERS = {
    CONTENT_SECURITY_POLICY_HEADER: (
        "default-src 'self';base-uri 'self';font-src 'self' https: data:;form-action 'self';"
        "frame-ancestors 'self';img-src 'self' data:;object-src 'none';script-src 'self';"
        "script-src-attr 'none';style-src 'self' https: 'unsafe-inline';upgrade-insecure-requests"
    ),
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Origin-Agent-Cluster": "?1",
    "Referrer-Policy": "no-referrer",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "X-DNS-Prefetch-Control": "off",
    "X-Download-Options": "noopen",
    "X-Frame-Options": "SAMEORIGIN",
    "X-Permitted-Cross-Domain-Policies": "none",
    "X-XSS-Protection": "0",
    "Cache-Control": "no-store",
}
DOCUMENTATION_PATHS = frozenset({DOCS_PATH, REDOC_PATH, OPENAPI_PATH})
ORIGIN_HEADER = "origin"
FORWARDED_FOR_HEADER = "x-forwarded-for"
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
RATE_LIMIT_LIMIT_HEADER = "RateLimit-Limit"
RATE_LIMIT_REMAINING_HEADER = "RateLimit-Remaining"
RETRY_AFTER_HEADER = "Retry-After"
SET_COOKIE_HEADER = "set-cookie"
UNKNOWN_CLIENT = "desconocida"
TIMESTAMP_PRECISION = "milliseconds"
UTC_OFFSET_SUFFIX = "+00:00"
UTC_ZULU_SUFFIX = "Z"
EXAMPLE_TIMESTAMP = "2026-10-24T12:00:00.000Z"
VALIDATION_LOCATIONS = frozenset({"body", "query", "path", "header", "cookie"})
JSON_INVALID_ERROR_TYPE = "json_invalid"
EXAMPLE_PATH = "/recurso"
SESSION_STATE_KEY = "sesion"
