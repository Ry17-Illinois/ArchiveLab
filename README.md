# ArchiveLab

A toolkit for AI-powered archival document processing, collaborative transcription validation, and named entity exploration. Built for digital humanities researchers working with large collections of scanned documents — from raw page scans through OCR, NER, metadata generation, crowdsourced correction, and interactive entity browsing.

## Overview

This toolkit provides a complete workflow from raw archival scans to human-validated transcriptions:

1. **Data Processing Pipeline** — OCR, document classification, NER extraction, and metadata generation via the Archive Analyzer GUI
2. **Editathon Platform** — Web-based collaborative interface for crowdsourced transcription validation and metadata correction
3. **Data Export & Reintegration** — Export validated data from the editathon and merge it back into the archive's JSON sidecars
4. **NER-Based Entity Browser** — Static web interface for exploring named entity mentions across documents with facsimile images

---

## 1. Data Processing Pipeline

The Archive Analyzer (`main.py`) is a tkinter GUI application that processes archival documents through multiple AI-powered stages.

### Prerequisites

```bash
pip install -r requirements.txt
```

Required system dependencies:
- Poppler (for pdf2image)
- Tesseract OCR (for pytesseract)

### Running the Pipeline

```bash
python main.py
```

### Processing Stages

**Stage 1: File Import**
- Load PDFs or image files (TIF, JPG, PNG) into the metadata ledger
- PDFs are split into per-page rows automatically
- Supports sidecar import for pre-processed archives (`--import-sidecars`)

**Stage 2: OCR Processing**
- Multiple engines: Tesseract, EasyOCR, OpenAI OCR, Ollama OCR, PyPDF2
- Batch processing via OpenAI Batch API for cost optimization
- Results stored in `metadata_ledger.csv`

**Stage 3: Document Classification**
- AI-powered classification: handwriting, typed, mixed-text, image
- Uses OpenAI or Ollama vision models

**Stage 4: Named Entity Recognition (NER)**
- Extracts PERSON, ORG, GPE, DATE, MONEY, PRODUCT, WORK_OF_ART entities
- Supports spaCy (local) or OpenAI-based extraction
- Results stored per-page in the ledger

**Stage 5: Metadata Generation**
- Dublin Core metadata fields generated from OCR text
- Uses configurable prompts (`prompts/` directory)
- Supports batch processing for multi-page PDFs

### Output Format

Each processed file gets a JSON sidecar containing:
- OCR text from all engines
- Named entities
- Dublin Core metadata
- Archival context (collection, box, folder)
- Document classification

### Key Files

| File | Purpose |
|------|---------|
| `main.py` | GUI application entry point |
| `src/ocr_processor.py` | Multi-engine OCR processing |
| `src/ner_processor.py` | Named entity extraction |
| `src/prompt_processor.py` | AI metadata generation |
| `src/ledger_manager.py` | CSV-based data management |
| `src/batch_manager.py` | OpenAI Batch API integration |
| `config.json` | API keys and model configuration |

---

## 2. Editathon Platform

A React + Express + PostgreSQL web application for collaborative OCR validation. Deployed to cPanel.

### Architecture

- **Frontend**: React (Vite build)
- **Backend**: Express.js with PostgreSQL
- **Database**: PostgreSQL with full schema for pages, OCR versions, entities, edits, and validations
- **Deployment**: cPanel Node.js hosting

### Setup Workflow

#### Step 1: Prepare Dataset

For PDF-based archives:
```bash
python prepare_editathon_dataset_multi.py "path/to/Doc1.pdf" "path/to/Doc2.pdf" --output editathon_data
```

For image-based archives (TIF/JPG with JSON sidecars):
```bash
python prepare_editathon_dataset_multi.py --directory "D:\ArchiveData\Collection" --output editathon_data
```

This produces:
- `editathon_dataset.json` — sequential page data
- `images/` — page images as JPEGs
- `entity_summary.json` — reference entity list

#### Step 2: Generate Import SQL

```bash
python EditathonSimple/generate_import_sql_chunked.py editathon_data/editathon_dataset.json
```

Produces chunked SQL files in `sql_chunks/` for pasting into phpPgAdmin.

#### Step 3: Clear & Import Database

In phpPgAdmin SQL tab (one statement at a time):
```sql
DELETE FROM entity_validations;
DELETE FROM metadata_validations;
DELETE FROM edits;
DELETE FROM entities;
DELETE FROM ocr_versions;
DELETE FROM pages;
DELETE FROM users WHERE is_admin IS NOT TRUE;
```

Then paste and execute each `sql_chunks/import_chunk_XX.sql` file in order.

#### Step 4: Add Users

Paste the INSERT from `EditathonSimple/add_users.sql` (without BEGIN/COMMIT) into phpPgAdmin. Default password for all users: `password`.

#### Step 5: Upload Images

Upload `editathon_data/images/` to the cPanel server's `data/images/` directory.

#### Step 6: Distribute Pages

Log into the admin panel (username: `admin`) and click "Auto-Distribute Pages".

#### Step 7: Restart App

Restart the Node.js app in cPanel to clear sessions.

### Admin Panel

Access the admin panel by logging in with the admin account at the same URL. Features:
- User management (add, edit, delete)
- Auto-distribute pages across users
- Export data (JSON or CSV)
- View progress statistics

### Key Files

| File | Purpose |
|------|---------|
| `EditathonSimple/server-postgres.js` | Express backend with PostgreSQL |
| `EditathonSimple/src/App.jsx` | Main React editor interface |
| `EditathonSimple/src/AdminDashboard.jsx` | Admin panel component |
| `EditathonSimple/schema.sql` | Database schema |
| `EditathonSimple/generate_import_sql_chunked.py` | SQL import generator |
| `prepare_editathon_dataset_multi.py` | Dataset preparation (PDF + directory modes) |

---

## 3. Data Export & Reintegration

After an editathon, export validated data and merge it back into the original archive sidecars.

### Export

From the admin panel, click "Export Data" → "Download JSON". This produces a JSON file with:
- Human-corrected transcriptions
- Metadata validations (approved/rejected/removed)
- Entity validations (approved/rejected/corrected)
- Source sidecar filenames for each page

### Merge Back to Archive

Preview changes (dry run):
```bash
python merge_editathon_results.py editathon-export-2026-06-01.json "D:\ArchiveData\Collection" --dry-run
```

Apply changes:
```bash
python merge_editathon_results.py editathon-export-2026-06-01.json "D:\ArchiveData\Collection"
```

### What Gets Added to Sidecars

The merge is additive only — no existing data is overwritten:

- `human_transcription` — editor-corrected text, source engine, editor name, timestamp
- `metadata_validations` — per-field approved/rejected/removed status
- `named_entities.validations` — per-entity approval/rejection/correction with corrected values

Original files are backed up as `.json.bak` on first modification.

### Key Files

| File | Purpose |
|------|---------|
| `merge_editathon_results.py` | Merge export back to sidecars |
| `EditathonSimple/server-postgres.js` | Export endpoint (`/api/admin/export`) |

---

## 4. NER-Based Entity Browser

A static HTML interface for exploring named entity mentions across documents with side-by-side facsimile images and OCR text.

### Generate Entity Reports

First, scan the archive to produce entity CSVs:
```bash
python archive_report_generator.py "D:\ArchiveData\Collection" report.txt
```

This generates:
- `entity_person.csv`, `entity_org.csv`, etc. — aggregated entity frequencies
- `instance_by_instance_person.csv`, etc. — per-page entity occurrences
- `entity_person_fullname.csv` — filtered to full names only
- `instance_by_instance_person_fullname_5plus.csv` — full names with 5+ mentions

### Generate Web Export

```bash
python web_export_generator.py "D:\ArchiveData\Collection" entity_person_fullname.csv instance_by_instance_person_fullname_5plus.csv web_export_persons
```

### Output

Opens as a static HTML file (`web_export_persons/index.html`) with:
- Left panel: entities sorted by frequency
- Middle panel: document instances for selected entity
- Right panel: split view with facsimile image and OCR text
- Entity highlighting in transcription text
- NER tags with hover-to-highlight
- Dublin Core metadata and archival context display

### Key Files

| File | Purpose |
|------|---------|
| `archive_report_generator.py` | Scan archive, generate entity CSVs |
| `web_export_generator.py` | Generate static HTML entity browser |

---

## Project Structure

```
├── main.py                          # Archive Analyzer GUI
├── src/                             # Processing modules
│   ├── ocr_processor.py
│   ├── ner_processor.py
│   ├── prompt_processor.py
│   ├── ledger_manager.py
│   ├── batch_manager.py
│   ├── export_manager.py
│   └── ...
├── prompts/                         # AI prompt templates
├── archive_report_generator.py      # Entity report generation
├── web_export_generator.py          # Static entity browser
├── prepare_editathon_dataset_multi.py  # Dataset preparation
├── merge_editathon_results.py       # Post-editathon merge
├── EditathonSimple/                 # Editathon web platform
│   ├── server-postgres.js
│   ├── src/App.jsx
│   ├── src/AdminDashboard.jsx
│   ├── schema.sql
│   ├── generate_import_sql_chunked.py
│   └── ...
├── config.json                      # API configuration
├── requirements.txt                 # Python dependencies
└── metadata_ledger.csv              # Processing state
```

---

## Requirements

### Python
- Python 3.10+
- See `requirements.txt` for packages
- System: Poppler, Tesseract OCR

### Node.js (Editathon)
- Node.js 18+
- PostgreSQL 14+
- See `EditathonSimple/package.json`

### API Keys
- OpenAI API key (for OCR, classification, metadata, NER)
- Ollama (optional, for local model inference)

---

## Quick Reference

| Task | Command |
|------|---------|
| Run Archive Analyzer | `python main.py` |
| Prepare editathon (PDFs) | `python prepare_editathon_dataset_multi.py doc1.pdf doc2.pdf --output editathon_data` |
| Prepare editathon (images) | `python prepare_editathon_dataset_multi.py --directory "path/to/archive" --output editathon_data` |
| Generate import SQL | `python EditathonSimple/generate_import_sql_chunked.py editathon_data/editathon_dataset.json` |
| Generate entity report | `python archive_report_generator.py "path/to/archive" report.txt` |
| Generate entity browser | `python web_export_generator.py "archive_dir" entity.csv instances.csv output_dir` |
| Merge editathon results | `python merge_editathon_results.py export.json "path/to/archive" --dry-run` |
| Run editathon locally | `cd EditathonSimple && npm run dev` |
