-- Migration 003: Add Issues Reporting Table
-- Allows users to flag problems with pages

BEGIN;

-- Create issues table
CREATE TABLE IF NOT EXISTS page_issues (
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

-- Create index for faster queries
CREATE INDEX idx_issues_page ON page_issues(page_id);
CREATE INDEX idx_issues_status ON page_issues(status);
CREATE INDEX idx_issues_user ON page_issues(username);

COMMIT;

-- Verify table was created
SELECT 
    table_name, 
    column_name, 
    data_type 
FROM information_schema.columns 
WHERE table_name = 'page_issues'
ORDER BY ordinal_position;
