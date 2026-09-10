from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.models import Meeting, MeetingMember, User

ORGANIZER_ID = "11111111-1111-4111-8111-111111111111"
PARTICIPANT_ID = "22222222-2222-4222-8222-222222222222"


def seed_demo_data(db: Session) -> None:
    users = [
        User(
            id=ORGANIZER_ID,
            name="Demo Organizer",
            email="admin@smartmom.test",
            role="organizer",
            password_hash=hash_password("Admin@12345"),
        ),
        User(
            id=PARTICIPANT_ID,
            name="Ayesha Participant",
            email="participant@smartmom.test",
            role="participant",
            password_hash=hash_password("Participant@12345"),
        ),
    ]
    for candidate in users:
        current = db.get(User, candidate.id)
        if current:
            current.name = candidate.name
            current.role = candidate.role
            current.password_hash = candidate.password_hash
        else:
            db.add(candidate)
    db.flush()

    meetings = [
        (
            "33333333-3333-4333-8333-333333333333",
            "FYP Progress Review",
            "saved",
            "Speaker 1: We reviewed the SmartMOM Bot requirements.\nSpeaker 2: Kalsoom will prepare the final demo script.",
            {
                "agenda": ["Review FYP requirements"],
                "decisions": ["Keep SmartMOM focused on AI meeting minutes"],
                "discussion": ["The team reviewed the final workflow."],
                "actions": [
                    {
                        "owner": "Kalsoom",
                        "task": "Prepare final demo script and screenshots",
                        "due": "Next supervisor meeting",
                    }
                ],
            },
        ),
        (
            "44444444-4444-4444-8444-444444444444",
            "Client Requirements Standup",
            "ready",
            "Speaker 1: The client asked for action items, decisions, and feedback.",
            {
                "agenda": ["Review client requests"],
                "decisions": ["Feedback remains part of review"],
                "discussion": [],
                "actions": [],
            },
        ),
        (
            "55555555-5555-4555-8555-555555555555",
            "Transcript Review Queue Sample",
            "transcribed",
            "Speaker 1: This sample is transcribed but not analyzed.",
            {
                "agenda": [],
                "decisions": [],
                "discussion": [],
                "actions": [],
            },
        ),
    ]

    for meeting_id, title, status, transcript, summary in meetings:
        meeting = db.get(Meeting, meeting_id)
        if not meeting:
            db.add(
                Meeting(
                    id=meeting_id,
                    owner_id=ORGANIZER_ID,
                    title=title,
                    status=status,
                    transcript=transcript,
                    summary=summary,
                    analysis={},
                )
            )
            db.flush()
        for user_id, role in (
            (ORGANIZER_ID, "organizer"),
            (PARTICIPANT_ID, "participant"),
        ):
            if not db.get(MeetingMember, (meeting_id, user_id)):
                db.add(
                    MeetingMember(
                        meeting_id=meeting_id,
                        user_id=user_id,
                        access_role=role,
                    )
                )
    db.commit()
