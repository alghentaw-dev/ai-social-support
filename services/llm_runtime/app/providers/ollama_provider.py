import json, requests
from typing import Dict, Iterable, Tuple
from .base import BaseProvider
from ..settings import settings

class OllamaProvider(BaseProvider):
    name = "ollama"

    def _options(self, options: Dict[str,str], max_tokens, temperature):
        opts = {}
        if "num_ctx" in options: opts["num_ctx"] = int(options["num_ctx"])
        if "num_gpu" in options: opts["num_gpu"] = options["num_gpu"]  # int or "auto"
        if temperature is not None: opts["temperature"] = temperature
        if max_tokens is not None: opts["num_predict"] = max_tokens
        return opts

    def generate(self, *, model, prompt, system, options, json_mode, json_schema,
                 max_tokens, temperature, timeout_ms) -> Tuple[str, str]:
        url = f"{settings.OLLAMA_ENDPOINT}/api/generate"
        prompt_text = prompt if not system else f"System:\n{system}\n\nUser:\n{prompt}"
        payload = {
            "model": model,
            "prompt": prompt_text,
            "stream": False,
            "options": self._options(options, max_tokens, temperature)
        }
        if json_mode:
            # basic JSON guard
            payload["format"] = "json"

        to = (timeout_ms/1000) if (timeout_ms and timeout_ms>0) else 120
        r = requests.post(url, json=payload, timeout=to)
        r.raise_for_status()
        data = r.json()
        return data.get("response",""), data.get("done_reason","stop")

    def generate_stream(self, *, model, prompt, system, options, json_mode, json_schema,
                        max_tokens, temperature, timeout_ms) -> Iterable[Tuple[str,bool,str]]:
        url = f"{settings.OLLAMA_ENDPOINT}/api/generate"
        prompt_text = prompt if not system else f"System:\n{system}\n\nUser:\n{prompt}"
        payload = {
            "model": model,
            "prompt": prompt_text,
            "stream": True,
            "options": self._options(options, max_tokens, temperature)
        }
        if json_mode:
            payload["format"] = "json"

        to = (timeout_ms/1000) if (timeout_ms and timeout_ms>0) else None
        with requests.post(url, json=payload, stream=True, timeout=to) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if not line: continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                delta = obj.get("response","")
                done = bool(obj.get("done"))
                finish = obj.get("done_reason","")
                yield (delta, done, finish)
                if done:
                    break
