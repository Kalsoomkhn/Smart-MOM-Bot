from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import new_id
from app.db.models import Feedback, Meeting, MeetingVersion
from app.repositories import MeetingRepository, UserRepository, meeting_dict, user_dict
from app.services.analysis import AnalysisService
from app.services.transcription import TranscriptionService


class MeetingService:
    allowed_audio = {"audio/mpeg", "audio/wav", "audio/x-m4a", "audio/mp4", "audio/ogg", "audio/webm"}

    def __init__(self, db: Session, settings: Settings):
        self.db, self.settings = db, settings
        self.meetings, self.users = MeetingRepository(db), UserRepository(db)

    def accessible(self, meeting_id: str, user_id: str, organizer=False) -> tuple[Meeting, str]:
        found = self.meetings.accessible(meeting_id, user_id)
        if not found or (organizer and found[1] != "organizer"): raise HTTPException(404, "Meeting not found.")
        return found

    def list(self, user_id: str) -> list[dict]: return [meeting_dict(*row) for row in self.meetings.list_for(user_id)]

    async def create(self, user_id: str, audio: UploadFile, title: str | None) -> dict:
        if audio.content_type not in self.allowed_audio: raise HTTPException(400, "A supported audio file is required.")
        self.settings.upload_dir.mkdir(parents=True, exist_ok=True)
        suffix = Path(audio.filename or "audio").suffix
        destination = self.settings.upload_dir / f"{uuid4()}{suffix}"
        size = 0
        try:
            with destination.open("wb") as target:
                while chunk := await audio.read(1024 * 1024):
                    size += len(chunk)
                    if size > self.settings.max_upload_mb * 1024 * 1024: raise HTTPException(413, "Audio files must be below 200 MB.")
                    target.write(chunk)
        except Exception:
            destination.unlink(missing_ok=True); raise
        meeting = Meeting(id=new_id(), owner_id=user_id, title=(title or Path(audio.filename or "Meeting").stem)[:150], status="uploaded", audio_path=str(destination), audio_mime=audio.content_type, transcript="")
        self.db.add(meeting); self.meetings.add_member(meeting.id, user_id, "organizer"); self.db.commit()
        return {"id": meeting.id, "title": meeting.title, "status": "uploaded", "access_role": "organizer"}

    def transcribe(self, meeting_id: str, user_id: str) -> dict:
        meeting, _ = self.accessible(meeting_id, user_id, True)
        if not meeting.audio_path or not Path(meeting.audio_path).exists(): raise HTTPException(400, "No source audio is available for this meeting. Upload or record audio before transcription.")
        meeting.status = "transcribing"; self.db.commit()
        try:
            result = TranscriptionService(self.settings).transcribe(Path(meeting.audio_path))
            meeting.transcript, meeting.status = result["text"], "transcribed"; self.db.commit(); return result
        except Exception:
            meeting.status = "failed"; self.db.commit(); raise

    def analyze(self, meeting_id: str, user_id: str) -> dict:
        meeting, _ = self.accessible(meeting_id, user_id, True)
        if not (meeting.transcript or "").strip(): raise HTTPException(400, "Transcribe or enter a transcript first.")
        result = AnalysisService(self.settings).analyze(meeting.transcript)
        summary = {key: result.get(key, []) for key in ("agenda", "decisions", "discussion", "actions")}
        meeting.summary, meeting.analysis, meeting.status = summary, result.get("sentiment", {}), "ready"; self.db.commit()
        return {"summary": summary, "analysis": meeting.analysis, "mode": result.get("mode", "local")}
