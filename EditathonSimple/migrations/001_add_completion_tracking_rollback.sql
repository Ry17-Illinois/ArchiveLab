-- Rollback Migration: Remove completion tracking and enhanced validation features
-- Date: 2024
-- Description: Reverts changes from 001_add_completion_tracking.sql

-- ============================================================================
-- 1. Drop trigger and function
-- ============================================================================

DROP TRIGGER IF EXISTS update_edits_updated_at ON edits;
DROP FUNCTION IF EXISTS update_updated_at_column();

-- ============================================================================
-- 2. Revert user_progress view to original
-- ============================================================================

DROP VIEW IF EXISTS user_progress;

CREATE VIEW user_progress AS
SELECT 
    u.username,
    u.name,
    u.assigned_start,
    u.assigned_end,
    (u.assigned_end - u.assigned_start + 1) as total_assigned,
    COUNT(e.id) as pages_edited,
    COUNT(CASE WHEN e.completed THEN 1 END) as pages_completed,
    ROUND(100.0 * COUNT(CASE WHEN e.completed THEN 1 END) / (u.assigned_end - u.assigned_start + 1), 2) as completion_percentage,
    MAX(e.timestamp) as last_activity
FROM users u
LEFT JOIN edits e ON u.username = e.username
GROUP BY u.username, u.name, u.assigned_start, u.assigned_end;

-- ============================================================================
-- 3. Remove entity_validations columns
-- ============================================================================

DROP INDEX IF EXISTS idx_entity_corrected;
ALTER TABLE entity_validations DROP COLUMN IF EXISTS validated_at;

-- ============================================================================
-- 4. Remove metadata_validations columns
-- ============================================================================

DROP INDEX IF EXISTS idx_metadata_removed;
ALTER TABLE metadata_validations DROP COLUMN IF EXISTS removed;
ALTER TABLE metadata_validations DROP COLUMN IF EXISTS validated_at;

-- ============================================================================
-- 5. Remove edits table columns
-- ============================================================================

DROP INDEX IF EXISTS idx_edits_completed_status;
DROP INDEX IF EXISTS idx_edits_last_saved;

ALTER TABLE edits DROP COLUMN IF EXISTS completed_status;
ALTER TABLE edits DROP COLUMN IF EXISTS last_saved_at;
ALTER TABLE edits DROP COLUMN IF EXISTS created_at;
ALTER TABLE edits DROP COLUMN IF EXISTS updated_at;

-- ============================================================================
-- Rollback complete
-- ============================================================================
