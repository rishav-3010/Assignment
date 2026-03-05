"""
Pipeline B: Onboarding Call -> Agent Modification (v1 -> v2)
Takes onboarding transcript + existing v1 data and produces v2 with changelog.
"""

import os
import sys
import json
import copy
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.utils.llm_client import call_llm, extract_json_from_response, is_llm_available
from scripts.utils.transcript_parser import get_transcript_text
from scripts.utils.storage import load_json, save_json, save_text
from scripts.utils.schema import AccountMemo, Changelog, ChangelogEntry


ONBOARDING_EXTRACTION_PROMPT = """You are an expert data extraction assistant for Clara Answers, an AI voice agent company.

You are given two things:
1. An EXISTING account memo (v1) that was created from a demo call.
2. A NEW onboarding call transcript that contains updated, confirmed, or corrected information.

Your job is to extract ONLY the UPDATES and CORRECTIONS from the onboarding transcript.

CRITICAL RULES:
1. ONLY extract information that is EXPLICITLY stated in the onboarding transcript.
2. If a field in v1 is correct and not contradicted, DO NOT change it.
3. If the onboarding has NEW information for a field that was empty in v1, ADD it.
4. If the onboarding CONTRADICTS v1, use the onboarding version (it takes priority).
5. NEVER invent or assume information.
6. For each change, note WHY it changed (e.g., "Confirmed during onboarding", "Corrected from demo assumption").

EXISTING ACCOUNT MEMO (v1):
{existing_memo}

ONBOARDING TRANSCRIPT:
{transcript}

Return a JSON object with two keys:
1. "updates": an object containing ONLY the fields that should be UPDATED (with their new values). Use the same field structure as the account memo. Only include fields that actually changed or were newly provided.
2. "change_reasons": an object mapping field names to the reason for the change.

Example:
{{
  "updates": {{
    "business_hours": {{
      "start": "07:30",
      "end": "17:30",
      "timezone": "America/Denver"
    }},
    "emergency_definition": ["sprinkler leak", "fire alarm triggered", "flooding"]
  }},
  "change_reasons": {{
    "business_hours": "Confirmed exact hours and timezone during onboarding",
    "emergency_definition": "Client added 'flooding' as an emergency trigger"
  }}
}}

IMPORTANT: Return ONLY valid JSON. No other text.
"""


def extract_onboarding_updates_llm(existing_memo: dict, transcript_text: str) -> tuple[dict, dict]:
    """Use LLM to extract only the changes from onboarding."""
    prompt = ONBOARDING_EXTRACTION_PROMPT.replace(
        "{existing_memo}", json.dumps(existing_memo, indent=2)
    ).replace(
        "{transcript}", transcript_text
    )

    system_instruction = (
        "You are a precise data extraction agent specializing in identifying changes "
        "between existing records and new information from calls. Extract ONLY updates, "
        "never repeat unchanged information."
    )

    response = call_llm(prompt, system_instruction)
    if response == "__RULE_BASED__":
        return rule_based_onboarding_extraction(existing_memo, transcript_text)

    data = extract_json_from_response(response)
    updates = data.get("updates", {})
    reasons = data.get("change_reasons", {})
    return updates, reasons


def rule_based_onboarding_extraction(existing_memo: dict, transcript_text: str) -> tuple[dict, dict]:
    """Fallback: rule-based extraction of onboarding updates."""
    import re
    text = transcript_text.lower()
    updates = {}
    reasons = {}

    # Check for business hours updates
    time_match = re.search(r'(\d{1,2}(?::\d{2})?)\s*(?:am|AM)?\s*(?:to|through|-)\s*(\d{1,2}(?::\d{2})?)\s*(?:pm|PM)?', transcript_text)
    if time_match:
        existing_start = existing_memo.get("business_hours", {}).get("start", "")
        new_start = time_match.group(1)
        if new_start != existing_start:
            if "business_hours" not in updates:
                updates["business_hours"] = {}
            updates["business_hours"]["start"] = new_start
            updates["business_hours"]["end"] = time_match.group(2)
            reasons["business_hours"] = "Updated from onboarding call"

    # Check for timezone updates
    tz_map = {
        'eastern': 'America/New_York', 'central': 'America/Chicago',
        'mountain': 'America/Denver', 'pacific': 'America/Los_Angeles'
    }
    for tz_name, tz_value in tz_map.items():
        if tz_name in text:
            existing_tz = existing_memo.get("business_hours", {}).get("timezone", "")
            if tz_value != existing_tz:
                if "business_hours" not in updates:
                    updates["business_hours"] = {}
                updates["business_hours"]["timezone"] = tz_value
                reasons.setdefault("business_hours", "")
                reasons["business_hours"] += f" Timezone confirmed as {tz_value}"

    # Check for new phone numbers
    phone_pattern = r'(\d{3}[-.\s]?\d{3}[-.\s]?\d{4})'
    phones = re.findall(phone_pattern, transcript_text)
    existing_phones = existing_memo.get("call_transfer_rules", {}).get("transfer_numbers", [])
    new_phones = [p for p in phones if p not in existing_phones]
    if new_phones:
        updates["call_transfer_rules"] = {
            "transfer_numbers": list(set(existing_phones + new_phones))
        }
        reasons["call_transfer_rules"] = "New phone numbers identified in onboarding"

    # Check for integration constraints
    constraint_keywords = [
        "never create", "do not create", "don't create",
        "never use", "do not use", "don't use",
        "must not", "should not", "cannot"
    ]
    for keyword in constraint_keywords:
        if keyword in text:
            # Find the sentence containing the constraint
            sentences = transcript_text.split('.')
            for sentence in sentences:
                if keyword in sentence.lower():
                    constraint = sentence.strip()
                    existing_constraints = existing_memo.get("integration_constraints", [])
                    if constraint not in existing_constraints:
                        updates["integration_constraints"] = existing_constraints + [constraint]
                        reasons["integration_constraints"] = "New constraint identified in onboarding"
                    break
            break

    return updates, reasons


def deep_merge(base: dict, updates: dict) -> dict:
    """Deep merge updates into base dict, preserving unchanged values."""
    result = copy.deepcopy(base)
    for key, value in updates.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        elif key in result and isinstance(result[key], list) and isinstance(value, list):
            # For lists, replace entirely (onboarding takes priority)
            result[key] = value
        else:
            result[key] = value
    return result


def build_changelog(account_id: str, company_name: str, v1_memo: dict, v2_memo: dict, reasons: dict) -> Changelog:
    """Build a changelog comparing v1 and v2 memos."""
    changes = []

    def compare(old, new, path=""):
        if isinstance(old, dict) and isinstance(new, dict):
            all_keys = set(list(old.keys()) + list(new.keys()))
            for key in sorted(all_keys):
                old_val = old.get(key)
                new_val = new.get(key)
                current_path = f"{path}.{key}" if path else key
                if old_val != new_val:
                    compare(old_val, new_val, current_path)
        elif isinstance(old, list) and isinstance(new, list):
            if old != new:
                changes.append(ChangelogEntry(
                    field=path,
                    old_value=json.dumps(old, indent=2) if old else "[]",
                    new_value=json.dumps(new, indent=2) if new else "[]",
                    reason=reasons.get(path.split('.')[0], "Updated from onboarding data")
                ))
        elif old != new:
            changes.append(ChangelogEntry(
                field=path,
                old_value=str(old) if old else "(empty)",
                new_value=str(new) if new else "(empty)",
                reason=reasons.get(path.split('.')[0], "Updated from onboarding data")
            ))

    # Skip metadata fields
    skip_fields = {"version", "source", "account_id"}
    v1_filtered = {k: v for k, v in v1_memo.items() if k not in skip_fields}
    v2_filtered = {k: v for k, v in v2_memo.items() if k not in skip_fields}
    compare(v1_filtered, v2_filtered)

    return Changelog(
        account_id=account_id,
        company_name=company_name,
        from_version="v1",
        to_version="v2",
        changes=changes,
        summary=f"Updated {len(changes)} field(s) from onboarding data for {company_name}."
    )


def update_agent_from_onboarding(
    transcript_path: str,
    account_id: str
) -> tuple[dict, Changelog]:
    """
    Main entry point for Pipeline B.
    
    Args:
        transcript_path: Path to the onboarding transcript
        account_id: Account ID to update
    
    Returns:
        Tuple of (v2 memo dict, changelog)
    """
    print(f"\n{'='*60}")
    print(f"🔄 Pipeline B: Onboarding update for: {account_id}")
    print(f"{'='*60}")

    # Load existing v1 memo
    v1_memo = load_json(account_id, "account_memo.json", "v1")
    if not v1_memo:
        raise FileNotFoundError(f"No v1 memo found for {account_id}. Run Pipeline A first.")

    # Parse onboarding transcript
    print("  📄 Parsing onboarding transcript...")
    transcript_text = get_transcript_text(transcript_path)
    print(f"  ✅ Parsed {len(transcript_text)} characters")

    # Extract updates
    if is_llm_available():
        print("  🤖 Using Gemini LLM for update extraction...")
        updates, reasons = extract_onboarding_updates_llm(v1_memo, transcript_text)
    else:
        print("  📏 Using rule-based update extraction...")
        updates, reasons = rule_based_onboarding_extraction(v1_memo, transcript_text)

    print(f"  📊 Found {len(updates)} field(s) to update")

    # Apply updates to create v2
    v2_memo = deep_merge(v1_memo, updates)
    v2_memo["version"] = "v2"
    v2_memo["source"] = "onboarding"

    # Save v2 memo
    save_json(v2_memo, account_id, "account_memo.json", "v2")
    print(f"  💾 Saved v2 account memo")

    # Generate v2 agent spec
    from scripts.generate_agent_spec import generate_agent_spec
    generate_agent_spec(account_id, "v2")

    # Build and save changelog
    changelog = build_changelog(
        account_id,
        v1_memo.get("company_name", ""),
        v1_memo,
        v2_memo,
        reasons
    )
    save_text(changelog.to_markdown(), account_id, "changelog.md", "v2")
    save_json(json.loads(changelog.to_json()), account_id, "changelog.json", "v2")
    print(f"  📋 Generated changelog with {len(changelog.changes)} change(s)")

    return v2_memo, changelog


def main():
    parser = argparse.ArgumentParser(description="Update agent from onboarding transcript")
    parser.add_argument("transcript", help="Path to the onboarding transcript file")
    parser.add_argument("account_id", help="Account ID to update")
    args = parser.parse_args()

    v2_memo, changelog = update_agent_from_onboarding(args.transcript, args.account_id)
    print(f"\n✅ Done! v2 memo and agent spec for: {v2_memo.get('company_name', args.account_id)}")
    print(f"📋 Changes:\n{changelog.to_markdown()}")


if __name__ == "__main__":
    main()
