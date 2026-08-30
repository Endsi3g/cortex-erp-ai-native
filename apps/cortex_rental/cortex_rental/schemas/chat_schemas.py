"""
Pydantic v2 models for the Cortex Chat Gateway (cortex_rental.api.v1.chat).

Two things this module deliberately does NOT let a client control, by
construction rather than by a runtime check someone could forget:
`company`, `agent`, `model`, and `allowed_tool_ids` simply have no field
on `SendMessageRequest`/`ChatContext` — and both models set
`extra="forbid"`, so a client that tries to sneak one in gets a hard
validation error, not a silently-ignored field. Those four values are
always server-resolved (get_company_context(), AgentRouter,
ToolPolicyResolver — see the sibling services/ modules).

`pydantic` is a real dependency of this app (see pyproject.toml,
matching apps/cortex-mcp's own `pydantic>=2.5.0` pin) — not an optional
one like `frappe`/`jsonschema` elsewhere in this codebase, because
there is no meaningful degraded mode for request validation: if
pydantic isn't installed, the chat endpoints simply aren't usable,
same as if `frappe` itself were missing.
"""

from typing import Annotated, Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

MAX_MESSAGE_LENGTH = 4000
MAX_SELECTED_IDS = 50
MAX_FILTER_KEYS = 20


class VisibleDateRange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start: str
    end: str


class ChatContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page: str = Field(min_length=1, max_length=64)
    active_doctype: Optional[str] = Field(default=None, max_length=140)
    active_document_name: Optional[str] = Field(default=None, max_length=140)
    selected_item_codes: List[str] = Field(default_factory=list, max_length=MAX_SELECTED_IDS)
    selected_serial_nos: List[str] = Field(default_factory=list, max_length=MAX_SELECTED_IDS)
    visible_date_range: Optional[VisibleDateRange] = None
    active_filters: Dict[str, Any] = Field(default_factory=dict, max_length=MAX_FILTER_KEYS)
    locale: Literal["fr-CA", "en-CA"] = "fr-CA"


class SendMessageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chat_session_id: Optional[str] = None
    message: str = Field(min_length=1, max_length=MAX_MESSAGE_LENGTH)
    context: ChatContext


# ---------------------------------------------------------------------
# Response blocks — see docs/design-system.md's chat spec "Blocs de
# message Cortex" for the rationale (never render an unverified model
# claim with the same visual weight as a real API fact).
# ---------------------------------------------------------------------


class VerifiedFactBlock(BaseModel):
    type: Literal["verified_fact"] = "verified_fact"
    title: str
    items: List[str]
    source_ids: List[str] = Field(default_factory=list)
    checked_at: str


class ExtractedField(BaseModel):
    label: str
    value: str
    confidence: Literal["high", "medium", "low"]
    evidence_id: Optional[str] = None


class ExtractedDataBlock(BaseModel):
    type: Literal["extracted_data"] = "extracted_data"
    title: str
    fields: List[ExtractedField]


class ProposalBlock(BaseModel):
    type: Literal["proposal"] = "proposal"
    title: str
    summary: str
    impact: List[str] = Field(default_factory=list)
    action: Literal["open_quote_composer", "create_quote_draft"]
    draft_id: Optional[str] = None
    requires_approval: bool = False


class ApprovalRequirement(BaseModel):
    label: str
    passed: bool


class ApprovalRequiredBlock(BaseModel):
    type: Literal["approval_required"] = "approval_required"
    approval_request_id: str
    action_label: str
    requirements: List[ApprovalRequirement] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)


class RiskBlock(BaseModel):
    type: Literal["risk"] = "risk"
    severity: Literal["info", "warning", "danger"]
    title: str
    explanation: str
    source_ids: List[str] = Field(default_factory=list)


class MissingInformationBlock(BaseModel):
    type: Literal["missing_information"] = "missing_information"
    fields: List[str]
    suggested_next_action: Optional[str] = None


class ToolProgressBlock(BaseModel):
    type: Literal["tool_progress"] = "tool_progress"
    tool_name: str
    state: Literal["running", "success", "failed"]
    message: str


class ErrorBlock(BaseModel):
    type: Literal["error"] = "error"
    title: str
    safe_message: str
    retry_allowed: bool = True


ChatBlock = Annotated[
    Union[
        VerifiedFactBlock,
        ExtractedDataBlock,
        ProposalBlock,
        ApprovalRequiredBlock,
        RiskBlock,
        MissingInformationBlock,
        ToolProgressBlock,
        ErrorBlock,
    ],
    Field(discriminator="type"),
]


class SendMessageResponseData(BaseModel):
    message_id: str
    chat_session_id: str
    status: Literal["completed", "processing"] = "completed"
    blocks: List[ChatBlock]
