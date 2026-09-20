"""Query-string helpers."""

def parse_pairs(query):
    return [tuple(part.split("=", 1)) for part in query.split("&") if "=" in part]

def has_parameter(query, key):
    return any(name == key for name, _ in parse_pairs(query))

def drop_parameter(query, key):
    return "&".join(f"{name}={value}" for name, value in parse_pairs(query) if name != key)

def first_parameter(query, key, default=None):
    return next((value for name, value in parse_pairs(query) if name == key), default)

def add_parameter(query, key, value):
    separator = "&" if query else ""
    return f"{query}{separator}{key}={value}"

def replace_parameter(query, key, value):
    """Replace all copies of key, or append it if key is absent."""
    pairs = parse_pairs(query)
    found = False
    output = []
    for name, old_value in pairs:
        if name == key:
            if not found:
                output.append((key, value))
                found = True
        else:
            output.append((name, old_value))
    return "&".join(f"{name}={item}" for name, item in output)
