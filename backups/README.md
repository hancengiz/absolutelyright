# Automated Database Backups

This directory contains automated backups from the GitHub Action workflow.

## Current Backup

- **`database.json`**: Current state of the database from `/api/by-workstation`
- Updated daily at midnight UTC via GitHub Actions
- Git history tracks all changes over time

## How It Works

### Automatic Updates (GitHub Actions)

The `.github/workflows/backup-data.yml` workflow runs daily at midnight UTC and:
1. Fetches data from `https://cc.cengizhan.com/api/by-workstation`
2. Saves to `backups/database.json`
3. Commits changes if data has changed
4. Git tracks the history of all changes

### Manual Update (Local)

To manually update the backup file locally:

```bash
# Fetch latest data and save to backup file
curl -s https://cc.cengizhan.com/api/by-workstation | python3 -m json.tool > backups/database.json

# Check what changed
git diff backups/database.json

# Commit if you want to save the changes
git add backups/database.json
git commit -m "Manual backup update: $(date +%Y-%m-%d)"
git push
```

### Trigger GitHub Action Manually

You can also trigger the backup workflow manually:
1. Go to [Actions tab](../../actions) in this repository
2. Select "Backup Database" workflow
3. Click "Run workflow" button

## Viewing Backup History

```bash
# View all backup commits
git log --oneline -- backups/database.json

# View changes in a specific commit
git show <commit-hash> backups/database.json

# View changes between dates
git diff HEAD~7 HEAD -- backups/database.json
```

## Restoring Data

If you need to restore data from a backup:

```bash
# View available backups in git history
git log --oneline -- backups/database.json

# Restore to a specific date
git checkout <commit-hash> -- backups/database.json

# Or restore from a specific date
git checkout 'main@{2024-10-20}' -- backups/database.json
```

Note: The backup contains the complete database state including all workstations. To restore to Railway, you would need to:
1. Parse the JSON file
2. Recreate the database records
3. Upload via the `/api/set` endpoint with appropriate workstation_id values
