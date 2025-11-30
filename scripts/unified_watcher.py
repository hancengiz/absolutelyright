#!/usr/bin/env python3
"""
Unified watcher for both tracker types (absolutely right + prompt words).
Runs both watchers concurrently in separate threads.
"""
import sys
import os
import threading
import time

def run_absolutely_right_watcher():
    """Run the absolutely right watcher in this thread"""
    try:
        # Import from scripts directory
        scripts_dir = os.path.dirname(os.path.abspath(__file__))
        sys.path.insert(0, scripts_dir)
        import watcher
        print("[ABSOLUTELY RIGHT WATCHER] Starting...")
        watcher.main()
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

        # Clear path and add only prompt_words to avoid conflicts
        if prompt_words_dir not in sys.path:
            sys.path.insert(0, prompt_words_dir)
        import watcher as prompt_watcher
        print("[PROMPT WORDS WATCHER] Starting...")
        prompt_watcher.main()
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

    # Pass through command-line arguments to child watchers
    # (e.g., --secret for authentication)
    sys.argv[0] = "unified_watcher"  # Keep original command name for child processes

    print()

    # Create daemon threads for both watchers
    absolutely_thread = threading.Thread(
        target=run_absolutely_right_watcher,
        name="AbsolutelyRightWatcher",
        daemon=True
    )

    prompt_words_thread = threading.Thread(
        target=run_prompt_words_watcher,
        name="PromptWordsWatcher",
        daemon=True
    )

    # Start both threads
    absolutely_thread.start()
    time.sleep(0.5)  # Slight delay so output doesn't mix
    prompt_words_thread.start()

    print()
    print("Both watchers are now running. Press Ctrl+C to stop all.")
    print("-" * 60)
    print()

    try:
        # Keep the main thread alive while daemon threads run
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        print()
        print("-" * 60)
        print("Stopping all watchers...")
        print("All watchers stopped.")


if __name__ == "__main__":
    main()
