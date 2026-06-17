-- Editathon PostgreSQL Database Schema
-- Full initialization script (includes all migrations through 004)

-- ============================================================================
-- Users table
-- ============================================================================
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(64) NOT NULL,
    name VARCHAR(100),
    assigned_start INTEGER NOT NULL,
    assigned_end INTEGER NOT NULL,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

COMMENT ON TABLE users IS 'Editathon participants with page assignments';

-- ============================================================================
-- Sessions table (persistent sessions across server restarts)
-- ============================================================================
CREATE TABLE sessions (
    session_id VARCHAR(64) PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    assigned_start INTEGER NOT NULL,
    assigned_end INTEGER NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
);

CREATE INDEX idx_sessions_expires ON sessions(expires_at);

COMMENT ON TABLE sessions IS 'Active user sessions stored in DB for persistence across restarts';

-- ============================================================================
-- Pages table (stores all page metadata from dataset)
-- ============================================================================
CREATE TABLE pages (
    id SERIAL PRIMARY KEY,
    page_id VARCHAR(20) UNIQUE NOT NULL,
    page_number INTEGER NOT NULL,
    json_file VARCHAR(255),
    image_path VARCHAR(255),
    document_filename VARCHAR(255),
    dublin_core JSONB,
    archival_context JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_pages_number ON pages(page_number);

COMMENT ON TABLE pages IS 'All pages from the dataset with metadata';

-- ============================================================================
-- OCR versions table (stores all OCR engine outputs)
-- ============================================================================
CREATE TABLE ocr_versions (
    id SERIAL PRIMARY KEY,
    page_id VARCHAR(20) NOT NULL,
    engine_name VARCHAR(50) NOT NULL,
    ocr_text TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (page_id) REFERENCES pages(page_id) ON DELETE CASCADE,
    UNIQUE(page_id, engine_name)
);

CREATE INDEX idx_ocr_page_engine ON ocr_versions(page_id, engine_name);

COMMENT ON TABLE ocr_versions IS 'OCR text from different engines for each page';

-- ============================================================================
-- Entities table (stores NER entities per page, including user-added)
-- ============================================================================
CREATE TABLE entities (
    id SERIAL PRIMARY KEY,
    page_id VARCHAR(20) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (page_id) REFERENCES pages(page_id) ON DELETE CASCADE
);

CREATE INDEX idx_entities_page ON entities(page_id);
CREATE INDEX idx_entities_type ON entities(entity_type);

COMMENT ON TABLE entities IS 'Named entities extracted from pages (NER + user-added)';

-- ============================================================================
-- Edits table (stores transcription work)
-- ============================================================================
CREATE TABLE edits (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    page_id VARCHAR(20) NOT NULL,
    page_number INTEGER NOT NULL,
    ocr_selected VARCHAR(50),
    transcription TEXT,
    transcription_edited BOOLEAN DEFAULT FALSE,
    completed BOOLEAN DEFAULT FALSE,
    completed_status VARCHAR(20) DEFAULT 'not_started'
        CHECK (completed_status IN ('not_started', 'in_progress', 'completed')),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE,
    FOREIGN KEY (page_id) REFERENCES pages(page_id) ON DELETE CASCADE,
    UNIQUE(username, page_id)
);

CREATE INDEX idx_edits_username ON edits(username);
CREATE INDEX idx_edits_page ON edits(page_id);
CREATE INDEX idx_edits_completed ON edits(completed);
CREATE INDEX idx_edits_completed_status ON edits(username, completed_status);
CREATE INDEX idx_edits_last_saved ON edits(last_saved_at);
CREATE INDEX idx_user_progress ON edits(username, completed);

COMMENT ON TABLE edits IS 'User transcription work and selections';
COMMENT ON COLUMN edits.completed_status IS 'Page completion status: not_started, in_progress, or completed';

-- Trigger to auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_edits_updated_at
    BEFORE UPDATE ON edits
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- Metadata validations table
-- ============================================================================
CREATE TABLE metadata_validations (
    id SERIAL PRIMARY KEY,
    edit_id INTEGER NOT NULL,
    field_name VARCHAR(100) NOT NULL,
    original_value TEXT,
    validation_status VARCHAR(20) CHECK (validation_status IN ('approved', 'rejected', 'removed')),
    notes TEXT,
    removed BOOLEAN DEFAULT FALSE,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    validated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (edit_id) REFERENCES edits(id) ON DELETE CASCADE
);

CREATE INDEX idx_metadata_edit ON metadata_validations(edit_id);
CREATE INDEX idx_metadata_removed ON metadata_validations(edit_id, removed);

COMMENT ON TABLE metadata_validations IS 'User validation of Dublin Core metadata fields';

-- ============================================================================
-- Entity validations table (user responses to NER)
-- ============================================================================
CREATE TABLE entity_validations (
    id SERIAL PRIMARY KEY,
    edit_id INTEGER NOT NULL,
    entity_id INTEGER NOT NULL,
    validation_status VARCHAR(20) CHECK (validation_status IN ('approved', 'rejected', 'corrected')),
    corrected_name VARCHAR(255),
    corrected_type VARCHAR(50),
    notes TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    validated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (edit_id) REFERENCES edits(id) ON DELETE CASCADE,
    FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE CASCADE,
    UNIQUE(edit_id, entity_id)
);

CREATE INDEX idx_entity_validations_edit ON entity_validations(edit_id);
CREATE INDEX idx_entity_validations_entity ON entity_validations(entity_id);
CREATE INDEX idx_entity_corrected ON entity_validations(entity_id, validation_status);

COMMENT ON TABLE entity_validations IS 'User validation of named entity recognition results';

-- ============================================================================
-- Page issues table (user-reported problems)
-- ============================================================================
CREATE TABLE page_issues (
    id SERIAL PRIMARY KEY,
    page_id VARCHAR(20) NOT NULL,
    username VARCHAR(50) NOT NULL,
    issue_type VARCHAR(50) NOT NULL,
    description TEXT,
    status VARCHAR(20) DEFAULT 'open' CHECK (status IN ('open', 'resolved', 'dismissed')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    resolved_by VARCHAR(50),
    FOREIGN KEY (page_id) REFERENCES pages(page_id) ON DELETE CASCADE,
    FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
);

CREATE INDEX idx_issues_page ON page_issues(page_id);
CREATE INDEX idx_issues_status ON page_issues(status);
CREATE INDEX idx_issues_user ON page_issues(username);

COMMENT ON TABLE page_issues IS 'User-reported problems with specific pages';

-- ============================================================================
-- Document groups table (user-defined document boundaries with metadata)
-- ============================================================================
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

CREATE INDEX idx_document_groups_user ON document_groups(created_by);
CREATE INDEX idx_document_groups_range ON document_groups(start_page, end_page);

COMMENT ON TABLE document_groups IS 'User-defined document boundaries with Dublin Core metadata. Each group represents a contiguous range of pages that form one logical archival object.';
COMMENT ON COLUMN document_groups.continues_before IS 'True if this document starts before the user assignment (partial document at start of range)';
COMMENT ON COLUMN document_groups.continues_after IS 'True if this document continues beyond the user assignment (partial document at end of range)';
COMMENT ON COLUMN document_groups.dublin_core IS 'User-authored Dublin Core metadata: {title, creator, date, subject, description, type, format, source, language, coverage, rights}';

-- ============================================================================
-- Views
-- ============================================================================

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

CREATE VIEW entity_validation_summary AS
SELECT 
    ent.entity_type,
    ent.entity_name,
    COUNT(DISTINCT ent.page_id) as page_count,
    COUNT(ev.id) as validation_count,
    COUNT(CASE WHEN ev.validation_status = 'approved' THEN 1 END) as approved_count,
    COUNT(CASE WHEN ev.validation_status = 'rejected' THEN 1 END) as rejected_count,
    COUNT(CASE WHEN ev.validation_status = 'corrected' THEN 1 END) as corrected_count
FROM entities ent
LEFT JOIN entity_validations ev ON ent.id = ev.entity_id
GROUP BY ent.entity_type, ent.entity_name;
