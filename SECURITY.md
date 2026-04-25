# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| `main`  | ✅ Yes     |

Only the current `main` branch receives security fixes.

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Report security issues privately by emailing **coding.projects.1642@proton.me**.

Include:
- A description of the vulnerability
- Steps to reproduce
- Potential impact
- Any suggested mitigations (optional)

You will receive an acknowledgment within 72 hours. We aim to release a fix within 14 days of a confirmed report, depending on severity and complexity.

## Scope

WorkStation manages the startup and runtime environment for the platform. The primary security surface is:

- **Docker socket exposure** — compose files that grant containers unintended host access
- **Secrets in environment files** — API tokens or credentials committed or leaked via `.env`
- **Port exposure** — services bound to `0.0.0.0` instead of `127.0.0.1` in development
- **Inter-service trust** — unauthenticated communication between platform services

## Out of Scope

- Vulnerabilities in Docker, Docker Compose, or upstream service images
- Issues requiring physical access to the host machine
- Network-level attacks against a properly firewalled development environment
