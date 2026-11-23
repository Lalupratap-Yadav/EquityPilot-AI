"""Configurable AI providers.

* offline   - built-in rule-based analyst (free, default, no data leaves the machine)
* anthropic - Claude via the Anthropic API (PAID, usage-based; needs your own API key -
              a Claude Pro chat subscription does NOT include API access)
* ollama    - a local open-source model served by Ollama (free; runs on your computer)

The API key is read from Streamlit secrets / environment, or entered for the current session
only. It is never written to the database or to disk by EquityPilot.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

SYSTEM_PROMPT = """You are EquityPilot's research assistant for Indian listed equities, used by students and analysts.

Grounding rules (mandatory):
1. Use ONLY the numbered source blocks provided in the context. Cite them inline like [S3]. Do not use outside knowledge for any company-specific figure, event or news.
2. Never invent, estimate or "recall" financial figures, dates or news. If something is not in the context, say clearly that it is not available and suggest where to find it (annual report, NSE/BSE filing).
3. Structure every answer with these headings, omitting empty ones:
   Facts (from sources) / Calculations (show formula and inputs) / Assumptions / Interpretation (your analysis, clearly labelled as such) / Limitations.
4. Do not give buy, sell or hold recommendations, target prices or personal investment advice. In India such recommendations require SEBI registration; explain the evidence instead.
5. Respect data labels: say when data is SAMPLE (fictional), THIRD-PARTY (verify with filings), DELAYED or a USER ASSUMPTION.
6. Use Indian conventions: ₹, crore, fiscal years (FY2025 = year ending March 2025).
7. Be concise and precise. Prefer short bullet points and tables."""

# Indicative list prices (USD per million tokens) - verify on Anthropic's pricing page before enabling.
ANTHROPIC_MODELS = {
    "claude-opus-5-5": {"label": "Claude Opus 5.5 (most capable)", "in": 4.00, "out": 20.00, "cache_read": 0.20},
    "claude-sonnet-5-5": {"label": "Claude Sonnet 5.5 (balanced)", "in": 2.00, "out": 10.00, "cache_read": 0.10},
    "claude-haiku-5-5": {"label": "Claude Haiku 5.5 (lowest cost)", "in": 0.10, "out": 0.50, "cache_read": 0.01},
}
# Models a refusal fallback may run on (priced at their own rates; cache reads at 10% of input where not published).
FALLBACK_PRICES = {"claude-opus-4-8": {"in": 5.00, "out": 25.00, "cache_read": 0.50},
                   "claude-opus-5": {"in": 5.00, "out": 25.00, "cache_read": 0.50}}
CACHE_WRITE_FACTOR = 1.25     # 5-minute prompt-cache writes cost 1.25x the input price
PRICING_NOTE = ("Indicative Anthropic API list prices (USD per million tokens) as of Nov 2026; check "
                "https://www.anthropic.com/pricing before enabling.")


class ProviderError(RuntimeError):
    pass


@dataclass
class ProviderResult:
    text: str
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    note: str | None = None


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)          # rough rule of thumb for English text


def estimate_cost_usd(model: str, input_tokens: int, output_tokens: int = 1200) -> float | None:
    p = ANTHROPIC_MODELS.get(model)
    if not p:
        return None
    return input_tokens / 1e6 * p["in"] + output_tokens / 1e6 * p["out"]


def cost_of(parts: list[tuple]) -> float | None:
    """Estimated USD for API attempts given as (model, input, output, cache read, cache write) tokens."""
    total, known = 0.0, False
    for model, inp, out, c_read, c_write in parts:
        p = ANTHROPIC_MODELS.get(model) or FALLBACK_PRICES.get(model)
        if not p:
            continue
        known = True
        total += (inp * p["in"] + out * p["out"] + c_read * p.get("cache_read", p["in"] * 0.1)
                  + c_write * p["in"] * CACHE_WRITE_FACTOR) / 1e6
    return total if known else None


def find_api_key(session_key: str | None = None) -> str | None:
    if session_key:
        return session_key
    try:
        import streamlit as st
        if "ANTHROPIC_API_KEY" in st.secrets:
            return st.secrets["ANTHROPIC_API_KEY"]
    except Exception:  # no secrets file - fine
        pass
    return os.environ.get("ANTHROPIC_API_KEY")


def explain_anthropic_error(exc: Exception) -> str:
    """A plain explanation of an Anthropic API error (shown to the user; the free offline engine answers instead)."""
    import anthropic
    if isinstance(exc, anthropic.AuthenticationError):
        return "The Anthropic API key was rejected. Check the key in Settings."
    if isinstance(exc, anthropic.PermissionDeniedError):
        return "This API key does not have access to the selected model."
    if isinstance(exc, anthropic.NotFoundError):
        return "The selected Claude model was not found for this account."
    if isinstance(exc, anthropic.RateLimitError):
        return "The Anthropic rate limit was reached - wait a minute and try again."
    if isinstance(exc, anthropic.BadRequestError):
        msg = getattr(exc, "message", "") or str(exc)
        if "credit balance" in msg.lower():
            return "Your Anthropic API credit balance is too low. Add credit at console.anthropic.com (API billing is separate from Claude Pro/Max plans)."
        return f"The Anthropic API rejected the request: {msg[:200]}"
    if isinstance(exc, anthropic.APIStatusError):
        return f"The Anthropic API is temporarily unavailable (HTTP {exc.status_code}). Try again shortly."
    if isinstance(exc, anthropic.APIConnectionError):
        return "Could not reach the Anthropic API (network problem)."
    return f"The Anthropic API returned an error ({type(exc).__name__})."


def ask_anthropic(context_text: str, history: list[dict], question: str, model: str, api_key: str,
                  effort: str = "medium") -> ProviderResult:
    try:
        import anthropic
    except ImportError as exc:
        raise ProviderError("The 'anthropic' package is not installed (pip install anthropic).") from exc
    client = anthropic.Anthropic(api_key=api_key, max_retries=2, timeout=120)
    messages = [*history[-6:], {"role": "user", "content": f"<context>\n{context_text}\n</context>\n\nQuestion: {question}"}]
    kwargs = dict(model=model, max_tokens=16000, system=SYSTEM_PROMPT, messages=messages,
                  output_config={"effort": effort})
    try:
        if model.startswith(("claude-opus", "claude-sonnet", "claude-fable")):
            # Server-side fallback: if a safety classifier declines, the API retries on a fallback model.
            resp = client.beta.messages.create(betas=["server-side-fallback-2026-07-01"], fallbacks="default", **kwargs)
        else:
            resp = client.beta.messages.create(**kwargs)
    except anthropic.AuthenticationError as exc:
        raise ProviderError("The Anthropic API key was rejected. Check the key in Settings.") from exc
    except anthropic.PermissionDeniedError as exc:
        raise ProviderError("This API key does not have access to the selected model.") from exc
    except anthropic.NotFoundError as exc:
        raise ProviderError(f"Model '{model}' was not found for this account.") from exc
    except anthropic.RateLimitError as exc:
        raise ProviderError("Rate limit reached - wait a minute and try again.") from exc
    except anthropic.BadRequestError as exc:
        raise ProviderError(f"The request was rejected: {exc.message}") from exc
    except anthropic.APIStatusError as exc:
        raise ProviderError(f"Anthropic API error ({exc.status_code}). Try again later.") from exc
    except anthropic.APIConnectionError as exc:
        raise ProviderError("Could not reach the Anthropic API (network problem).") from exc
    if resp.stop_reason == "refusal":
        return ProviderResult("The model declined to answer this request. Try rephrasing the question.", resp.model)
    text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
    note = "Response truncated at the token limit." if resp.stop_reason == "max_tokens" else None
    return ProviderResult(text, resp.model, getattr(resp.usage, "input_tokens", None),
                          getattr(resp.usage, "output_tokens", None), note)


def ask_ollama(context_text: str, history: list[dict], question: str, model: str,
               host: str = "http://localhost:11434") -> ProviderResult:
    import requests
    messages = [{"role": "system", "content": SYSTEM_PROMPT}, *history[-6:],
                {"role": "user", "content": f"<context>\n{context_text}\n</context>\n\nQuestion: {question}"}]
    try:
        r = requests.post(f"{host.rstrip('/')}/api/chat", json={"model": model, "messages": messages, "stream": False},
                          timeout=300)
    except requests.RequestException as exc:
        raise ProviderError(f"Could not reach Ollama at {host}. Is it installed and running ('ollama serve')?") from exc
    if r.status_code == 404:
        raise ProviderError(f"Ollama model '{model}' not found. Run: ollama pull {model}")
    if not r.ok:
        raise ProviderError(f"Ollama error {r.status_code}: {r.text[:200]}")
    data = r.json()
    return ProviderResult(data.get("message", {}).get("content", ""), model,
                          data.get("prompt_eval_count"), data.get("eval_count"))


def ollama_available(host: str = "http://localhost:11434") -> list[str] | None:
    """List locally installed Ollama models, or None if Ollama isn't running."""
    import requests
    try:
        r = requests.get(f"{host.rstrip('/')}/api/tags", timeout=2)
        return [m["name"] for m in r.json().get("models", [])] if r.ok else None
    except requests.RequestException:
        return None
