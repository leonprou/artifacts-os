---
created: 2026-05-11
id: n0010
kind: note
name: zero-shadow-org-92-list
---

## Issue

**Org:** Zero Shadow (92)
**Agent:** addressTransferActivityV2, rule 67127
**List:** a67b5d9f-8dab-4e5f-b4bb-6e201b09b99b (Heimdall/zeroShadow Investigations/Bitrefill)

The agent is configured with `chain: main_evm_chains` but the asset list only has addresses stored under the `ethereum` chain key in Redis. This means:

- ✅ Ethereum — alerts will fire (fixed recently)
- ❌ Arbitrum, Polygon, BSC, Optimism, Base, Avalanche — no alerts, because list lookups for those chains return empty

## Root Cause

The customer originally configured the list with the wrong chain prefix. They recently corrected it to `ethereum`, but did not add addresses for the other main EVM chains.

## Action Required

The customer needs to re-add addresses to the list for **all main EVM chains** (not just ethereum) if they want full `main_evm_chains` coverage.

## Broader Impact

**This is not unique to org 92.** Any customer using `addressTransferActivity` (or similar list-based agents) with a `main_evm_chains` rule but a list that only covers a subset of chains will silently miss alerts on uncovered chains. There is no validation or warning when a rule's chain scope is broader than the list's chain coverage.

### Suggested Platform Improvement

Add a validation check (at agent creation or config sync time) that warns when a rule references `main_evm_chains` (or other chain groups) but the monitored list has addresses only for a subset of those chains.

## Tags

#zero-shadow #org-92 #addressTransferActivity #list-mismatch #main-evm-chains #customer-issue