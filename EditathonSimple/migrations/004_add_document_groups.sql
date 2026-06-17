-- Migration 004: Add document_groups table
-- Allows users to define document boundaries within their assigned page ranges
-- and assign Dublin Core metadata to each document group.

CREATE TABLE document_groups (
    id SERIAL PRIMARY KEY,
    created_by VARCHAR(50) NOT NULL,
    start_page INTEGER NOT NULL,
    end_page INTEGER NOT NULL,
    continues_before BOOLEAN DEFAULT FALSE,
    continues_after BOOLEAN DEFAULT FALSE,
    dublin_core JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(username) ON DELETE CASCADE
);

-- Prevent overlapping groups for the same user
-- (A user cannot have two groups that cover the same page)
CREATE INDEX idx_document_groups_user ON document_groups(created_by);
CREATE INDEX idx_document_groups_range ON document_groups(start_page, end_page);

COMMENT ON TABLE document_groups IS 'User-defined document boundaries with Dublin Core metadata. Each group represents a contiguous range of pages that form one logical archival object.';
COMMENT ON COLUMN document_groups.continues_before IS 'True if this document starts before the user assignment (partial document at start of range)';
COMMENT ON COLUMN document_groups.continues_after IS 'True if this document continues beyond the user assignment (partial document at end of range)';
COMMENT ON COLUMN document_groups.dublin_core IS 'User-authored Dublin Core metadata for this document group: {title, creator, date, subject, description, type, format, source, language, coverage, rights}';
