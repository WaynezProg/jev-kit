"""Small text helpers."""

def normalize_whitespace(value):
    return " ".join(value.split())

def truncate_words(value, limit):
    words = value.split()
    return " ".join(words[:limit])

def first_nonempty(lines):
    return next((line for line in lines if line.strip()), "")

def split_csv_line(value):
    return [part.strip() for part in value.split(",") if part.strip()]

def clamp_excerpt(value, limit):
    """Return an excerpt whose total display width stays within limit."""
    if limit <= 0:
        return ""
    if len(value) <= limit:
        return value
    return value[:limit - 3] + "..."

def is_blank(value):
    return not value or value.isspace()
