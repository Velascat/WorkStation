# Provider Setup

9router manages LLM provider credentials internally — no API keys are stored in `.env` files or passed through environment variables. Credentials are connected once through the 9router dashboard and persist in the local database.

This means the stack can start with zero secrets configured. Connect a provider after the stack is running.

---

## Free providers

All five options below are free to use and require no paid subscription or API key.

| Provider | Models | Sign-up | Notes |
|----------|--------|---------|-------|
| **Kiro** | Claude Sonnet 4.5 | GitHub OAuth | Recommended first pick — fast, no quota limits |
| **iFlow** | Deepseek R1, Qwen3, GLM | OAuth | Multiple strong open-weight models |
| **Qwen** | Qwen3-Coder | Device code auth | Good for coding-focused workloads |
| **Gemini** | Gemini 2.5 Pro | Google OAuth | Capable but quota-limited |
| **Ollama** | Any local model | No account | Runs on your hardware — CPU-only performance is limited; see note below |

### Kiro (recommended)

Kiro provides free access to Claude Sonnet 4.5 via AWS Builder ID, with GitHub OAuth as the sign-in method. No payment method required, no quota ceiling mentioned.

Setup time: ~30 seconds. Click "Connect" in the 9router dashboard → GitHub OAuth flow → done.

### iFlow

Provides Deepseek R1, Qwen3, and GLM via OAuth. Good fallback if Kiro is unavailable.

### Qwen

Provides Qwen3-Coder via device code authentication (similar to GitHub device flow — you get a code, visit a URL, paste it in).

### Gemini

Provides Gemini 2.5 Pro via Google OAuth. The free tier is quota-limited (requests per minute / per day), which can cause failures under sustained load. Fine for demos and light use.

### Ollama

Runs models locally on your own hardware — no account, no internet required after model download. The tradeoff is inference speed: without a GPU, CPU-only inference is typically 5–30 tokens/second on a 7B model, which feels slow in interactive use. Larger models (13B+) are generally impractical on CPU.

Use Ollama when you need fully offline/air-gapped operation. For anything else, a cloud provider is a better experience.

---

## Connecting a provider

**Option 1 — via `fob providers`:**

```bash
fob providers        # opens dashboard, shows this table
fob providers --wait # same, then polls until a provider connects
```

**Option 2 — manually:**

1. Ensure the stack is running (`fob demo` starts it if not)
2. Open `http://localhost:20128` in a browser
3. Navigate to the Providers section
4. Click "Connect" next to your chosen provider
5. Complete the OAuth or device-code flow
6. The provider appears as active — no restart needed

---

## Checking provider status

```bash
# via fob
fob providers

# via curl
curl -s http://localhost:20128/api/providers | jq '.[] | {name, connected}'
```

---

## Which provider does SwitchBoard use?

SwitchBoard selects providers based on `config/profiles.yaml` and the active policy in `config/policy.yaml`. The `fast` profile routes to whichever downstream model is mapped there; the `capable` profile routes to a higher-tier model.

As long as at least one provider is connected in 9router that matches a configured profile, SwitchBoard will route successfully. If a provider becomes unavailable, SwitchBoard's adaptive routing demotes it automatically and falls back to another.

See [SwitchBoard docs/profiles.md](../../SwitchBoard/docs/profiles.md) for profile configuration.
