# Work Order — Manifest as Cognition Host (CL / RepoGraph / Manifest contract split)

_Status: Draft · 2026-05-22_
_Design rationale: `ContextLifecycle/.console/log.md` 2026-05-22 · `PlatformManifest/.console/log.md` 2026-05-22_

---

## Goal

Move durable cognition state out of consumer repos and into the anchoring **manifest** (PlatformManifest or the private-manifest repo). Establish a three-way contract:

- **ContextLifecycle (CL)** — schema + I/O + policy enforcement; ships a Python CLI from its own `.venv/`.
- **RepoGraph** — repo↔manifest visibility/authorization; gates every cognition write against the active session anchor's scope.
- **Manifest** — session anchor + `.context/` host; durable cognition lives here, not in consumer repos.
- **Consumer repos** (executors, etc.) — carry a ~1-line shim hook; no `.context/` data, no CL imports.

Sessions are anchored explicitly at launch (`cl session start <manifest>` → `CL_ANCHOR` env var). Hard error if anchor unset. Mis-selects are caught by RepoGraph at write time.

---

## Phase 0 — Spec Lockdown (Prerequisite)

Lock these before writing code. Document each decision in this work order under "Locked Specs" once made.

- [ ] **P0.1** — Env var name: `CL_ANCHOR` vs alternative. Confirm naming.
- [ ] **P0.2** — `cl session start` CLI signature. Positional manifest arg? `--json` for agent consumers? Subshell-spawn vs `eval $(cl session start ...)` pattern? Behavior when called with no arg (RepoGraph-inferred default + hard error on ambiguous)?
- [ ] **P0.3** — Shim's `cl` resolution: `CL_HOME` env var → `$CL_HOME/.venv/bin/cl`? PATH symlink? Both with fallback?
- [ ] **P0.4** — RepoGraph authorization schema: how PM and PrivM declare repo membership in a form RepoGraph can read for visibility checks. Extend existing repo-membership data or new field?
- [ ] **P0.5** — Manifest `.context/` layout when hosting concurrent loops across multiple consumer repos: capsule namespacing (per-repo subdirs? flat with `repo:` field? per-loop session id?).
- [ ] **P0.6** — Standalone-repo failure mode: confirm hard error (no fallback to local `.context/`).

**DoD:** All six specs answered in this document. Code work does not start until DoD is met.

---

## Phase 1 — CL CLI + Hook Logic Port

Port the existing `pre_tool_use.sh` (330 lines) and `stop.sh` (116 lines) policy logic from bash to Python. Ship as `cl` CLI installable from CL's own `.venv/`.

- [ ] **P1.1** — `cl` CLI skeleton (`click` or `typer`); subcommands `hook`, `session`. Reads `CL_ANCHOR` env var; hard error if missing.
- [ ] **P1.2** — `cl hook pre_tool_use` — port all checks from bash: `require_capsule`, lease expiry, pre_write (forbidden_paths / allowed_paths / mutation_policy), pre_spawn (max_subagents, high_parallelism, subagent_heavy), context_risk flags (long_lived_session, checkpoint_stale, reload_scope_too_large). Reads YAML from anchor manifest's `.context/`, not local repo.
- [ ] **P1.3** — `cl hook stop` — port checkpoint-on-stop enforcement.
- [ ] **P1.4** — `cl session start <manifest>` — sets/emits anchor; validates manifest exists and is well-formed; resolves manifest path.
- [ ] **P1.5** — Tests for every block/warn branch (parity with bash hook behavior).
- [ ] **P1.6** — Tagged CL release.

**DoD:** `cl hook` produces identical allow/block/warn decisions to the current bash hooks given equivalent YAML state. `cl session start` cleanly sets anchor. Installable from CL's `.venv/`.

---

## Phase 2 — RepoGraph Visibility Enforcement

Add the authorization check API RepoGraph exposes to CL. **RepoGraph owns manifest discovery, parsing, topology, and authorization logic. CL is a pure consumer** — it passes only the active anchor path and the target repo name; it does not configure RepoGraph's view of the ecosystem, does not pass `root_dir`, does not parse YAML, does not know that other manifests exist.

### Boundary discipline (load-bearing)

| Concern | Owner |
|---|---|
| What manifests exist in the ecosystem | **RepoGraph** |
| Parsing manifest YAML | **RepoGraph** |
| Authorization logic (3-clause check) | **RepoGraph** |
| Which manifest is anchoring *this session* | CL (reads `CL_ANCHOR`) |
| Enforcing the authorization result on a write | CL |

### Tasks

- [ ] **P2.0** — RepoGraph: per-machine manifest registry. RepoGraph owns its own config of "which manifests exist on this machine." Default location: `${XDG_CONFIG_HOME:-~/.config}/repograph/manifests.yaml`. Schema:
  ```yaml
  manifests:
    - /home/dev/Documents/GitHub/PlatformManifest
    - <private-manifest-repo>
  ```
  Registry is per-machine config (not committed to any repo) — manifest *paths* are machine-local; what's tracked in git is manifest *contents*.

- [ ] **P2.1** — RepoGraph CLI for registry management:
  ```
  repograph manifest add <path>      # register a manifest
  repograph manifest list            # show known manifests
  repograph manifest remove <path>   # unregister
  repograph manifest validate        # re-check exclusive ownership + also_hosts refs
  ```

- [ ] **P2.2** — RepoGraph: `RepoGraph()` self-initializes from its own registry (P2.0). On init, loads every registered manifest's YAML, builds the topology index (repo → owner manifest, manifest → `also_hosts` grants), runs load-time validations. No `root_dir`, env var, or path argument from CL.

- [ ] **P2.3** — RepoGraph: `can_anchor_host(anchor_path: Path, repo_name: str) → (bool, str)` API. Three-clause authorization (owner / public-source / explicit `also_hosts` grant). Anchor path must resolve to a known registered manifest; unknown anchor → block with clear error.

- [ ] **P2.4** — RepoGraph: `find_anchor_for_path(cwd: Path) → Path | None` API for `cl session start` no-arg inference (P0.2). Walks the registry to find which manifest claims the given cwd (via its `repos:` list). Returns unique match, raises on ambiguous, returns None if no claim.

- [ ] **P2.5** — RepoGraph load-time validations: exactly-one-owner per repo (dual claim across manifests = fatal); `also_hosts` entries reference real (manifest, repo) pairs (bad ref = fatal); warn on redundant `also_hosts` grants pointing at public-owned repos.

- [ ] **P2.6** — CL: on every write to `.context/`, call `RepoGraph().can_anchor_host(anchor_path, repo)` for each repo involved in the capsule/checkpoint/handoff. Hard error if any returns false; error message names the owning manifest and the failing clause. CL imports RepoGraph as a Python package; in-process call, no IPC.

- [ ] **P2.7** — Tests covering each authorization clause: (a) anchor owns repo → allowed; (b) repo in public manifest → allowed regardless of anchor scope; (c) cross-private with `also_hosts` grant → allowed; (d) cross-private without grant → blocked; (e) public anchor touching private-owned repo → blocked; (f) unregistered repo → blocked; (g) unknown anchor path → blocked. Each block path verifies the reason string is operator-actionable. Plus tests for registry CLI and `find_anchor_for_path` (unique / ambiguous / none).

- [ ] **P2.8** — Tagged RepoGraph release; CL pin bumped.

**DoD:** A session anchored to PM cannot write a capsule that references a private repo. Failure mode is a hard error with the operator told exactly which repo and why. CL has zero knowledge of manifest paths beyond what's set in `CL_ANCHOR`; all topology questions go through RepoGraph.

---

## Phase 3 — Manifest `.context/` Host

Add the `.context/` skeleton to PM and PrivM. Document the layout (per P0.5). Migrate existing cognition state from OC to the appropriate manifest.

- [ ] **P3.1** — PM: `.context/{active,checkpoints,handoffs,templates}/` + `config.yaml`. Public scope only.
- [ ] **P3.2** — PrivM: same layout. Private scope.
- [ ] **P3.3** — Document `.context/` layout in `PlatformManifest/docs/` and the private-manifest repo's `docs/`.
- [ ] **P3.4** — Migration: move OC's existing `.context/` contents to PM (public-only) or PrivM (any private). Preserve any active capsules / recent checkpoints.
- [ ] **P3.5** — OC: remove `.context/` directory; update `OperationsCenter/CLAUDE.md` to point to anchoring manifest pattern instead of local `.context/`.

**DoD:** PM and PrivM each have a populated `.context/` skeleton. OC's local `.context/` is gone. No cognition data is lost in migration.

---

## Phase 4 — OC Dispatcher CL Integration

OC dispatcher wraps each executor call with CL's pre/around/post hooks. Lineage passed as parameter, not constructor arg (per design discussion).

- [ ] **P4.1** — OC dispatcher: import CL Python API (in-process, not subprocess) for the pre/around/post wrap.
- [ ] **P4.2** — `cl.hydrate(lineage_id, work_item)` before dispatch; `cl.capture(lineage_id, result)` after.
- [ ] **P4.3** — Optional `cl.peek(work_item)` available to router for read-only context inspection (do not wire into routing logic yet).
- [ ] **P4.4** — Tests: dispatch produces correct CL writes to anchor manifest's `.context/`; hydrate reads from correct location.

**DoD:** OC dispatcher runs through CL middleware on every executor call. Anchor's `.context/` shows the resulting capsule/checkpoint writes.

---

## Phase 5 — Executor Shim + Revert

Strip CLP scaffolding from TE, DE, CE. Replace with a 1-line shim per hook. Confirm executor code has zero CL imports (it doesn't today; keep it that way).

- [ ] **P5.1** — TE: delete `.context/` (config + templates). Delete `.claude/hooks/pre_tool_use.sh` and `stop.sh`. Replace with shim hooks calling `cl hook <event>`.
- [ ] **P5.2** — DE: same.
- [ ] **P5.3** — CE: same.
- [ ] **P5.4** — Confirm no `from ContextLifecycle` or equivalent import in TE/DE/CE source. Grep + CI check.
- [ ] **P5.5** — Each executor's `CLAUDE.md`: remove "Cognition Lifecycle" section pointing to local `.context/`; replace with note that cognition is hosted by the anchoring manifest.

**DoD:** TE/DE/CE each carry only the shim. Standalone Claude Code session in any executor repo fails closed (hard error: no anchor set) unless an operator explicitly anchors via `cl session start`.

---

## Phase 6 — Cleanup + Documentation

- [ ] **P6.1** — Update or supersede any ADR that assumed per-repo `.context/` (incl. OC ADR 0005 if it references local cognition).
- [ ] **P6.2** — Update `PlatformManifest/platform_manifest.yaml` `context_lifecycle` participation metadata: manifest now `cognition_host=true`; consumer repos `cognition_host=false, shim_only=true`.
- [ ] **P6.3** — Write ADR companion to this work order (manifest as repo-type, contract split, info-flow rule) if not already paired.
- [ ] **P6.4** — Update memory: manifest concept locked, PD owns shared docs, executor revert complete.

**DoD:** Docs, manifest metadata, and memory all reflect the new architecture. No stale references to per-repo `.context/` in CLAUDE.md files or ADRs.

---

## Locked Specs

_Locked 2026-05-22._

### P0.1 — Session anchor env var

- **Name:** `CL_ANCHOR`
- **Value:** absolute path to the anchoring manifest's repo root (e.g. `/home/dev/Documents/GitHub/PlatformManifest`).
- **Companion:** `CL_SESSION_ID` — set alongside `CL_ANCHOR` at session start; identifies the per-session subdir under `.context/sessions/` (see P0.5). Format: `s-<YYYY-MM-DD>-<short-rand>` (e.g. `s-2026-05-22-a1b2`).
- `cl session start` resolves a manifest name or path argument into the absolute path; hooks read the path verbatim, no name→path lookup at hook time.

### P0.2 — `cl session start` CLI signature

Default invocation is **eval-style** — emits shell `export` lines on stdout so `eval $(cl session start <manifest>)` sets the env in the caller's shell. Agents use `--json` and inject into subprocess env.

```
cl session start [MANIFEST] [--json] [--shell] [--require-clean]

Positional:
  MANIFEST    Manifest name (e.g. PlatformManifest) or absolute path.
              If omitted, ask RepoGraph to infer from cwd; hard error
              if ambiguous (>1 candidate) or unresolvable (0 candidates).

Options:
  --json      Emit anchor info as JSON to stdout (for agent consumers):
              {"anchor": "<path>", "session_id": "<id>", "manifest_name": "..."}
              Mutually exclusive with --shell.
  --shell     Spawn a new subshell with CL_ANCHOR + CL_SESSION_ID set;
              session ends when shell exits. Mutually exclusive with --json.
  --require-clean
              Fail if anchor manifest has uncommitted changes (avoid
              writing cognition into a dirty manifest state).

Exit codes:
  0  anchor set successfully
  1  manifest not found / unresolvable
  2  ambiguous inference (no MANIFEST arg, RepoGraph found multiple)
  3  anchor manifest missing prerequisites (no .context/ skeleton, etc.)
  4  --require-clean violation
```

Companion subcommands:
- `cl session show` — prints current anchor + session_id (reads env), or exits non-zero if unset.
- `cl session end` — prints `unset CL_ANCHOR CL_SESSION_ID` for `eval`; optionally archives session subdir.

### P0.3 — Shim's `cl` resolution

Shim resolves `cl` via `CL_HOME` env var first, falling back to `cl` on `PATH`. Hard error with explicit guidance if neither resolves.

**CL owns the entrypoint, not the consumer.** CL ships a stable wrapper script at `bin/cl` inside its repo. The wrapper knows how to find and exec CL's actual implementation (currently `.venv/bin/cl`, possibly `python -m context_lifecycle` later, etc.). Consumer shims only know "there's a `bin/cl` at `$CL_HOME`" — they do not reach into CL's internals.

This decouples consumer shims from CL's layout. If CL ever restructures its venv, switches package manager, or moves modules, only `bin/cl` updates. Every consumer shim in every repo stays unchanged.

**CL repo layout (relevant pieces):**

```
ContextLifecycle/
  bin/
    cl              ← stable entrypoint; CL maintains its external contract
  src/
    context_lifecycle/...
  .venv/            ← CL's internal venv, free to restructure
```

`bin/cl` (owned by CL):

```bash
#!/usr/bin/env bash
# Stable entrypoint. Absorbs internal layout changes so consumer shims don't break.
set -euo pipefail
SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "${SELF_DIR}/../.venv/bin/cl" "$@"
```

**Consumer repo shim** (`.claude/hooks/pre_tool_use.sh`):

```bash
#!/usr/bin/env bash
set -euo pipefail
CL_BIN="${CL_HOME:+$CL_HOME/bin/cl}"
CL_BIN="${CL_BIN:-$(command -v cl 2>/dev/null || true)}"
if [[ -z "$CL_BIN" || ! -x "$CL_BIN" ]]; then
  echo "ContextLifecycle: cl not found. Set CL_HOME to the CL repo root or install cl on PATH." >&2
  exit 1
fi
exec "$CL_BIN" hook pre_tool_use "$@"
```

Dev setup: `export CL_HOME=/home/dev/Documents/GitHub/ContextLifecycle` in shell profile.
Install setup: `pipx install context-lifecycle` (or equivalent) places `cl` on PATH; `CL_HOME` not needed.

### P0.4 — RepoGraph authorization schema

**Ownership model: exclusive ownership with explicit cross-private allowlist.**

The visibility check is *not* a linear hierarchy. Public is a **single shared namespace** (one PM, universally visible). Private is **per-manifest namespace** (each private manifest is its own walled garden). Two private manifests are not "the same scope" — they're separate gardens that both happen to be non-public.

**Ownership rules:**
- Each repo is owned by **exactly one** manifest (declared in that manifest's `repos:` list).
- Dual claims = RepoGraph load-time error. Operator must pick one home per repo.
- Cross-manifest access requires either (a) the source manifest being public-scoped, or (b) an explicit grant in the consuming manifest's `also_hosts:` list.

**Authorization rule (three clauses, any one sufficient):**

```
allowed(anchor, repo) =
     repo.owner == anchor                    # (1) anchor owns the repo
  OR repo.owner.scope == public              # (2) public is universally visible
  OR repo in anchor.also_hosts               # (3) explicit cross-private grant
```

**Why this shape:**
- Clause (1) covers the common case — a session anchored to manifest X writes cognition about repos X owns.
- Clause (2) makes public manifests universally consumable. Any private manifest can host cognition about public-owned repos without configuration. Public "contaminates upward" in the sense that it's freely available to private consumers, but it doesn't leak the other direction.
- Clause (3) handles legitimate cross-private dependencies (e.g. PrivateProjectFoo needs a component owned by PrivateProjectBar). Explicit, audit-friendly, no silent reclassification.

**Manifest schema:**

```yaml
# PlatformManifest/platform_manifest.yaml
visibility_scope: public
repos:
  - name: OperationsCenter
  - name: ContextLifecycle
  - name: TeamExecutor
  - name: SwitchBoard
  # ...

# <private-manifest-repo>/private_manifest.yaml
visibility_scope: private
repos:
  - name: example-private-repo-A
  # ... other private repos owned by this manifest
  #     (concrete names intentionally omitted — PD is public-scope and
  #      private-repo names belong to the private-manifest repo's tracked
  #      files only)

# Hypothetical PrivateProjectFoo/private_project_foo_manifest.yaml
visibility_scope: private
repos:
  - name: foo-internal-thing
also_hosts:
  - manifest: PrivateProjectBar
    repos:
      - shared-component   # explicit cross-private grant
```

**RepoGraph API:**

```python
RepoGraph.can_anchor_host(anchor_manifest_path: Path, repo_name: str) -> tuple[bool, str]
# Returns (allowed, reason).
# Logic:
#   owner = manifest that lists repo_name in its `repos:` (exactly one)
#   if owner == anchor manifest               → (True, "anchor owns repo")
#   elif owner.visibility_scope == "public"   → (True, "repo is in a public manifest")
#   elif repo_name in anchor.also_hosts       → (True, "explicit grant via also_hosts")
#   else                                       → (False, "<reason>")
#
# Load-time validations (RepoGraph startup):
#   - Each repo appears in exactly one manifest's `repos:`. Dual claim → fatal.
#   - Each `also_hosts` entry references a real (manifest, repo) pair. Bad ref → fatal.
#   - Optional warning: `also_hosts` granting access to a public-owned repo
#     (redundant; clause 2 already covers it).
```

**Edge cases:**
- Repo claimed by zero manifests → `(False, "repo not registered in any manifest")`. Operator must register the repo in exactly one manifest before any anchor can host cognition about it.
- Public-anchored session attempting to write cognition about a private-owned repo → blocked (no clause matches). Operator gets a clear message naming the owning private manifest.
- Two private manifests with mutual `also_hosts` grants → allowed but logged as an architectural smell. If two private projects are tightly coupled enough to need mutual access, consider whether they're actually one project.

### P0.5 — Manifest `.context/` layout for concurrent loops

Per-session subdirs under `.context/sessions/<session_id>/`. Lineage IDs (from the dispatcher) live as files inside a session.

```
<manifest_repo>/.context/
  sessions/
    s-2026-05-22-a1b2/         ← active session (CL_SESSION_ID)
      active/
        l-team-001.yaml        ← lineage-scoped capsule
        l-team-002.yaml
      checkpoints/
        2026-05-22T10-30-00Z.yaml
        2026-05-22T10-45-00Z.yaml
      handoffs/
        worker-1.yaml
    s-2026-05-22-c3d4/         ← concurrent session, isolated
      active/...
      checkpoints/...
      handoffs/...
  archived/                    ← ended sessions moved here (cl session end)
    s-2026-05-21-9z8y/
      ...
  templates/                   ← shared across sessions
    capsule.yaml
    checkpoint.yaml
    handoff.yaml
  config.yaml                  ← manifest-wide CL config (guard flags, etc.)
```

Naming:
- `session_id` (`CL_SESSION_ID`) format: `s-<YYYY-MM-DD>-<4-char-rand>`.
- `lineage_id` format: `l-<short-tag>-<NNN>` (tag chosen by dispatcher; e.g. `l-team-001`, `l-dag-014`).
- Checkpoint files: ISO-8601 UTC with `-` separators (filesystem-safe), `.yaml` extension.

Cleanup:
- `cl session end` moves the session subdir from `sessions/` to `archived/`.
- Archived sessions are git-tracked (durable record). Retention policy TBD in a later work order.

### P0.6 — Standalone failure mode

Hard error. If `CL_ANCHOR` is unset when a hook fires, `cl hook` exits non-zero with a clear message:

```
ContextLifecycle: no session anchor set (CL_ANCHOR is unset).
Run `eval $(cl session start <manifest>)` before invoking Claude Code in this repo.
```

No fallback to local `.context/`. No silent pass-through. The whole point of the model is that unguarded sessions are impossible.

---

## Non-Goals

- `.console/` compaction or relocation (separate future work).
- Routing logic that consumes CL state (cl.peek wired in P4.3 as read-only only; routing decisions remain manifest-agnostic).
- Replacing `.claude/hooks/` with a parent-level setup (option (c) from design); the shim-per-repo approach is the chosen path.
- Adapters for non-Claude-Code runtimes (Codex, Aider, etc.) — out of scope for this work order; CL's existing adapter pattern handles future extension.
