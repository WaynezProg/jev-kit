"""Dictionary record helpers."""

def get_nested(record, keys, default=None):
    current = record
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current

def pick(record, keys):
    return {key: record[key] for key in keys if key in record}

def omit(record, keys):
    return {key: value for key, value in record.items() if key not in keys}

def required(record, key):
    if key not in record:
        raise KeyError(key)
    return record[key]

def coerce_flag(value):
    """Coerce common textual flags without accepting ambiguous arbitrary strings."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.lower()
        if normalized in {"true", "yes", "1", "on"}:
            return True
        if normalized in {"false", "no", "0", "off"}:
            return False
    raise ValueError("not a boolean flag")

def rename_key(record, old, new):
    result = dict(record)
    if old in result:
        result[new] = result.pop(old)
    return result
