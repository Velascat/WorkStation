---
name: Feature Request
about: Suggest an improvement or new capability
labels: enhancement
assignees: ''
---

## Summary

A one-sentence description of the feature.

## Problem It Solves

What is currently difficult or impossible that this would fix?

## Proposed Solution

How you imagine it working. Include config or command examples if relevant.

## Startup Authority Check

WorkStation is the sole startup authority. Confirm this change stays within that boundary:

- [ ] No planning, routing, or execution logic introduced
- [ ] New services are started via `up.sh` or compose, not independently
- [ ] Secrets are managed via `.env` / `.env.example`, not hardcoded

## Alternatives Considered

Other approaches and why you ruled them out.

## Additional Context

Related issues, architecture docs, or prior discussion.
