# TODO

## Pattern Detection Verification

### Verify "completely right" pattern detection works

**Status:** ✅ VERIFIED (2025-10-26)

**Context:**

- Added "completely right" to the "absolutely" pattern regex on 2025-10-26
- Pattern: `You(?:'re| are) (?:absolutely|completely) right`

**Verification Results:**

- [x] Regex correctly matches "You're completely right" ✓
- [x] Regex correctly matches "You are completely right" ✓
- [x] Regex correctly matches "You're absolutely right" ✓
- [x] Regex correctly matches "You are absolutely right" ✓
- [x] Current conversation files are being scanned ✓
- [x] Backfill detects both variants correctly ✓

**Test Results (2025-10-26):**
- Found 2x "You're completely right"
- Found 1x "You are completely right"
- Found 5x "You're absolutely right"
- Found 0x "You are absolutely right"
- Total: 8 instances detected correctly

**Conclusion:** Pattern detection is working perfectly. Both "absolutely right" and "completely right" variants (with both 're and are forms) are being detected and counted correctly.

---

## Multi-Workstation Data Integrity

### Implement data merging instead of replacement

**Status:** ✅ COMPLETED (2025-10-26)

**Implementation completed:**

- [x] Phase 1: Database Reset & Schema Update
  - [x] Backed up existing database from Railway (counts_backup_20251026.json)
  - [x] Modified `src/models.py` to use composite primary key (day, workstation_id)
  - [x] Deleted existing database on Railway
  - [x] Tested schema locally
  - [x] Deployed to Railway

- [x] Phase 2: API Modification
  - [x] Modified POST `/api/set` to UPSERT per workstation (src/main.py:161-182)
  - [x] Modified GET `/api/today` to aggregate across workstations (src/main.py:44-78)
  - [x] Modified GET `/api/history` to aggregate across workstations (src/main.py:81-116)
  - [x] Added GET `/api/by-workstation` for debugging/inspection (src/main.py:119-158)

- [x] Phase 3: Client Updates
  - [x] Added `get_workstation_id()` function to `scripts/claude_counter.py:33-57`
  - [x] Modified upload function to include workstation_id (scripts/claude_counter.py:99-100)
  - [x] Tested workstation ID detection on macOS (returns "cengizs-MacBook-Pro")

- [x] Phase 4: Coordinated Deployment
  - [x] Deployed new API to Railway
  - [x] Reset database
  - [x] Ran fresh backfill from cengizs-MacBook-Pro workstation
  - [x] Verified aggregation works correctly

- [x] Phase 5: Documentation & Automation
  - [x] Created comprehensive ADR (docs/adr/001-multi-workstation-data-merging.md)
  - [x] Added GitHub Action for automated daily backups (.github/workflows/backup-data.yml)
  - [x] Created initial backup file (backups/database.json)

**Result:** Multi-workstation support fully implemented. Each workstation can now independently upload data without conflicts. API transparently aggregates across all workstations.

---

## Future Enhancements

- [x] Add `/api/stats` endpoint showing per-workstation contributions ✅ (implemented as `/api/by-workstation`)
- [ ] Create UI view showing data provenance by workstation
- [ ] Add pattern toggle persistence (remember user's chart preferences)
- [ ] Mobile chart improvements (better touch interactions)
- [ ] Add data export functionality (CSV, JSON downloads)
- [ ] Implement rate limiting on API endpoints
- [ ] Add health check endpoint for monitoring
