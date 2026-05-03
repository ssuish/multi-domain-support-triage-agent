from pydantic import BaseModel, Field
from enum import StrEnum


class Status(StrEnum):
    REPLIED = "replied"
    ESCALATED = "escalated"


class Company(StrEnum):
    HACKERRANK = "hackerrank"
    CLAUDE = "claude"
    VISA = "visa"
    NONE = "none"


class RequestType(StrEnum):
    PRODUCT_ISSUE = "product_issue"
    FEATURE_REQUEST = "feature_request"
    BUG = "bug"
    INVALID = "invalid"


class PredictionOut(BaseModel):
    issue: str = Field(..., description="Full ticket issue / body text.")
    subject: str = Field(..., description="Ticket subject line.")
    company: Company = Field(
        ..., description="Which customer corpus applies (hackerrank, claude, visa)."
    )
    response: str = Field(..., description="Customer-facing reply or escalation notice.")
    product_area: str = Field(..., description="Short internal label for the product or topic.")
    status: Status = Field(..., description="replied if answered; escalated for human handoff.")
    request_type: RequestType = Field(
        ..., description="Classify as product_issue, feature_request, bug, or invalid."
    )
    justification: str = Field(
        ...,
        description="Evidence: cite rel_path or source_url for each factual claim.",
    )


class SupportTicketInput(BaseModel):
    issue: str = Field(..., description="Ticket issue / body as received.")
    subject: str = Field(..., description="Ticket subject as received.")
    company: str = Field(..., description="Company name or identifier from the ticket row.")
