"""
Transcript parser: normalizes various transcript formats into a clean,
structured list of speaker turns for downstream processing.
"""

import re
import os
from dataclasses import dataclass


@dataclass
class SpeakerTurn:
    """A single turn in a conversation."""
    timestamp: str
    speaker: str
    text: str


def parse_chat_txt(content: str) -> list[SpeakerTurn]:
    """
    Parse Zoom-style chat.txt format:
    HH:MM:SS  From SpeakerName : message text
    """
    turns = []
    pattern = r'(\d{1,2}:\d{2}:\d{2})\s+From\s+(.+?)\s*:\s*(.*)'
    for line in content.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        match = re.match(pattern, line)
        if match:
            turns.append(SpeakerTurn(
                timestamp=match.group(1),
                speaker=match.group(2).strip(),
                text=match.group(3).strip()
            ))
        elif turns:
            # Continuation of previous message
            turns[-1].text += " " + line
    return turns


def parse_plain_transcript(content: str) -> list[SpeakerTurn]:
    """
    Parse a plain transcript with speaker labels:
    Speaker Name: message text
    or
    [HH:MM:SS] Speaker Name: message text
    """
    turns = []
    # Try timestamped format first
    ts_pattern = r'\[?(\d{1,2}:\d{2}(?::\d{2})?)\]?\s*(.+?):\s*(.*)'
    # Simple speaker: text format
    simple_pattern = r'^([A-Za-z\s\.]+?):\s*(.*)'

    for line in content.strip().split('\n'):
        line = line.strip()
        if not line:
            continue

        ts_match = re.match(ts_pattern, line)
        simple_match = re.match(simple_pattern, line)

        if ts_match:
            turns.append(SpeakerTurn(
                timestamp=ts_match.group(1),
                speaker=ts_match.group(2).strip(),
                text=ts_match.group(3).strip()
            ))
        elif simple_match:
            speaker = simple_match.group(1).strip()
            # Filter out false positives (very long "speaker" names are likely not speakers)
            if len(speaker) < 40:
                turns.append(SpeakerTurn(
                    timestamp="",
                    speaker=speaker,
                    text=simple_match.group(2).strip()
                ))
            elif turns:
                turns[-1].text += " " + line
        elif turns:
            # Continuation of previous message
            turns[-1].text += " " + line
        else:
            # No speaker identified yet, treat as unnamed
            turns.append(SpeakerTurn(timestamp="", speaker="Unknown", text=line))

    return turns


def parse_fireflies_transcript(content: str) -> list[SpeakerTurn]:
    """
    Parse Fireflies.ai transcript format.
    Typically: Speaker Name
    timestamp
    message text
    """
    turns = []
    lines = content.strip().split('\n')
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue

        # Check if next line is a timestamp
        if i + 1 < len(lines) and re.match(r'\d{1,2}:\d{2}', lines[i + 1].strip()):
            speaker = line
            timestamp = lines[i + 1].strip()
            text_lines = []
            i += 2
            while i < len(lines) and lines[i].strip() and not (
                i + 1 < len(lines) and re.match(r'\d{1,2}:\d{2}', lines[i + 1].strip())
            ):
                text_lines.append(lines[i].strip())
                i += 1
            # Include the line before the next timestamp pattern
            if i < len(lines) and lines[i].strip():
                # Check if THIS is a speaker line (next line is timestamp)
                if i + 1 < len(lines) and re.match(r'\d{1,2}:\d{2}', lines[i + 1].strip()):
                    pass  # Don't include, it's the next speaker
                else:
                    text_lines.append(lines[i].strip())
                    i += 1
            turns.append(SpeakerTurn(
                timestamp=timestamp,
                speaker=speaker,
                text=" ".join(text_lines)
            ))
        else:
            # Fall back to simple parsing
            simple_match = re.match(r'^([A-Za-z\s\.]+?):\s*(.*)', line)
            if simple_match and len(simple_match.group(1)) < 40:
                turns.append(SpeakerTurn(
                    timestamp="",
                    speaker=simple_match.group(1).strip(),
                    text=simple_match.group(2).strip()
                ))
            elif turns:
                turns[-1].text += " " + line
            i += 1

    return turns


def detect_format(content: str) -> str:
    """Detect the transcript format based on content patterns."""
    lines = content.strip().split('\n')[:20]  # Check first 20 lines
    
    # Zoom chat format
    if any(re.match(r'\d{1,2}:\d{2}:\d{2}\s+From\s+', line) for line in lines):
        return "chat_txt"
    
    # Fireflies format (speaker line followed by timestamp line)
    for i in range(len(lines) - 1):
        if (lines[i].strip() and 
            not re.match(r'\d', lines[i].strip()[0]) and
            re.match(r'\d{1,2}:\d{2}', lines[i + 1].strip())):
            return "fireflies"
    
    # Default plain transcript
    return "plain"


def parse_transcript(file_path: str) -> list[SpeakerTurn]:
    """
    Auto-detect format and parse a transcript file.
    Returns a list of SpeakerTurn objects.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Transcript file not found: {file_path}")

    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    if not content.strip():
        raise ValueError(f"Transcript file is empty: {file_path}")

    fmt = detect_format(content)

    if fmt == "chat_txt":
        turns = parse_chat_txt(content)
    elif fmt == "fireflies":
        turns = parse_fireflies_transcript(content)
    else:
        turns = parse_plain_transcript(content)

    return turns


def turns_to_text(turns: list[SpeakerTurn]) -> str:
    """Convert parsed turns back to a clean text format for LLM processing."""
    lines = []
    for turn in turns:
        prefix = f"[{turn.timestamp}] " if turn.timestamp else ""
        lines.append(f"{prefix}{turn.speaker}: {turn.text}")
    return "\n".join(lines)


def get_transcript_text(file_path: str) -> str:
    """
    Convenience function: parse a transcript file and return as clean text.
    If parsing fails, return raw content.
    """
    try:
        turns = parse_transcript(file_path)
        if turns:
            return turns_to_text(turns)
    except Exception:
        pass

    # Fallback: return raw content
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        return f.read()
