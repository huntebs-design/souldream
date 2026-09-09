"""List Venice chat models without printing credentials."""

from __future__ import annotations

import json
import os

import requests


api_key = os.getenv("VENICE_API_KEY")
if not api_key:
    raise RuntimeError("VENICE_API_KEY is not configured")

response = requests.get(
    "https://api.venice.ai/api/v1/models?type=text",
    headers={"Authorization": f"Bearer {api_key}"},
    timeout=30,
)
response.raise_for_status()
payload = response.json()
models = payload.get("data", payload)
for item in models:
    model_id = str(item.get("id") or "")
    lowered = model_id.lower()
    if any(term in lowered for term in ("uncensored", "role", "dolphin", "qwen", "llama", "mistral")):
        print(
            json.dumps(
                {
                    "id": model_id,
                    "name": item.get("name"),
                    "traits": item.get("model_spec", {}).get("traits"),
                    "pricing": item.get("model_spec", {}).get("pricing"),
                },
                ensure_ascii=False,
            )
        )
