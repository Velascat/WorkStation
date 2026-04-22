# Upstream Patch Evaluation

## Purpose

This document explains the late-stage, evidence-based process for deciding
whether external systems such as `openclaw`, `archon`, or `kodo` justify any
upstream patching, forking, or deeper native integration work.

The baseline posture remains adapter-first. Upstream modification is not an
early architectural assumption.

## Why This Is Late

The platform was deliberately designed so ControlPlane, SwitchBoard, and the
adapter layer could move forward without assuming early upstream changes.

By the time this evaluation exists, the system has:

- retained execution evidence
- support-check histories
- changed-file evidence patterns
- routing and tuning findings
- operator and wrapper friction observations

That makes it possible to ask whether an issue is merely annoying or is now a
recurring structural problem worth evaluating for upstream work.

## Inputs

The evaluation uses normalized evidence such as:

- backend support-check failures
- recurring changed-file uncertainty
- repeated normalization or parsing limitations
- routing/tuning findings that show backend underfit
- repeated adapter or operator pain
- repeated wrapper complexity and brittle invocation surfaces

It should not be driven by anecdotes alone.

## Core Separation

The system keeps these distinct:

1. observed recurring friction
2. evaluation findings
3. candidate patch proposals
4. accepted roadmap work

Patch proposals are reviewable recommendations, not silent commitments.

## Flow

```text
Retained execution / adapter friction evidence
  -> evaluation and classification
  -> findings + workaround assessments
  -> upstream patch proposals
  -> human-reviewed roadmap decisions later
```

## Evaluation Dimensions

The process stays bounded and readable:

- `FrequencyClass`: `rare`, `occasional`, `recurring`, `persistent`
- `SeverityClass`: `low`, `medium`, `high`, `critical`
- `ArchitecturalImpactClass`: `minor`, `moderate`, `major`
- `WorkaroundComplexityClass`: `simple`, `moderate`, `high`
- `EvidenceStrength`: `weak`, `moderate`, `strong`

Additional tradeoffs must stay explicit:

- workaround reliability
- maintenance burden
- divergence risk
- expected value

## Default Posture

Adapter-first remains the default unless evidence is both meaningful and
repeated.

Continue adapting locally when:

- evidence is weak
- friction is isolated or occasional
- architectural impact is minor
- workaround complexity is low and stable

Consider an upstream patch proposal only when:

- friction is recurring or persistent
- workaround cost is high or brittle
- architectural impact is major
- native support would provide material value
- maintenance and divergence tradeoffs are explicit

## Architectural Constraint

This evaluation layer does not:

- change live routing
- change live execution behavior
- rewrite canonical contracts around an upstream tool
- create roadmap commitments automatically

Human review decides whether any proposal becomes real planned work.
