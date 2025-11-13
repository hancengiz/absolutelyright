#!/usr/bin/env python3
"""
Cleanup script to delete the prompt_word_counts table from production database.
Run on Railway server: railway ssh -- python3 scripts/cleanup_prompt_words.py
"""
import sqlite3
import os

def cleanup_prompt_words_table():
    """Delete the prompt_word_counts table"""
    db_path = 'counts.db'

    if not os.path.exists(db_path):
        print(f"✗ Database file not found: {db_path}")
        return False

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check what tables exist before
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables_before = [t[0] for t in cursor.fetchall()]
        print(f"Tables before: {tables_before}")

        # Check if prompt_word_counts exists and has data
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='prompt_word_counts'")
        table_exists = cursor.fetchone()[0]

        if table_exists:
            cursor.execute("SELECT COUNT(*) FROM prompt_word_counts")
            row_count = cursor.fetchone()[0]
            print(f"Found prompt_word_counts with {row_count} rows")

            # Delete the table
            cursor.execute('DROP TABLE prompt_word_counts')
            conn.commit()
            print("✓ prompt_word_counts table deleted")
        else:
            print("ℹ prompt_word_counts table does not exist")

        # Verify what tables remain
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables_after = [t[0] for t in cursor.fetchall()]
        print(f"Tables after: {tables_after}")

        conn.close()
        return True

    except Exception as e:
        print(f"✗ Error: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Cleaning up prompt_words data from production database")
    print("=" * 60)
    print()

    success = cleanup_prompt_words_table()

    print()
    if success:
        print("✓ Cleanup complete. Next: run backfill to rebuild clean data")
        print("  Command: python3 scripts/prompt_words/backfill.py --upload https://cc.cengizhan.com <secret>")
    else:
        print("✗ Cleanup failed")
