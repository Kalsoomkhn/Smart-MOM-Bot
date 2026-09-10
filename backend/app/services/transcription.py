import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from openai import OpenAI
from transformers import pipeline

from app.core.config import Settings


@lru_cache(maxsize=2)
def _get_hf_asr_pipeline(model_name: str) -> Any:
    return pipeline("automatic-speech-recognition", model=model_name)


def speaker_turns_to_transcript(raw: str) -> dict[str, Any]:
    pieces = [
        part.strip()
        for part in re.split(r"(\[SPEAKER_TURN\])", raw.replace("\r", ""))
        if part.strip()
    ]
    speaker = 1
    segments: list[dict[str, str]] = []
    for piece in pieces:
        if piece == "[SPEAKER_TURN]":
            speaker = 2 if speaker == 1 else 1
            continue
        text = re.sub(r"^\[[\d:.]+\s*-->\s*[\d:.]+\]\s*", "", piece, flags=re.MULTILINE)
        text = re.sub(r"\s+", " ", text).strip()
        if text:
            segments.append({"speaker": f"Speaker {speaker}", "text": text})
    formatted_text = "\n".join(f"{x['speaker']}: {x['text']}" for x in segments)
    return {"text": formatted_text, "segments": segments}


class TranscriptionService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def transcribe(self, audio_path: Path) -> dict[str, Any]:
        provider = self.settings.transcription_provider.lower()
        if provider == "openai":
            return self._openai(audio_path)
        if provider in ("local", "hf", "huggingface"):
            return self._local_hf(audio_path)
        raise ValueError(
            f"Unsupported transcription provider: {self.settings.transcription_provider}"
        )

    def _openai(self, audio_path: Path) -> dict[str, Any]:
        if not self.settings.openai_api_key:
            raise HTTPException(
                status_code=503,
                detail="OPENAI_API_KEY is required when TRANSCRIPTION_PROVIDER=openai.",
            )
        with audio_path.open("rb") as audio:
            client = OpenAI(api_key=self.settings.openai_api_key)
            result = client.audio.transcriptions.create(
                file=audio,
                model=self.settings.openai_transcription_model,
                response_format="diarized_json",
                chunking_strategy="auto",
            )
        raw_segments = getattr(result, "segments", []) or []
        segments = [
            {"speaker": getattr(x, "speaker", "Unknown Speaker"), "text": x.text}
            for x in raw_segments
        ]
        formatted_text = "\n".join(
            f"{x['speaker']}: {x['text']}" for x in segments
        ) or getattr(result, "text", "")
        return {
            "text": formatted_text,
            "segments": segments,
            "mode": "openai",
        }

    def _local_hf(self, audio_path: Path) -> dict[str, Any]:
        try:
            asr = _get_hf_asr_pipeline(self.settings.hf_transcription_model)
            out = asr(str(audio_path), return_timestamps=True)
            text = (
                out.get("text", "").strip()
                if isinstance(out, dict)
                else str(out).strip()
            )
            raw_chunks = out.get("chunks", []) if isinstance(out, dict) else []
            segments: list[dict[str, str]] = []
            if raw_chunks:
                for idx, chunk in enumerate(raw_chunks, start=1):
                    chunk_text = chunk.get("text", "").strip()
                    if chunk_text:
                        segments.append(
                            {"speaker": f"Speaker {1 + (idx % 2)}", "text": chunk_text}
                        )
            else:
                segments = [{"speaker": "Speaker 1", "text": text}]
            return {
                "text": "\n".join(f"{s['speaker']}: {s['text']}" for s in segments)
                if len(segments) > 1
                else text,
                "segments": segments,
                "mode": "local-hf-whisper",
            }
        except Exception as err:  # noqa: BLE001
            raise HTTPException(
                status_code=500,
                detail=f"Hugging Face transformers transcription error: {err!s}",
            )
