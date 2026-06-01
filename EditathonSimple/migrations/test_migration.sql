-- Test script for migration 001_add_completion_tracking
-- This script tests the schema changes with sample data

-- ============================================================================
-- Setup: Create test data
-- ============================================================================

-- Insert test user
INSERT INTO users (username, password_hash, name, assigned_start, assigned_end)
VALUES ('test_user', 'test_hash', 'Test User', 1, 10)
ON CONFLICT (username) DO NOTHING;

-- Insert test page
INSERT INTO pages (page_id, page_number, json_file, dublin_core, archival_context)
VALUES ('test_page_001', 1, 'test.json', '{"title": "Test Page"}'::jsonb, '{}'::jsonb)
ON CONFLICT (page_id) DO NOTHING;

-- Insert test entity
INSERT INTO entities (page_id, entity_type, entity_name)
VALUES ('test_page_001', 'PERSON', 'John Doe')
ON CONFLICT DO NOTHING
RETURNING id AS test_entity_id;

-- ============================================================================
-- Test 1: Verify edits table has new columns
-- ============================================================================

SELECT 
    column_name, 
    data_type, 
    column_default,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'edits' 
  AND column_name IN ('completed_status', 'last_saved_at', 'created_at', 'updated_at')
ORDER BY column_name;

-- Expected: 4 rows showing the new columns

-- ============================================================================
-- Test 2: Insert edit with new completion status
-- ============================================================================

INSERT INTO edits (username, page_id, page_number, ocr_selected, transcription, transcription_edited, completed_status)
VALUES ('test_user', 'test_page_001', 1, 'tesseract', 'Test transcription', true, 'in_progress')
ON CONFLICT (username, page_id) 
DO UPDATE SET 
    transcription = EXCLUDED.transcription,
    completed_status = EXCLUDED.completed_status,
    last_saved_at = CURRENT_TIMESTAMP
RETURNING id, completed_status, last_saved_at, created_at, updated_at;

-- Expected: Returns row with completed_status = 'in_progress' and timestamps

-- ============================================================================
-- Test 3: Verify completion status constraint
-- ============================================================================

-- This should fail with constraint violation
DO $$
BEGIN
    INSERT INTO edits (username, page_id, page_number, completed_status)
    VALUES ('test_user', 'test_page_002', 2, 'invalid_status');
    RAISE EXCEPTION 'Test failed: Invalid status was accepted';
EXCEPTION
    WHEN check_violation THEN
        RAISE NOTICE 'Test passed: Invalid status rejected correctly';
END $$;

-- ============================================================================
-- Test 4: Test metadata_validations with removed flag
-- ============================================================================

WITH edit_record AS (
    SELECT id FROM edits WHERE username = 'test_user' AND page_id = 'test_page_001' LIMIT 1
)
INSERT INTO metadata_validations (edit_id, field_name, original_value, validation_status, removed)
SELECT id, 'title', 'Test Title', 'approved', false FROM edit_record
ON CONFLICT DO NOTHING
RETURNING id, field_name, validation_status, removed, validated_at;

-- Expected: Returns row with removed = false and validated_at timestamp

-- ============================================================================
-- Test 5: Test entity_validations with corrections
-- ============================================================================

WITH edit_record AS (
    SELECT id FROM edits WHERE username = 'test_user' AND page_id = 'test_page_001' LIMIT 1
),
entity_record AS (
    SELECT id FROM entities WHERE page_id = 'test_page_001' AND entity_name = 'John Doe' LIMIT 1
)
INSERT INTO entity_validations (edit_id, entity_id, validation_status, corrected_name, corrected_type)
SELECT e.id, ent.id, 'corrected', 'Jane Doe', 'PERSON'
FROM edit_record e, entity_record ent
ON CONFLICT (edit_id, entity_id)
DO UPDATE SET
    validation_status = EXCLUDED.validation_status,
    corrected_name = EXCLUDED.corrected_name,
    corrected_type = EXCLUDED.corrected_type
RETURNING id, validation_status, corrected_name, corrected_type, validated_at;

-- Expected: Returns row with corrected values and validated_at timestamp

-- ============================================================================
-- Test 6: Verify indexes were created
-- ============================================================================

SELECT 
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename IN ('edits', 'metadata_validations', 'entity_validations')
  AND indexname IN (
    'idx_edits_completed_status',
    'idx_edits_last_saved',
    'idx_metadata_removed',
    'idx_entity_corrected'
  )
ORDER BY indexname;

-- Expected: 4 rows showing the new indexes

-- ============================================================================
-- Test 7: Test user_progress view with new columns
-- ============================================================================

SELECT 
    username,
    total_assigned,
    pages_edited,
    pages_completed,
    pages_in_progress,
    pages_not_started,
    completion_percentage,
    avg_seconds_per_page
FROM user_progress
WHERE username = 'test_user';

-- Expected: Returns row with progress statistics including new status breakdown

-- ============================================================================
-- Test 8: Test updated_at trigger
-- ============================================================================

-- Get current updated_at
WITH before_update AS (
    SELECT updated_at FROM edits WHERE username = 'test_user' AND page_id = 'test_page_001'
)
SELECT pg_sleep(1); -- Wait 1 second

-- Update the record
UPDATE edits 
SET transcription = 'Updated transcription'
WHERE username = 'test_user' AND page_id = 'test_page_001';

-- Check if updated_at changed
SELECT 
    'Trigger test: ' || 
    CASE 
        WHEN updated_at > (SELECT updated_at FROM before_update) 
        THEN 'PASSED - updated_at was automatically updated'
        ELSE 'FAILED - updated_at was not updated'
    END as test_result
FROM edits 
WHERE username = 'test_user' AND page_id = 'test_page_001';

-- ============================================================================
-- Test 9: Test completion status transitions
-- ============================================================================

-- Test transition: not_started -> in_progress
UPDATE edits 
SET completed_status = 'in_progress'
WHERE username = 'test_user' AND page_id = 'test_page_001'
RETURNING completed_status;

-- Test transition: in_progress -> completed
UPDATE edits 
SET completed_status = 'completed'
WHERE username = 'test_user' AND page_id = 'test_page_001'
RETURNING completed_status;

-- Expected: Both updates succeed and return the new status

-- ============================================================================
-- Test 10: Test metadata removed/restore workflow
-- ============================================================================

WITH edit_record AS (
    SELECT id FROM edits WHERE username = 'test_user' AND page_id = 'test_page_001' LIMIT 1
)
-- Insert active metadata
INSERT INTO metadata_validations (edit_id, field_name, original_value, validation_status, removed)
SELECT id, 'creator', 'Test Creator', 'approved', false FROM edit_record
ON CONFLICT DO NOTHING;

-- Mark as removed
UPDATE metadata_validations
SET removed = true
WHERE field_name = 'creator'
RETURNING field_name, removed;

-- Restore it
UPDATE metadata_validations
SET removed = false
WHERE field_name = 'creator'
RETURNING field_name, removed;

-- Expected: Successfully toggles removed flag

-- ============================================================================
-- Cleanup: Remove test data
-- ============================================================================

DELETE FROM entity_validations 
WHERE edit_id IN (SELECT id FROM edits WHERE username = 'test_user');

DELETE FROM metadata_validations 
WHERE edit_id IN (SELECT id FROM edits WHERE username = 'test_user');

DELETE FROM edits WHERE username = 'test_user';
DELETE FROM entities WHERE page_id = 'test_page_001';
DELETE FROM pages WHERE page_id = 'test_page_001';
DELETE FROM users WHERE username = 'test_user';

-- ============================================================================
-- Test Summary
-- ============================================================================

SELECT 
    '✓ All migration tests completed' as status,
    'Review output above to verify all tests passed' as note;
