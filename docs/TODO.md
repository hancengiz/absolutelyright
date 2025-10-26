# TODO

## Pattern Detection Verification

### Verify "completely right" pattern detection works

**Context:**

- Added "completely right" to the "absolutely" pattern regex on 2025-10-26
- Pattern: `You(?:'re| are) (?:absolutely|completely) right`
- Found 52 occurrences in current conversation but backfill only showing 4 total for today

**Tasks:**

- [ ] Verify the regex correctly matches "You're completely right"
- [ ] Check if current conversation (4f4802bd-3ba4-46c1-888e-00d24a2f68fa.jsonl) is being scanned
- [ ] Run backfill again after this conversation is saved to disk
- [ ] Manually test the regex pattern:

  ```python
  import re
  pattern = re.compile(r"You(?:'re| are) (?:absolutely|completely) right", re.IGNORECASE)
  pattern.search("You're completely right")  # Should match
  pattern.search("You are completely right")  # Should match
  ```

- [ ] Compare expected vs actual counts:
  - Expected: 52+ (from grep count in current conversation)
  - Actual: 4 (from backfill)
  - Investigate discrepancy

- [ ] Possible issues to investigate:

  - [ ] Backfill deduplication logic
  - [ ] Case sensitivity
  - [ ] Message type filtering (only counting assistant messages once?)
  - [ ] File write timing (conversation still being written)

**Next Steps:**

1. Wait for conversation to complete and save
2. Re-run backfill: `python3 scripts/backfill.py`
3. Upload new counts: `echo "y" | python3 scripts/backfill.py --upload --secret "..."`
4. Verify on <https://cc.cengizhan.com>

---

## Multi-Workstation Data Integrity

### Implement data merging instead of replacement

**Status:** ADR created (docs/adr/001-multi-workstation-data-merging.md)

**Implementation tasks:**

- [ ] Phase 1: Database Reset & Schema Update

  - [ ] **Backup existing database from Railway**:
    ```bash
    railway login
    railway link
    railway run cat /app/data/counts.db > counts_backup_$(date +%Y%m%d).db
    ```
  - [ ] Verify backup file is valid (check file size, try opening with sqlite3)
  - [ ] Delete existing database on Railway
  - [ ] Create `processed_messages` table migration
  - [ ] Add SQLAlchemy model for ProcessedMessage
  - [ ] Test migration locally
  - [ ] Deploy to Railway

- [ ] Phase 2: API Modification (Breaking Change)

  - [ ] Replace existing `/api/set` with merge logic
  - [ ] Add deduplication logic
  - [ ] Add tests for merge behavior
  - [ ] Remove old SET/replace code

- [ ] Phase 3: Client Updates (All at Once)

  - [ ] Add `get_workstation_id()` function to `claude_counter.py` (uses macOS LocalHostName)
  - [ ] Modify `claude_counter.py` to include workstation_id in uploads
  - [ ] Update `backfill.py` with same workstation_id logic
  - [ ] Update `watcher.py` with same workstation_id logic
  - [ ] Test workstation ID detection on macOS (should return "cengizs-MacBook-Pro")

- [ ] Phase 4: Coordinated Deployment

  - [ ] Stop all running watchers/backfills
  - [ ] Deploy new API to Railway
  - [ ] Reset database
  - [ ] Update client scripts on all workstations
  - [ ] Run fresh backfill from all workstations

- [ ] Phase 5: Documentation

  - [ ] Update README with breaking change notice
  - [ ] Update README with multi-workstation setup instructions
  - [ ] Document environment variables
  - [ ] Add migration guide

**Priority:** High (prevents data loss when using multiple workstations)

**Note:** This is a breaking change - database reset and all clients must update together.

---

## Future Enhancements

- [ ] Add `/api/stats` endpoint showing per-workstation contributions
- [ ] Create UI view showing data provenance by workstation
- [ ] Implement cleanup job for old processed_messages (>90 days)
- [ ] Add pattern toggle persistence (remember user's chart preferences)
- [ ] Mobile chart improvements (better touch interactions)
