from artifacts_os.core import frontmatter


def test_round_trip() -> None:
    meta = {"kind": "task", "id": "t0001", "tags": ["a", "b"]}
    body = "# Title\n\nSome body text."
    text = frontmatter.dump(meta, body)
    parsed_meta, parsed_body = frontmatter.parse(text)
    assert parsed_meta == meta
    assert parsed_body == body


def test_no_frontmatter() -> None:
    text = "Just a plain markdown file.\n"
    meta, body = frontmatter.parse(text)
    assert meta == {}
    assert body == text.strip() or body == text or body.startswith("Just")


def test_preserves_pyyaml_types() -> None:
    text = """---
kind: task
count: 42
tags:
  - a
  - b
flag: true
---
body
"""
    meta, _ = frontmatter.parse(text)
    assert meta["count"] == 42
    assert meta["tags"] == ["a", "b"]
    assert meta["flag"] is True
