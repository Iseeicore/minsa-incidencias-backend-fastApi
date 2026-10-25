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
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Cache-Control": "no-store",
    "Referrer-Policy": "no-referrer",
    "X-Frame-Options": "DENY",
}
TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
EXAMPLE_TIMESTAMP = "2026-10-24T12:00:00Z"
EXAMPLE_PATH = "/recurso"
