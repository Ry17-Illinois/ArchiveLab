-- Migration: Add admin role to users table
-- Run this in phpPgAdmin SQL tab

-- Add is_admin column to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE;

-- Create an admin user (username: admin, password: admin123)
-- Password hash for "admin123": 240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9
INSERT INTO users (username, password_hash, name, assigned_start, assigned_end, is_admin)
VALUES ('admin', '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9', 'Administrator', 1, 504, TRUE)
ON CONFLICT (username) DO UPDATE SET is_admin = TRUE;

-- Grant admin privileges to existing user if needed (optional)
-- UPDATE users SET is_admin = TRUE WHERE username = 'your_username';
