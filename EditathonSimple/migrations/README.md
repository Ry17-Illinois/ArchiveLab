# Database Migrations

This directory contains database migration scripts for the EditathonSimple application.

## Migration 001: Completion Tracking and Enhanced Validations

**Purpose**: Add support for progress tracking, auto-save, and enhanced validation workflows.

**Changes**:
- Adds completion status tracking to `edits` table (not_started, in_progress, completed)
- Adds timestamp columns for tracking save times and edit duration
- Adds removed flag to `metadata_validations` for removed metadata panel
- Adds validated_at timestamps to validation tables
- Updates `user_progress` view to include new statistics
- Creates automatic `updated_at` trigger

### Running the Migration

**Prerequisites**:
- PostgreSQL database is running
- You have database credentials with ALTER TABLE permissions
- Backup your database before running migrations

**Apply Migration**:
```bash
psql -U your_username -d editathon_db -f migrations/001_add_completion_tracking.sql
```

**Test Migration**:
```bash
psql -U your_username -d editathon_db -f migrations/test_migration.sql
```

**Rollback Migration** (if needed):
```bash
psql -U your_username -d editathon_db -f migrations/001_add_completion_tracking_rollback.sql
```

### What Gets Modified

#### edits table
- **New columns**:
  - `completed_status` VARCHAR(20) - Replaces boolean `completed` with enum
  - `last_saved_at` TIMESTAMP - Tracks last save time (auto or manual)
  - `created_at` TIMESTAMP - When edit record was first created
  - `updated_at` TIMESTAMP - Last modification time (auto-updated)
- **New indexes**:
  - `idx_edits_completed_status` - For filtering by status
  - `idx_edits_last_saved` - For sorting by save time
- **Data migration**: Existing `completed` boolean values are migrated to `completed_status`

#### metadata_validations table
- **New columns**:
  - `removed` BOOLEAN - Whether field is in removed section
  - `validated_at` TIMESTAMP - When validation was performed
- **New indexes**:
  - `idx_metadata_removed` - For filtering removed metadata
- **Data migration**: Existing `timestamp` values are copied to `validated_at`

#### entity_validations table
- **New columns**:
  - `validated_at` TIMESTAMP - When validation was performed
- **New indexes**:
  - `idx_entity_corrected` - For querying corrected entities
- **Data migration**: Existing `timestamp` values are copied to `validated_at`
- **Note**: `corrected_name` and `corrected_type` columns already exist in schema

#### user_progress view
- **Updated** to use new `completed_status` column
- **New columns**:
  - `pages_in_progress` - Count of in-progress pages
  - `pages_not_started` - Count of not-started pages
  - `avg_seconds_per_page` - Average time to complete a page

#### New database objects
- **Function**: `update_updated_at_column()` - Auto-updates `updated_at` timestamp
- **Trigger**: `update_edits_updated_at` - Calls function on edits table updates

### Backward Compatibility

The migration maintains backward compatibility:
- Old `completed` boolean column is preserved (not dropped)
- New `completed_status` is populated from `completed` values
- Existing queries using `completed` will continue to work
- New code should use `completed_status` instead

### Testing

The `test_migration.sql` script performs comprehensive tests:
1. Verifies new columns exist with correct types
2. Tests completion status constraints
3. Tests metadata removed flag
4. Tests entity corrections
5. Verifies indexes were created
6. Tests user_progress view
7. Tests updated_at trigger
8. Tests status transitions
9. Tests metadata remove/restore workflow
10. Cleans up test data

Run the test script after applying the migration to verify everything works correctly.

### Rollback Considerations

The rollback script:
- Removes all new columns and indexes
- Restores original `user_progress` view
- Drops the `updated_at` trigger and function
- **Does NOT** restore data in the old `completed` column
- **Warning**: Rolling back will lose data in new columns

### Performance Impact

- **Minimal**: New indexes improve query performance
- **Storage**: Adds ~50 bytes per edit record for timestamps
- **Trigger overhead**: Negligible (single timestamp update)

### Next Steps

After running this migration:
1. Update backend API to use new `completed_status` column
2. Update queries to use new timestamp columns
3. Implement auto-save functionality using `last_saved_at`
4. Update frontend to display progress statistics
5. Implement removed metadata panel
6. Implement entity correction workflow

## Future Migrations

Additional migrations will be added to this directory as needed. Each migration should:
- Have a sequential number (001, 002, etc.)
- Include both forward and rollback scripts
- Include a test script
- Document changes in this README
