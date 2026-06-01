# Deployment Instructions

## What's Ready:

✅ Built React app in `dist/`
✅ Dataset with 504 pages in `data/`
✅ Express server in `server.js`
✅ Package.json configured

## Deploy to cPanel:

### 1. Create deployment ZIP

Include these folders/files:
- `dist/` (built app)
- `data/` (dataset + 504 images)
- `server.js`
- `package.json`

Create folder `editathon-simple-deploy` and copy these into it, then ZIP it.

### 2. Upload to cPanel

- Upload ZIP to `/home/editathon/editathon-app-v2/`
- Extract the ZIP
- Delete the ZIP file

### 3. Configure Node.js App

In cPanel → Setup Node.js App:
- Node version: 18.20.8
- Application mode: production
- Application root: `/home/editathon/editathon-app-v2`
- Application URL: `https://editathon.web.illinois.edu`
- Startup file: `server.js`

Click "Create"

### 4. Install Dependencies

Click "Run NPM Install"

### 5. Create edits folder

Via File Manager, create empty folder:
`/home/editathon/editathon-app-v2/edits/`

Set permissions to 755

### 6. Start App

Click "Start App"

Visit: https://editathon.web.illinois.edu

## Features:

- Sequential page navigation (1-504)
- OCR version tabs (Tesseract, OpenAI OCR)
- Metadata display
- Entity tags
- Save functionality
- Clean, simple interface

## Test Locally First:

```bash
npm run dev
```

Visit http://localhost:3000
