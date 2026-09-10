from pathlib import Path
from typing import Any, ClassVar
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import new_id
from app.db.models import Meeting
from app.repositories import MeetingRepository, UserRepository, meeting_dict
from app.services.analysis import AnalysisService
from app.services.transcription import TranscriptionService


class MeetingService:
    allowed_audio: ClassVar[set[str]] = {
        "audio/mpeg",
        "audio/wav",
        "audio/x-m4a",
        "audio/mp4",
        "audio/ogg",
        "audio/webm",
    }

    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.meetings = MeetingRepository(db)
        self.users = UserRepository(db)

    def accessible(
        self, meeting_id: str, user_id: str, organizer: bool = False
    ) -> tuple[Meeting, str]:
        found = self.meetings.accessible(meeting_id, user_id)
        if not found or (organizer and found[1] != "organizer"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Meeting not found.",
            )
        return found

    def list(self, user_id: str) -> list[dict[str, Any]]:
        return [meeting_dict(*row) for row in self.meetings.list_for(user_id)]

    async def create(
        self, user_id: str, audio: UploadFile, title: str | None
    ) -> dict[str, Any]:
        if audio.content_type not in self.allowed_audio:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A supported audio file is required.",
            )
        self.settings.upload_dir.mkdir(parents=True, exist_ok=True)
        suffix = Path(audio.filename or "audio").suffix
        destination = self.settings.upload_dir / f"{uuid4()}{suffix}"
        size = 0
        try:
            with destination.open("wb") as target:
                while chunk := await audio.read(1024 * 1024):
                    size += len(chunk)
                    if size > self.settings.max_upload_mb * 1024 * 1024:
                        raise HTTPException(
                            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            detail="Audio files must be below 200 MB.",
                        )
                    target.write(chunk)
        except Exception:
            destination.unlink(missing_ok=True)
            raise

        meeting_title = (title or Path(audio.filename or "Meeting").stem)[:150]
        meeting = Meeting(
            id=new_id(),
            owner_id=user_id,
            title=meeting_title,
            status="uploaded",
            audio_path=str(destination),
            audio_mime=audio.content_type,
            transcript="",
        )
        self.db.add(meeting)
        self.meetings.add_member(meeting.id, user_id, "organizer")
        self.db.commit()
        return {
            "id": meeting.id,
            "title": meeting.title,
            "status": "uploaded",
            "access_role": "organizer",
        }

    def transcribe(self, meeting_id: str, user_id: str) -> dict[str, Any]:
        meeting, _ = self.accessible(meeting_id, user_id, organizer=True)
        if not meeting.audio_path or not Path(meeting.audio_path).exists():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No source audio is available for this meeting. Upload or record audio before transcription.",
            )
        meeting.status = "transcribing"
        self.db.commit()
        try:
            result = TranscriptionService(self.settings).transcribe(
                Path(meeting.audio_path)
            )
            meeting.transcript = result["text"]
            meeting.status = "transcribed"
            self.db.commit()
            return result
        except Exception:
            meeting.status = "failed"
            self.db.commit()
            raise

    def analyze(self, meeting_id: str, user_id: str) -> dict[str, Any]:
        meeting, _ = self.accessible(meeting_id, user_id, organizer=True)
        if not (meeting.transcript or "").strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Transcribe or enter a transcript first.",
            )
        result = AnalysisService(self.settings).analyze(meeting.transcript)
        summary = {
            key: result.get(key, [])
            for key in ("agenda", "decisions", "discussion", "actions")
        }
        meeting.summary = summary
        meeting.analysis = result.get("sentiment", {})
        meeting.status = "ready"
        self.db.commit()
        return {
            "summary": summary,
            "analysis": meeting.analysis,
            "mode": result.get("mode", "local"),
        }
