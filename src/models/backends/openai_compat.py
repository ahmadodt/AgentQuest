import json
import time
from dataclasses import dataclass
from typing import Any, Dict, List

import requests

from src.models.base import ChatMessage, GenerationResult


@dataclass
class OpenAICompatConfig:
    base_url: str
    api_key: str
    model: str
    timeout_s: int = 60


class OpenAICompatHandler:
    def __init__(self, cfg: OpenAICompatConfig):
        self.cfg = cfg
        self._session = requests.Session()

    def generate(self, messages: List[ChatMessage], *, max_tokens: int = 256, temperature: float = 0.0) -> GenerationResult:
        url = self.cfg.base_url.rstrip("/") + "/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.cfg.api_key}",
        }
        payload = {
            "model": self.cfg.model,
            "messages": messages,
            "temperature": float(temperature),
            "max_tokens": int(max_tokens),
        }

        t0 = time.time()
        try:
            r = self._session.post(url, headers=headers, data=json.dumps(payload), timeout=self.cfg.timeout_s)
            latency_s = time.time() - t0
        except Exception as e:
            return GenerationResult(raw_text="", metadata={"ok": False, "error": str(e), "latency_s": None})

        if r.status_code >= 400:
            return GenerationResult(
                raw_text="",
                metadata={"ok": False, "status_code": r.status_code, "body": r.text[:2000], "latency_s": latency_s},
            )

        data = r.json()
        raw_text = ""
        try:
            raw_text = data["choices"][0]["message"]["content"]
        except Exception:
            raw_text = ""

        return GenerationResult(
            raw_text=raw_text or "",
            metadata={
                "ok": True,
                "latency_s": latency_s,
                "usage": data.get("usage", {}),
                "model": data.get("model", self.cfg.model),
                "id": data.get("id"),
            },
        )