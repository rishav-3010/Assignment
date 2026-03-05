"""
Pipeline A: Demo Call -> Account Memo (v1)
Extracts structured account data from a demo call transcript
and generates an account_memo.json.
"""

import os
import sys
import json
import re
import argparse

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.utils.llm_client import call_llm, extract_json_from_response, is_llm_available
from scripts.utils.transcript_parser import get_transcript_text
from scripts.utils.storage import save_json, sanitize_account_id
from scripts.utils.schema import AccountMemo, BusinessHours, OfficeAddress, RoutingRule, CallTransferRules


def load_extraction_prompt() -> str:
    """Load the extraction prompt template."""
    template_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "templates", "extraction_prompt.txt"
    )
    with open(template_path, 'r', encoding='utf-8') as f:
        return f.read()


def extract_with_llm(transcript_text: str) -> dict:
    """Use Gemini to extract structured data from transcript."""
    prompt_template = load_extraction_prompt()
    prompt = prompt_template.replace("{transcript}", transcript_text)

    system_instruction = (
        "You are a precise data extraction agent. Extract ONLY what is explicitly stated. "
        "Never invent or assume information. Return valid JSON only."
    )

    response = call_llm(prompt, system_instruction)

    if response == "__RULE_BASED__":
        return rule_based_extraction(transcript_text)

    return extract_json_from_response(response)


def rule_based_extraction(transcript_text: str) -> dict:
    """
    Fallback: rule-based extraction using regex and keyword matching.
    Less accurate but works without an LLM.
    """
    text = transcript_text.lower()
    result = {
        "company_name": "",
        "business_hours": {"days": [], "start": "", "end": "", "timezone": ""},
        "office_address": {"street": "", "city": "", "state": "", "zip_code": "", "country": "US"},
        "services_supported": [],
        "emergency_definition": [],
        "emergency_routing_rules": [],
        "non_emergency_routing_rules": [],
        "call_transfer_rules": {
            "timeout_seconds": 60,
            "max_retries": 2,
            "fallback_message": "I apologize, I'm unable to connect you right now. Let me take your information and have someone call you back as soon as possible.",
            "transfer_numbers": [],
            "notes": ""
        },
        "integration_constraints": [],
        "after_hours_flow_summary": "",
        "office_hours_flow_summary": "",
        "questions_or_unknowns": [],
        "notes": "Extracted using rule-based fallback (no LLM available)"
    }

    # Words to ignore as company names (agent/system names)
    ignore_names = {"clara", "clara answers", "retell", "demo", "rep", "sales rep"}

    # Extract company name - look for common patterns (ordered by specificity)
    company_patterns = [
        # "I own/run [Company Name]"
        r"(?:i own|i run|owner of|president of|manager at|work for)\s+([A-Z][A-Za-z'\s&]+(?:LLC|Inc|Corp|Solutions|Services|Electric|Plumbing|HVAC|Fire|Protection|Mechanical|Alarm|Systems)?)",
        # Explicit company name with industry suffix
        r"([A-Z][A-Za-z']+(?:\s+[A-Z][A-Za-z']+)*\s+(?:Electric(?:al)?|Plumbing|HVAC|Fire Protection|Alarm Systems|Mechanical|Services|Solutions))",
        # "at [Company]" pattern
        r"(?:at|with)\s+([A-Z][A-Za-z'\s&]+(?:LLC|Inc|Corp|Solutions|Services|Electric|Plumbing|HVAC|Fire|Protection|Alarm|Mechanical))",
    ]
    for pattern in company_patterns:
        matches = re.findall(pattern, transcript_text)
        for name in matches:
            name = name.strip()
            if len(name) > 3 and len(name) < 60 and name.lower() not in ignore_names:
                result["company_name"] = name
                break
        if result["company_name"]:
            break

    # Extract phone numbers
    phone_pattern = r'(\d{3}[-.\s]?\d{3}[-.\s]?\d{4})'
    phones = re.findall(phone_pattern, transcript_text)
    if phones:
        result["call_transfer_rules"]["transfer_numbers"] = list(set(phones))

    # Extract email addresses
    email_pattern = r'[\w.+-]+@[\w-]+\.[\w.]+'
    emails = re.findall(email_pattern, transcript_text)

    # Extract times (business hours)
    time_patterns = [
        r'(\d{1,2})\s*(?:am|AM)\s*(?:to|through|-)\s*(\d{1,2})\s*(?:pm|PM)',
        r'(\d{1,2}:\d{2})\s*(?:am|AM)?\s*(?:to|through|-)\s*(\d{1,2}:\d{2})\s*(?:pm|PM)?',
    ]
    for pattern in time_patterns:
        match = re.search(pattern, transcript_text)
        if match:
            result["business_hours"]["start"] = match.group(1)
            result["business_hours"]["end"] = match.group(2)
            break

    # Extract timezone
    tz_patterns = [
        (r'eastern', 'America/New_York'),
        (r'central', 'America/Chicago'),
        (r'mountain', 'America/Denver'),
        (r'pacific', 'America/Los_Angeles'),
        (r'est\b', 'America/New_York'),
        (r'cst\b', 'America/Chicago'),
        (r'mst\b', 'America/Denver'),
        (r'pst\b', 'America/Los_Angeles'),
    ]
    for pattern, tz in tz_patterns:
        if re.search(pattern, text):
            result["business_hours"]["timezone"] = tz
            break

    # Extract services (keyword matching)
    service_keywords = [
        "fire protection", "sprinkler", "alarm", "fire alarm", "electrical",
        "hvac", "plumbing", "inspection", "maintenance", "installation",
        "repair", "monitoring", "extinguisher", "suppression", "backflow",
        "pressure washing", "cleaning"
    ]
    for service in service_keywords:
        if service in text:
            result["services_supported"].append(service.title())

    # Extract emergency definitions
    emergency_keywords = [
        "sprinkler leak", "fire alarm", "water leak", "flood", "fire",
        "gas leak", "power outage", "electrical fire", "system down",
        "broken pipe", "emergency"
    ]
    for keyword in emergency_keywords:
        if keyword in text:
            result["emergency_definition"].append(keyword.title())

    # Flag unknowns
    if not result["company_name"]:
        result["questions_or_unknowns"].append("Company name could not be determined")
    if not result["business_hours"]["start"]:
        result["questions_or_unknowns"].append("Business hours not specified")
    if not result["services_supported"]:
        result["questions_or_unknowns"].append("Services not clearly specified")
    if not result["emergency_definition"]:
        result["questions_or_unknowns"].append("Emergency definitions not specified")

    # Extract names (potential contacts)
    name_patterns = [
        r"(?:my name is|i'm|this is|contact)\s+([A-Z][a-z]+\s+[A-Z][a-z]+)",
        r"(?:ask for|speak (?:to|with)|call)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
    ]
    contacts = []
    for pattern in name_patterns:
        names = re.findall(pattern, transcript_text)
        for name in names:
            if len(name) > 3:
                contacts.append(name)

    if contacts and phones:
        for i, contact in enumerate(contacts[:3]):
            rule = {
                "contact_name": contact,
                "phone_number": phones[i] if i < len(phones) else "",
                "role": "Contact",
                "priority": i + 1,
                "notes": ""
            }
            result["non_emergency_routing_rules"].append(rule)

    return result


def extract_account_memo(transcript_path: str, account_id: str = None, source: str = "demo") -> AccountMemo:
    """
    Main entry point: extract account memo from a transcript file.
    
    Args:
        transcript_path: Path to transcript file
        account_id: Optional account ID (auto-generated from company name if not provided)
        source: 'demo' or 'onboarding'
    
    Returns:
        AccountMemo pydantic model
    """
    print(f"\n{'='*60}")
    print(f"📋 Extracting account memo from: {os.path.basename(transcript_path)}")
    print(f"{'='*60}")

    # Parse transcript
    print("  📄 Parsing transcript...")
    transcript_text = get_transcript_text(transcript_path)
    print(f"  ✅ Parsed {len(transcript_text)} characters")

    # Extract data
    if is_llm_available():
        print("  🤖 Using Gemini LLM for extraction...")
        raw_data = extract_with_llm(transcript_text)
    else:
        print("  📏 Using rule-based extraction (no LLM configured)...")
        raw_data = rule_based_extraction(transcript_text)

    # Build AccountMemo
    company_name = raw_data.get("company_name", "")
    
    # If account_id was provided (from directory name), use it as truth
    # and fall back to deriving a nice company name from it
    if account_id and (not company_name or company_name.lower() in {"clara", "clara answers", "unknown company", ""}):
        # Derive company name from account_id: "bens_electric_solutions" -> "Bens Electric Solutions"
        company_name = account_id.replace('_', ' ').title()
    
    if not company_name:
        company_name = "Unknown Company"
    
    if not account_id:
        # Try to infer it from the parent directory first
        parent_dir = os.path.basename(os.path.dirname(transcript_path))
        if parent_dir and parent_dir not in ("demo", "onboarding", "data"):
            account_id = sanitize_account_id(parent_dir)
        else:
            # Fall back to sanitizing the company name
            account_id = sanitize_account_id(company_name)

    memo = AccountMemo(
        account_id=account_id,
        company_name=company_name,
        business_hours=BusinessHours(**raw_data.get("business_hours", {})),
        office_address=OfficeAddress(**raw_data.get("office_address", {})),
        services_supported=raw_data.get("services_supported", []),
        emergency_definition=raw_data.get("emergency_definition", []),
        emergency_routing_rules=[
            RoutingRule(**r) for r in raw_data.get("emergency_routing_rules", [])
        ],
        non_emergency_routing_rules=[
            RoutingRule(**r) for r in raw_data.get("non_emergency_routing_rules", [])
        ],
        call_transfer_rules=CallTransferRules(**raw_data.get("call_transfer_rules", {})),
        integration_constraints=raw_data.get("integration_constraints", []),
        after_hours_flow_summary=raw_data.get("after_hours_flow_summary", ""),
        office_hours_flow_summary=raw_data.get("office_hours_flow_summary", ""),
        questions_or_unknowns=raw_data.get("questions_or_unknowns", []),
        notes=raw_data.get("notes", ""),
        version="v1",
        source=source
    )

    # Save to storage
    memo_dict = memo.model_dump()
    saved_path = save_json(memo_dict, account_id, "account_memo.json", "v1")
    print(f"  💾 Saved account memo to: {saved_path}")
    print(f"  🏢 Company: {memo.company_name}")
    print(f"  🆔 Account ID: {memo.account_id}")

    return memo


def main():
    parser = argparse.ArgumentParser(description="Extract account memo from a demo call transcript")
    parser.add_argument("transcript", help="Path to the transcript file")
    parser.add_argument("--account-id", help="Override account ID")
    parser.add_argument("--source", default="demo", choices=["demo", "onboarding"],
                        help="Source of the transcript")
    args = parser.parse_args()

    memo = extract_account_memo(args.transcript, args.account_id, args.source)
    print(f"\n✅ Done! Account memo saved for: {memo.company_name} ({memo.account_id})")


if __name__ == "__main__":
    main()
