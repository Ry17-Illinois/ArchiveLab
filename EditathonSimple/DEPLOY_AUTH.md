# Deployment with Authentication

## ✅ New Features Added:

- Login page with username/password
- User authentication with session management
- Page assignments (each user sees only their assigned pages)
- 10 users created with 50-51 pages each

## Files to Deploy:

```
EditathonSimple/
├── dist/           (rebuilt with login)
├── data/           (504 pages + images)
├── server.js       (updated with auth)
├── package.json
├── users.json      (10 users with page assignments)
└── passwords.txt   (DELETE after distributing!)
```

## User Credentials:

See `passwords.txt` for all 10 users:
- guest1: edit001 (pages 1-51)
- guest2: edit002 (pages 52-101)
- guest3: edit003 (pages 102-151)
- ...etc

## Deploy Steps:

### 1. Create deployment folder

```bash
mkdir editathon-auth-deploy
```

Copy these into it:
- `dist/` folder
- `data/` folder  
- `server.js`
- `package.json`
- `users.json`

### 2. Upload to cPanel

- ZIP the `editathon-auth-deploy` folder
- Upload to `/home/editathon/editathon-app-v3/`
- Extract
- Delete ZIP

### 3. Configure Node.js App

- Application root: `/home/editathon/editathon-app-v3`
- Startup file: `server.js`
- Node version: 18.20.8
- Run NPM Install
- Start App

### 4. Create edits folder

```bash
mkdir /home/editathon/editathon-app-v3/edits
chmod 755 /home/editathon/editathon-app-v3/edits
```

### 5. Test Login

Visit: https://editathon.web.illinois.edu

Login with:
- Username: guest1
- Password: edit001

You should see pages 1-51 only.

### 6. Distribute Credentials

Send each participant their username/password from `passwords.txt`

**Then DELETE passwords.txt from the server!**

## How It Works:

1. User logs in with username/password
2. Server validates against `users.json` (passwords are SHA256 hashed)
3. Server creates session and returns sessionId
4. User sees only their assigned pages (e.g., guest1 sees pages 1-51)
5. All saves include sessionId for authentication
6. Logout clears session

## Security:

- Passwords hashed with SHA256
- Session-based authentication
- Users can only access their assigned pages
- All API calls require valid session

## To Add More Users:

```bash
python generate_users.py 20 504
```

This creates 20 users with ~25 pages each.
