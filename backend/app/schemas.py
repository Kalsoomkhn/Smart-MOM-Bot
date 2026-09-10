from typing import Annotated, Literal

from email_validator import EmailNotValidError, validate_email
from pydantic import AfterValidator, BaseModel, Field


def _clean_email(v: str) -> str:
    if not isinstance(v, str) or "@" not in v:
        raise ValueError("An email address must contain @.")
    try:
        return validate_email(
            v.strip(), check_deliverability=False, test_environment=True
        ).normalized
    except EmailNotValidError as e:
        raise ValueError(str(e))


ValidEmail = Annotated[str, AfterValidator(_clean_email)]
Role = Literal["organizer", "participant"]


class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    email: ValidEmail
    password: str = Field(min_length=10)
    role: Role = "organizer"


class LoginRequest(BaseModel):
    email: ValidEmail
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
