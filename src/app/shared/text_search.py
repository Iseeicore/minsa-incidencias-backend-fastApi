from app.constants.cursor import LIKE_WILDCARDS


def escape_wildcards(text: str) -> str:
    return "".join(f"\\{character}" if character in LIKE_WILDCARDS else character for character in text)


def like_pattern(text: str | None) -> str | None:
    return f"%{escape_wildcards(text)}%" if text else None
