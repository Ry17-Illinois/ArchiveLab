# cPanel Deployment Guide - Step by Step

## Quick Start (For Updates)

If you already have EditathonSimple running on cPanel:

### On Your Computer:
1. Open Command Prompt in the EditathonSimple folder
2. Run: `build-for-deployment.cmd`
3. This creates `editathon-deployment.zip`

### In cPanel:
1. Upload `editathon-deployment.zip` to your app folder
2. Extract it (replaces old files)
3. Restart Node.js app
4. Done! ✅

---

## Detailed First-Time Deployment

### Part 1: Prepare on Your Computer

#### Step 1: Build the Application

Open Command Prompt (cmd) in the EditathonSimple folder:

```cmd
cd EditathonSimple
npm install
npm run build
```

You should see:
```
✓ built in XXXms
```

This creates a `dist` folder with your compiled app.

#### Step 2: Use the Deployment Script (Easiest)

Double-click `build-for-deployment.cmd` or run:

```cmd
build-for-deployment.cmd
```

This creates `editathon-deployment.zip` containing:
- dist/ (your built React app)
- server-postgres.js (Node.js server)
- package.json (dependencies)
- .env.local.template (database config template)

**OR** manually create a folder with these files if you prefer.

---

### Part 2: Upload to cPanel

#### Step 1: Login to cPanel

1. Go to your hosting provider's cPanel URL
2. Login with your credentials

#### Step 2: Open File Manager

1. Find "File Manager" in cPanel
2. Click to open
3. Navigate to your home directory (usually `/home/yourusername/`)

#### Step 3: Create/Navigate to App Directory

If first deployment:
1. Click "New Folder"
2. Name it `editathon-app` (or your preferred name)
3. Open the folder

If updating:
1. Navigate to your existing app folder
2. **Backup first!** Right-click folder → Compress → Download

#### Step 4: Upload Files

**Option A: Upload ZIP (Recommended)**

1. Click "Upload" button at top
2. Select `editathon-deployment.zip`
3. Wait for upload to complete
4. Go back to File Manager
5. Right-click the zip file
6. Select "Extract"
7. Extract to current directory
8. Delete the zip file after extraction

**Option B: Upload Individual Files**

1. Click "Upload" button
2. Upload each file/folder:
   - dist/ (upload as zip, then extract)
   - server-postgres.js
   - package.json
   - .env.local.template

#### Step 5: Configure Environment Variables

1. Find `.env.local.template` in File Manager
2. Right-click → Rename to `.env.local`
3. Right-click → Edit
4. Replace `YOUR_PASSWORD_HERE` with your actual PostgreSQL password:

```env
DB_HOST=localhost
DB_NAME=editathon_db
DB_USER=editathon_user
DB_PASSWORD=your_actual_password_here
DB_PORT=5432
PORT=3000
```

5. Click "Save Changes"

#### Step 6: Set File Permissions

1. Select all uploaded files
2. Right-click → Change Permissions
3. Set:
   - Files: 644
   - Folders: 755
4. Check "Recurse into subdirectories"
5. Click "Change Permissions"

---

### Part 3: Configure Node.js Application

#### Step 1: Find Node.js App Manager

1. In cPanel, search for "Node.js"
2. Click "Setup Node.js App"

#### Step 2: Create or Edit Application

**If First Time:**

1. Click "Create Application"
2. Fill in:
   - **Node.js version:** 18.x or 20.x (latest available)
   - **Application mode:** Production
   - **Application root:** `/home/yourusername/editathon-app`
   - **Application URL:** Choose your domain/subdomain
   - **Application startup file:** `server-postgres.js`
   - **Passenger log file:** (leave default)

3. Click "Create"

**If Updating:**

1. Find your existing application in the list
2. Click "Edit" (pencil icon)
3. Verify settings are correct
4. No changes needed unless you moved files

#### Step 3: Add Environment Variables

In the Node.js App configuration:

1. Scroll to "Environment Variables" section
2. Add each variable:

| Key | Value |
|-----|-------|
| DB_HOST | localhost |
| DB_NAME | editathon_db |
| DB_USER | editathon_user |
| DB_PASSWORD | your_actual_password |
| DB_PORT | 5432 |
| PORT | 3000 |

3. Click "Save" after adding each one

**Note:** You can also use the .env.local file instead of adding variables here.

#### Step 4: Install Dependencies

1. In the Node.js App page, find your application
2. Click "Run NPM Install" button
3. Wait for installation to complete (may take 1-2 minutes)
4. You should see "Success" message

#### Step 5: Start/Restart Application

1. Click "Restart" button
2. Wait for restart to complete
3. Status should show "Running"

---

### Part 4: Verify Deployment

#### Step 1: Test the Application

1. Open your application URL in a browser
2. You should see the login page

#### Step 2: Test Login

1. Login with a test user account
2. You should see:
   - Left sidebar with page list
   - Top metadata bar
   - Facsimile and transcription panels

#### Step 3: Test Functionality

1. Click a page in the sidebar
2. Verify image loads
3. Click OCR version tabs
4. Click "Set as Ground Truth & Edit"
5. Try editing the transcription
6. Test validation buttons
7. Click "Save & Continue"

#### Step 4: Check for Errors

If something doesn't work:

1. **Check Browser Console:**
   - Press F12
   - Look for red errors
   - Note any 404 or 500 errors

2. **Check cPanel Error Logs:**
   - Go to cPanel → Errors
   - Look for recent errors
   - Note any Node.js errors

3. **Check Node.js App Status:**
   - Go to Setup Node.js App
   - Verify status is "Running"
   - Check if any errors are shown

---

## Common Issues and Solutions

### Issue 1: White Screen / Blank Page

**Symptoms:** Page loads but shows nothing

**Solutions:**
1. Clear browser cache (Ctrl+Shift+Delete)
2. Hard refresh (Ctrl+F5)
3. Check if dist/ folder was uploaded correctly
4. Verify Node.js app is running
5. Check browser console for errors

### Issue 2: Images Not Loading

**Symptoms:** Page loads but images show broken icon

**Solutions:**
1. Verify `data/images/` folder exists in app directory
2. Check file permissions (should be 755 for folder, 644 for images)
3. Verify image filenames match database (e.g., page_0001.jpg)
4. Check if images were uploaded correctly

### Issue 3: Can't Login

**Symptoms:** Login button does nothing or shows error

**Solutions:**
1. Check .env.local has correct database credentials
2. Verify PostgreSQL is running
3. Test database connection:
   - Go to phpPgAdmin in cPanel
   - Try to connect with same credentials
4. Check server logs for database errors

### Issue 4: Save Not Working

**Symptoms:** Click save but nothing happens

**Solutions:**
1. Check browser console for API errors
2. Verify database connection
3. Check if edits table exists in database
4. Verify user has permission to write to database

### Issue 5: Old Interface Still Showing

**Symptoms:** Changes not visible after deployment

**Solutions:**
1. Clear browser cache completely
2. Try incognito/private browsing mode
3. Verify new dist/ folder was uploaded
4. Check timestamp on dist/index.html (should be recent)
5. Restart Node.js app in cPanel

### Issue 6: 404 Errors

**Symptoms:** Some pages or resources not found

**Solutions:**
1. Verify all files in dist/ were uploaded
2. Check Application root path in Node.js app settings
3. Verify server-postgres.js is the startup file
4. Check if .htaccess file is interfering (shouldn't exist)

### Issue 7: 500 Internal Server Error

**Symptoms:** Server error when accessing app

**Solutions:**
1. Check cPanel error logs
2. Verify Node.js version is compatible (18.x or 20.x)
3. Check if npm install completed successfully
4. Verify all dependencies installed
5. Check server-postgres.js for syntax errors

---

## Updating After Initial Deployment

When you make changes and need to redeploy:

### Quick Update Process:

1. **On your computer:**
   ```cmd
   cd EditathonSimple
   npm run build
   ```

2. **Create zip of dist folder:**
   - Right-click dist folder
   - Send to → Compressed (zipped) folder
   - Name it `dist.zip`

3. **In cPanel File Manager:**
   - Navigate to your app directory
   - Delete old `dist` folder
   - Upload `dist.zip`
   - Extract it
   - Delete `dist.zip`

4. **Restart Node.js app:**
   - Go to Setup Node.js App
   - Click "Restart"

5. **Clear browser cache and test**

**That's it!** No need to reinstall npm packages or reconfigure.

---

## Maintenance Tips

### Regular Backups

1. **Weekly:** Download backup of app folder
2. **Before updates:** Always backup first
3. **Database:** Export PostgreSQL database regularly

### Monitoring

1. **Check Node.js app status** weekly
2. **Review error logs** for issues
3. **Monitor disk space** usage
4. **Check database size** growth

### Performance

1. **Restart app** if it becomes slow
2. **Clear old logs** periodically
3. **Optimize images** if needed
4. **Monitor memory usage** in cPanel

---

## Getting Help

### Information to Provide

When asking for help, include:

1. **Error message** (exact text)
2. **Browser console errors** (screenshot)
3. **cPanel error logs** (recent entries)
4. **What you were doing** when error occurred
5. **Node.js version** from cPanel
6. **Application URL** (if not sensitive)

### Where to Get Help

1. **Check this guide first**
2. **Review DEPLOYMENT_CHECKLIST.md**
3. **Check MIGRATION_NOTES.md**
4. **Contact hosting support** for cPanel issues
5. **Check Node.js documentation** for app issues

---

## Checklist

Use this checklist for deployment:

### Pre-Deployment
- [ ] Backup existing installation (if updating)
- [ ] Build application locally (`npm run build`)
- [ ] Create deployment package
- [ ] Have database credentials ready

### Upload
- [ ] Upload files to cPanel
- [ ] Extract if uploaded as zip
- [ ] Configure .env.local with database credentials
- [ ] Set file permissions (644/755)

### Configuration
- [ ] Configure Node.js app in cPanel
- [ ] Set correct application root
- [ ] Set server-postgres.js as startup file
- [ ] Add environment variables
- [ ] Run NPM Install
- [ ] Start/Restart application

### Testing
- [ ] Application loads without errors
- [ ] Login works
- [ ] Page list displays
- [ ] Images load correctly
- [ ] OCR versions display
- [ ] Ground truth workflow works
- [ ] Transcription editing works
- [ ] Validation buttons work
- [ ] Save functionality works
- [ ] Navigation works

### Post-Deployment
- [ ] Clear browser cache and retest
- [ ] Test with different browsers
- [ ] Test with real user account
- [ ] Monitor error logs
- [ ] Document any issues
- [ ] Update user documentation if needed

---

## Success!

If you've completed all steps and tests pass, your deployment is successful! 🎉

Users can now access the improved EditathonSimple interface with:
- Better navigation
- Ground truth workflow
- Enhanced validation interface
- Improved user experience

Remember to share the QUICK_START_GUIDE.md with your users!
