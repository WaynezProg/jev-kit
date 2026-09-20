"""Duration and timestamp helpers."""

def seconds_to_minutes(seconds):
    return seconds / 60

def format_duration(seconds):
    minutes, remainder = divmod(int(seconds), 60)
    return f"{minutes}:{remainder:02d}"

def is_weekend(weekday):
    return weekday >= 5

def add_seconds(timestamp, seconds):
    return timestamp + seconds

def retry_delays(attempts, base_seconds):
    """Produce exponential retry delays, capped by the supplied base policy."""
    if attempts < 0 or base_seconds < 0:
        raise ValueError("attempts and base_seconds must be non-negative")
    return [base_seconds * (2 ** attempt) for attempt in range(attempts + 1)]

def elapsed(start, end):
    return end - start
