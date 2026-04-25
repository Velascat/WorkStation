## Summary

<!-- One or two sentences describing what this PR does and why. -->

## Changes

<!-- Bullet list of what changed. -->

-

## Startup Authority Checklist

- [ ] Stack is still started exclusively via `up.sh` / Docker Compose
- [ ] No planning, routing, or execution logic introduced
- [ ] `.env.example` updated if environment variables changed
- [ ] No secrets committed

## Testing

- [ ] Tests pass: `.venv/bin/python -m pytest`
- [ ] Stack starts cleanly: `bash up.sh`
- [ ] Health checks pass after startup

## Related Issues

<!-- Closes #N or References #N -->

## Notes for Reviewer

<!-- Anything non-obvious: service dependencies, port changes, volume changes, follow-up items. -->
