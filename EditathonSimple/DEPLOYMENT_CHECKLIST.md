# Deployment Checklist for cPanel

## Step 1: Build the Application Locally

On your local machine (Windows):

```cmd
cd EditathonSimple
npm install
npm run build
```

This creates a `dist/` folder with the compiled React application.

## Step 2: Prepare Deployment Package

Create a deployment folder with these files:

```
editathon-deploy/
├── dist/                    (built React app - from npm run build)
├── data/                    (your dataset)
│   ├── images/             (all page images)
│   └── (no JSON file needed - data is in PostgreSQL)
├── server-postgres.js       (Node.js server)
├── package.json            (dependencies)
├── .env.local              (database credentials - create this)
└── node_modules/           (will be installed on server)
```

## Step 3: Create .env.local File

Create `EditathonSimple/.env.local` with your database credentials:

```env
DB_HOST=localhost
DB_NAME=editathon_db
DB_USER=editathon_user
DB_PASSWORD=your_secure_password
DB_PORT=5432
PORT=3000
```

**Important:** Replace `your_secure_password` with your actual PostgreSQL password.

## Step 4: What to Upload to cPanel

### Option A: Upload Everything (Recommended for First Deployment)

Upload these folders/files to your cPanel directory (e.g., `/home/username/editathon-app/`):

1. **dist/** - The built React application
2. **data/images/** - All your page images
3. **server-postgres.js** - The Node.js server
4. **package.json** - Dependencies list
5. **.env.local** - Database credentials (create on server)

### Option B: Update Existing Installation (If Already Deployed)

Only upload these files:

1. **dist/** - Replace the entire folder
2. **server-postgres.js** - Replace if you made server changes (you didn't in this update)

## Step 5: cPanel File Manager Steps

1. **Login to cPanel**
2. **Open File Manager**
3. **Navigate to your app directory** (e.g., `/home/username/editathon-app/`)
4. **Upload files:**
   - Click "Upload" button
   - Select and upload the `dist` folder (as a zip file is easier)
   - Upload other files as needed

5. **Extract if uploaded as zip:**
   - Right-click the zip file
   - Select "Extract"
   - Delete the zip file after extraction

## Step 6: Configure Node.js Application in cPanel

1. **Go to "Setup Node.js App"** in cPanel
2. **Edit your existing application** or create new:
   - **Node.js version:** 18.x or higher
   - **Application mode:** Production
   - **Application root:** `/home/username/editathon-app`
   - **Application URL:** Your domain/subdomain
   - **Application startup file:** `server-postgres.js`
   - **Environment variables:** Add from .env.local:
     ```
     DB_HOST=localhost
     DB_NAME=editathon_db
     DB_USER=editathon_user
     DB_PASSWORD=your_secure_password
     DB_PORT=5432
     ```

3. **Click "Run NPM Install"** (if first deployment or package.json changed)
4. **Click "Restart"** to apply changes

## Step 7: Verify Deployment

1. **Visit your application URL**
2. **Test login** with a user account
3. **Check that:**
   - Page list appears in left sidebar
   - Images load correctly
   - OCR versions display
   - Ground truth workflow works
   - Save functionality works

## Quick Reference: What Changed

### Files Modified (Need to Upload)
- ✅ `src/App.jsx` - Complete UI redesign
- ✅ `src/index.css` - New styles
- ✅ `dist/` - Rebuilt application (contains both changes)

### Files NOT Modified (Don't Need to Upload)
- ❌ `server-postgres.js` - No changes
- ❌ `package.json` - No changes
- ❌ Database schema - No changes
- ❌ `data/images/` - No changes (unless you have new images)

### New Documentation Files (Optional)
- 📄 `UI_IMPROVEMENTS.md`
- 📄 `QUICK_START_GUIDE.md`
- 📄 `MIGRATION_NOTES.md`
- 📄 `DEPLOYMENT_CHECKLIST.md` (this file)

## Minimal Update Process

If you already have EditathonSimple deployed and working:

### On Your Local Machine:
```cmd
cd EditathonSimple
npm run build
```

### Upload to cPanel:
1. Zip the `dist` folder
2. Upload to cPanel File Manager
3. Extract in your app directory (replace old dist folder)
4. Restart Node.js app in cPanel

**That's it!** The new UI will be live.

## Troubleshooting

### Issue: White screen after deployment
**Solution:** 
- Check browser console for errors
- Verify all files in `dist/` were uploaded
- Check Node.js app is running in cPanel

### Issue: Images not loading
**Solution:**
- Verify `data/images/` folder exists
- Check file permissions (should be 644 for files, 755 for folders)
- Verify image paths in database match actual files

### Issue: Can't login
**Solution:**
- Check database connection in .env.local
- Verify PostgreSQL is running
- Check server logs in cPanel

### Issue: Save not working
**Solution:**
- Check browser console for API errors
- Verify database credentials
- Check server-postgres.js is the startup file

### Issue: Old interface still showing
**Solution:**
- Clear browser cache (Ctrl+F5)
- Verify new dist/ folder was uploaded
- Check Node.js app was restarted

## Rollback Plan

If you need to revert to the old interface:

1. **Restore backup dist/ folder**
2. **Upload to cPanel**
3. **Restart Node.js app**

No database changes needed.

## Performance Tips

After deployment:

1. **Enable compression** in Node.js (add to server-postgres.js):
   ```javascript
   const compression = require('compression');
   app.use(compression());
   ```

2. **Set cache headers** for static files:
   ```javascript
   app.use(express.static('dist', {
     maxAge: '1d'
   }));
   ```

3. **Monitor memory usage** in cPanel Node.js app section

## Security Checklist

- ✅ .env.local file is NOT in dist/ folder
- ✅ Database credentials are in environment variables
- ✅ PostgreSQL password is strong
- ✅ Node.js app runs as non-root user
- ✅ File permissions are correct (644/755)

## Support

If you encounter issues:

1. **Check cPanel Error Logs:**
   - Go to "Errors" in cPanel
   - Look for Node.js application errors

2. **Check Browser Console:**
   - Press F12 in browser
   - Look for JavaScript errors

3. **Test API endpoints:**
   - Visit: `https://yourdomain.com/api/dataset`
   - Should return JSON or authentication error

4. **Verify database:**
   - Use phpPgAdmin or psql to check connection
   - Verify tables exist and have data

## Next Steps After Deployment

1. **Test with real users** - Have 1-2 users try the new interface
2. **Gather feedback** - Note any issues or confusion
3. **Update documentation** - Share Quick Start Guide with users
4. **Monitor performance** - Check server resources and response times
5. **Plan training** - Consider a brief orientation session

## Estimated Deployment Time

- **First-time deployment:** 30-45 minutes
- **Update existing installation:** 5-10 minutes
- **Testing:** 10-15 minutes

Total: 15-60 minutes depending on experience level.
