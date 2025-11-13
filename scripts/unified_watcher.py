#!/usr/bin/env python3
"""
Unified watcher for both tracker types (absolutely right + prompt words).
Runs both watchers concurrently in separate threads.
"""
import sys
import os
import threading
import time
from pathlib import Path

# Add scripts to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompt_words"))


def run_absolutely_right_watcher():
    """Run the absolutely right watcher in this thread"""
    try:
        from watcher import main as absolutely_main
        print("[ABSOLUTELY RIGHT WATCHER] Starting...")
        absolutely_main()
    except KeyboardInterrupt:
        print("[ABSOLUTELY RIGHT WATCHER] Stopped by user")
    except Exception as e:
        print(f"[ABSOLUTELY RIGHT WATCHER] Error: {e}")


def run_prompt_words_watcher():
    """Run the prompt words watcher in this thread"""
    try:
        # Change to prompt_words directory for proper imports
        original_cwd = os.getcwd()
        prompt_words_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompt_words")
        os.chdir(prompt_words_dir)

        from watcher import main as prompt_words_main
        print("[PROMPT WORDS WATCHER] Starting...")
        prompt_words_main()
    except KeyboardInterrupt:
        print("[PROMPT WORDS WATCHER] Stopped by user")
    except Exception as e:
        print(f"[PROMPT WORDS WATCHER] Error: {e}")
    finally:
        os.chdir(original_cwd)


def main():
    """Main unified watcher orchestrator"""
    print("=" * 60)
    print("UNIFIED WATCHER - Running both trackers concurrently")
    print("=" * 60)
    print()

    # Create threads for both watchers
    absolutely_thread = threading.Thread(
        target=run_absolutely_right_watcher,
        name="AbsolutelyRightWatcher",
        daemon=False
    )

    prompt_words_thread = threading.Thread(
        target=run_prompt_words_watcher,
        name="PromptWordsWatcher",
        daemon=False
    )

    # Start both threads
    absolutely_thread.start()
    time.sleep(0.5)  # Slight delay so output doesn't mix
    prompt_words_thread.start()

    print()
    print("Both watchers are now running. Press Ctrl+C to stop all.")
    print("-" * 60)

    try:
        # Wait for both threads to complete
        absolutely_thread.join()
        prompt_words_thread.join()
    except KeyboardInterrupt:
        print()
        print("-" * 60)
        print("Stopping all watchers...")
        # Threads will stop on KeyboardInterrupt
        absolutely_thread.join(timeout=5)
        prompt_words_thread.join(timeout=5)
        print("All watchers stopped.")


if __name__ == "__main__":
    main()
