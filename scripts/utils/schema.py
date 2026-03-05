"""
Pydantic models for Account Memo and Retell Agent Spec.
Defines the JSON schema for all pipeline outputs.
"""

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


# ─── Account Memo Schema ────────────────────────────────────────

class BusinessHours(BaseModel):
    days: list[str] = Field(default_factory=list, description="e.g. ['Monday','Tuesday',...]")
    start: str = Field(default="", description="e.g. '08:00'")
    end: str = Field(default="", description="e.g. '17:00'")
    timezone: str = Field(default="", description="e.g. 'America/New_York'")


class OfficeAddress(BaseModel):
    street: str = Field(default="")
    city: str = Field(default="")
    state: str = Field(default="")
    zip_code: str = Field(default="")
    country: str = Field(default="US")


class RoutingRule(BaseModel):
    contact_name: str = Field(default="")
    phone_number: str = Field(default="")
    role: str = Field(default="", description="e.g. 'On-call technician', 'Manager'")
    priority: int = Field(default=0, description="Order in the escalation chain")
    notes: str = Field(default="")


class CallTransferRules(BaseModel):
    timeout_seconds: Optional[int] = Field(default=60, description="How long to wait before fallback")
    max_retries: Optional[int] = Field(default=2)
    fallback_message: str = Field(
        default="I apologize, I'm unable to connect you right now. Let me take your information and have someone call you back as soon as possible.",
        description="What to say if transfer fails"
    )
    transfer_numbers: list[str] = Field(default_factory=list)
    notes: str = Field(default="")


class AccountMemo(BaseModel):
    """Structured account memo extracted from demo/onboarding calls."""
    account_id: str = Field(default="", description="Unique account identifier (auto-generated)")
    company_name: str = Field(default="")
    business_hours: BusinessHours = Field(default_factory=BusinessHours)
    office_address: OfficeAddress = Field(default_factory=OfficeAddress)
    services_supported: list[str] = Field(default_factory=list)
    emergency_definition: list[str] = Field(
        default_factory=list,
        description="List of triggers that constitute an emergency"
    )
    emergency_routing_rules: list[RoutingRule] = Field(
        default_factory=list,
        description="Who to call in order for emergencies"
    )
    non_emergency_routing_rules: list[RoutingRule] = Field(
        default_factory=list,
        description="Who to contact for non-emergency requests"
    )
    call_transfer_rules: CallTransferRules = Field(default_factory=CallTransferRules)
    integration_constraints: list[str] = Field(
        default_factory=list,
        description="e.g. 'never create sprinkler jobs in ServiceTrade'"
    )
    after_hours_flow_summary: str = Field(default="")
    office_hours_flow_summary: str = Field(default="")
    questions_or_unknowns: list[str] = Field(
        default_factory=list,
        description="Only if truly missing from the call"
    )
    notes: str = Field(default="")
    version: str = Field(default="v1")
    source: str = Field(default="demo", description="'demo' or 'onboarding'")

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)


# ─── Retell Agent Spec Schema ───────────────────────────────────

class RetellAgentSpec(BaseModel):
    """Retell-compatible agent configuration spec."""
    agent_name: str = Field(default="")
    version: str = Field(default="v1")
    version_description: str = Field(default="")
    voice_id: str = Field(default="retell-Cimo", description="Default Retell voice")
    voice_model: str = Field(default="eleven_turbo_v2")
    voice_style: str = Field(default="professional, warm, empathetic")
    voice_temperature: float = Field(default=0.8)
    voice_speed: float = Field(default=1.0)
    language: str = Field(default="en-US")
    system_prompt: str = Field(default="", description="The generated agent prompt")
    key_variables: dict = Field(
        default_factory=dict,
        description="timezone, business_hours, address, emergency_routing"
    )
    tool_invocation_placeholders: list[dict] = Field(
        default_factory=list,
        description="Tool definitions (never mentioned to caller)"
    )
    call_transfer_protocol: dict = Field(
        default_factory=dict,
        description="Transfer numbers, timeout, retries"
    )
    fallback_protocol: dict = Field(
        default_factory=dict,
        description="What to do if transfer fails"
    )
    enable_backchannel: bool = Field(default=True)
    backchannel_frequency: float = Field(default=0.8)
    interruption_sensitivity: float = Field(default=0.8)
    responsiveness: float = Field(default=0.9)
    end_call_after_silence_ms: int = Field(default=30000)
    max_call_duration_ms: int = Field(default=1800000)
    enable_voicemail_detection: bool = Field(default=True)
    voicemail_message: str = Field(default="")
    post_call_analysis_data: list[dict] = Field(default_factory=list)
    boosted_keywords: list[str] = Field(default_factory=list)

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)


# ─── Changelog Entry ────────────────────────────────────────────

class ChangelogEntry(BaseModel):
    field: str = Field(description="The field that changed")
    old_value: str = Field(default="")
    new_value: str = Field(default="")
    reason: str = Field(default="Updated from onboarding data")


class Changelog(BaseModel):
    account_id: str = Field(default="")
    company_name: str = Field(default="")
    from_version: str = Field(default="v1")
    to_version: str = Field(default="v2")
    changes: list[ChangelogEntry] = Field(default_factory=list)
    summary: str = Field(default="")

    def to_markdown(self) -> str:
        lines = [
            f"# Changelog: {self.company_name}",
            f"## {self.from_version} → {self.to_version}",
            "",
            f"**Account ID:** {self.account_id}",
            "",
            f"### Summary",
            self.summary,
            "",
            "### Changes",
            "",
            "| Field | Old Value | New Value | Reason |",
            "|-------|-----------|-----------|--------|"
        ]
        for c in self.changes:
            old_val = c.old_value[:80] + "..." if len(c.old_value) > 80 else c.old_value
            new_val = c.new_value[:80] + "..." if len(c.new_value) > 80 else c.new_value
            lines.append(f"| {c.field} | {old_val} | {new_val} | {c.reason} |")
        return "\n".join(lines)

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)
