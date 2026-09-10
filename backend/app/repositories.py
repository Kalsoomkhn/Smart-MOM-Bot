from typing import Any

from sqlalchemy import case, or_, select
from sqlalchemy.orm import Session

from app.db.models import Feedback, Meeting, MeetingMember, MeetingVersion, User


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        return self.db.scalar(stmt)

    def by_id(self, user_id: str) -> User | None:
        return self.db.get(User, user_id)

    def add(self, user: User) -> User:
        self.db.add(user)
        self.db.flush()
        return user


class MeetingRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def accessible(self, meeting_id: str, user_id: str) -> tuple[Meeting, str] | None:
        stmt = (
            select(
                Meeting,
                case(
                    (Meeting.owner_id == user_id, "organizer"),
                    else_=MeetingMember.access_role,
                ),
            )
            .outerjoin(
                MeetingMember,
                (MeetingMember.meeting_id == Meeting.id)
                & (MeetingMember.user_id == user_id),
            )
            .where(
                Meeting.id == meeting_id,
                or_(Meeting.owner_id == user_id, MeetingMember.user_id == user_id),
            )
        )
        row = self.db.execute(stmt).first()
        if not row:
            return None
        return (row[0], row[1])

    def list_for(self, user_id: str) -> list[tuple[Meeting, str]]:
        stmt = (
            select(
                Meeting,
                case(
                    (Meeting.owner_id == user_id, "organizer"),
                    else_=MeetingMember.access_role,
                ),
            )
            .outerjoin(
                MeetingMember,
                (MeetingMember.meeting_id == Meeting.id)
                & (MeetingMember.user_id == user_id),
            )
            .where(or_(Meeting.owner_id == user_id, MeetingMember.user_id == user_id))
            .order_by(Meeting.created_at.desc())
        )
        return list(self.db.execute(stmt).all())

    def members(self, meeting_id: str) -> list[tuple[User, str]]:
        stmt = (
            select(User, MeetingMember.access_role)
            .join(MeetingMember, User.id == MeetingMember.user_id)
            .where(MeetingMember.meeting_id == meeting_id)
            .order_by(MeetingMember.created_at)
        )
        return list(self.db.execute(stmt).all())

    def add_member(self, meeting_id: str, user_id: str, role: str) -> None:
        member = self.db.get(MeetingMember, (meeting_id, user_id))
        if member:
            member.access_role = role
        else:
            self.db.add(
                MeetingMember(meeting_id=meeting_id, user_id=user_id, access_role=role)
            )

    def add_version(self, version: MeetingVersion) -> None:
        self.db.add(version)

    def add_feedback(self, feedback: Feedback) -> None:
        self.db.add(feedback)


def user_dict(user: User) -> dict[str, Any]:
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role or "organizer",
    }


def meeting_dict(meeting: Meeting, access_role: str) -> dict[str, Any]:
    return {
        "id": meeting.id,
        "title": meeting.title,
        "status": meeting.status,
        "transcript": meeting.transcript or "",
        "summary": meeting.summary,
        "analysis": meeting.analysis,
        "created_at": meeting.created_at,
        "updated_at": meeting.updated_at,
        "access_role": access_role,
    }
