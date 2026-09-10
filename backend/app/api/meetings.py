import re
from io import BytesIO
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile, status
from fastapi.responses import StreamingResponse

from app.api.dependencies import CurrentUser, Db
from app.core.config import get_settings
from app.core.security import new_id
from app.db.models import Feedback, MeetingVersion
from app.repositories import user_dict
from app.schemas import (
    FeedbackRequest,
    InviteRequest,
    SummaryRequest,
    TranscriptRequest,
)
from app.services.meetings import MeetingService
from app.services.pdf import create_minutes_pdf

router = APIRouter(prefix="/meetings", tags=["meetings"])


def get_service(db: Db) -> MeetingService:
    return MeetingService(db, get_settings())


@router.get("", response_model=None)
def list_meetings(user: CurrentUser, db: Db) -> list[dict[str, Any]]:
    return get_service(db).list(user.id)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_meeting(
    user: CurrentUser,
    db: Db,
    audio: UploadFile = File(...),  # noqa: B008
    title: str | None = Form(None),
) -> dict[str, Any]:
    return await get_service(db).create(user.id, audio, title)


@router.get("/{meeting_id}/participants")
def participants(meeting_id: str, user: CurrentUser, db: Db) -> list[dict[str, Any]]:
    manager = get_service(db)
    meeting, _ = manager.accessible(meeting_id, user.id)
    members = manager.meetings.members(meeting.id)
    return [{**user_dict(member), "access_role": role} for member, role in members]


@router.post("/{meeting_id}/participants", status_code=status.HTTP_201_CREATED)
def invite(
    meeting_id: str,
    request: InviteRequest,
    user: CurrentUser,
    db: Db,
) -> dict[str, Any]:
    manager = get_service(db)
    meeting, _ = manager.accessible(meeting_id, user.id, organizer=True)
    raw = request.emails or (request.email or "").split(",")
    emails = list(
        dict.fromkeys(email.lower().strip() for email in raw if email.strip())
    )[:20]
    if not emails:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one registered participant email is required.",
        )
    invited: list[dict[str, Any]] = []
    missing: list[str] = []
    for email in emails:
        member = manager.users.by_email(email)
        if not member:
            missing.append(email)
            continue
        role = "organizer" if member.id == meeting.owner_id else "participant"
        manager.meetings.add_member(meeting.id, member.id, role)
        invited.append(user_dict(member))

    db.commit()
    return {"invited": invited, "missing": missing}


@router.post("/{meeting_id}/transcribe")
def transcribe(meeting_id: str, user: CurrentUser, db: Db) -> dict[str, Any]:
    return get_service(db).transcribe(meeting_id, user.id)


@router.put("/{meeting_id}/transcript", status_code=status.HTTP_204_NO_CONTENT)
def update_transcript(
    meeting_id: str,
    request: TranscriptRequest,
    user: CurrentUser,
    db: Db,
) -> Response:
    meeting, _ = get_service(db).accessible(meeting_id, user.id, organizer=True)
    meeting.transcript = request.transcript.strip()
    meeting.status = "transcribed"
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{meeting_id}/analyze")
def analyze(meeting_id: str, user: CurrentUser, db: Db) -> dict[str, Any]:
    return get_service(db).analyze(meeting_id, user.id)


@router.put("/{meeting_id}/summary")
def update_summary(
    meeting_id: str,
    request: SummaryRequest,
    user: CurrentUser,
    db: Db,
) -> dict[str, Any]:
    manager = get_service(db)
    meeting, _ = manager.accessible(meeting_id, user.id, organizer=True)
    summary = request.summary.model_dump()
    meeting.summary = summary
    meeting.status = "saved"
    manager.meetings.add_version(
        MeetingVersion(
            id=new_id(),
            meeting_id=meeting.id,
            editor_id=user.id,
            summary=summary,
        )
    )
    db.commit()
    return {"summary": summary}


@router.delete("/{meeting_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_meeting(meeting_id: str, user: CurrentUser, db: Db) -> Response:
    meeting, _ = get_service(db).accessible(meeting_id, user.id, organizer=True)
    audio_path = Path(meeting.audio_path) if meeting.audio_path else None
    db.delete(meeting)
    db.commit()
    if audio_path:
        audio_path.unlink(missing_ok=True)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{meeting_id}/feedback", status_code=status.HTTP_201_CREATED)
def feedback(
    meeting_id: str,
    request: FeedbackRequest,
    user: CurrentUser,
    db: Db,
) -> dict[str, bool]:
    manager = get_service(db)
    meeting, _ = manager.accessible(meeting_id, user.id)
    manager.meetings.add_feedback(
        Feedback(
            id=new_id(),
            meeting_id=meeting.id,
            user_id=user.id,
            rating=request.rating,
            comment=request.comment,
        )
    )
    db.commit()
    return {"ok": True}


@router.get("/{meeting_id}/export.pdf")
def export_pdf(meeting_id: str, user: CurrentUser, db: Db) -> StreamingResponse:
    meeting, _ = get_service(db).accessible(meeting_id, user.id)
    clean_title = re.sub(r"[^a-zA-Z0-9]", "-", meeting.title)
    filename = f"{clean_title}-minutes.pdf"
    pdf_bytes = create_minutes_pdf(meeting.title, meeting.summary or {})
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
