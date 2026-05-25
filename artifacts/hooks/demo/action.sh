#!/bin/sh
# demo hook action — records that the hook was fired.
# Used by the integration test to verify end-to-end hook execution.
#
# Environment variables set by the hook runner:
#   ARTIFACT_EVENT  — event type (e.g. "artifact.created")
#   ARTIFACT_KIND   — artifact kind
#   ARTIFACT_ID     — artifact id/slug
#
# Writes a sentinel file so tests can assert the hook ran.

SENTINEL="${VAULT_ROOT:-.}/.demo-hook-fired"
printf '%s %s %s\n' "${ARTIFACT_EVENT}" "${ARTIFACT_KIND}" "${ARTIFACT_ID}" >> "${SENTINEL}"
