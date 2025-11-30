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
        # Add scripts directory to path temporarily for this watcher's imports
        scripts_dir = os.path.dirname(os.path.abspath(__file__))
        sys.path.insert(0, scripts_dir)

        import watcher
        print("[ABSOLUTELY RIGHT WATCHER] Starting...")
        watcher.main()
    except KeyboardInterrupt:
        print("[ABSOLUTELY RIGHT WATCHER] Stopped by user")
    except Exception as e:
        print(f"[ABSOLUTELY RIGHT WATCHER] Error: {e}")
    finally:
        # Clean up path
        if scripts_dir in sys.path:
            sys.path.remove(scripts_dir)


def run_prompt_words_watcher():
    """Run the prompt words watcher in this thread"""
    try:
        # Load prompt words watcher as a unique module to avoid conflicts
        scripts_dir = os.path.dirname(os.path.abspath(__file__))
        prompt_words_dir = os.path.join(scripts_dir, "prompt_words")
        prompt_watcher_path = os.path.join(prompt_words_dir, "watcher.py")

        # Change to prompt_words directory for any relative paths they might use
        original_cwd = os.getcwd()
        os.chdir(prompt_words_dir)

        spec = importlib.util.spec_from_file_location("promptwords_watcher", prompt_watcher_path)
        prompt_watcher = importlib.util.module_from_spec(spec)
        sys.modules["promptwords_watcher"] = prompt_watcher
        spec.loader.exec_module(prompt_watcher)

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
    # time.sleep(0.5)  # Slight delay so output doesn't mix
    # TEMPORARILY DISABLED: prompt_words_thread causing duplicate uploads due to module import conflicts
    # TODO: Fix by running in separate processes instead of threads
    # prompt_words_thread.start()

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
