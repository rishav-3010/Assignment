"""
Pipeline A (Part 2): Account Memo -> Retell Agent Draft Spec
Takes an account_memo.json and generates a Retell-compatible agent spec.
"""

import os
import sys
import json
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.utils.storage import load_json, save_json
from scripts.utils.schema import RetellAgentSpec, AccountMemo


def load_prompt_template() -> str:
    """Load the agent prompt template."""
    template_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "templates", "agent_prompt_template.txt"
    )
    with open(template_path, 'r', encoding='utf-8') as f:
        return f.read()


def build_system_prompt(memo: dict) -> str:
    """Generate the system prompt from account memo data and template."""
    template = load_prompt_template()

    company_name = memo.get("company_name", "the company")
    bh = memo.get("business_hours", {})
    addr = memo.get("office_address", {})

    # Format business hours
    days = bh.get("days", [])
    bh_days = ", ".join(days) if days else "Monday through Friday"
    bh_start = bh.get("start", "8:00 AM")
    bh_end = bh.get("end", "5:00 PM")
    timezone = bh.get("timezone", "")

    # Format address
    addr_parts = [
        addr.get("street", ""),
        addr.get("city", ""),
        addr.get("state", ""),
        addr.get("zip_code", "")
    ]
    office_address = ", ".join(p for p in addr_parts if p) or "Not specified"

    # Format services
    services = memo.get("services_supported", [])
    services_list = ", ".join(services) if services else "General services"

    # Format emergency definitions
    emergencies = memo.get("emergency_definition", [])
    emergency_defs = ", ".join(emergencies) if emergencies else "Situations requiring immediate attention"

    # Format emergency routing
    emergency_rules = memo.get("emergency_routing_rules", [])
    emergency_routing_text = ""
    if emergency_rules:
        lines = ["   - Emergency routing:"]
        for rule in sorted(emergency_rules, key=lambda r: r.get("priority", 0)):
            name = rule.get("contact_name", "On-call")
            phone = rule.get("phone_number", "")
            role = rule.get("role", "")
            lines.append(f"     - Priority {rule.get('priority', 1)}: {name} ({role}) at {phone}")
        emergency_routing_text = "\n".join(lines)
    else:
        emergency_routing_text = "   - Transfer to the main emergency contact line."

    # Format non-emergency routing
    non_emergency_rules = memo.get("non_emergency_routing_rules", [])
    non_emergency_text = ""
    if non_emergency_rules:
        lines = ["   - Non-emergency routing:"]
        for rule in sorted(non_emergency_rules, key=lambda r: r.get("priority", 0)):
            name = rule.get("contact_name", "Office")
            phone = rule.get("phone_number", "")
            role = rule.get("role", "")
            lines.append(f"     - {name} ({role}) at {phone}")
        non_emergency_text = "\n".join(lines)
    else:
        non_emergency_text = "   - Route to the main office line."

    # Transfer rules
    transfer_rules = memo.get("call_transfer_rules", {})
    timeout = transfer_rules.get("timeout_seconds", 60)
    retries = transfer_rules.get("max_retries", 2)
    fallback = transfer_rules.get("fallback_message",
        "I apologize, I'm unable to connect you right now. Let me take your information and have someone call you back as soon as possible.")
    transfer_numbers = transfer_rules.get("transfer_numbers", [])

    # Integration constraints
    constraints = memo.get("integration_constraints", [])
    constraints_section = ""
    if constraints:
        constraints_section = "## INTEGRATION CONSTRAINTS\n" + "\n".join(f"- {c}" for c in constraints)

    # Additional notes
    additional = ""
    notes = memo.get("notes", "")
    if notes:
        additional = f"## ADDITIONAL NOTES\n{notes}"

    # Fill template
    prompt = template.replace("{company_name}", company_name)
    prompt = prompt.replace("{business_hours_days}", bh_days)
    prompt = prompt.replace("{business_hours_start}", bh_start)
    prompt = prompt.replace("{business_hours_end}", bh_end)
    prompt = prompt.replace("{timezone}", timezone or "local time")
    prompt = prompt.replace("{office_address}", office_address)
    prompt = prompt.replace("{services_list}", services_list)
    prompt = prompt.replace("{emergency_definitions}", emergency_defs)
    prompt = prompt.replace("{emergency_routing_during_hours}", emergency_routing_text)
    prompt = prompt.replace("{non_emergency_routing}", non_emergency_text)
    prompt = prompt.replace("{transfer_timeout}", str(timeout))
    prompt = prompt.replace("{max_retries}", str(retries))
    prompt = prompt.replace("{fallback_message}", fallback)
    prompt = prompt.replace("{emergency_transfer_numbers}", ", ".join(transfer_numbers) if transfer_numbers else "main on-call number")
    prompt = prompt.replace("{next_business_day}", "the next business day")
    prompt = prompt.replace("{closing_message}", "We appreciate your call!")
    prompt = prompt.replace("{integration_constraints_section}", constraints_section)
    prompt = prompt.replace("{additional_notes}", additional)

    return prompt


def generate_agent_spec(account_id: str, version: str = "v1") -> RetellAgentSpec:
    """
    Generate a Retell Agent Draft Spec from the account memo.
    
    Args:
        account_id: The account ID to look up
        version: Which version of the memo to use
    
    Returns:
        RetellAgentSpec model
    """
    print(f"\n{'='*60}")
    print(f"🤖 Generating Retell Agent Spec for: {account_id} ({version})")
    print(f"{'='*60}")

    # Load account memo
    memo = load_json(account_id, "account_memo.json", version)
    if not memo:
        raise FileNotFoundError(f"No account memo found for {account_id}/{version}")

    company_name = memo.get("company_name", "Unknown")
    bh = memo.get("business_hours", {})
    transfer_rules = memo.get("call_transfer_rules", {})

    # Generate system prompt
    print("  📝 Building system prompt from template...")
    system_prompt = build_system_prompt(memo)

    # Build agent spec
    spec = RetellAgentSpec(
        agent_name=f"Clara - {company_name}",
        version=version,
        version_description=f"{'Preliminary agent from demo call' if version == 'v1' else 'Updated agent after onboarding'}",
        system_prompt=system_prompt,
        key_variables={
            "timezone": bh.get("timezone", ""),
            "business_hours": f"{bh.get('start', '')} - {bh.get('end', '')}",
            "business_days": bh.get("days", []),
            "address": memo.get("office_address", {}),
            "emergency_routing": memo.get("emergency_routing_rules", []),
            "services": memo.get("services_supported", [])
        },
        call_transfer_protocol={
            "transfer_numbers": transfer_rules.get("transfer_numbers", []),
            "timeout_seconds": transfer_rules.get("timeout_seconds", 60),
            "max_retries": transfer_rules.get("max_retries", 2)
        },
        fallback_protocol={
            "message": transfer_rules.get("fallback_message", ""),
            "action": "collect_info_and_notify"
        },
        tool_invocation_placeholders=[
            {
                "name": "transfer_call",
                "description": "Transfer the call to a specified number",
                "parameters": {"phone_number": "string"}
            },
            {
                "name": "create_ticket",
                "description": "Create a service ticket in the tracking system",
                "parameters": {"caller_name": "string", "phone": "string", "description": "string", "priority": "string"}
            },
            {
                "name": "check_business_hours",
                "description": "Check if current time is within business hours",
                "parameters": {}
            }
        ],
        boosted_keywords=memo.get("services_supported", []) + [company_name],
        voicemail_message=f"Thank you for calling {company_name}. We're unable to take your call right now. Please leave a message and we'll get back to you as soon as possible.",
        post_call_analysis_data=[
            {"type": "string", "name": "caller_name", "description": "Name of the caller"},
            {"type": "string", "name": "caller_phone", "description": "Caller's phone number"},
            {"type": "string", "name": "call_type", "description": "emergency or non-emergency"},
            {"type": "string", "name": "service_needed", "description": "What service the caller needs"},
            {"type": "boolean", "name": "transfer_successful", "description": "Whether the call was successfully transferred"},
            {"type": "string", "name": "follow_up_required", "description": "Any follow-up actions needed"}
        ]
    )

    # Save spec
    spec_dict = spec.model_dump()
    saved_path = save_json(spec_dict, account_id, "agent_spec.json", version)
    print(f"  💾 Saved agent spec to: {saved_path}")
    print(f"  🤖 Agent: {spec.agent_name}")
    print(f"  📋 Prompt length: {len(system_prompt)} chars")

    return spec


def main():
    parser = argparse.ArgumentParser(description="Generate Retell Agent Spec from account memo")
    parser.add_argument("account_id", help="Account ID to generate spec for")
    parser.add_argument("--version", default="v1", help="Memo version to use")
    args = parser.parse_args()

    spec = generate_agent_spec(args.account_id, args.version)
    print(f"\n✅ Agent spec generated for: {spec.agent_name}")


if __name__ == "__main__":
    main()