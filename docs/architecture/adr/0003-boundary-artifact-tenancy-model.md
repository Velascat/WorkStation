# ADR 0003 — Boundary artifact tenancy model

_Status: Accepted · 2026-05-22_

## Context

The boundary artifact pipeline (private-manifest repo → public-repo CI) was finished
end-to-end on 2026-05-22. Three things became "set in stone" once consumers
were configured:

1. **One PAT, one URL, one secret pair per consuming repo.** GitHub Actions
   secrets are flat key/value strings; there is no native list type. Every
   consuming repo currently holds exactly two secrets:
   `PRIVATEMANIFEST_READ_TOKEN` and `REPOGRAPH_BOUNDARY_ARTIFACT_FILE`.
2. **The boundary artifact is generated from `graph/repos.yaml` and
   `graph/edges.yaml`** at the private-manifest repo root — a single flat
   graph instance. Per-project files under `manifests/<project>/` are
   organizational metadata, not the source of truth for boundary generation.
3. **ContextLifecycle anchors sessions at the repo level**
   (`cl session start <private-manifest-repo>`) and writes cognition under that
   anchor's `.context/sessions/<sid>/`. There is no per-project sub-anchor.

This ADR records the deliberate decision to ship single-tenant **now**, the
known limitations of doing so, and the migration path to a per-project /
per-tenant model when it becomes necessary.

## Decision

**Accept the single-tenant model for the current era.** All private projects
share one private-manifest repo, one boundary artifact, one PAT, and one
cognition anchor. The boundary artifact contains the **union** of every
private name across every project hosted in the private-manifest repo. Every consuming
repo audits against the full union.

## Consequences

### Positive

- **Operational simplicity.** Two secrets per consumer repo, one PAT to
  rotate annually, one URL to update if the artifact ever moves.
- **No cross-repo orchestration.** The pipeline has zero moving parts beyond
  the publish-boundary workflow and the materialize step in each consumer.
- **Atomic freshness.** Every CI run fetches the current artifact from
  the private manifest's `main` branch — no background sync, no per-tenant rotation.

### Negative / Limitations

- **No cross-tenant isolation.** If a second tenant's private overlay is
  added to the private-manifest repo, all consumer contributors gain visibility into
  every tenant's forbidden names. This is a real disclosure boundary that
  cannot be re-tightened without splitting the private-manifest repo.
- **CL anchoring is flat.** Sessions touching private code anchor at
  the private-manifest repo, not at the project hosted within. Cognition for
  BazCorp, FooCorp, and BarCorp would land under the same
  `.context/sessions/` tree, distinguished only by capsule metadata. The
  long-term goal (per-project cognition hosting, e.g. inside a
  hypothetical `manifests/bazcorp/.context/`) is incompatible with the
  current single-anchor implementation.
- **Audit scope is global.** Every consumer audits against the full
  forbidden_names list, including names for projects it has nothing to do
  with. This is harmless today (false-positive leakage of private names
  is rare) but coupling-wise it spreads.

### Neutral

- **The schema already supports multi-artifact.**
  `BoundaryDisclosureArtifact` carries `source_graph_id` and
  `source_ref_or_commit` fields. RepoGraph's `build_boundary_artifact()`
  can be called with different source_graph_ids for different graphs.
  Nothing in the artifact format requires single-tenancy.

## Migration path to per-tenant / per-project

When the constraints above start to bind, the migration is:

1. **Split the private-manifest repo by tenant.** Each tenant (or major project)
   becomes its own private repo: `<private-manifest>-BazCorp`,
   `<private-manifest>-FooCorp`. Each runs its own publish-boundary workflow
   producing its own artifact at its own raw URL.

2. **Custodian gains multi-artifact support.** The detector accepts
   `boundary_artifact_files: [path1, path2, ...]` (plural) in config and
   `REPOGRAPH_BOUNDARY_ARTIFACT_FILES` (plural, comma-separated paths) in
   env. Forbidden_names are unioned across all artifacts; provenance is
   tracked per-source. *Implemented in Custodian PR #XXX as part of this
   ADR's preparatory work — see step 4 in the threat model section of
   `PlatformManifest/docs/forking-guide.md`.*

3. **Consumer repos receive per-tenant secret pairs.** Each consumer that
   needs visibility into a tenant adds a secret pair for that tenant:
   `BOUNDARY_VIDEOFOUNDRY_URL` / `BOUNDARY_VIDEOFOUNDRY_TOKEN`,
   `BOUNDARY_FOOCORP_URL` / `BOUNDARY_FOOCORP_TOKEN`, etc. The materialize
   step in each workflow fetches every configured artifact, writes to
   temp files, and passes the comma-joined paths to Custodian.

4. **ContextLifecycle adds per-project anchoring.** The CLI accepts a
   `--project <name>` argument and resolves the anchor to
   `<private-manifest-repo>/.context/projects/<name>/sessions/<sid>/` instead
   of the flat `<private-manifest-repo>/.context/sessions/<sid>/`. This is a CL
   schema change, not a downstream consumer change. ([[adr-0002]])

5. **Bootstrap tooling is updated.** The `bootstrap-boundary-secrets.sh`
   script (in PlatformManifest) is extended to accept multiple
   `--tenant <name> --url <url> --token-file <path>` triples in one
   invocation.

The total cost of migration is bounded: it's a single Custodian PR
(detector + env parsing), per-consumer workflow updates (mechanical), and
a CL schema bump. The schema and generator already support it; nothing
needs to be re-architected.

## Why not migrate now?

Three reasons:

1. **There is exactly one tenant.** Building multi-tenancy speculatively
   means designing against unknown future shape. Each tenant has slightly
   different needs (which projects audit against which graphs) that are
   easier to design correctly when there is a concrete second tenant.

2. **The Custodian change is small.** ~50 LOC in
   `audit_kit/detectors/boundary.py`. We can pay it any time within a
   single PR, including reactively when the second tenant arrives.

3. **The CL anchoring change is the actually-load-bearing piece** and is
   already a known item on the platform roadmap (ADR 0002 Phase 4+). It
   makes no sense to ship multi-tenant boundary artifacts before CL
   supports per-project anchoring — the two changes belong together.

## Related work

- ADR 0002 — Work order: manifest as cognition host (CL anchoring foundation)
- `PlatformManifest/docs/forking-guide.md` — operator-level setup tutorial
- `Custodian/src/custodian/audit_kit/detectors/boundary.py` — current
  single-artifact detector implementation
- `<private-manifest-repo>/scripts/export_private_repo_names.py` — current
  single-graph generator entry point

## Decision log

- **2026-05-22 — Initial decision.** Single-tenant accepted. Migration
  path documented above is the binding plan for when a second tenant
  appears or per-project cognition becomes required.
