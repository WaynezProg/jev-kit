"""Collection helpers."""

def unique_in_order(values):
    return list(dict.fromkeys(values))

def chunks(values, size):
    return [values[index:index + size] for index in range(0, len(values), size)]

def count_by(values):
    counts = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return counts

def flatten(groups):
    return [item for group in groups for item in group]

def merge_defaults(defaults, overrides):
    """Merge mappings; None means the caller left that setting unspecified."""
    result = dict(defaults)
    result.update(overrides)
    return result

def pairs(values):
    return list(zip(values[::2], values[1::2]))
