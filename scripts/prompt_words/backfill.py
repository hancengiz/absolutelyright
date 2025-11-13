#!/usr/bin/env python3
"""Backfill script for prompt words - scans all historical user messages"""
import sys
from word_counter import *


def scan_all_projects():
    """Scan all projects for user messages and word matches"""
    compiled_tracked = {
        name: re.compile(pattern, re.IGNORECASE) for name, pattern in TRACKED_WORDS.items()
    }

    daily_word_counts = {name: defaultdict(int) for name in TRACKED_WORDS}
    total_word_counts = {name: 0 for name in TRACKED_WORDS}
    total_user_messages_per_day = defaultdict(int)
    seen_message_ids = set()  # Track processed message IDs to avoid duplicates

    if not os.path.exists(CLAUDE_PROJECTS_BASE):
        print(f"Error: Projects directory not found at {CLAUDE_PROJECTS_BASE}")
        print("Set CLAUDE_PROJECTS env variable to your Claude projects path")
        return daily_word_counts, total_user_messages_per_day

    print("Scanning all Claude projects for user messages...")

    for project_dir in Path(CLAUDE_PROJECTS_BASE).iterdir():
        if project_dir.is_dir() and not project_dir.name.startswith("."):
            for jsonl_file in project_dir.glob("*.jsonl"):
                try:
                    with open(jsonl_file, "r") as f:
                        for line in f:
                            try:
                                entry = json.loads(line)
                                result = process_user_message_entry(entry, compiled_tracked)

                                if not result:
                                    continue

                                msg_id = result["msg_id"]

                                # Skip if we've already processed this message
                                if msg_id in seen_message_ids:
                                    continue

                                seen_message_ids.add(msg_id)
                                date_str = result["date_str"]

                                # Count total user messages
                                total_user_messages_per_day[date_str] += 1

                                # Process text blocks for word matches (count once per message)
                                message_words = set()
                                for text, matched_words in result["text_blocks"]:
                                    message_words.update(matched_words.keys())

                                for word_name in message_words:
                                    daily_word_counts[word_name][date_str] += 1
                                    total_word_counts[word_name] += 1

                            except:
                                continue
                except:
                    pass

    for name, count in total_word_counts.items():
        unique_days = len(daily_word_counts[name])
        print(f"Found {count} '{name}' across {unique_days} days")

    return daily_word_counts, total_user_messages_per_day


def main():
    """Main backfill process"""
    print("Prompt Words Backfill")
    print("=" * 50)

    # Use config server URL by default, allow command line override
    api_url = SERVER_URL if "--upload" in sys.argv else None
    secret = None

    for i, arg in enumerate(sys.argv):
        if arg == "--upload":
            # Check if next arg is a URL (doesn't start with --)
            if i + 1 < len(sys.argv) and not sys.argv[i + 1].startswith("--"):
                api_url = sys.argv[i + 1]
                # Check if there's a secret after the URL
                if i + 2 < len(sys.argv) and not sys.argv[i + 2].startswith("--"):
                    secret = sys.argv[i + 2]
        elif arg == "--secret" and i + 1 < len(sys.argv):
            secret = sys.argv[i + 1]

    # Show current settings
    print(f"Projects directory: {CLAUDE_PROJECTS_BASE}")
    print("Tracking words:")
    for name, pattern in TRACKED_WORDS.items():
        print(f"  {name}: {pattern}")
    if api_url:
        print(f"Will upload to: {api_url}")
    print("-" * 50)

    # Scan all projects
    daily_word_counts, total_user_messages_per_day = scan_all_projects()

    if not any(daily_word_counts.values()):
        print("No data found.")
        return

    # Get all dates that have any data (word matches OR total messages)
    all_dates = set()
    for word_counts in daily_word_counts.values():
        all_dates.update(word_counts.keys())
    all_dates.update(total_user_messages_per_day.keys())
    sorted_dates = sorted(all_dates)

    print(f"\nFound {len(sorted_dates)} days with data")
    print("\nDaily counts:")
    print("-" * 80)

    # Output format based on arguments
    if "--json" in sys.argv:
        # JSON output for piping to other tools
        output = {word: dict(counts) for word, counts in daily_word_counts.items()}
        output["total_user_messages"] = dict(total_user_messages_per_day)
        print(json.dumps(output, indent=2))
    else:
        # Human-readable output
        for date in sorted_dates:
            # Get counts for configured words
            word_summary = []
            for word_name in TRACKED_WORDS.keys():
                count = daily_word_counts[word_name].get(date, 0)
                if count > 0:
                    word_summary.append(f"{word_name}={count}")

            total_msgs = total_user_messages_per_day.get(date, 0)

            words_str = ", ".join(word_summary) if word_summary else "no words"
            print(f"{date}: {words_str}, total_user_messages={total_msgs}")

        print("-" * 50)
        for word_name in TRACKED_WORDS.keys():
            total = sum(daily_word_counts[word_name].values())
            print(f"Total '{word_name}': {total}")

        # Upload to API if requested
        if api_url:
            print("\n" + "-" * 50)
            total_to_upload = sum(
                1
                for date in sorted_dates
                if any(daily_word_counts[word].get(date, 0) > 0 for word in daily_word_counts.keys())
                or total_user_messages_per_day.get(date, 0) > 0
            )

            print(f"Found {total_to_upload} days with data to upload.")
            confirm = input("Continue with upload? (y/N): ").strip().lower()
            if confirm not in ["y", "yes"]:
                print("Upload cancelled.")
                return

            print("Uploading to API...")
            success = 0
            failed = 0

            for date in sorted_dates:
                # Collect all word counts for this date
                date_words = {name: counts.get(date, 0) for name, counts in daily_word_counts.items()}
                total_msgs = total_user_messages_per_day.get(date, 0)

                # Only upload if there are any word matches or messages
                if any(date_words.values()) or total_msgs > 0:
                    words_summary = ", ".join([f"{name}={count:2d}" for name, count in date_words.items()])
                    upload_text = f"  Uploading {date}: {words_summary}, total_user_messages={total_msgs:3d}..."
                    print(f"{upload_text:<75}", end="")

                    result = upload_to_api(
                        api_url, secret, date, words_dict=date_words, total_user_messages=total_msgs
                    )
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
