"""Minimal LLM client for Gemini, OpenRouter and NVIDIA (standard library only).

Responses are cached on disk, keyed by provider, model, temperature, prompt
and sample index, so re-running an evaluation costs nothing and gives
identical numbers, while repeated samples (sample=1, 2, ...) are distinct.
Rate-limit (429) and transient server errors are retried with backoff,
honouring Retry-After / Gemini's retryDelay when the server sends one.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CACHE = ROOT / "results" / "llm_cache"

PROVIDERS = {
    "gemini": {"key_env": "GEMINI_API_KEY", "default_model": "gemini-3.5-flash"},
    # OpenAI-compatible chat-completions endpoints.
    "openrouter": {"key_env": "OPENROUTER_API_KEY",
                   "default_model": "meta-llama/llama-3.3-70b-instruct:free",
                   "base_url": "https://openrouter.ai/api/v1"},
    # Free NIM endpoints from build.nvidia.com (keys start with "nvapi-").
    "nvidia": {"key_env": "NVIDIA_API_KEY",
               "default_model": "nvidia/nemotron-3-ultra-550b-a55b",
               "base_url": "https://integrate.api.nvidia.com/v1"},
}
RETRY_STATUS = {429, 500, 502, 503, 504}


class LLMError(RuntimeError):
    pass


def load_dotenv(path: Path = ROOT / ".env") -> None:
    """Read KEY=VALUE lines into os.environ without overriding what is set."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


@dataclass
class LLMClient:
    provider: str = "gemini"
    model: str = ""
    api_key: str = ""
    temperature: float = 0.0
    cache_dir: Path | None = DEFAULT_CACHE
    max_retries: int = 6
    timeout: float = 120.0
    calls: int = field(default=0, init=False)       # network requests made
    cache_hits: int = field(default=0, init=False)

    def __post_init__(self):
        if self.provider not in PROVIDERS:
            raise LLMError(f"unknown provider {self.provider!r}")
        spec = PROVIDERS[self.provider]
        self.model = self.model or os.environ.get("PLCGUARD_MODEL") or spec["default_model"]

    def _key(self) -> str:
        if not self.api_key:
            load_dotenv()
            self.api_key = os.environ.get(PROVIDERS[self.provider]["key_env"], "")
        if not self.api_key:
            raise LLMError(f"set {PROVIDERS[self.provider]['key_env']} in the "
                           "environment or in .env")
        return self.api_key

    # -- public ---------------------------------------------------------------

    def complete(self, system: str, user: str, sample: int = 0) -> str:
        digest = hashlib.sha256(json.dumps(
            [self.provider, self.model, self.temperature, system, user, sample]
        ).encode()).hexdigest()
        cached = self.cache_dir / f"{digest}.json" if self.cache_dir else None
        if cached and cached.is_file():
            self.cache_hits += 1
            return json.loads(cached.read_text(encoding="utf-8"))["response"]

        text = self._request(system, user)
        if cached:
            cached.parent.mkdir(parents=True, exist_ok=True)
            cached.write_text(json.dumps({"provider": self.provider, "model": self.model,
                                          "temperature": self.temperature,
                                          "sample": sample, "response": text}, indent=1), encoding="utf-8")
        return text

    # -- providers ------------------------------------------------------------

    def _request(self, system: str, user: str) -> str:
        if self.provider == "gemini":
            url = ("https://generativelanguage.googleapis.com/v1beta/models/"
                   f"{self.model}:generateContent")
            headers = {"x-goog-api-key": self._key()}
            body = {"systemInstruction": {"parts": [{"text": system}]},
                    "contents": [{"role": "user", "parts": [{"text": user}]}],
                    "generationConfig": {"temperature": self.temperature,
                                         "responseMimeType": "application/json"}}
            data = self._post(url, headers, body)
            try:
                parts = data["candidates"][0]["content"]["parts"]
            except (KeyError, IndexError) as exc:
                raise LLMError(f"no candidate in Gemini response: {str(data)[:300]}") from exc
            return "".join(p.get("text", "") for p in parts if not p.get("thought"))

        url = PROVIDERS[self.provider]["base_url"] + "/chat/completions"
        headers = {"Authorization": f"Bearer {self._key()}", "X-Title": "PLCGuard"}
        body = {"model": self.model, "temperature": self.temperature,
                "max_tokens": 8192,
                "messages": [{"role": "system", "content": system},
                             {"role": "user", "content": user}]}
        data = self._post(url, headers, body)
        try:
            return data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError) as exc:
            raise LLMError(f"no choice in {self.provider} response: {str(data)[:300]}") from exc

    def list_models(self) -> list[str]:
        """Model ids the provider serves (OpenAI-compatible providers only)."""
        if "base_url" not in PROVIDERS[self.provider]:
            raise LLMError(f"model listing is not supported for {self.provider}")
        req = urllib.request.Request(PROVIDERS[self.provider]["base_url"] + "/models",
                                     headers={"Authorization": f"Bearer {self._key()}"})
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return sorted(m["id"] for m in json.loads(resp.read())["data"])

    def _post(self, url: str, headers: dict, body: dict) -> dict:
        payload = json.dumps(body).encode()
        headers = {"Content-Type": "application/json", **headers}
        for attempt in range(self.max_retries + 1):
            self.calls += 1
            req = urllib.request.Request(url, payload, headers, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    return json.loads(resp.read())
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode(errors="replace")
                if exc.code not in RETRY_STATUS or attempt == self.max_retries:
                    raise LLMError(f"HTTP {exc.code}: {detail[:500]}") from exc
                delay = _retry_delay(exc.headers.get("Retry-After"), detail, attempt)
            except (urllib.error.URLError, TimeoutError) as exc:
                if attempt == self.max_retries:
                    raise LLMError(f"network error: {exc}") from exc
                delay = _retry_delay(None, "", attempt)
            time.sleep(delay)
        raise AssertionError("unreachable")


def _retry_delay(retry_after: str | None, body: str, attempt: int) -> float:
    if retry_after:
        try:
            return float(retry_after) + 1
        except ValueError:
            pass
    m = re.search(r'"retryDelay":\s*"(\d+(?:\.\d+)?)s"', body)
    if m:
        return float(m.group(1)) + 1
    return min(2 ** attempt * 2, 60)
