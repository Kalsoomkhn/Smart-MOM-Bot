from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator


Role = Literal["organizer", "participant"]


class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    email: EmailStr
    password: str = Field(min_length=10)
    role: Role = "organizer"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RoleRequest(BaseModel):
    role: Role


class InviteRequest(BaseModel):
    email: str | None = None
    emails: list[str] | None = None


class TranscriptRequest(BaseModel):
    transcript: str = Field(min_length=1)


class ActionItem(BaseModel):
    owner: str = "Unassigned"
    task: str
    due: str = "Not specified"


class Summary(BaseModel):
    agenda: list[str]
    decisions: list[str]
    discussion: list[str] = Field(default_factory=list)
    actions: list[ActionItem]


class SummaryRequest(BaseModel):
    summary: Summary


class FeedbackRequest(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str = Field(default="", max_length=2000)
