-- Add Additional Users
-- Default password for all users: "password"
-- Password hash: 5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8

BEGIN;

-- Add 30 new users
INSERT INTO users (username, password_hash, name, assigned_start, assigned_end, is_admin)
VALUES 
    ('user6', '5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8', 'Test User 6', 0, 0, false),
    ('user7', '5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8', 'Test User 7', 0, 0, false),
    ('user8', '5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8', 'Test User 8', 0, 0, false),
    ('user9', '5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8', 'Test User 9', 0, 0, false),
    ('user10', '5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8', 'Test User 10', 0, 0, false),
    ('user11', '5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8', 'Test User 11', 0, 0, false),
    ('user12', '5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8', 'Test User 12', 0, 0, false),
    ('user13', '5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8', 'Test User 13', 0, 0, false),
    ('user14', '5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8', 'Test User 14', 0, 0, false),
    ('user15', '5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8', 'Test User 15', 0, 0, false),
    ('user16', '5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8', 'Test User 16', 0, 0, false),
    ('user17', '5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8', 'Test User 17', 0, 0, false),
    ('user18', '5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8', 'Test User 18', 0, 0, false),
    ('user19', '5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8', 'Test User 19', 0, 0, false),
    ('user20', '5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8', 'Test User 20', 0, 0, false),
    ('user21', '5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8', 'Test User 21', 0, 0, false),
    ('user22', '5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8', 'Test User 22', 0, 0, false),
    ('user23', '5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8', 'Test User 23', 0, 0, false),
    ('user24', '5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8', 'Test User 24', 0, 0, false),
    ('user25', '5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8', 'Test User 25', 0, 0, false),
    ('user26', '5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8', 'Test User 26', 0, 0, false),
    ('user27', '5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8', 'Test User 27', 0, 0, false),
    ('user28', '5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8', 'Test User 28', 0, 0, false),
    ('user29', '5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8', 'Test User 29', 0, 0, false),
    ('user30', '5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8', 'Test User 30', 0, 0, false),
    ('user31', '5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8', 'Test User 31', 0, 0, false),
    ('user32', '5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8', 'Test User 32', 0, 0, false),
    ('user33', '5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8', 'Test User 33', 0, 0, false),
    ('user34', '5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8', 'Test User 34', 0, 0, false),
    ('user35', '5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8', 'Test User 35', 0, 0, false);

COMMIT;

-- Verify users were added
SELECT COUNT(*) as total_users FROM users WHERE is_admin = FALSE;
SELECT username, name, assigned_start, assigned_end FROM users WHERE is_admin = FALSE ORDER BY id;

-- Note: After adding users, use the "Auto-Distribute Pages" button in the admin panel
-- to assign page ranges to all users
