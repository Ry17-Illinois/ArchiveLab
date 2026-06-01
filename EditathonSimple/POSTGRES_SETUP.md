# PostgreSQL Editathon Platform - Complete Setup Guide

## Overview

This version stores ALL data in PostgreSQL:
- User accounts and page assignments
- Complete dataset (pages, OCR versions, entities)
- User edits and transcriptions
- Metadata validations
- Entity validations (NER responses)

## Prerequisites

- cPanel with PostgreSQL support
- Python 3 (for data import)
- Node.js 18+ (already configured)

---

## Step 1: Create PostgreSQL Database in cPanel

1. **Go to cPanel → PostgreSQL Databases**

2. **Create Database:**
   - Database name: `editathon_db`
   - Click "Create Database"

3. **Create User:**
   - Username: `editathon_user`
   - Password: (generate strong password)
   - Click "Create User"

4. **Add User to Database:**
   - Select user: `editathon_user`
   - Select database: `editathon_db`
   - Click "Add"
   - Grant ALL PRIVILEGES

5. **Note your credentials:**
   - Host: `localhost`
   - Database: `editathon_db`
   - User: `editathon_user`
   - Password: (your password)
   - Port: `5432`

---

## Step 2: Create Database Schema

1. **Go to cPanel → phpPgAdmin**

2. **Select your database** (`editathon_db`)

3. **Click SQL tab**

4. **Copy and paste** the entire contents of `schema.sql`

5. **Click Execute**

You should see tables created:
- users
- pages
- ocr_versions
- entities
- edits
- metadata_validations
- entity_validations

---

## Step 3: Import Dataset (Local Machine)

### Install Python PostgreSQL driver:

```bash
pip install psycopg2-binary
```

### Run import script:

```bash
python import_to_postgres.py \
  data/editathon_dataset.json \
  users.json \
  localhost \
  editathon_db \
  editathon_user \
  your_password
```

**Note:** If running from your local machine to cPanel server, you may need to:
1. Enable remote PostgreSQL access in cPanel
2. Use server IP instead of `localhost`
3. Or upload files and run import on server via SSH

### Alternative: Import via cPanel

If you can't connect remotely:

1. Upload `import_to_postgres.py`, `data/editathon_dataset.json`, and `users.json` to server
2. SSH into server
3. Run: `python3 import_to_postgres.py ...`

---

## Step 4: Configure Server

### Create `.env` file on server:

```bash
DB_HOST=localhost
DB_NAME=editathon_db
DB_USER=editathon_user
DB_PASSWORD=your_actual_password
DB_PORT=5432
PORT=3000
```

### Update server.js:

Replace `server.js` with `server-postgres.js`:

```bash
cp server-postgres.js server.js
```

---

## Step 5: Deploy to cPanel

### Files to upload to `/home/editathon/editathon-app/`:

```
editathon-app/
├── dist/              (rebuilt React app)
├── data/
│   └── images/        (504 page images - ONLY images, no JSON)
├── server.js          (PostgreSQL version)
├── package.json       (with pg dependency)
├── .env               (database credentials)
└── edits/             (can be empty, not used with PostgreSQL)
```

### In cPanel Node.js App:

1. **Stop the app**

2. **Run NPM Install** (installs `pg` package)

3. **Start the app**

4. **Check logs** for "Database connected successfully"

---

## Step 6: Test

Visit: https://editathon.web.illinois.edu

Login with:
- Username: `guest1`
- Password: `edit001`

You should see:
- Pages 1-51 loaded from database
- OCR versions from database
- Entities from database
- Save functionality working

---

## Step 7: Verify Data

### Check database has data:

In phpPgAdmin, run:

```sql
-- Check pages imported
SELECT COUNT(*) FROM pages;
-- Should return 504

-- Check OCR versions
SELECT COUNT(*) FROM ocr_versions;
-- Should return ~1000 (2 engines × 504 pages)

-- Check entities
SELECT COUNT(*) FROM entities;
-- Should return thousands

-- Check users
SELECT username, assigned_start, assigned_end FROM users;
-- Should show 10 users
```

---

## Benefits of PostgreSQL Version

### Data Integrity:
- ✅ All data in one place
- ✅ ACID transactions
- ✅ Foreign key constraints
- ✅ No file system issues

### Performance:
- ✅ Indexed queries
- ✅ Efficient filtering
- ✅ Concurrent access
- ✅ Connection pooling

### Features:
- ✅ User progress tracking
- ✅ Real-time statistics
- ✅ Advanced queries
- ✅ Easy data export

### Administration:
- ✅ Built-in cPanel backup
- ✅ Query-based reports
- ✅ User management
- ✅ Audit trail

---

## API Endpoints

### Authentication:
- `POST /api/login` - Login with username/password

### Data:
- `GET /api/dataset` - Get user's assigned pages (from DB)
- `POST /api/save` - Save edit with validations
- `GET /api/progress` - Get user's progress

### Admin:
- `GET /api/admin/progress` - All users' progress
- `GET /api/admin/export` - Export all edits

---

## Database Schema Summary

### users
- User accounts with page assignments
- Password hashes (SHA256)
- Last login tracking

### pages
- All 504 pages with metadata
- Dublin Core fields (JSONB)
- Archival context (JSONB)

### ocr_versions
- Multiple OCR engine outputs per page
- Linked to pages table

### entities
- Named entities per page
- Entity type and name
- Used for validation UI

### edits
- User transcription work
- Selected OCR engine
- Completion status
- One row per user per page

### metadata_validations
- User validation of metadata fields
- Approved/rejected/removed status
- Linked to edits

### entity_validations
- User validation of NER results
- Approved/rejected/corrected status
- Corrected values if changed
- Linked to edits and entities

---

## Querying Data

### Get user progress:
```sql
SELECT * FROM user_progress WHERE username = 'guest1';
```

### Get all edits for a page:
```sql
SELECT e.*, u.name 
FROM edits e 
JOIN users u ON e.username = u.username 
WHERE e.page_id = 'page_0042';
```

### Get entity validation summary:
```sql
SELECT * FROM entity_validation_summary 
WHERE entity_type = 'PERSON' 
ORDER BY validation_count DESC;
```

### Export all transcriptions:
```sql
SELECT 
  e.username,
  e.page_number,
  e.ocr_selected,
  e.transcription,
  e.timestamp
FROM edits e
WHERE e.completed = true
ORDER BY e.page_number;
```

---

## Troubleshooting

### "Database connection error":
- Check `.env` file has correct credentials
- Verify PostgreSQL user has permissions
- Check database exists

### "Failed to load dataset":
- Verify data was imported (check page count)
- Check server logs for SQL errors
- Verify user has assigned pages

### "Failed to save":
- Check foreign key constraints
- Verify session is valid
- Check server logs for details

---

## Backup & Recovery

### Backup database:
In cPanel → PostgreSQL Databases → Backup

Or via command line:
```bash
pg_dump -U editathon_user editathon_db > backup.sql
```

### Restore database:
```bash
psql -U editathon_user editathon_db < backup.sql
```

---

## Next Steps

1. Test with multiple users simultaneously
2. Monitor database performance
3. Set up automated backups
4. Create admin dashboard for progress monitoring
5. Export final results after editathon

---

**PostgreSQL version is production-ready!**
