from enum import StrEnum


class LogLevel(StrEnum):
    FATAL = "fatal"
    ERROR = "error"
    WARN = "warn"
    INFO = "info"
    DEBUG = "debug"
    TRACE = "trace"
    SILENT = "silent"
