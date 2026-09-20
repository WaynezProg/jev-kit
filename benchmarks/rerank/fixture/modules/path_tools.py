"""Portable path-string helpers; these do not touch the filesystem."""

def extension(path):
    name = path.rsplit("/", 1)[-1]
    return name.rsplit(".", 1)[-1] if "." in name else ""

def parent_path(path):
    return path.rsplit("/", 1)[0] if "/" in path else ""

def join_url_path(base, child):
    return base.rstrip("/") + "/" + child.lstrip("/")

def strip_leading_slash(path):
    return path.lstrip("/")

def relative_path(path, root):
    """Return path under root, rejecting siblings that merely share its prefix."""
    clean_root = root.rstrip("/")
    if path == clean_root:
        return ""
    if path.startswith(clean_root):
        return path[len(clean_root):].lstrip("/")
    raise ValueError("path is outside root")

def filename(path):
    return path.rsplit("/", 1)[-1]
