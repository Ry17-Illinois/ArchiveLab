# Deployment Order - Complete Checklist

## The Correct Order for First-Time Setup

### Phase 1: Database Setup (MUST BE FIRST!)

#### 1.1 Create PostgreSQL Database in cPanel
- [ ] Create database: `editathon_db`
- [ ] Create user: `editathon_user`
- [ ] Set strong password
- [ ] Grant ALL PRIVILEGES to user

#### 1.2 Create Database Schema
- [ ] Open phpPgAdmin in cPanel
- [ ] Select `editathon_db`
- [ ] Go to SQL tab
- [ ] Copy/paste entire `schema-clean.sql` file
- [ ] Execute
- [ ] Verify tables created (users, pages, ocr_versions, entities, edits, etc.)

#### 1.3 Generate Users
On your local machine:
```bash
cd EditathonSimple
python generate_users.py 10 504
```
- [ ] Creates `users.json`
- [ ] Creates `passwords.txt`
- [ ] Note: 10 users, 504 pages (adjust as needed)

#### 1.4 Import Data to Database
```bash
python import_to_postgres.py \
  data/editathon_dataset.json \
  users.json \
  localhost \
  editathon_db \
  editathon_user \
  YOUR_PASSWORD
```
- [ ] Imports all 504 pages
- [ ] Imports OCR versions
- [ ] Imports entities
- [ ] Imports users

**Alternative:** Upload files to server and run import there

#### 1.5 Verify Database
```bash
python check_database.py localhost editathon_db editathon_user YOUR_PASSWORD
```
- [ ] Connection successful
- [ ] All tables exist
- [ ] Pages imported (504)
- [ ] Users imported (10)
- [ ] OCR versions imported (~1000+)

**✅ Phase 1 Complete: Database is ready**

---

### Phase 2: Build Application

#### 2.1 Build React App
On your local machine:
```bash
cd EditathonSimple
npm install
npm run build
```
- [ ] Creates `dist/` folder
- [ ] Contains compiled React app

**OR use the automated script:**
```bash
build-for-deployment.cmd
```
- [ ] Creates `editathon-deployment.zip`

**✅ Phase 2 Complete: Application is built**

---

### Phase 3: Upload to cPanel

#### 3.1 Upload Files
Upload to `/home/yourusername/editathon-app/`:

- [ ] `dist/` folder (entire folder)
- [ ] `data/images/` folder (all 504 images)
- [ ] `server-postgres.js`
- [ ] `package.json`

#### 3.2 Create Environment File
Create `.env.local` on server with:
```env
DB_HOST=localhost
DB_NAME=editathon_db
DB_USER=editathon_user
DB_PASSWORD=your_actual_password
DB_PORT=5432
PORT=3000
```
- [ ] File created
- [ ] Password is correct
- [ ] No extra spaces or quotes

**✅ Phase 3 Complete: Files uploaded**

---

### Phase 4: Configure Node.js App

#### 4.1 Setup Node.js Application in cPanel
- [ ] Go to "Setup Node.js App"
- [ ] Create or edit application
- [ ] Set Node.js version: 18.x or 20.x
- [ ] Set Application mode: Production
- [ ] Set Application root: `/home/yourusername/editathon-app`
- [ ] Set Application URL: Your domain/subdomain
- [ ] Set Startup file: `server-postgres.js`

#### 4.2 Install Dependencies
- [ ] Click "Run NPM Install"
- [ ] Wait for completion
- [ ] Verify `node_modules/` folder created

#### 4.3 Start Application
- [ ] Click "Restart" or "Start"
- [ ] Status shows "Running" (green)
- [ ] Check logs for "Database connected successfully"

**✅ Phase 4 Complete: Application running**

---

### Phase 5: Test & Verify

#### 5.1 Test API Endpoints
Open in browser:
- [ ] `https://your-app-url/api/test` (if you added test endpoint)
- [ ] Should return JSON, not HTML

#### 5.2 Test Application
- [ ] Visit your application URL
- [ ] Login page loads
- [ ] Login with `guest1` / `edit001`
- [ ] Page list appears in left sidebar
- [ ] Click a page
- [ ] Image loads
- [ ] OCR versions display
- [ ] Metadata shows
- [ ] Entities show

#### 5.3 Test Functionality
- [ ] Select OCR version
- [ ] Click "Set as Ground Truth & Edit"
- [ ] Edit transcription
- [ ] Validate metadata (approve/reject)
- [ ] Validate entities (approve/reject)
- [ ] Click "Save & Continue"
- [ ] Verify save successful
- [ ] Check next page loads

**✅ Phase 5 Complete: Application working!**

---

## Common Mistakes (What NOT to Do)

### ❌ Mistake 1: Deploying Without Database
**Problem:** Upload files and start app without importing data
**Result:** "Failed to load dataset" error
**Solution:** Complete Phase 1 first!

### ❌ Mistake 2: Wrong Server File
**Problem:** Using `server.js` instead of `server-postgres.js`
**Result:** App tries to read JSON files instead of database
**Solution:** Use `server-postgres.js` as startup file

### ❌ Mistake 3: Missing Images
**Problem:** Forget to upload `data/images/` folder
**Result:** Images don't load (broken image icons)
**Solution:** Upload entire images folder

### ❌ Mistake 4: Wrong Database Credentials
**Problem:** Typo in password or database name
**Result:** "Database connection error"
**Solution:** Double-check .env.local matches cPanel settings

### ❌ Mistake 5: Not Running NPM Install
**Problem:** Skip "Run NPM Install" step
**Result:** "Cannot find module 'pg'" error
**Solution:** Click "Run NPM Install" in cPanel

### ❌ Mistake 6: Wrong Application URL
**Problem:** Access root domain when app is in subfolder
**Result:** 404 or wrong page loads
**Solution:** Use exact URL from Node.js app settings

---

## Quick Troubleshooting

### Issue: "Failed to load dataset"
**Check:**
1. Is Node.js app running? (cPanel → Setup Node.js App)
2. Is database imported? (Run check_database.py)
3. Are credentials correct? (.env.local)
4. Is startup file correct? (server-postgres.js)

### Issue: Images not loading
**Check:**
1. Does `data/images/` folder exist on server?
2. Are file permissions correct? (755 for folder, 644 for files)
3. Do image filenames match database? (page_0001.jpg format)

### Issue: Can't login
**Check:**
1. Are users imported? (SELECT COUNT(*) FROM users;)
2. Is password correct? (Check passwords.txt)
3. Is database connection working? (Check logs)

### Issue: White screen
**Check:**
1. Is dist/ folder uploaded?
2. Is Node.js app running?
3. Clear browser cache (Ctrl+F5)
4. Check browser console for errors (F12)

---

## Verification Checklist

Before going live, verify:

### Database:
- [ ] PostgreSQL database exists
- [ ] Schema created (all tables exist)
- [ ] Data imported (504 pages)
- [ ] Users imported (10 users)
- [ ] Can query data in phpPgAdmin

### Files:
- [ ] dist/ folder uploaded
- [ ] data/images/ folder uploaded (504 images)
- [ ] server-postgres.js uploaded
- [ ] package.json uploaded
- [ ] .env.local created with correct credentials

### Node.js App:
- [ ] Application configured in cPanel
- [ ] Startup file is server-postgres.js
- [ ] NPM install completed
- [ ] App status is "Running"
- [ ] Logs show "Database connected successfully"

### Functionality:
- [ ] Login works
- [ ] Pages load
- [ ] Images display
- [ ] OCR versions show
- [ ] Ground truth workflow works
- [ ] Transcription editing works
- [ ] Validation buttons work
- [ ] Save functionality works

---

## Time Estimates

- **Phase 1 (Database):** 30-45 minutes
- **Phase 2 (Build):** 5-10 minutes
- **Phase 3 (Upload):** 10-20 minutes
- **Phase 4 (Configure):** 10-15 minutes
- **Phase 5 (Test):** 15-20 minutes

**Total:** 70-110 minutes for first-time setup

**Updates:** 5-10 minutes (just rebuild and upload dist/)

---

## Success Criteria

You know it's working when:

✅ Login page loads without errors
✅ Can login with guest1 / edit001
✅ See page list in left sidebar
✅ Pages show completion status
✅ Images load correctly
✅ Can select and view OCR versions
✅ Can set ground truth and edit transcription
✅ Can validate metadata and entities
✅ Save works and advances to next page
✅ No errors in browser console
✅ No errors in Node.js app logs

---

## Getting Help

If stuck, collect this information:

1. **Which phase are you on?** (1-5)
2. **What error message?** (exact text)
3. **Database status:** Run check_database.py output
4. **Node.js app status:** Running or stopped?
5. **Browser console errors:** Screenshot of F12 console
6. **Server logs:** Last 20 lines from Node.js app logs

Then refer to:
- `TROUBLESHOOTING_API_ERROR.md` - For API issues
- `DATABASE_IMPORT_REQUIRED.md` - For database questions
- `CPANEL_DEPLOYMENT_GUIDE.md` - For deployment steps
- `POSTGRES_SETUP.md` - For database setup

---

**Remember: Database first, then application!**
