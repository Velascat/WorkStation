# Sync Topology — Manifest as Sync Authority

_Status: Design · 2026-05-23_

How operational and cognition data moves between machines in the ProtocolWarden
fleet, and which repo owns which part of that movement. This page is the
canonical cross-repo description; the public site mirrors a reader-facing
version under Architecture → Sync & Data Transport.

## Problem

Syncing was being pulled toward an `N×M` repo explosion — one repo per
*data-type* (operational data, cognition, CLI memory) per *project* (VF, CL, …).
That scales multiplicatively and leaves no single owner for "what syncs where."

## Decision

**Group by manifest, never by data-type.** The manifest is already the scoping
authority — it declares the ecosystem, hosts cognition, and anchors sessions.
"What data syncs, from where, to where, organized how in Syncthing" is one more
thing the manifest *declares*. That collapses `N×M` → `N`: one sync surface per
manifest. You add a declaration, not a repo.

Three layers, following the established public-mechanism / private-binding split:

```
  ┌─────────────────────────────────────────────────────────────┐
  │  MANIFEST  (declaration / contract)                           │
  │  PlatformManifest (public)   PrivateManifest, … (private)     │
  │  ─ declares data CLASSES + per-asset SYNC MODE + folder layout│
  │  ─ public manifest = structure only, no destinations/secrets  │
  └───────────────┬───────────────────────────┬──────────────────┘
                  │ shape                       │ identity + destinations
                  ▼                             ▼
  ┌───────────────────────────┐   ┌──────────────────────────────┐
  │ SYNC MECHANISM  (public)   │   │ PRIVATE BINDING               │
  │ ─ Syncthing schema /       │◄──┤ FleetMgmt: device IDs, keys,  │
  │   vocabulary               │   │   machine-link setup scripts  │
  │ ─ setup / backup / restore │   │ PrivateManifest: dest folders │
  │   orchestration + shims    │   │   per-machine routing         │
  │ ─ reads shape + binding,   │   └──────────────────────────────┘
  │   emits Syncthing config   │
  └───────────────┬────────────┘
                  │ invokes (shim contract)
                  ▼
  ┌───────────────────────────────────────────────────────────────┐
  │ PAYLOAD — backup/restore implementations live in EACH repo     │
  │ (only a repo knows how to dump/restore its own data)           │
  │ OC operational data, per-project cognition / CLI memory        │
  └───────────────────────────────────────────────────────────────┘
```

### Repos

| Repo | Role | Visibility |
|---|---|---|
| **Sync Mechanism** (new, extracted from SyncingSolution) | Syncthing schema/vocabulary; setup/backup/restore orchestration + shim contract | Public, configurable |
| **FleetMgmt** (SyncingSolution's remainder) | Machine identity keys, machine-link setup scripts | Private |
| **SSHInventory** | Index of SSH keys in use / rotated / retired | (distinct from FleetMgmt) |
| **PlatformManifest** / **PrivateManifest** / project manifests | Declare sync layout for their scope | Public / Private |
| Each participating repo (OC, executors, …) | Owns its backup/restore implementation behind the shim contract | per-repo |

`FleetMgmt` and `SSHInventory` are deliberately separate: FleetMgmt holds the
machine-identity keys and link-setup scripts; SSHInventory is only the index of
SSH keys and their lifecycle.

## Sync modes (vocabulary)

Defined in the public Sync Mechanism repo; chosen per-asset in the manifest.
Derived from the media-pipeline precedent:

| Mode | Meaning | Example |
|---|---|---|
| `copy` | Small things snapshotted into a `sync/` directory | OC configs, work items, campaigns |
| `in-repo` | Large things synced in place | VF models |
| `external` | Cannot live in-repo; synced from an out-of-tree location | OC plane backups |

## Key invariants

- **The manifest is the only place grouping is defined.** New data → a
  declaration in an existing manifest, never a new data-type repo.
- **A public manifest declares structure only** — never destinations, device
  IDs, or secrets. Those inject from the private layer (FleetMgmt +
  private manifests). This keeps "PlatformManifest is public" from leaking into
  "OC operational data is public."
- **Backup/restore implementations live in their own repo**, behind a shim
  contract owned by the public mechanism (same shape as the CL shim hooks the
  executors carry).
- **Payload location and sync mode are declared per-asset in the manifest**;
  the mechanism's vocabulary defines the legal modes.
- **Coverage is observable.** An asset with no declared sync mode is a
  detectable gap, not a silent omission — useful for auditing thin coverage
  (e.g. current OC).

## Open decision

Whether each repo's payload syncs from *inside* the repo or from a per-manifest
data home it is exported into is a churn-coupling call, made **per manifest via
its declared mode** — not globalized. The VF split (small → `copy`, large →
`in-repo`) is the working precedent.
