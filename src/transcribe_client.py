from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import requests

from exceptions import CancelledError

__all__ = ["TranscribeClient", "TranscriptionResult", "CancelledError"]


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
        cancel_check: Callable[[], bool] | None = None,
    ) -> TranscriptionResult:
        candidate_fields: list[str] = []
        for name in (file_field, "file", "audio_file", "audio", "upload_file"):
            if name and name not in candidate_fields:
                candidate_fields.append(name)

        resp: requests.Response | None = None
        for current_field in candidate_fields:
            files = {
                current_field: (filename, file_bytes, "audio/wav"),
            }
            resp = requests.post(
                self.endpoint,
                files=files,
                data={"dialogue_id": filename},
                timeout=self.timeout_sec,
            )
            # 422 often means "wrong multipart field name"; try known alternatives.
            if resp.status_code == 422 and current_field != candidate_fields[-1]:
                continue
            break

        assert resp is not None
        try:
            resp.raise_for_status()
        except requests.HTTPError as e:
            detail = _extract_error_detail(resp)
            if detail:
                raise requests.HTTPError(
                    f"{e}. Service response: {detail}",
                    response=resp,
                    request=getattr(e, "request", None),
                ) from e
            raise

        data = resp.json()
        dialogue_id = str(data.get("dialogue_id") or data.get("dialogueId") or "")
        transcript = str(data.get("transcript") or data.get("text") or data.get("result") or "")

        if not dialogue_id:
            dialogue_id = filename

        if cancel_check and cancel_check():
            # Cancel after response (can't truly cancel mid-request without extra work)
            raise CancelledError()

        return TranscriptionResult(dialogue_id=dialogue_id, transcript=transcript)


def _extract_error_detail(resp: requests.Response) -> str:
    try:
        data = resp.json()
    except Exception:
        return (resp.text or "").strip()

    if isinstance(data, dict):
        detail = data.get("detail")
        if detail is not None:
            return str(detail)
        return str(data)
    return str(data)

