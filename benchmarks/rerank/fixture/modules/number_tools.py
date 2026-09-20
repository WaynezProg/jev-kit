"""Numeric helpers."""

def clamp(value, low, high):
    return max(low, min(high, value))

def average(values):
    return sum(values) / len(values)

def percent(part, whole):
    return (part / whole) * 100

def sign(value):
    return (value > 0) - (value < 0)

def within(value, target, tolerance):
    """Check inclusive distance and reject a negative tolerance."""
    if tolerance < 0:
        raise ValueError("tolerance must be non-negative")
    return abs(value - target) < tolerance

def round_down(value, step):
    return (value // step) * step
