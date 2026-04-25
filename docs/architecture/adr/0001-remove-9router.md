# ADR 0001 — Archival: Remove 9router from the Architecture

**Status:** Accepted  
**Date:** 2026-04-21  
**Deciders:** Platform team

> Archival note: this ADR is retained only as historical record for the removed
> provider-proxy design. It does not describe any active runtime component.

---

## Context

`9router` was a provider-routing service (a separate repo, `decolua/9router`) that sat
between SwitchBoard and external LLM providers. Its job was to:

- Accept normalised requests from SwitchBoard
- Select the best provider (OpenAI, Anthropic, local) based on routing hints
- Translate requests into provider-specific wire format
- Handle retries and failover across providers
- Hold provider API keys so they were never exposed to clients

WorkStation owned the 9router Dockerfile and compose service. SwitchBoard forwarded
every chat completion request to 9router via an `HttpNineRouterGateway` adapter.

---

## Why 9router Was Attractive

- Consolidated credential management (API keys in one place)
- Provider-format abstraction (OpenAI, Anthropic, Cohere, local — all behind one API)
- Retry and failover logic separate from SwitchBoard's policy logic
- Made SwitchBoard's `Forwarder` simple: send to one URL, get back one response

---

## Why 9router Is No Longer a Fit

**The execution model changed.** The system moved from API-call-based execution to
CLI-based lane execution. The three execution lanes are:

- `claude_cli` — Claude Code CLI, OAuth/subscription auth
- `codex_cli` — Codex CLI, OpenAI subscription auth
- `aider_local` — Aider against locally deployed tiny models

None of these lanes use provider API keys. They use CLI OAuth sessions or local
models. A provider-credential proxy adds no value when there are no credentials to
proxy.

**SwitchBoard's role clarified.** SwitchBoard is an execution-lane selector, not a
universal OpenAI-compatible proxy. It classifies tasks and routes them to the right
lane. It does not sit in a hot path between a client app and an LLM API. The
forwarding-to-provider pattern that 9router enabled is not the right abstraction for
the new model.

**9router introduced coupling to a free-provider OAuth flow.** The platform previously
depended on 9router's dashboard-based provider setup (GitHub OAuth, Google OAuth,
device code flows for Qwen, Kiro, etc.). This created friction: operators had to
complete OAuth flows through 9router's UI before coding lanes worked. The CLI-based
lanes (Claude CLI, Codex CLI) have their own OAuth handled by the CLI itself, and
`aider_local` has no external auth at all.

**Operational complexity without proportional benefit.** 9router added a second
hop for every execution request, a separate container to maintain, a separate OAuth
flow to complete, and a separate failure mode to diagnose. Given the lane-based model,
this complexity serves no purpose.

---

## What Replaced 9router's Role

| 9router responsibility | New owner |
|------------------------|-----------|
| Provider credential management | CLI OAuth (each lane manages its own auth) |
| Provider format translation | Claude Agent SDK / Codex SDK (each handles its own wire format) |
| Retry and failover across providers | kodo's execution loop; lane-level retry logic |
| Local model serving | WorkStation (deploys tiny models for `aider_local` lane) |
| Provider selection | SwitchBoard lane selection (chooses which lane, not which API) |

---

## Design Constraints This Removal Clarifies

1. **SwitchBoard is not a proxy.** It selects lanes. It does not forward HTTP requests
   to external provider APIs. Any future version of SwitchBoard that starts proxying
   API calls to providers is drifting back toward the removed pattern.

2. **WorkStation owns local model infra.** The tiny models that the `aider_local` lane
   uses are deployed by WorkStation, not by a provider routing service. This makes the
   local cheap lane a WorkStation concern, not an external dependency.

3. **CLI auth is CLI-managed.** The premium lanes (`claude_cli`, `codex_cli`) handle
   their own authentication via their respective CLIs. The platform does not hold or
   broker provider credentials for these lanes.

4. **Provider diversity is the lane boundary.** If a new provider becomes relevant
   (e.g., a Gemini CLI lane), the right place to add it is as a new lane definition in
   SwitchBoard's policy, not as a new provider behind a proxy layer.

---

## Migration Impact

- `WorkStation/docker/Dockerfile.9router` — no longer built or maintained
- `WorkStation/compose/docker-compose.yml` — 9router service removed
- `SwitchBoard/src/switchboard/adapters/http_nine_router_gateway.py` — to be replaced
  in a future phase with a lane-dispatch adapter
- `SwitchBoard/docs/` — references to 9router updated to reflect new lane model
- `WorkStation/docs/architecture.md` — superseded by `system_overview.md`
- `WorkStation/README.md` — updated to remove 9router from services table

No existing OperationsCenter or kodo code depends on 9router directly. The change is
primarily an infrastructure and SwitchBoard adapter concern.
