# Quick Start Guide - Database Migration 001

## TL;DR

This migration adds completion tracking, auto-save timestamps, and enhanced validation features.

## Running the Migration

### Option 1: Using Node.js Script (Recommended)

```bash
cd EditathonSimple
node migrations/run_migration.js apply 001
```

### Option 2: Using psql Directly

```bash
cd EditathonSimple/migrations
psql -U editathon_user -d editathon_db -f 001_add_completion_tracking.sql
```

### Option 3: Using Environment Variables

```bash
export DB_HOST=localhost
export DB_NAME=editathon_db
export DB_USER=editathon_user
export DB_PASSWORD=your_password
export DB_PORT=5432

node migrations/run_migration.js apply 001
```

## Testing the Migration

```bash
node migrations/run_migration.js test 001
```

This will:
- Create test data
- Verify all new columns exist
- Test constraints and triggers
- Clean up test data

## What Changed?

### edits table
- ✓ Added `completed_status` (not_started, in_progress, completed)
- ✓ Added `last_saved_at`, `created_at`, `updated_at` timestamps
- ✓ Auto-updates `updated_at` on changes

### metadata_validations table
- ✓ Added `removed` flag (for removed metadata panel)
- ✓ Added `validated_at` timestamp

### entity_validations table
- ✓ Added `validated_at` timestamp
- ✓ Already has `corrected_name` and `corrected_type`

### user_progress view
- ✓ Now includes `pages_in_progress`, `pages_not_started`
- ✓ Calculates `avg_seconds_per_page`

## Verification

After running the migration, check:

```sql
-- Verify new columns
\d edits
\d metadata_validations
\d entity_validations

-- Verify indexes
\di idx_edits_completed_status
\di idx_edits_last_saved
\di idx_metadata_removed
\di idx_entity_corrected

-- Verify view
SELECT * FROM user_progress LIMIT 1;

-- Verify trigger
SELECT tgname FROM pg_trigger WHERE tgname = 'update_edits_updated_at';
```

## Common Issues

### Issue: "relation already exists"
**Solution:** Migration was already applied. Check with:
```sql
SELECT column_name FROM information_schema.columns 
WHERE table_name = 'edits' AND column_name = 'completed_status';
```

### Issue: "permission denied"
**Solution:** Ensure your database user has ALTER TABLE permissions:
```sql
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO editathon_user;
```

### Issue: "database connection failed"
**Solution:** Check your database is running and credentials are correct:
```bash
psql -U editathon_user -d editathon_db -c "SELECT NOW();"
```

## Rollback (Emergency Only)

⚠️ **Warning:** Rolling back will delete data in new columns!

```bash
node migrations/run_migration.js rollback 001
```

## Next Steps

After successful migration:

1. **Update Backend API** - Modify endpoints to use new columns
2. **Update Frontend** - Add UI for progress tracking
3. **Test Thoroughly** - Verify all workflows work correctly

## Need Help?

- See `README.md` for detailed documentation
- See `SCHEMA_CHANGES.md` for API integration examples
- Check `test_migration.sql` for usage examples
