#!/usr/bin/env python3
import os
import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

CLAUDE_PROJECTS_BASE = os.environ.get(
    "CLAUDE_PROJECTS", os.path.expanduser("~/.claude/projects")
)
DATA_DIR = os.path.expanduser("~/.absolutelyright")

PATTERNS = {
    "absolutely": r"You(?:'re| are) absolutely right",
    "right": r"You(?:'re| are) right",
}

# Example additional patterns (uncomment to track):
# "issue": r"I see the issue",
# "perfect": r"Perfect!",
# "excellent": r"Excellent!"


def upload_to_api(api_url, secret, date_str, count, right_count=None, total_messages=None):
    """Upload counts to API. Returns True/False/'STOP'"""
    if not api_url:
        return False

    try:
        data = {"day": date_str, "count": count}
        if secret:
            data["secret"] = secret
        if right_count is not None:
            data["right_count"] = right_count
        if total_messages is not None:
            data["total_messages"] = total_messages

        req = urllib.request.Request(
            f"{api_url}/api/set",
            data=json.dumps(data).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )

        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                return True
            elif response.status == 401:
                print(f"\n🚫 AUTHORIZATION FAILED!")
                print(f"   Check your secret key and try again.")
                return "STOP"
            else:
                print(f"  API error for {date_str}: {response.status}")
                return False
    except urllib.error.HTTPError as e:
        if e.code == 401:
            print(f"\n🚫 AUTHORIZATION FAILED!")
            print(f"   Check your secret key and try again.")
            return "STOP"
        else:
            print(f"  API error for {date_str}: HTTP {e.code}")
            return False
    except Exception as e:
        print(f"  API error for {date_str}: {e}")
        return False


def process_message_entry(entry, compiled_patterns):
    """
    Process a single JSONL entry and extract message info + pattern matches.

    Returns dict with:
        - msg_id: The message UUID
        - date_str: Date in YYYY-MM-DD format
        - text_blocks: List of (text, matched_patterns) tuples
    Returns None if entry should be skipped.
    """
    if entry.get("type") != "assistant":
        return None

    msg_id = entry.get("uuid") or entry.get("requestId")
    if not msg_id:
        return None

    # Parse timestamp
    timestamp = entry.get("timestamp", "")
    if timestamp:
        entry_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        date_str = entry_time.strftime("%Y-%m-%d")
    else:
        date_str = get_utc_today()

    # Extract text blocks and check for pattern matches
    text_blocks = []
    message = entry.get("message", {})
    if "content" in message:
        for content_item in message.get("content", []):
            if isinstance(content_item, dict) and content_item.get("type") == "text":
                text = content_item.get("text", "")

                # Check for pattern matches
                matched_patterns = {}
                for pattern_name, pattern_regex in compiled_patterns.items():
                    if pattern_regex.search(text):
                        matched_patterns[pattern_name] = True

                text_blocks.append((text, matched_patterns))

    return {
        "msg_id": msg_id,
        "date_str": date_str,
        "text_blocks": text_blocks,
    }


def get_project_display_name(project_dir_name):
    name = project_dir_name
    for prefix in ["-Users-", "-home-", "-var-"]:
        if name.startswith(prefix):
            parts = name.split("-", 3)
            if len(parts) > 3:
                name = parts[3]
            break
    return name


def get_utc_today():
    """Get today's date in UTC (same format as JSONL timestamps)"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)
