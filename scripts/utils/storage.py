"""
File-based storage helpers for reading/writing pipeline outputs.
Manages the outputs/accounts/<account_id>/v1 and v2 directory structure.
"""

import os
import json
import re
from typing import Optional


BASE_OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "outputs", "accounts")


def sanitize_account_id(name: str) -> str:
    """Generate a clean account_id from a company name."""
    account_id = name.lower().strip()
    account_id = re.sub(r'[^a-z0-9]+', '_', account_id)
    account_id = account_id.strip('_')
    return account_id or "unknown_account"


def get_account_dir(account_id: str, version: str = "v1") -> str:
    """Get the output directory for an account version."""
    path = os.path.join(BASE_OUTPUT_DIR, account_id, version)
    os.makedirs(path, exist_ok=True)
    return path


def save_json(data: dict, account_id: str, filename: str, version: str = "v1") -> str:
    """Save a JSON file to the account output directory."""
    dir_path = get_account_dir(account_id, version)
    file_path = os.path.join(dir_path, filename)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    return file_path


def load_json(account_id: str, filename: str, version: str = "v1") -> Optional[dict]:
    """Load a JSON file from the account output directory."""
    dir_path = get_account_dir(account_id, version)
    file_path = os.path.join(dir_path, filename)
    if not os.path.exists(file_path):
        return None
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_text(content: str, account_id: str, filename: str, version: str = "v1") -> str:
    """Save a text file to the account output directory."""
    dir_path = get_account_dir(account_id, version)
    file_path = os.path.join(dir_path, filename)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    return file_path


def load_text(account_id: str, filename: str, version: str = "v1") -> Optional[str]:
    """Load a text file from the account output directory."""
    dir_path = get_account_dir(account_id, version)
    file_path = os.path.join(dir_path, filename)
    if not os.path.exists(file_path):
        return None
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


def list_accounts() -> list[str]:
    """List all account IDs in the output directory."""
    if not os.path.exists(BASE_OUTPUT_DIR):
        return []
    return [
        d for d in os.listdir(BASE_OUTPUT_DIR)
        if os.path.isdir(os.path.join(BASE_OUTPUT_DIR, d))
    ]


def account_has_version(account_id: str, version: str) -> bool:
    """Check if an account has a specific version."""
    dir_path = os.path.join(BASE_OUTPUT_DIR, account_id, version)
    return os.path.exists(dir_path) and bool(os.listdir(dir_path))


def get_all_outputs(account_id: str) -> dict:
    """Get all outputs for an account across all versions."""
    result = {}
    account_dir = os.path.join(BASE_OUTPUT_DIR, account_id)
    if not os.path.exists(account_dir):
        return result
    
    for version in sorted(os.listdir(account_dir)):
        version_dir = os.path.join(account_dir, version)
        if os.path.isdir(version_dir):
            result[version] = {}
            for filename in os.listdir(version_dir):
                file_path = os.path.join(version_dir, filename)
                if filename.endswith('.json'):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        result[version][filename] = json.load(f)
                elif filename.endswith('.md'):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        result[version][filename] = f.read()
    
    return result
