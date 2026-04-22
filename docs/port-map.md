# Port Map

All ports used by the WorkStation stack.

---

## Core Services

| SERVICE     | PORT  | PROTOCOL | PURPOSE                                                   |
|-------------|-------|----------|-----------------------------------------------------------|
| SwitchBoard | 20401 | TCP/HTTP | Execution-lane selector — task classification and dispatch |
| Status API  | 20400 | TCP/HTTP | Stack-level health and metadata aggregation               |

---

## Observability Profile

| SERVICE    | PORT | PROTOCOL | PURPOSE                        |
|------------|------|----------|--------------------------------|
| Prometheus | 9090 | TCP/HTTP | Metrics scraping UI and API    |
| Grafana    | 3000 | TCP/HTTP | Dashboarding UI                |

---

## Dev Profile

| SERVICE | PORT | PROTOCOL | PURPOSE                        |
|---------|------|----------|--------------------------------|
| Mailpit | 1025 | TCP/SMTP | Local SMTP mail capture        |
| Mailpit | 8025 | TCP/HTTP | Mailpit web inspection UI      |

---

## Notes

- All ports are host-mapped (host:container). The container-side ports are fixed; the host-side ports can be overridden via `.env`.
- To change a host port without editing compose files, set the corresponding variable in `.env`:
  ```
  PORT_SWITCHBOARD=20401
  PORT_STATUS=20400
  ```
- Internal service-to-service traffic uses Docker bridge network DNS and does not traverse host ports.
- Port 20400 (Status API) is reserved for a future aggregate health service; it is not yet implemented.
