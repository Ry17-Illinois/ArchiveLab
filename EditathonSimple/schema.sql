-- Editathon PostgreSQL Database Schema

-- Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(64) NOT NULL,
    name VARCHAR(100),
    assigned_start INTEGER NOT NULL,
    assigned_end INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

-- Pages table (stores all page metadata from dataset)
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

-- OCR versions table (stores all OCR engine outputs)
CREATE TABLE ocr_versions (
    id SERIAL PRIMARY KEY,
    page_id VARCHAR(20) NOT NULL,
    engine_name VARCHAR(50) NOT NULL,
    ocr_text TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (page_id) REFERENCES pages(page_id) ON DELETE CASCADE,
    UNIQUE(page_id, engine_name)
);

-- Entities table (stores original NER entities per page)
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

-- User edits table (stores transcription work)
CREATE TABLE edits (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    page_id VARCHAR(20) NOT NULL,
    page_number INTEGER NOT NULL,
    ocr_selected VARCHAR(50),
    transcription TEXT,
    transcription_edited BOOLEAN DEFAULT FALSE,
    completed BOOLEAN DEFAULT FALSE,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE,
    FOREIGN KEY (page_id) REFERENCES pages(page_id) ON DELETE CASCADE,
    UNIQUE(username, page_id)
);

CREATE INDEX idx_edits_username ON edits(username);
CREATE INDEX idx_edits_page ON edits(page_id);
CREATE INDEX idx_edits_completed ON edits(completed);

-- Metadata validations table
CREATE TABLE metadata_validations (
    id SERIAL PRIMARY KEY,
    edit_id INTEGER NOT NULL,
    field_name VARCHAR(100) NOT NULL,
    original_value TEXT,
    validation_status VARCHAR(20) CHECK (validation_status IN ('approved', 'rejected', 'removed')),
    notes TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (edit_id) REFERENCES edits(id) ON DELETE CASCADE
);

CREATE INDEX idx_metadata_edit ON metadata_validations(edit_id);

-- Entity validations table (user responses to NER)
CREATE TABLE entity_validations (
    id SERIAL PRIMARY KEY,
    edit_id INTEGER NOT NULL,
    entity_id INTEGER NOT NULL,
    validation_status VARCHAR(20) CHECK (validation_status IN ('approved', 'rejected', 'corrected')),
    corrected_name VARCHAR(255),
    corrected_type VARCHAR(50),
    notes TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (edit_id) REFERENCES edits(id) ON DELETE CASCADE,
    FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE CASCADE,
    UNIQUE(edit_id, entity_id)
);

CREATE INDEX idx_entity_validations_edit ON entity_validations(edit_id);
CREATE INDEX idx_entity_validations_entity ON entity_validations(entity_id);

-- Progress tracking view
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

-- Entity validation summary view
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

-- Create indexes for performance
CREATE INDEX idx_pages_number ON pages(page_number);
CREATE INDEX idx_ocr_page_engine ON ocr_versions(page_id, engine_name);
CREATE INDEX idx_user_progress ON edits(username, completed);

-- Comments for documentation
COMMENT ON TABLE users IS 'Editathon participants with page assignments';
COMMENT ON TABLE pages IS 'All pages from the dataset with metadata';
COMMENT ON TABLE ocr_versions IS 'OCR text from different engines for each page';
COMMENT ON TABLE entities IS 'Named entities extracted from pages';
COMMENT ON TABLE edits IS 'User transcription work and selections';
COMMENT ON TABLE metadata_validations IS 'User validation of Dublin Core metadata fields';
COMMENT ON TABLE entity_validations IS 'User validation of named entity recognition results';
