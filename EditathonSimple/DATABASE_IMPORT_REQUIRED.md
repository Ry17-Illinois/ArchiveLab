# Database Import - REQUIRED for Application to Function

## Short Answer

**YES, the data MUST be imported into PostgreSQL for the application to work.**

The application does NOT read from JSON files. It reads ALL data from the PostgreSQL database:
- Pages and metadata
- OCR versions
- Named entities
- User accounts
- User edits

## What Needs to Be in the Database

### Required Data:
1. **Pages** - All 504 pages with metadata
2. **OCR Versions** - Multiple OCR outputs per page
3. **Entities** - Named entities extracted from pages
4. **Users** - User accounts with page assignments

### Where This Data Comes From:
- `data/editathon_dataset.json` → PostgreSQL tables
- `users.json` → PostgreSQL users table
- `data/images/` → Stays as files (NOT imported to database)

## Current Status Check

### How to Check if Data is Already Imported

**In cPanel:**
1. Go to "phpPgAdmin"
2. Login and select your database (`editathon_db`)
3. Click "SQL" tab
4. Run this query:

```sql
SELECT 
  (SELECT COUNT(*) FROM pages) as page_count,
  (SELECT COUNT(*) FROM ocr_versions) as ocr_count,
  (SELECT COUNT(*) FROM entities) as entity_count,
  (SELECT COUNT(*) FROM users) as user_count;
```

**Expected Results:**
- page_count: 504 (or your total pages)
- ocr_count: ~1000+ (multiple OCR versions per page)
- entity_count: ~10,000+ (named entities)
- user_count: 10 (or your number of users)

**If all counts are 0 or tables don't exist:**
→ You need to import the data (see below)

**If counts look correct:**
→ Data is already imported! Your issue is something else (see troubleshooting)

## How to Import Data

### Prerequisites

1. **PostgreSQL database created** in cPanel
2. **Schema created** (tables exist)
3. **Python 3 installed** on your computer or server
4. **psycopg2 package** installed: `pip install psycopg2-binary`

### Step 1: Generate Users (If Not Already Done)

**On your local machine:**

```bash
cd EditathonSimple
python generate_users.py 10 504
```

This creates:
- `users.json` - User accounts with hashed passwords
- `passwords.txt` - Plain text passwords (distribute to users, then DELETE)

**Arguments:**
- `10` = number of users
- `504` = total pages in your dataset

### Step 2: Import Data to PostgreSQL

**Option A: From Your Local Machine (If You Have Remote Access)**

```bash
python import_to_postgres.py \
  data/editathon_dataset.json \
  users.json \
  YOUR_SERVER_IP \
  editathon_db \
  editathon_user \
  YOUR_DB_PASSWORD
```

**Option B: Upload and Run on Server (Recommended for cPanel)**

1. **Upload these files to your server** (via cPanel File Manager):
   - `import_to_postgres.py`
   - `data/editathon_dataset.json`
   - `users.json`

2. **SSH into your server** (or use cPanel Terminal if available)

3. **Run the import:**
   ```bash
   cd /home/yourusername/editathon-app
   python3 import_to_postgres.py \
     data/editathon_dataset.json \
     users.json \
     localhost \
     editathon_db \
     editathon_user \
     YOUR_DB_PASSWORD
   ```

**Option C: Manual Import via phpPgAdmin (For Small Datasets)**

If Python isn't available, you can manually insert data, but this is tedious for 504 pages.

### Step 3: Verify Import

**Run this query in phpPgAdmin:**

```sql
-- Check pages
SELECT page_id, page_number FROM pages LIMIT 5;

-- Check OCR versions
SELECT page_id, engine_name FROM ocr_versions LIMIT 5;

-- Check users
SELECT username, assigned_start, assigned_end FROM users;
```

You should see data returned.

## What About the Images?

**Images are NOT imported to the database.**

Images stay as files in the `data/images/` folder:
```
data/images/
├── page_0001.jpg
├── page_0002.jpg
├── page_0003.jpg
└── ...
```

The database only stores the IMAGE PATH, not the image itself.

**You must upload the images folder to your server:**
```
/home/yourusername/editathon-app/data/images/
```

## Complete Import Checklist

### Before Import:
- [ ] PostgreSQL database created in cPanel
- [ ] Database schema created (run schema.sql)
- [ ] Python 3 available
- [ ] psycopg2 installed (`pip install psycopg2-binary`)
- [ ] Database credentials ready

### Files Needed:
- [ ] `import_to_postgres.py` (import script)
- [ ] `data/editathon_dataset.json` (your dataset)
- [ ] `users.json` (generated from generate_users.py)
- [ ] `data/images/` folder (uploaded separately)

### Import Process:
- [ ] Generate users: `python generate_users.py 10 504`
- [ ] Run import: `python import_to_postgres.py ...`
- [ ] Verify data in phpPgAdmin
- [ ] Upload images folder to server
- [ ] Test application

### After Import:
- [ ] Delete `passwords.txt` after distributing credentials
- [ ] Backup database
- [ ] Test login with a user account
- [ ] Verify pages load in application

## Troubleshooting Import

### Error: "psycopg2 not found"
```bash
pip install psycopg2-binary
```

### Error: "Connection refused"
**If importing from local machine:**
- Enable remote PostgreSQL access in cPanel
- Use server IP instead of localhost
- Check firewall allows PostgreSQL port (5432)

**Better solution:**
- Upload files to server and run import there

### Error: "Permission denied"
- Verify database user has ALL PRIVILEGES
- Check database name is correct
- Verify password is correct

### Error: "Table does not exist"
- Run schema.sql first to create tables
- Verify you're connected to correct database

### Error: "Duplicate key violation"
- Data already imported (this is OK)
- Script uses ON CONFLICT DO NOTHING
- Check if data exists: `SELECT COUNT(*) FROM pages;`

## Why PostgreSQL Instead of JSON Files?

The original version might have used JSON files, but the PostgreSQL version has major advantages:

### Performance:
- ✅ Indexed queries (fast page lookups)
- ✅ Efficient filtering by user
- ✅ Concurrent access (multiple users)

### Data Integrity:
- ✅ ACID transactions (no data loss)
- ✅ Foreign key constraints (data consistency)
- ✅ Validation at database level

### Features:
- ✅ User progress tracking
- ✅ Real-time statistics
- ✅ Complex queries for reporting
- ✅ Easy data export

### Administration:
- ✅ Built-in cPanel backup
- ✅ Query-based reports
- ✅ User management
- ✅ Audit trail

## Alternative: JSON File Version

If you want to use JSON files instead of PostgreSQL, you would need:

1. **Different server file** - Use `server.js` instead of `server-postgres.js`
2. **JSON file in data folder** - `data/editathon_dataset.json`
3. **No database setup** - Skip all PostgreSQL steps
4. **File-based edits** - Saves to `edits/` folder

**However, the current UI expects PostgreSQL!**

The server-postgres.js file is what the application uses, and it queries the database.

## Summary

**To answer your question directly:**

1. **Does data need to be in database?** 
   → YES, absolutely required

2. **How does it get there?**
   → Run `import_to_postgres.py` script

3. **What about images?**
   → Images stay as files, just upload the folder

4. **Is data already imported?**
   → Check with SQL query: `SELECT COUNT(*) FROM pages;`

5. **What if I haven't imported yet?**
   → Follow the import steps above before deploying

**The application will NOT work without data in PostgreSQL!**

## Quick Start for First-Time Setup

```bash
# 1. Generate users
python generate_users.py 10 504

# 2. Import to database
python import_to_postgres.py \
  data/editathon_dataset.json \
  users.json \
  localhost \
  editathon_db \
  editathon_user \
  YOUR_PASSWORD

# 3. Upload to server:
#    - dist/ folder
#    - data/images/ folder
#    - server-postgres.js
#    - package.json
#    - .env.local (with DB credentials)

# 4. In cPanel:
#    - Run NPM Install
#    - Restart Node.js app

# 5. Test:
#    - Login with guest1 / edit001
```

## Need Help?

If you're stuck on the import process:

1. **Check if database exists** - cPanel → PostgreSQL Databases
2. **Check if schema exists** - phpPgAdmin → check for tables
3. **Check if data exists** - Run `SELECT COUNT(*) FROM pages;`
4. **Check Python version** - `python --version` (need 3.x)
5. **Check psycopg2 installed** - `pip list | grep psycopg2`

**Most common issue:** Trying to run the app without importing data first!
