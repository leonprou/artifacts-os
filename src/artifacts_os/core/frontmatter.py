"""Frontmatter parsing and serialization (python-frontmatter wrapper).

Spec: s2060-artifacts-os-architecture § frontmatter.py
"""

import frontmatter as _fm


def parse(text: str) -> tuple[dict, str]:
    """Parse markdown text into (frontmatter_dict, body_str).

    Returns ({}, text) if no frontmatter block is present.
    """
    post = _fm.loads(text)
    return dict(post.metadata), post.content


def dump(meta: dict, body: str) -> str:
    """Serialize (frontmatter_dict, body) back to a markdown string."""
    post = _fm.Post(body, **meta)
    return _fm.dumps(post)
