# Editathon Simple - React App

A simplified React-based editathon platform that loads your prepared dataset.

## Features

- Sequential page navigation
- Multiple OCR version comparison
- Metadata display
- Named entity tags
- Save edits via API

## Local Development

1. Install dependencies:
```bash
npm install
```

2. Copy your dataset:
```bash
mkdir data
cp -r ../editathon_data/* data/
```

3. Run development server:
```bash
npm run dev
```

Visit http://localhost:3000

## Build for Production

```bash
npm run build
```

This creates a `dist/` folder.

## Deploy to cPanel

1. Build locally (above)

2. Create deployment package:
```
editathon-simple-deploy/
├── dist/          (built React app)
├── data/          (your editathon_dataset.json + images/)
├── server.js
├── package.json
└── edits/         (empty folder, will store user edits)
```

3. Upload to `/home/editathon/editathon-app/`

4. In cPanel Node.js:
   - Application root: `/home/editathon/editathon-app`
   - Startup file: `server.js`
   - Run NPM Install
   - Start App

## Data Structure

Expects `/data/editathon_dataset.json` with:
```json
{
  "document": { ... },
  "pages": [
    {
      "page_id": "page_0001",
      "page_number": 1,
      "ocr_versions": {
        "tesseract": "text...",
        "openai_ocr": "text..."
      },
      "entities": { ... },
      "metadata": { ... }
    }
  ]
}
```

Images at: `/data/images/page_XXXX.jpg`

## API Endpoints

- `GET /data/editathon_dataset.json` - Load dataset
- `GET /data/images/page_XXXX.jpg` - Load page images
- `POST /api/save` - Save user edits

Edits saved to: `edits/[username]_[page_id].json`
