---
created: 2026-06-11
id: t0205
kind: task
name: core-discover-resolve-wikilink-true
owner: user
priority: low
status: backlog
type: feature
---

# core.discover.resolve: wikilink=True to auto-strip [[...]] wrappers

## Why

Filed from openstation (spec ref: open-station
`s2068-openstation-module-system` § 13.3). Frontmatter references
are stored as wikilinks (`"[[t0042-name]]"`); every consumer strips
the brackets before calling resolve. A `wikilink=True` kwarg (or
always-on tolerant parsing) removes ~5 LOC of wrapper per consumer.

## Requirements

- `resolve(reg, ref, wikilink=True)` accepts `"[[stem]]"` and
  resolves as if passed `"stem"`. A tolerant default (auto-strip
  always) is also acceptable.

## Verification

- [ ] resolve works for both `"t0042-name"` and `"[[t0042-name]]"`
      forms.
