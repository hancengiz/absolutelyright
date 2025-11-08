#!/usr/bin/env python3
"""Restore database from backup JSON file."""
import json
import asyncio
from pathlib import Path
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.database import init_db, get_session
from src.models import DayCount


async def restore_from_backup(backup_file: str):
    """Restore database from backup JSON."""
    # Read backup file
    with open(backup_file, 'r') as f:
        backup_data = json.load(f)

    print(f"Loading backup from {backup_file}")
    print(f"Found {len(backup_data)} workstations")

    # Initialize database
    await init_db()

    # Get session
    from src.database import async_session_maker
    async with async_session_maker() as session:
        # Clear existing data (optional - comment out to append)
        from sqlalchemy import delete
        await session.execute(delete(DayCount))
        await session.commit()
        print("Cleared existing data")

        # Import data
        total_records = 0
        for ws_data in backup_data:
            workstation_id = ws_data['workstation_id']
            history = ws_data['history']

            print(f"\nImporting {workstation_id}: {len(history)} days")

            for day_data in history:
                day = day_data['day']
                total_messages = day_data.get('total_messages', 0)

                # Extract patterns
                patterns = {}
                for key in ['absolutely', 'right', 'perfect', 'excellent']:
                    if key in day_data:
                        patterns[key] = day_data[key]

                # Create record
                record = DayCount(
                    day=day,
                    workstation_id=workstation_id,
                    patterns=json.dumps(patterns),
                    total_messages=total_messages
                )
                session.add(record)
                total_records += 1

        # Commit all records
        await session.commit()
        print(f"\n✓ Imported {total_records} total records")

    print("\nRestore complete!")


if __name__ == "__main__":
    backup_file = sys.argv[1] if len(sys.argv) > 1 else "backups/database.json"

    if not Path(backup_file).exists():
        print(f"Error: Backup file {backup_file} not found")
        sys.exit(1)

    asyncio.run(restore_from_backup(backup_file))