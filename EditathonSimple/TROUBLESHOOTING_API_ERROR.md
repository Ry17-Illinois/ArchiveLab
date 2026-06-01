# Troubleshooting: "Failed to load dataset" Error

## Error Message
```
Failed to load dataset: SyntaxError: Unexpected token '<', "<!DOCTYPE "... is not valid JSON
```

## What This Means

The `/api/dataset` endpoint is returning HTML instead of JSON. This happens when:

1. **Node.js app isn't running** - Apache is serving a 404 page
2. **Wrong URL routing** - Request isn't reaching your Node.js app
3. **Authentication redirect** - Server is redirecting to an error page
4. **Database connection failed** - Server crashed and Apache is handling requests

## Quick Diagnosis

### Step 1: Check if Node.js App is Running

**In cPanel:**
1. Go to "Setup Node.js App"
2. Find your application
3. Check status - should say "Running" in green
4. If it says "Stopped" or red, click "Restart"

### Step 2: Check Application URL

The app should be accessed through the URL configured in Node.js app settings, not directly through the domain root.

**Example:**
- ✅ Correct: `https://yourdomain.com/editathon/` (if app URL is /editathon)
- ✅ Correct: `https://editathon.yourdomain.com/` (if using subdomain)
- ❌ Wrong: `https://yourdomain.com/` (if app is in subfolder)

### Step 3: Test the API Directly

Open a new browser tab and try:
```
https://your-app-url/api/dataset
```

**Expected responses:**

**If working but not logged in:**
```json
{"success":false,"message":"Unauthorized"}
```

**If Node.js not running:**
```html
<!DOCTYPE html>
<html>
...404 Not Found...
```

**If database error:**
```json
{"success":false,"message":"Failed to load dataset"}
```

## Solutions

### Solution 1: Restart Node.js Application

**In cPanel:**
1. Go to "Setup Node.js App"
2. Find your application
3. Click "Restart" button
4. Wait 10-15 seconds
5. Try accessing the app again

### Solution 2: Check Application Root Path

**In cPanel Node.js App settings:**

1. Verify "Application root" is correct:
   ```
   /home/yourusername/editathon-app
   ```
   (Replace with your actual path)

2. Verify "Application startup file" is:
   ```
   server-postgres.js
   ```

3. Click "Save" if you made changes
4. Click "Restart"

### Solution 3: Check Database Connection

**Test database credentials:**

1. In cPanel, go to "phpPgAdmin" or "PostgreSQL Databases"
2. Try to connect with the credentials from your .env.local:
   - Host: localhost
   - Database: editathon_db
   - User: editathon_user
   - Password: (your password)

3. If connection fails, fix database credentials in .env.local or Node.js app environment variables

### Solution 4: Check Server Logs

**In cPanel:**
1. Go to "Setup Node.js App"
2. Find your application
3. Look for "Log file" path
4. Click to view logs
5. Look for errors like:
   - "Database connection error"
   - "ECONNREFUSED"
   - "Cannot find module"
   - Any red error messages

**Common errors and fixes:**

**Error: "Cannot find module 'express'"**
- Solution: Click "Run NPM Install" in Node.js app

**Error: "ECONNREFUSED" or "Database connection error"**
- Solution: Fix database credentials

**Error: "Port 3000 already in use"**
- Solution: Change PORT in environment variables

### Solution 5: Verify File Structure

**In cPanel File Manager, verify this structure:**
```
/home/yourusername/editathon-app/
├── dist/
│   ├── index.html
│   ├── assets/
│   └── ...
├── data/
│   └── images/
├── server-postgres.js
├── package.json
├── .env.local
└── node_modules/
```

**If node_modules is missing:**
1. Go to Node.js App in cPanel
2. Click "Run NPM Install"
3. Wait for completion
4. Click "Restart"

### Solution 6: Check Environment Variables

**In cPanel Node.js App:**

Verify these environment variables are set:

| Variable | Value |
|----------|-------|
| DB_HOST | localhost |
| DB_NAME | editathon_db |
| DB_USER | editathon_user |
| DB_PASSWORD | (your actual password) |
| DB_PORT | 5432 |

**Or check .env.local file:**
1. In File Manager, open .env.local
2. Verify all values are correct
3. Make sure there are no extra spaces or quotes
4. Save if you made changes
5. Restart Node.js app

### Solution 7: Check .htaccess Interference

**If you have a .htaccess file in your app directory:**

1. Rename it to `.htaccess.backup`
2. Restart Node.js app
3. Test if app works

Node.js apps in cPanel don't need .htaccess files and they can interfere with routing.

## Advanced Debugging

### Enable Detailed Logging

Add this to the top of server-postgres.js (after `const app = express();`):

```javascript
// Debug logging
app.use((req, res, next) => {
  console.log(`${new Date().toISOString()} - ${req.method} ${req.url}`);
  next();
});
```

Then check the logs to see if requests are reaching the server.

### Test with curl (if available)

```bash
curl -v https://your-app-url/api/dataset
```

This shows the full HTTP response and helps identify redirects or errors.

### Check Browser Network Tab

1. Open browser DevTools (F12)
2. Go to "Network" tab
3. Refresh the page
4. Find the `/api/dataset` request
5. Click it to see:
   - Status code (should be 401 or 200, not 404)
   - Response headers
   - Response body

## Common Scenarios

### Scenario 1: Fresh Deployment

**Symptoms:** App loads but shows this error immediately

**Checklist:**
- [ ] Node.js app is running
- [ ] npm install completed successfully
- [ ] Database credentials are correct
- [ ] Database has data (users and pages tables)
- [ ] Application URL is correct

### Scenario 2: Was Working, Now Broken

**Symptoms:** App worked before, now shows error

**Likely causes:**
- Node.js app crashed or stopped
- Database connection lost
- Server restarted and app didn't auto-start

**Quick fix:**
1. Restart Node.js app in cPanel
2. Check database is running
3. Verify credentials still correct

### Scenario 3: After Update

**Symptoms:** Error appeared after uploading new files

**Likely causes:**
- Didn't restart Node.js app
- Uploaded files to wrong directory
- Corrupted upload

**Quick fix:**
1. Verify files uploaded to correct directory
2. Check dist/index.html exists and is recent
3. Restart Node.js app
4. Clear browser cache

## Still Not Working?

### Collect This Information:

1. **Node.js app status** (Running/Stopped)
2. **Application URL** (from Node.js app settings)
3. **URL you're accessing** (from browser)
4. **Server logs** (last 20 lines)
5. **Browser console errors** (screenshot)
6. **Network tab** (screenshot of failed request)
7. **File structure** (screenshot of app directory)

### Create a Test Endpoint

Add this to server-postgres.js (before the `app.get('*', ...)` line):

```javascript
// Test endpoint
app.get('/api/test', (req, res) => {
  res.json({
    success: true,
    message: 'API is working!',
    timestamp: new Date().toISOString(),
    env: {
      DB_HOST: process.env.DB_HOST || 'not set',
      DB_NAME: process.env.DB_NAME || 'not set',
      DB_USER: process.env.DB_USER || 'not set',
      DB_PASSWORD: process.env.DB_PASSWORD ? '***set***' : 'not set',
      PORT: process.env.PORT || 'not set'
    }
  });
});
```

Then restart and visit: `https://your-app-url/api/test`

If this works, the problem is with database connection or authentication.
If this doesn't work, the problem is with Node.js app routing.

## Prevention

### Regular Maintenance

1. **Monitor app status** - Check weekly that it's running
2. **Check logs** - Review for errors regularly
3. **Test after updates** - Always test immediately after deploying
4. **Keep backups** - Backup before making changes

### Best Practices

1. **Use environment variables** - Don't hardcode credentials
2. **Test locally first** - Run `npm run dev` before deploying
3. **Deploy during low-traffic times** - Minimize user impact
4. **Have rollback plan** - Keep previous version available

## Quick Reference

### Restart Node.js App
cPanel → Setup Node.js App → Find app → Restart

### View Logs
cPanel → Setup Node.js App → Find app → Click log file path

### Run NPM Install
cPanel → Setup Node.js App → Find app → Run NPM Install

### Check Database
cPanel → phpPgAdmin → Login → Check tables exist

### Clear Browser Cache
Ctrl+Shift+Delete → Clear cache → Hard refresh (Ctrl+F5)
