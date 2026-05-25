---
kind: hook
name: demo
host: artifacts-os
matcher:
  event: artifact.created
action:
  type: shell
  command: ./action.sh
phase: post
blocking: false
timeout: 30
---

# Demo Hook

This is a demo hook bundled with artifacts-os to demonstrate the
`kind: hook` artbook distribution mechanism (s0032 §8.3).

It fires after every `artifact.created` event and writes the event
payload to `.demo-hook-fired` in the vault root.

This hook is **not active by default** — run
`artifacts hooks promote demo` to activate it.
