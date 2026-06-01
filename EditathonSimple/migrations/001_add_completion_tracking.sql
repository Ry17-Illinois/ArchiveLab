-- Migration: Add completion tracking and enhanced validation features
-- Date: 2024
-- Description: Adds completion status, timestamps, removed flag, and entity corrections

-- ============================================================================
-- 1. Modify edits table for completion tracking
-- ============================================================================

-- Add completion status column (replaces boolean completed with enum)
ALTER TABLE edits
ADD COLUMN completed_status VARCHAR(20) DEFAULT 'not_started' 
  CHECK (completed_status IN ('not_started', 'in_progress', 'completed'));

-- Add timestamp columns for tracking
ALTER TABLE edits
ADD COLUMN last_saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Migrate existing completed boolean to completed_status
UPDATE edits 
SET completed_status = CASE 
  WHEN completed = TRUE THEN 'completed'
  WHEN transcription_edited = TRUE THEN 'in_progress'
  ELSE 'not_started'
END;

-- Backfill timestamps from existing timestamp column
UPDATE edits 
SET created_at = timestamp,
    last_saved_at = timestamp,
    updated_at = timestamp;

-- Create indexes for performance
CREATE INDEX idx_edits_completed_status ON edits(username, completed_status);
CREATE INDEX idx_edits_last_saved ON edits(last_saved_at);

-- Add comment
COMMENT ON COLUMN edits.completed_status IS 'Page completion status: not_started, in_progress, or completed';
COMMENT ON COLUMN edits.last_saved_at IS 'Timestamp of last save (manual or auto-save)';
COMMENT ON COLUMN edits.created_at IS 'Timestamp when edit record was first created';
COMMENT ON COLUMN edits.updated_at IS 'Timestamp of last update to edit record';

-- ============================================================================
-- 2. Modify metadata_validations table for removed metadata
-- ============================================================================

-- Add removed flag
ALTER TABLE metadata_validations
ADD COLUMN removed BOOLEAN DEFAULT FALSE;

-- Add validated_at timestamp
ALTER TABLE metadata_validations
ADD COLUMN validated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Backfill validated_at from existing timestamp
UPDATE metadata_validations 
SET validated_at = timestamp;

-- Create index for removed metadata queries
CREATE INDEX idx_metadata_removed ON metadata_validations(edit_id, removed);

-- Add comments
COMMENT ON COLUMN metadata_validations.removed IS 'Whether metadata field has been removed from active section';
COMMENT ON COLUMN metadata_validations.validated_at IS 'Timestamp when validation status was set';

-- ============================================================================
-- 3. Modify entity_validations table for entity corrections
-- ============================================================================

-- Add validated_at timestamp (corrected_name and corrected_type already exist)
ALTER TABLE entity_validations
ADD COLUMN validated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Backfill validated_at from existing timestamp
UPDATE entity_validations 
SET validated_at = timestamp;

-- Create index for corrected entities
CREATE INDEX idx_entity_corrected ON entity_validations(entity_id, validation_status);

-- Add comment
COMMENT ON COLUMN entity_validations.validated_at IS 'Timestamp when validation status was set';
COMMENT ON COLUMN entity_validations.corrected_name IS 'User-corrected entity name (if status is corrected)';
COMMENT ON COLUMN entity_validations.corrected_type IS 'User-corrected entity type (if status is corrected)';

-- ============================================================================
-- 4. Update user_progress view to use new completed_status
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
    COUNT(CASE WHEN e.completed_status = 'completed' THEN 1 END) as pages_completed,
    COUNT(CASE WHEN e.completed_status = 'in_progress' THEN 1 END) as pages_in_progress,
    COUNT(CASE WHEN e.completed_status = 'not_started' THEN 1 END) as pages_not_started,
    ROUND(100.0 * COUNT(CASE WHEN e.completed_status = 'completed' THEN 1 END) / (u.assigned_end - u.assigned_start + 1), 2) as completion_percentage,
    MAX(e.updated_at) as last_activity,
    AVG(CASE 
      WHEN e.completed_status = 'completed' 
      THEN EXTRACT(EPOCH FROM (e.updated_at - e.created_at))
      ELSE NULL 
    END) as avg_seconds_per_page
FROM users u
LEFT JOIN edits e ON u.username = e.username
GROUP BY u.username, u.name, u.assigned_start, u.assigned_end;

COMMENT ON VIEW user_progress IS 'User progress statistics with completion status breakdown and average time per page';

-- ============================================================================
-- 5. Create function to update updated_at timestamp automatically
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for edits table
CREATE TRIGGER update_edits_updated_at
    BEFORE UPDATE ON edits
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

COMMENT ON FUNCTION update_updated_at_column IS 'Automatically updates updated_at timestamp on row modification';

-- ============================================================================
-- Migration complete
-- ============================================================================
