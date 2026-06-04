# ADR 0005 — Sync-spec declarations belong in manifests, not in the fleet executor

_Status: Accepted · 2026-05-27_

## Context

ADR 0004 established that the **manifest is the sync authority**: grouping is
defined once per manifest, never per data-type. The invariant reads:

> *The manifest is the only place grouping is defined.*

The initial implementation landed a `sync-spec.yaml` inside the private fleet
executor repo — rather than in the manifests. This worked for a single-machine
bring-up but violates the declared invariant: the fleet executor is the
*executor*, not the *authority*.

The misplacement has two concrete consequences:

1. **Scope leak.** A private executor repo is declaring assets that belong to
   different scopes: `platform-config`/`platform-backups` are public-platform
   concerns (PD + OC); private-tenant assets are private-tenant concerns. Mixing
   them in one file in one private repo collapses the public/private boundary the
   manifest design was built to enforce.

2. **Single-executor coupling.** The declarations are only readable by the fleet
   executor. A second executor (or a coverage audit tool) would need to read from
   the fleet executor's private tree, which is wrong.

## Decision

**Move sync-spec declarations into the manifests that own the assets:**

- **PlatformManifest** declares `platform-config` and `platform-backups`
  (public-platform assets owned by PD + OC).
- **The private-manifest repo** declares the private-tenant asset groups
  (config, assets, models, backups).

Each manifest gains a `sync_spec:` top-level block in its YAML:

```yaml
# PlatformManifest/src/platform_manifest/data/platform_manifest.yaml
sync_spec:
  schema_version: "1.0"
  assets:
    - id: platform-config
      data_class: operational
      mode: copy
      source: PlatformDeployment + OperationsCenter gitignored config/secrets
      folder: platform-config
    - id: platform-backups
      data_class: operational
      mode: external
      source: out-of-tree platform backup archives
      folder: platform-backups
```

```yaml
# <private-manifest-repo>/manifests/<tenant>/private_manifest.yaml
sync_spec:
  schema_version: "1.0"
  assets:
    - id: <tenant>-config
      data_class: operational
      mode: copy
      source: tenant .env + config/
      folder: <tenant>-config
    - id: <tenant>-assets
      data_class: asset
      mode: copy
      source: tenant assets/
      folder: <tenant>-assets
    - id: <tenant>-models
      data_class: asset
      mode: in-repo
      source: tenant models/
      folder: <tenant>-models
    - id: <tenant>-backups
      data_class: operational
      mode: copy
      source: tenant backup/
      folder: <tenant>-backups
```

**The fleet executor** becomes a pure executor:

- Removes `sync-spec.yaml` from its own tree.
- Loads specs from whichever manifest(s) it is configured to serve (via a
  `manifest_paths:` config key or by discovering registered manifests from
  RepoGraph).
- The private `devices.yaml` binding stays in the fleet executor — it is
  machine/device routing, not asset declaration.

**SyncMechanism** parses `sync_spec:` blocks from manifest YAMLs using the
existing `SyncSpec` / `SyncAsset` models — no new schema needed.

## Consequences

- Adding a new synced asset to the platform is a manifest change (reviewed,
  visible, auditable) rather than a private fleet-executor change.
- Public-platform sync coverage is readable without cloning any private repo.
- The fleet executor can serve multiple manifests (public + private) from one
  executor by loading each manifest's declared spec — the N×M collapse ADR 0004
  promised is now fully realised.
- The `scope:` field in the current `sync-spec.yaml` is dropped; scope is
  implicit in which manifest the block appears in.

## Migration

1. Add `sync_spec:` blocks to PM and PrivM YAMLs.
2. Update PM and PrivM schema validators to accept the new top-level key.
3. Update the fleet executor's `sync_cli.py` / `backup_cli.py` to load specs
   from manifest paths rather than a local file (SyncMechanism loader already
   handles YAML dicts — the only change is where the dict comes from).
4. Delete the fleet executor's `sync-spec.yaml` once step 3 is validated.

Steps 1–4 are sequenced work; the current `sync-spec.yaml` remains the
operational source of truth until step 4 completes.

## Invariants (restated)

- The manifest is the only place sync grouping is defined.
- A public manifest declares structure only; no device IDs, folder paths, or
  secrets.
- The fleet executor reads specs, never authors them.
- Coverage is observable — a manifest asset with no declared sync mode is a
  detectable gap.
