import os, json, time
from typing import Dict, Iterable, Tuple
import requests
from .base import BaseProvider
from ..settings import settings

class OpenAIProvider(BaseProvider):
    name = "openai"

    def _headers(self):
        return {"Authorization": f"Bearer {settings.OPENAI_API_KEY}"}

    def generate(self, *, model, prompt, system, options, json_mode, json_schema,
                 max_tokens, temperature, timeout_ms) -> Tuple[str, str]:
        url = f"{settings.OPENAI_BASE_URL}/chat/completions"
        msgs = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": msgs,
            "stream": False
        }
        if max_tokens is not None: payload["max_tokens"] = max_tokens
        if temperature is not None: payload["temperature"] = temperature

        # JSON mode (for structured extraction)
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
            # You can add JSON schema with new OpenAI structured output if desired
            # (here we keep it simple; the model will return valid JSON)

        to = (timeout_ms/1000) if (timeout_ms and timeout_ms>0) else 120
        r = requests.post(url, headers=self._headers(), json=payload, timeout=to)
        r.raise_for_status()
        data = r.json()
        text = data["choices"][0]["message"]["content"]
        finish = data["choices"][0].get("finish_reason", "stop")
        return text, finish

    def generate_stream(self, **kw) -> Iterable[Tuple[str, bool, str]]:
        url = f"{settings.OPENAI_BASE_URL}/chat/completions"
        msgs = []
        system = kw.get("system")
        if system:
            msgs.append({"role":"system","content":system})
        msgs.append({"role":"user","content":kw["prompt"]})

        payload = {
            "model": kw["model"],
            "messages": msgs,
            "stream": True
        }
        if kw.get("max_tokens") is not None: payload["max_tokens"] = kw["max_tokens"]
        if kw.get("temperature") is not None: payload["temperature"] = kw["temperature"]
        if kw.get("json_mode"):
            payload["response_format"] = {"type":"json_object"}

        to = (kw.get("timeout_ms",0)/1000) if kw.get("timeout_ms") else None
        with requests.post(url, headers=self._headers(), json=payload, timeout=to, stream=True) as r:
            r.raise_for_status()
            finish = "stop"
            for line in r.iter_lines():
                if not line: continue
                if line.startswith(b"data: "):
                    chunk = line[6:]
                    if chunk == b"[DONE]":
                        yield ("", True, finish)
                        break
                    try:
                        obj = json.loads(chunk)
                        delta = obj["choices"][0]["delta"].get("content","")
                        finish = obj["choices"][0].get("finish_reason") or finish
                        if delta:
                            yield (delta, False, "")
                    except Exception:
                        continue
