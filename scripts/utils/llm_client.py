"""
LLM Client: wraps Google Gemini API (free tier) with rate limiting,
caching, and fallback to rule-based extraction.
"""

import os
import json
import time
import hashlib
import re
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv

# Define base dir and explicitly load .env
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
dotenv_path = os.path.join(BASE_DIR, ".env")
load_dotenv(dotenv_path, override=True)

# ─── Config ──────────────────────────────────────────────────────

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
LLM_MODE = os.getenv("LLM_MODE", "gemini")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-preview-05-20")
GEMINI_RPM = int(os.getenv("GEMINI_RPM", "10"))
GEMINI_RPD = int(os.getenv("GEMINI_RPD", "50"))

# Cache directory
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".cache", "llm")
os.makedirs(CACHE_DIR, exist_ok=True)

# Rate limiter state
_request_timestamps: list[float] = []
_daily_count: int = 0
_daily_reset: float = 0.0


def _rate_limit():
    """Enforce rate limits: max RPM and RPD."""
    global _request_timestamps, _daily_count, _daily_reset
    
    now = time.time()
    
    # Reset daily counter
    if now - _daily_reset > 86400:
        _daily_count = 0
        _daily_reset = now
    
    # Check daily limit
    if _daily_count >= GEMINI_RPD:
        raise RuntimeError(f"Daily Gemini API limit reached ({GEMINI_RPD} RPD). Use LLM_MODE=rule_based or wait 24h.")
    
    # Enforce per-minute limit
    _request_timestamps = [t for t in _request_timestamps if now - t < 60]
    if len(_request_timestamps) >= GEMINI_RPM:
        wait_time = 60 - (now - _request_timestamps[0])
        if wait_time > 0:
            print(f"  ⏳ Rate limiting: waiting {wait_time:.1f}s...")
            time.sleep(wait_time)
    
    _request_timestamps.append(now)
    _daily_count += 1


def _cache_key(prompt: str) -> str:
    """Generate a cache key from the prompt."""
    return hashlib.md5(prompt.encode()).hexdigest()


def _get_cached(prompt: str) -> Optional[str]:
    """Check if a response is cached."""
    key = _cache_key(prompt)
    cache_file = os.path.join(CACHE_DIR, f"{key}.json")
    if os.path.exists(cache_file):
        with open(cache_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get("response")
    return None


def _set_cached(prompt: str, response: str):
    """Cache a response."""
    key = _cache_key(prompt)
    cache_file = os.path.join(CACHE_DIR, f"{key}.json")
    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump({"prompt_hash": key, "response": response}, f)


def call_gemini(prompt: str, system_instruction: str = "") -> str:
    """
    Call Gemini API with rate limiting and caching.
    Returns the text response.
    """
    # Check cache first
    cached = _get_cached(prompt)
    if cached:
        print("  📦 Using cached LLM response")
        return cached
    
    try:
        import google.generativeai as genai
    except ImportError:
        raise ImportError("google-generativeai package not installed. Run: pip install google-generativeai")
    
    if not GEMINI_API_KEY or GEMINI_API_KEY == "your_gemini_api_key_here":
        raise ValueError("GEMINI_API_KEY not set. Get one free at https://aistudio.google.com/apikey")
    
    genai.configure(api_key=GEMINI_API_KEY)
    
    _rate_limit()
    
    model = genai.GenerativeModel(
        model_name=GEMINI_MODEL,
        system_instruction=system_instruction if system_instruction else None
    )
    
    response = model.generate_content(prompt)
    result = response.text
    
    # Cache the response
    _set_cached(prompt, result)
    
    return result


def extract_json_from_response(text: str) -> dict:
    """Extract JSON from an LLM response that may contain markdown code blocks."""
    # Try to find JSON in code blocks
    json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if json_match:
        text = json_match.group(1)
    
    # Try to find raw JSON object
    text = text.strip()
    
    # Find the first { and last } to extract JSON
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1:
        json_str = text[start:end + 1]
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass
    
    # Try the whole text
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        raise ValueError(f"Could not extract valid JSON from LLM response:\n{text[:500]}")


def call_llm(prompt: str, system_instruction: str = "") -> str:
    """
    Main entry point: calls Gemini if available, otherwise returns
    a marker indicating rule-based fallback should be used.
    """
    if LLM_MODE == "rule_based":
        return "__RULE_BASED__"
    
    try:
        return call_gemini(prompt, system_instruction)
    except (ImportError, ValueError, RuntimeError) as e:
        print(f"  ⚠️ LLM unavailable ({e}), falling back to rule-based extraction")
        return "__RULE_BASED__"
    except Exception as e:
        print(f"  ⚠️ LLM error ({e}), falling back to rule-based extraction")
        return "__RULE_BASED__"


def is_llm_available() -> bool:
    """Check if LLM (Gemini) is available and configured."""
    if LLM_MODE == "rule_based":
        return False
    if not GEMINI_API_KEY or GEMINI_API_KEY == "your_gemini_api_key_here":
        return False
    try:
        import google.generativeai
        return True
    except ImportError:
        return False
