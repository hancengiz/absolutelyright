#!/usr/bin/env python3
import sys
import time
from claude_counter import *

# Additional data files for watcher
PROJECT_COUNTS_FILE = os.path.join(DATA_DIR, "project_counts.json")
PROCESSED_IDS_FILE = os.path.join(DATA_DIR, "processed_ids.json")


def load_processed_ids():
    """Load set of already processed message IDs"""
    if os.path.exists(PROCESSED_IDS_FILE):
        try:
            with open(PROCESSED_IDS_FILE, "r") as f:
                return set(json.load(f))
        except:
            pass
    return set()


def save_processed_ids(ids_set):
    """Save processed message IDs"""
    with open(PROCESSED_IDS_FILE, "w") as f:
        json.dump(list(ids_set), f)


def load_project_counts():
    """Load per-project counts"""
    if os.path.exists(PROJECT_COUNTS_FILE):
        try:
            with open(PROJECT_COUNTS_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {}


def save_project_counts(counts):
    """Save per-project counts"""
    with open(PROJECT_COUNTS_FILE, "w") as f:
        json.dump(counts, f, indent=2)


def load_pattern_counts(pattern_name):
    """Load daily counts for a specific pattern"""
    filename = os.path.join(DATA_DIR, f"daily_{pattern_name}_counts.json")
    if os.path.exists(filename):
        try:
            with open(filename, "r") as f:
                return json.load(f)
        except:
            pass
    return {}


def save_pattern_counts(pattern_name, counts):
    """Save daily counts for a specific pattern"""
    filename = os.path.join(DATA_DIR, f"daily_{pattern_name}_counts.json")
    with open(filename, "w") as f:
        json.dump(counts, f, indent=2)


def main():
    """Main watcher loop"""
    ensure_data_dir()

    # Check for upload parameters from command line
    api_url = None
    api_secret = None

    for i, arg in enumerate(sys.argv):
        if arg == "--upload" and i + 1 < len(sys.argv):
            api_url = sys.argv[i + 1]
            if i + 2 < len(sys.argv) and not sys.argv[i + 2].startswith("--"):
                api_secret = sys.argv[i + 2]
            break

    print("Claude Pattern Watcher")
    print("=" * 50)
    print(f"Watching: {CLAUDE_PROJECTS_BASE}")
    print(f"Data directory: {DATA_DIR}")
    print("Tracking patterns:")
    for name, pattern in PATTERNS.items():
        print(f"  {name}: {pattern}")
    if api_url:
        print(f"API URL: {api_url}")
    print("-" * 50)

    # Compile patterns
    compiled_patterns = {
        name: re.compile(pattern, re.IGNORECASE) for name, pattern in PATTERNS.items()
    }

    # Initialize
    processed_ids = load_processed_ids()
    project_counts = load_project_counts()
    pattern_counts = {name: load_pattern_counts(name) for name in PATTERNS}

    # Upload today's data on startup if API is configured
    if api_url:
        today = datetime.now().strftime("%Y-%m-%d")
        today_abs = pattern_counts["absolutely"].get(today, 0)
        today_right = pattern_counts["right"].get(today, 0)
        print(f"Uploading today's counts: absolutely={today_abs}, right={today_right}")
        if upload_to_api(api_url, api_secret, today, today_abs, today_right):
            print("  ✓ Upload successful")
        else:
            print("  ✗ Upload failed")

    print("-" * 50)

    if not os.path.exists(CLAUDE_PROJECTS_BASE):
        print(f"Error: Claude projects directory not found at {CLAUDE_PROJECTS_BASE}")
        print("Set CLAUDE_PROJECTS environment variable to your Claude projects path")
        return

    try:
        while True:
            new_matches_by_pattern = {name: 0 for name in PATTERNS}

            for project_dir in Path(CLAUDE_PROJECTS_BASE).iterdir():
                if project_dir.is_dir() and not project_dir.name.startswith("."):
                    project_name = get_project_display_name(project_dir.name)

                    # Scan all JSONL files in this project
                    for jsonl_file in project_dir.glob("*.jsonl"):
                        matches = scan_jsonl_file(
                            jsonl_file, processed_ids, project_name, compiled_patterns
                        )

                        for match in matches:
                            # Add to processed IDs
                            processed_ids.add(match["id"])

                            # Update counts for each matched pattern
                            for pattern_name in match["matches"]:
                                new_matches_by_pattern[pattern_name] += 1

                                # Update daily counts
                                date_str = match["date"]
                                if date_str not in pattern_counts[pattern_name]:
                                    pattern_counts[pattern_name][date_str] = 0
                                pattern_counts[pattern_name][date_str] += 1

                                # Update project counts (only for "absolutely")
                                if pattern_name == "absolutely":
                                    if project_name not in project_counts:
                                        project_counts[project_name] = 0
                                    project_counts[project_name] += 1

                            # Print notification
                            match_types = list(match["matches"].keys())
                            print(
                                f"[{datetime.now().strftime('%H:%M:%S')}] {', '.join(match_types).upper()} in {project_name}: {match['text']}"
                            )

            if any(new_matches_by_pattern.values()):
                # Save all state
                save_project_counts(project_counts)
                save_processed_ids(processed_ids)
                for pattern_name, counts in pattern_counts.items():
                    save_pattern_counts(pattern_name, counts)

                updates = [
                    f"{name}: +{count}"
                    for name, count in new_matches_by_pattern.items()
                    if count > 0
                ]
                print(f"Updated: {', '.join(updates)}")

                # Upload to API if configured (only absolutely and right)
                if api_url:
                    today = datetime.now().strftime("%Y-%m-%d")
                    today_abs = pattern_counts["absolutely"].get(today, 0)
                    today_right = pattern_counts["right"].get(today, 0)
                    if upload_to_api(
                        api_url, api_secret, today, today_abs, today_right
                    ):
                        print(
                            f"  ✓ Uploaded to API: absolutely={today_abs}, right={today_right}"
                        )

            time.sleep(int(os.environ.get("CHECK_INTERVAL", "2")))

    except KeyboardInterrupt:
        print("\n" + "-" * 50)
        print("Stopping watcher...")
        for name in PATTERNS:
            total = sum(pattern_counts[name].values())
            print(f"Final '{name}' count: {total}")


if __name__ == "__main__":
    main()
