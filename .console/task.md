# Active Mission

_The current live assignment. One objective at a time._
_Replace contents when the objective changes. Do not accumulate history here — that belongs in log.md._

## Objective

Add a PlatformDeployment convenience wrapper that materializes a RepoGraph
boundary artifact through the private-manifest repo and then runs Custodian
locally or in CI without changing Custodian semantics.

## Context

Wrapper belongs to PlatformDeployment as runtime/topography glue. Custodian
must still fail closed and only consume REPOGRAPH_BOUNDARY_ARTIFACT_FILE.

## Definition of Done

Wrapper script, docs, and tests are in place; local artifact acceptance,
missing-artifact failure, generated-artifact flow, exit-code preservation, and
keep-artifacts mode are all verified.
