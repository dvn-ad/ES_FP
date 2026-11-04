"""Optional LLM adjudication for ambiguous element pairs.

Disabled by default so the prototype stays deterministic and offline.  Any
OpenAI-compatible chat-completions endpoint can be used:

    export BPMNDIFF_LLM=1
    export BPMNDIFF_LLM_URL=https://api.openai.com/v1/chat/completions
    export BPMNDIFF_LLM_MODEL=gpt-4o-mini
    export OPENAI_API_KEY=...

If the call fails, the questionable pairs remain flagged ``needs_review``.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request


class LLMAdjudicator:
    def __init__(
        self,
        url: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
        timeout: float = 20.0,
    ) -> None:
        self.url = url or os.environ.get(
            "BPMNDIFF_LLM_URL", "https://api.openai.com/v1/chat/completions"
        )
        self.model = model or os.environ.get("BPMNDIFF_LLM_MODEL", "gpt-4o-mini")
        self.api_key = api_key or os.environ.get("BPMNDIFF_LLM_API_KEY") or os.environ.get(
            "OPENAI_API_KEY", ""
        )
        self.timeout = timeout

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def _prompt(self, pairs: list[tuple[str, str]]) -> str:
        lines = [
            "You compare labels of business-process elements from two model variants.",
            "For each numbered pair choose exactly one label:",
            "- identical: same meaning, only case/punctuation differs",
            "- synonym: same activity, different wording",
            "- meaning_changed: related wording but the business meaning differs",
            "- unmatched: unrelated elements",
            "Return a JSON array only, one object per pair:",
            '{"id": 0, "label": "synonym", "confidence": "high", "reason": "..."}',
            "Pairs:",
        ]
        for index, (left, right) in enumerate(pairs):
            lines.append(f'{index}. A="{left}" | B="{right}"')
        return "\n".join(lines)

    def adjudicate(self, pairs: list[tuple[str, str]]) -> list[dict | None]:
        if not pairs:
            return []
        if not self.available:
            return [None] * len(pairs)
        payload = {
            "model": self.model,
            "temperature": 0,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a conservative BPMN process-model analyst. Answer with JSON only.",
                },
                {"role": "user", "content": self._prompt(pairs)},
            ],
        }
        request = urllib.request.Request(
            self.url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
            content = body["choices"][0]["message"]["content"]
            content = content.strip()
            if content.startswith("```"):
                content = content.strip("`")
                if content.startswith("json"):
                    content = content[4:]
            parsed = json.loads(content)
        except (urllib.error.URLError, KeyError, IndexError, ValueError, TimeoutError):
            return [None] * len(pairs)

        results: list[dict | None] = [None] * len(pairs)
        if isinstance(parsed, dict):
            parsed = parsed.get("pairs", [])
        if isinstance(parsed, list):
            for item in parsed:
                if not isinstance(item, dict):
                    continue
                try:
                    index = int(item.get("id", -1))
                except (TypeError, ValueError):
                    continue
                if 0 <= index < len(pairs):
                    results[index] = item
        return results


def get_adjudicator(enabled: bool) -> LLMAdjudicator | None:
    if not enabled:
        return None
    adjudicator = LLMAdjudicator()
    return adjudicator if adjudicator.available else None
