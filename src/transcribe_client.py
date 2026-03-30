from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import requests


@dataclass(frozen=True)
class TranscriptionResult:
    dialogue_id: str
    transcript: str


class TranscribeClient:
    def __init__(self, endpoint: str, timeout_sec: int = 600):
        self.endpoint = endpoint
        self.timeout_sec = timeout_sec

    def transcribe_wav(
        self,
        *,
        file_bytes: bytes,
        filename: str,
        file_field: str = "file",
        cancel_check: Optional[callable] = None,
    ) -> TranscriptionResult:
        files = {
            file_field: (filename, file_bytes, "audio/wav"),
        }

        resp = requests.post(
            self.endpoint,
            files=files,
            timeout=self.timeout_sec,
        )
        resp.raise_for_status()

        data = resp.json()
        dialogue_id = str(data.get("dialogue_id") or data.get("dialogueId") or "")
        transcript = str(data.get("transcript") or data.get("text") or data.get("result") or "")

        if not dialogue_id:
            dialogue_id = filename

        if cancel_check and cancel_check():
            # Cancel after response (can't truly cancel mid-request without extra work)
            raise CancelledError()

        return TranscriptionResult(dialogue_id=dialogue_id, transcript=transcript)


class CancelledError(RuntimeError):
    pass

