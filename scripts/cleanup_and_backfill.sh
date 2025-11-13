#!/bin/bash
set -e

echo "=========================================="
echo "Cleaning up prompt_words and backfilling"
echo "=========================================="
echo

# Delete the table
python3 << 'PYEOF'
import sqlite3
db = sqlite3.connect('counts.db')
db.execute('DROP TABLE IF EXISTS prompt_word_counts')
db.commit()
db.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [t[0] for t in db.fetchall()]
print(f"✓ Remaining tables: {tables}")
db.close()
PYEOF

echo
echo "✓ Table deleted. Running backfill..."
echo

# Run backfill with API upload
cd scripts/prompt_words
python3 backfill.py --upload https://cc.cengizhan.com

echo
echo "✓ Backfill complete!"
