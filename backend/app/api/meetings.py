import re
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, File, Form, Response, UploadFile
from fastapi.responses import StreamingResponse

from app.api.dependencies import CurrentUser, Db
from app.core.config import get_settings
from app.core.security import new_id
from app.db.models import Feedback, MeetingVersion
from app.repositories import user_dict
from app.schemas import FeedbackRequest, InviteRequest, SummaryRequest, TranscriptRequest
from app.services.meetings import MeetingService
from app.services.pdf import create_minutes_pdf

router = APIRouter(prefix="/meetings", tags=["meetings"])


def service(db: Db) -> MeetingService: return MeetingService(db, get_settings())


@router.get("")
def list_meetings(user: CurrentUser, db: Db): return service(db).list(user.id)


@router.post("", status_code=201)
async def create_meeting(user: CurrentUser, db: Db, audio: UploadFile = File(...), title: str | None = Form(None)):
    return await service(db).create(user.id, audio, title)


@router.get("/{meeting_id}/participants")
def participants(meeting_id: str, user: CurrentUser, db: Db):
    manager = service(db); meeting, _ = manager.accessible(meeting_id, user.id)
    return [{**user_dict(member), "access_role": role} for member, role in manager.meetings.members(meeting.id)]


@router.post("/{meeting_id}/participants", status_code=201)
def invite(meeting_id: str, request: InviteRequest, user: CurrentUser, db: Db):
    manager = service(db); meeting, _ = manager.accessible(meeting_id, user.id, True)
    raw = request.emails or (request.email or "").split(",")
    emails = list(dict.fromkeys(email.lower().strip() for email in raw if email.strip()))[:20]
    if not emails: from fastapi import HTTPException; raise HTTPException(400, "At least one registered participant email is required.")
    invited, missing = [], []
    for email in emails:
        member = manager.users.by_email(email)
        if not member: missing.append(email); continue
        manager.meetings.add_member(meeting.id, member.id, "organizer" if member.id == meeting.owner_id else "participant")
        invited.append(user_dict(member))
    db.commit(); return {"invited": invited, "missing": missing}


@router.post("/{meeting_id}/transcribe")
def transcribe(meeting_id: str, user: CurrentUser, db: Db): return service(db).transcribe(meeting_id, user.id)


@router.put("/{meeting_id}/transcript", status_code=204)
def update_transcript(meeting_id: str, request: TranscriptRequest, user: CurrentUser, db: Db):
    meeting, _ = service(db).accessible(meeting_id, user.id, True)
    meeting.transcript, meeting.status = request.transcript.strip(), "transcribed"; db.commit(); return Response(status_code=204)


@router.post("/{meeting_id}/analyze")
def analyze(meeting_id: str, user: CurrentUser, db: Db): return service(db).analyze(meeting_id, user.id)


@router.put("/{meeting_id}/summary")
def update_summary(meeting_id: str, request: SummaryRequest, user: CurrentUser, db: Db):
    manager = service(db); meeting, _ = manager.accessible(meeting_id, user.id, True)
    summary = request.summary.model_dump(); meeting.summary, meeting.status = summary, "saved"
    manager.meetings.add_version(MeetingVersion(id=new_id(), meeting_id=meeting.id, editor_id=user.id, summary=summary)); db.commit()
    return {"summary": summary}


@router.delete("/{meeting_id}", status_code=204)
def delete_meeting(meeting_id: str, user: CurrentUser, db: Db):
    meeting, _ = service(db).accessible(meeting_id, user.id, True)
    audio_path = Path(meeting.audio_path) if meeting.audio_path else None
    db.delete(meeting); db.commit()
    if audio_path: audio_path.unlink(missing_ok=True)
    return Response(status_code=204)


@router.post("/{meeting_id}/feedback", status_code=201)
def feedback(meeting_id: str, request: FeedbackRequest, user: CurrentUser, db: Db):
    manager = service(db); meeting, _ = manager.accessible(meeting_id, user.id)
    manager.meetings.add_feedback(Feedback(id=new_id(), meeting_id=meeting.id, user_id=user.id, rating=request.rating, comment=request.comment)); db.commit()
    return {"ok": True}


@router.get("/{meeting_id}/export.pdf")
def export_pdf(meeting_id: str, user: CurrentUser, db: Db):
    meeting, _ = service(db).accessible(meeting_id, user.id)
    filename = re.sub(r"[^a-zA-Z0-9]", "-", meeting.title) + "-minutes.pdf"
    return StreamingResponse(BytesIO(create_minutes_pdf(meeting.title, meeting.summary or {})), media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{filename}"'})
