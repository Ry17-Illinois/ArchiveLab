-- Clear Editathon Data Tables
-- This removes all page data but preserves users and table structure
-- Run this in phpPgAdmin before importing new data

BEGIN;

-- Clear data tables (in order to respect foreign key constraints)
DELETE FROM entity_validations;
DELETE FROM metadata_validations;
DELETE FROM edits;
DELETE FROM entities;
DELETE FROM ocr_versions;
DELETE FROM pages;

-- Optionally clear user assignments (uncomment if you want to reassign pages)
-- UPDATE users SET assigned_start = 0, assigned_end = 0 WHERE username != 'admin';

-- Clear sessions (optional - forces all users to log in again)
-- DELETE FROM sessions;

COMMIT;

-- Verify tables are empty
SELECT 'pages' as table_name, COUNT(*) as count FROM pages
UNION ALL
SELECT 'ocr_versions', COUNT(*) FROM ocr_versions
UNION ALL
SELECT 'entities', COUNT(*) FROM entities
UNION ALL
SELECT 'edits', COUNT(*) FROM edits
UNION ALL
SELECT 'metadata_validations', COUNT(*) FROM metadata_validations
UNION ALL
SELECT 'entity_validations', COUNT(*) FROM entity_validations;

-- Show remaining users (should still be there)
SELECT username, is_admin, assigned_start, assigned_end, (assigned_end - assigned_start + 1) as page_count FROM users;
