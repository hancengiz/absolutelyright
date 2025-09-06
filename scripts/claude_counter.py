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


def upload_to_api(api_url, secret, date_str, count, right_count=None):
    """Upload counts to API. Returns True/False/'STOP'"""
    if not api_url:
        return False

    try:
        data = {"day": date_str, "count": count}
        if secret:
            data["secret"] = secret
        if right_count is not None:
            data["right_count"] = right_count

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


def scan_jsonl_file(filepath, processed_ids, project_name, compiled_patterns):
    """Scan a JSONL file for pattern matches"""
    new_matches = []

    try:
        with open(filepath, "r") as f:
            for line in f:
                try:
                    entry = json.loads(line)

                    if entry.get("type") != "assistant":
                        continue

                    msg_id = entry.get("uuid") or entry.get("requestId")
                    if not msg_id or msg_id in processed_ids:
                        continue
                    message = entry.get("message", {})
                    if "content" in message:
                        for content_item in message.get("content", []):
                            if (
                                isinstance(content_item, dict)
                                and content_item.get("type") == "text"
                            ):
                                text = content_item.get("text", "")

                                timestamp = entry.get("timestamp", "")
                                if timestamp:
                                    entry_time = datetime.fromisoformat(
                                        timestamp.replace("Z", "+00:00")
                                    )
                                    time_str = entry_time.strftime("%H:%M:%S")
                                    date_str = entry_time.strftime("%Y-%m-%d")
                                else:
                                    time_str = "unknown"
                                    date_str = get_utc_today()

                                matches = {}
                                for (
                                    pattern_name,
                                    pattern_regex,
                                ) in compiled_patterns.items():
                                    if pattern_regex.search(text):
                                        matches[pattern_name] = True

                                if matches:
                                    new_matches.append(
                                        {
                                            "id": msg_id,
                                            "time": time_str,
                                            "date": date_str,
                                            "text": text.strip()[:100],
                                            "project": project_name,
                                            "matches": matches,
                                        }
                                    )

                except json.JSONDecodeError:
                    continue
                except Exception:
                    continue

    except Exception:
        pass

    return new_matches


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
