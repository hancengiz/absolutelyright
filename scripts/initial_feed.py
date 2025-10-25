#!/usr/bin/env python3
"""
One-time script to upload ALL historical data to the server.
Unlike backfill.py, this doesn't skip the first day.
"""
import sys
from claude_counter import *


def scan_all_projects():
    compiled_patterns = {
        name: re.compile(pattern, re.IGNORECASE) for name, pattern in PATTERNS.items()
    }
    daily_counts = {name: defaultdict(int) for name in PATTERNS}
    total_counts = {name: 0 for name in PATTERNS}
    total_messages_per_day = defaultdict(int)
    seen_message_ids = set()  # Track processed message IDs to avoid duplicates

    if not os.path.exists(CLAUDE_PROJECTS_BASE):
        print(f"Error: Projects directory not found at {CLAUDE_PROJECTS_BASE}")
        print("Set CLAUDE_PROJECTS env variable to your Claude projects path")
        return daily_counts, total_messages_per_day

    print("Scanning all Claude projects...")

    for project_dir in Path(CLAUDE_PROJECTS_BASE).iterdir():
        if project_dir.is_dir() and not project_dir.name.startswith("."):
            project_name = get_project_display_name(project_dir.name)

            for jsonl_file in project_dir.glob("*.jsonl"):
                try:
                    with open(jsonl_file, "r") as f:
                        for line in f:
                            try:
                                entry = json.loads(line)
                                result = process_message_entry(entry, compiled_patterns)

                                if not result:
                                    continue

                                msg_id = result["msg_id"]

                                # Skip if we've already processed this message
                                if msg_id in seen_message_ids:
                                    continue

                                seen_message_ids.add(msg_id)
                                date_str = result["date_str"]

                                # Count total assistant messages
                                total_messages_per_day[date_str] += 1

                                # Count pattern matches (once per message, not per text block)
                                message_patterns = set()
                                for text, matched_patterns in result["text_blocks"]:
                                    message_patterns.update(matched_patterns.keys())

                                for pattern_name in message_patterns:
                                    daily_counts[pattern_name][date_str] += 1
                                    total_counts[pattern_name] += 1

                            except:
                                continue
                except:
                    pass

    for name, count in total_counts.items():
        unique_days = len(daily_counts[name])
        print(f"Found {count} '{name}' across {unique_days} days")

    return daily_counts, total_messages_per_day


def main():
    """Main initial feed process"""
    print("Claude Pattern Counter - Initial Feed")
    print("=" * 50)
    print("This will upload ALL historical data (no days skipped)")
    print("=" * 50)

    # Check for upload parameters
    api_url = None
    secret = None

    for i, arg in enumerate(sys.argv):
        if arg == "--upload" and i + 2 < len(sys.argv):
            api_url = sys.argv[i + 1]
            secret = sys.argv[i + 2]
            break
        elif arg == "--upload" and i + 1 < len(sys.argv):
            api_url = sys.argv[i + 1]
            break

    if not api_url:
        print("Error: Must specify --upload URL SECRET")
        print("Usage: python3 initial_feed.py --upload https://your-server.com YOUR_SECRET")
        return

    # Show current settings
    print(f"Projects directory: {CLAUDE_PROJECTS_BASE}")
    print("Tracking patterns:")
    for name, pattern in PATTERNS.items():
        print(f"  {name}: {pattern}")
    print(f"Will upload to: {api_url}")
    print("-" * 50)

    # Scan all projects
    daily_counts, total_messages_per_day = scan_all_projects()

    if not any(daily_counts.values()):
        print("No data found.")
        return

    # Get all dates that have any data (pattern matches OR total messages)
    all_dates = set()
    for pattern_counts in daily_counts.values():
        all_dates.update(pattern_counts.keys())
    all_dates.update(total_messages_per_day.keys())
    sorted_dates = sorted(all_dates)

    print(f"\nFound {len(sorted_dates)} days with data")
    print("\nDaily counts:")
    print("-" * 80)

    # Human-readable output
    for date in sorted_dates:
        abs_count = daily_counts["absolutely"].get(date, 0)
        right_count = daily_counts["right"].get(date, 0)
        total_msgs = total_messages_per_day.get(date, 0)

        print(f"{date}: absolutely={abs_count:3d}, right={right_count:3d}, total={total_msgs:3d}")

    print("-" * 50)
    print(f"Total 'absolutely right': {sum(daily_counts['absolutely'].values())}")
    print(f"Total 'right': {sum(daily_counts['right'].values())}")

    # Upload to API
    print("\n" + "-" * 50)
    total_to_upload = len(sorted_dates)
    print(f"Will upload {total_to_upload} days to {api_url}")
    confirm = input("Continue with upload? (y/N): ").strip().lower()
    if confirm not in ["y", "yes"]:
        print("Upload cancelled.")
        return

    print("Uploading to API...")
    success = 0
    failed = 0

    for date in sorted_dates:
        # Collect all pattern counts for this date
        date_patterns = {name: counts.get(date, 0) for name, counts in daily_counts.items()}
        total_msgs = total_messages_per_day.get(date, 0)

        patterns_summary = ", ".join([f"{name}={count:2d}" for name, count in date_patterns.items()])
        upload_text = f"  Uploading {date}: {patterns_summary}, total={total_msgs:3d}..."
        print(f"{upload_text:<75}", end="")

        result = upload_to_api(api_url, secret, date, patterns_dict=date_patterns, total_messages=total_msgs)
        if result == True:
            print("✓")
            success += 1
        elif result == "STOP":
            print("✗")
            failed += 1
            break
        else:
            print("✗")
            failed += 1

    print("-" * 50)
    print(f"Upload complete: {success} successful, {failed} failed")
    if success > 0:
        print(f"View at: {api_url}")


if __name__ == "__main__":
    main()
