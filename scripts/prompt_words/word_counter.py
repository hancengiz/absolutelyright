#!/usr/bin/env python3
"""Word counter for user prompt messages - shared utilities."""
import os
import json
import re
import urllib.request
import socket
import subprocess
import platform
import logging
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

CLAUDE_PROJECTS_BASE = os.environ.get(
    "CLAUDE_PROJECTS", os.path.expanduser("~/.claude/projects")
)
DATA_DIR = os.path.expanduser("~/.absolutelyright/prompt_words")

# Get script directory for logging and config
SCRIPT_DIR = Path(__file__).parent
LOG_DIR = SCRIPT_DIR.parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
UPLOAD_LOG_FILE = LOG_DIR / "prompt_words_uploads.log"

# Set up rotating logger for uploads
upload_logger = logging.getLogger("prompt_words_uploads")
upload_logger.setLevel(logging.INFO)
upload_handler = TimedRotatingFileHandler(
    UPLOAD_LOG_FILE,
    when="midnight",
    interval=1,
    backupCount=7,  # Keep 7 days of logs
    encoding="utf-8"
)
upload_handler.setFormatter(logging.Formatter('%(message)s'))
upload_logger.addHandler(upload_handler)

# Load word patterns and server URL from config
CONFIG_FILE = SCRIPT_DIR / "words_config.json"
with open(CONFIG_FILE, "r") as f:
    CONFIG = json.load(f)

TRACKED_WORDS = CONFIG["tracked_words"]
SERVER_URL = CONFIG.get("server_url", "http://localhost:3003")


def get_workstation_id():
    """Get a stable, friendly workstation identifier"""
    # Check for environment variable first (allows manual override)
    if os.environ.get("WORKSTATION_ID"):
        return os.environ.get("WORKSTATION_ID")

    # On macOS, use LocalHostName (clean, stable, user-friendly)
    if platform.system() == "Darwin":
        try:
            result = subprocess.run(
                ["scutil", "--get", "LocalHostName"],
                capture_output=True,
                text=True,
                timeout=1
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass

    # Fallback to socket.gethostname() for other platforms
    return socket.gethostname()


WORKSTATION_ID = get_workstation_id()


def log_upload(api_url, data, status, response_text=None, error=None):
    """Log upload attempts to file with automatic daily rotation"""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = {
            "timestamp": timestamp,
            "url": api_url,
            "data": {k: v for k, v in data.items() if k != "secret"},  # Don't log secret
            "status": status,
        }
        if response_text:
            log_entry["response"] = response_text
        if error:
            log_entry["error"] = str(error)

        upload_logger.info(json.dumps(log_entry))
    except Exception as e:
        # Don't fail if logging fails
        print(f"  Warning: Could not write to log: {e}")


def upload_to_api(api_url, secret, date_str, words_dict=None, total_user_messages=None):
    """
    Upload word counts to API. Returns True/False/'STOP'

    Args:
        api_url: API endpoint URL
        secret: Optional API secret
        date_str: Date in YYYY-MM-DD format
        words_dict: Dictionary of word_name -> count
        total_user_messages: Total number of user messages
    """
    if not api_url:
        return False

    try:
        data = {
            "day": date_str,
            "workstation_id": WORKSTATION_ID
        }

        # Add word counts as flat fields
        if words_dict:
            data.update(words_dict)

        if total_user_messages is not None:
            data["total_user_messages"] = total_user_messages
        if secret:
            data["secret"] = secret

        req = urllib.request.Request(
            f"{api_url}/api/things-i-tell-claude/set",
            data=json.dumps(data).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )

        with urllib.request.urlopen(req, timeout=5) as response:
            response_text = response.read().decode("utf-8")
            if response.status == 200:
                log_upload(api_url, data, "success", response_text)
                return True
            elif response.status == 401:
                log_upload(api_url, data, "unauthorized")
                print(f"\n🚫 AUTHORIZATION FAILED!")
                print(f"   Check your secret key and try again.")
                return "STOP"
            else:
                log_upload(api_url, data, f"error_http_{response.status}")
                print(f"  API error for {date_str}: {response.status}")
                return False
    except urllib.error.HTTPError as e:
        if e.code == 401:
            log_upload(api_url, data, "unauthorized", error=e)
            print(f"\n🚫 AUTHORIZATION FAILED!")
            print(f"   Check your secret key and try again.")
            return "STOP"
        else:
            log_upload(api_url, data, f"error_http_{e.code}", error=e)
            print(f"  API error for {date_str}: HTTP {e.code}")
            return False
    except Exception as e:
        log_upload(api_url, data, "error_exception", error=e)
        print(f"  API error for {date_str}: {e}")
        return False


def process_user_message_entry(entry, compiled_tracked):
    """
    Process a single JSONL entry for user messages and extract word matches.

    Returns dict with:
        - msg_id: The message UUID
        - date_str: Date in YYYY-MM-DD format
        - text_blocks: List of (text, matched_words) tuples
    Returns None if entry should be skipped.
    """
    if entry.get("type") != "user":
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

    # Extract text blocks and check for word matches
    text_blocks = []
    message = entry.get("message", {})
    content = message.get("content")

    if content:
        # Handle both string format and array format
        if isinstance(content, str):
            # Direct string content
            matched_words = {}
            for word_name, word_regex in compiled_tracked.items():
                if word_regex.search(content):
                    matched_words[word_name] = True
            text_blocks.append((content, matched_words))
        elif isinstance(content, list):
            # Array of content items
            for content_item in content:
                if isinstance(content_item, dict) and content_item.get("type") == "text":
                    text = content_item.get("text", "")

                    # Check for tracked word matches
                    matched_words = {}
                    for word_name, word_regex in compiled_tracked.items():
                        if word_regex.search(text):
                            matched_words[word_name] = True

                    text_blocks.append((text, matched_words))

    return {
        "msg_id": msg_id,
        "date_str": date_str,
        "text_blocks": text_blocks,
    }


def get_project_display_name(project_dir_name):
    """Extract readable project name from directory name"""
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
    """Ensure data directory exists"""
    os.makedirs(DATA_DIR, exist_ok=True)
