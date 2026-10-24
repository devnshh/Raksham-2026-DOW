"""Pydantic v2 data models and API schemas for SATARK."""

from typing import Any, Optional
from pydantic import BaseModel, Field, model_validator


class SessionSignals(BaseModel):
    """Raw device and session dynamics sent by the client SDK."""
    on_call: bool = False
    # On a call with someone saved in the user's contacts. None means not measured (no permission,
    # an outgoing or internet call), which scores like an unknown caller.
    caller_in_contacts: Optional[bool] = None
    screen_shared: bool = False
    remote_app_present: bool = False
    remote_app_new: bool = False
    app_switches: int = 0
    # Measured on the phone; None means "not measured" and scores as no evidence.
    typing_ms: Optional[float] = None
    pauses: Optional[int] = None
    # Unknown before the PIN screen; only sent with /v1/payments/complete.
    pin_secs: Optional[float] = None
    device_new: bool = False
    failed_auth: int = 0


class ContextSignals(BaseModel):
    """Contextual metadata surrounding the payment entry."""
    note_intent: Optional[str] = None
    # Deprecated: the app sends only note_intent. If an old client sends text, it is used to
    # derive the intent and then discarded (never stored).
    note_text: Optional[str] = None
    link_domain: Optional[str] = None
    link_bad: Optional[bool] = None
    link_domain_age_days: Optional[float] = None
    secs_link_to_pay: Optional[float] = None


class RiskAssessmentRequest(BaseModel):
    """
    Risk assessment input payload according to README Section 17 contract.
    Accepts user_ref or user_id for flexible compatibility.
    """
    txn_ref: Optional[str] = None
    user_ref: Optional[str] = None
    user_id: Optional[str] = None
    payee_vpa: str
    amount: float
    entry_channel: str = "typed_vpa"
    session: SessionSignals = Field(default_factory=SessionSignals)
    context: ContextSignals = Field(default_factory=ContextSignals)
    questionnaire_answers: Optional[dict[str, Any]] = None

    @model_validator(mode="after")
    def unify_user_reference(self) -> "RiskAssessmentRequest":
        # Ensure either user_ref or user_id is populated
        if not self.user_ref and self.user_id:
            self.user_ref = self.user_id
        elif not self.user_ref:
            self.user_ref = "default_user"
        return self


class RiskAssessmentResponse(BaseModel):
    """
    STRICT response contract from README Section 17:
    ONLY {tier, reasons[], template_id, hold_minutes, case_id}.
    Never returns score or model weights to the app.
    """
    tier: str
    reasons: list[str]
    template_id: str
    hold_minutes: int
    case_id: str


class ReportRequest(BaseModel):
    """User scam reporting request payload."""
    reporter_id: str
    payee_vpa: str
    reason: str
    notes: Optional[str] = ""


class ReportResponse(BaseModel):
    """Response confirming user scam report."""
    status: str = "success"
    report_id: str
    payee_vpa: str
    prior_reports_count: int


class ConfirmScamRequest(BaseModel):
    """Analyst confirmation request payload. Two distinct analysts required."""
    analyst_id: str
    notes: Optional[str] = ""


class ConfirmScamResponse(BaseModel):
    """Analyst confirmation result."""
    payee_vpa: str
    analyst_id: str
    total_confirmations: int
    is_confirmed_scam: bool
    status: str  # "pending_second_analyst" or "analyst_confirmed_scam"


class CaseResponse(BaseModel):
    """Evidence case record for security review."""
    case_id: str
    user_ref: str
    payee_vpa: str
    amount: float
    tier: str
    reasons: list[str]
    template_id: str
    hold_minutes: int
    created_at: str
    status: str = "open"  # "open", or "completed" once the app reported the payment done
    dispute: Optional[str] = None  # "this_was_me", "false_alarm_pending" or "false_alarm_accepted"
    evidence_pack: Optional[dict[str, Any]] = None


class PolicyResponse(BaseModel):
    """Active policy configuration schema."""
    version: str
    rules: dict[str, Any]


class HealthResponse(BaseModel):
    """System health and audit chain verification status."""
    status: str
    database: str
    audit_chain: str
    policy_version: str
    model_version: str


class QuestionnaireRequest(BaseModel):
    """Answers to the red-tier check, attached to an existing case."""
    user_ref: str
    answers: dict[str, Any]


class AppealRequest(BaseModel):
    """The user disputes a warning on their own case."""
    user_ref: str


class AppealResponse(BaseModel):
    case_id: str
    status: str  # "payee_trusted" (amber, This was me) or "sent_for_review" (red or decline)


class PaymentCompleteRequest(BaseModel):
    """Sent by the app after the PIN succeeds. Only completed payments update baselines and fan-in."""
    case_id: str
    user_ref: str
    payee_vpa: str
    amount: float
    typing_ms: Optional[float] = None
    pauses: Optional[int] = None
    pin_secs: Optional[float] = None


class PaymentCompleteResponse(BaseModel):
    status: str
    case_id: str
