# ADR 0004 — Sync topology: manifest as sync authority

_Status: Accepted · 2026-05-23_

## Context

Fleet data movement (operational data, cognition, CLI memory across machines)
was drifting toward an `N×M` repo explosion — one repo per *data-type* per
*project*. No single thing owned "what syncs where," and the scope felt like it
was creeping with every new data class.

Separately, today's `SyncingSolution` repo conflates four concerns: machine
identity keys (in commit history, so permanently private), syncthing setup
tooling, fleet state, and project data assets.

## Decision

**Group by manifest, never by data-type.** The manifest is already the scoping
authority (declares the ecosystem, hosts cognition, anchors sessions); the sync
layout becomes one more thing it *declares*. This collapses `N×M` → `N`: one
sync surface per manifest. New data is a declaration, not a new repo.

Three layers, following the established public-mechanism / private-binding split:

1. **Manifest (declaration).** Declares data classes, per-asset sync mode, and
   folder layout. A *public* manifest declares structure only — never
   destinations, device IDs, or secrets.
2. **Sync Mechanism (public, new repo).** Extracted from `SyncingSolution`.
   Owns the Syncthing schema/vocabulary and the setup/backup/restore
   orchestration + shim contract. Reads manifest shape + private binding, emits
   Syncthing config.
3. **Private binding.** `FleetMgmt` (the remainder of `SyncingSolution` —
   permanently private due to keys in history) supplies device IDs, keys, and
   machine-link setup. Private manifests supply destination folders / routing.

**Backup/restore implementations live in each participating repo**, behind the
shim contract the mechanism owns — only a repo knows how to dump/restore its own
data (same shape as the CL shim hooks the executors carry).

**Sync modes** (vocabulary in the mechanism repo, chosen per-asset in the
manifest), from the media-pipeline precedent: *copy* (small → snapshot into a
`sync/` dir), *in-repo* (large, e.g. models), *external* (cannot live in-repo,
e.g. OC plane backups).

`FleetMgmt` and `SSHInventory` stay distinct: FleetMgmt = machine identity keys
+ link-setup scripts; SSHInventory = index of SSH keys and their lifecycle.

Full model and diagram: [`system/sync-topology.md`](../system/sync-topology.md).
Public reader-facing mirror lives on the Pages site under Architecture →
Sync & Data Transport.

## Considered alternatives

- **One repo per data-type per project** (operational / cognition / memory ×
  each project). Rejected: `N×M` explosion, no single owner of grouping.
- **One global rule for payload home.** Rejected: churn coupling differs per
  asset; the mode is declared per-asset instead.
- **Keep SyncingSolution as one repo.** Rejected: it mixes permanently-private
  keys with tooling that should be public and configurable.

## Open decision

Whether a repo's payload syncs from inside the repo or from a per-manifest data
home it is exported into is a churn-coupling call, made per manifest via its
declared mode — not globalized.

## Invariants

- The manifest is the only place grouping is defined.
- A public manifest declares structure only; the private layer injects
  destinations, device IDs, and secrets.
- Backup/restore implementations live per-repo behind the mechanism's shim
  contract.
- Coverage is observable — an asset with no declared sync mode is a detectable
  gap.
