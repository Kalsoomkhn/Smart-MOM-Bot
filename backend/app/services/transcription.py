import re
import subprocess
import tempfile
from pathlib import Path

from fastapi import HTTPException
from imageio_ffmpeg import get_ffmpeg_exe
from openai import OpenAI

from app.core.config import Settings


def speaker_turns_to_transcript(raw: str) -> dict:
    pieces = [part.strip() for part in re.split(r"(\[SPEAKER_TURN\])", raw.replace("\r", "")) if part.strip()]
    speaker, segments = 1, []
    for piece in pieces:
        if piece == "[SPEAKER_TURN]": speaker = 2 if speaker == 1 else 1; continue
        text = re.sub(r"^\[[\d:.]+\s*-->\s*[\d:.]+\]\s*", "", piece, flags=re.MULTILINE)
        text = re.sub(r"\s+", " ", text).strip()
        if text: segments.append({"speaker": f"Speaker {speaker}", "text": text})
    return {"text": "\n".join(f"{x['speaker']}: {x['text']}" for x in segments), "segments": segments}


class TranscriptionService:
    def __init__(self, settings: Settings): self.settings = settings

    def transcribe(self, audio_path: Path) -> dict:
        if self.settings.transcription_provider.lower() == "openai": return self._openai(audio_path)
        if self.settings.transcription_provider.lower() != "local": raise ValueError(f"Unsupported transcription provider: {self.settings.transcription_provider}")
        return self._local(audio_path)

    def _openai(self, audio_path: Path) -> dict:
        if not self.settings.openai_api_key: raise HTTPException(503, "OPENAI_API_KEY is required when TRANSCRIPTION_PROVIDER=openai.")
        with audio_path.open("rb") as audio:
            result = OpenAI(api_key=self.settings.openai_api_key).audio.transcriptions.create(file=audio, model=self.settings.openai_transcription_model, response_format="diarized_json", chunking_strategy="auto")
        segments = [{"speaker": getattr(x, "speaker", "Unknown Speaker"), "text": x.text} for x in (result.segments or [])]
        return {"text": "\n".join(f"{x['speaker']}: {x['text']}" for x in segments) or result.text, "segments": segments, "mode": "openai"}

    def _local(self, audio_path: Path) -> dict:
        executable, model = self.settings.whisper_cpp_path.resolve(), self.settings.whisper_model_path.resolve()
        if not executable.exists() or not model.exists(): raise HTTPException(503, "Local transcription is not installed. Run scripts/setup-local-whisper.ps1, then restart the API.")
        with tempfile.TemporaryDirectory(prefix="smartmom-") as temp:
            wav, output = Path(temp) / "audio.wav", Path(temp) / "transcript"
            subprocess.run([get_ffmpeg_exe(), "-y", "-i", str(audio_path), "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(wav)], check=True, capture_output=True)
            subprocess.run([str(executable), "-m", str(model), "-f", str(wav), "-tdrz", "-otxt", "-of", str(output), "-l", self.settings.whisper_language], check=True, capture_output=True)
            parsed = speaker_turns_to_transcript(output.with_suffix(".txt").read_text(encoding="utf-8"))
            if not parsed["text"]: raise ValueError("The local Whisper model did not detect any speech in this recording.")
            return {**parsed, "mode": "local-whisper"}
