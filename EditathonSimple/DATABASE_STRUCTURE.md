# Database Structure Reference

## Entity Relationship Diagram

```
┌─────────────────┐
│     users       │
├─────────────────┤
│ id (PK)         │
│ username (UQ)   │◄─────────┐
│ password_hash   │          │
│ assigned_start  │          │
│ assigned_end    │          │
└─────────────────┘          │
                             │
┌─────────────────┐          │
│     pages       │          │
├─────────────────┤          │
│ id (PK)         │          │
│ page_id (UQ)    │◄─────┐   │
│ page_number     │      │   │
│ dublin_core     │      │   │
│ archival_ctx    │      │   │
└─────────────────┘      │   │
         │               │   │
         │               │   │
    ┌────┴────┐          │   │
    │         │          │   │
    ▼         ▼          │   │
┌─────────┐ ┌──────────┐│   │
│ocr_vers │ │ entities ││   │
├─────────┤ ├──────────┤│   │
│page_id  │ │page_id   ││   │
│engine   │ │type      ││   │
│ocr_text │ │name      ││   │
└─────────┘ └──────────┘│   │
                  │     │   │
                  │     │   │
                  │  ┌──┴───┴────────┐
                  │  │     edits     │
                  │  ├───────────────┤
                  │  │ id (PK)       │
                  │  │ username (FK) │
                  │  │ page_id (FK)  │
                  │  │ ocr_selected  │
                  │  │ transcription │
                  │  │ completed     │
                  │  └───────────────┘
                  │         │
                  │    ┌────┴────┐
                  │    │         │
                  │    ▼         ▼
                  │  ┌────────┐ ┌────────────┐
                  │  │metadata│ │entity_valid│
                  │  │_valid  │ │            │
                  │  ├────────┤ ├────────────┤
                  │  │edit_id │ │edit_id     │
                  │  │field   │ │entity_id   │
                  │  │status  │ │status      │
                  │  └────────┘ └────────────┘
                  │                   │
                  └───────────────────┘
```

## Table Purposes

### Core Tables

**users**
- Stores editathon participants
- Page assignments (start/end range)
- Authentication (password hashes)

**pages**
- All 504 pages from dataset
- Metadata (Dublin Core, archival context)
- Links to OCR and entities

**ocr_versions**
- Multiple OCR engine outputs per page
- Tesseract, OpenAI OCR, etc.
- Full text for each engine

**entities**
- Named entities extracted per page
- PERSON, ORG, GPE, DATE, etc.
- Used for validation UI

### Work Tables

**edits**
- User's transcription work
- Selected OCR engine
- Final transcription text
- Completion status
- One row per user per page

**metadata_validations**
- User validation of metadata fields
- approved/rejected/removed
- Per field (title, date, creator, etc.)

**entity_validations**
- User validation of NER results
- approved/rejected/corrected
- Corrected values if changed
- Links to specific entity

## Data Flow

### 1. Import (One-time)
```
editathon_dataset.json → PostgreSQL
users.json → PostgreSQL
```

### 2. User Login
```
User enters credentials
→ Check users table
→ Create session
→ Return assigned page range
```

### 3. Load Pages
```
User session → assigned_start/end
→ Query pages WHERE page_number IN range
→ JOIN ocr_versions
→ JOIN entities
→ Return to frontend
```

### 4. User Edits
```
User selects OCR version
User edits transcription
User validates metadata
User validates entities
→ INSERT/UPDATE edits table
→ INSERT metadata_validations
→ INSERT entity_validations
```

### 5. Export Results
```
Query all edits
→ JOIN metadata_validations
→ JOIN entity_validations
→ Export as JSON/CSV
```

## Key Relationships

- **users.username** → **edits.username** (one-to-many)
- **pages.page_id** → **edits.page_id** (one-to-many)
- **pages.page_id** → **ocr_versions.page_id** (one-to-many)
- **pages.page_id** → **entities.page_id** (one-to-many)
- **edits.id** → **metadata_validations.edit_id** (one-to-many)
- **edits.id** → **entity_validations.edit_id** (one-to-many)
- **entities.id** → **entity_validations.entity_id** (one-to-many)

## Indexes for Performance

```sql
-- User lookups
CREATE INDEX idx_users_username ON users(username);

-- Page queries
CREATE INDEX idx_pages_number ON pages(page_number);
CREATE INDEX idx_pages_page_id ON pages(page_id);

-- OCR lookups
CREATE INDEX idx_ocr_page_engine ON ocr_versions(page_id, engine_name);

-- Entity queries
CREATE INDEX idx_entities_page ON entities(page_id);
CREATE INDEX idx_entities_type ON entities(entity_type);

-- Edit queries
CREATE INDEX idx_edits_username ON edits(username);
CREATE INDEX idx_edits_page ON edits(page_id);
CREATE INDEX idx_edits_completed ON edits(completed);

-- Validation queries
CREATE INDEX idx_metadata_edit ON metadata_validations(edit_id);
CREATE INDEX idx_entity_validations_edit ON entity_validations(edit_id);
CREATE INDEX idx_entity_validations_entity ON entity_validations(entity_id);
```

## Views for Reporting

### user_progress
```sql
-- Shows completion stats per user
SELECT * FROM user_progress;
```

### entity_validation_summary
```sql
-- Shows validation stats per entity
SELECT * FROM entity_validation_summary 
WHERE entity_type = 'PERSON';
```

## Storage Estimates

For 504 pages with 10 users:

- **pages**: ~500 KB (504 rows)
- **ocr_versions**: ~50 MB (1,008 rows, full text)
- **entities**: ~2 MB (~10,000 rows)
- **users**: ~1 KB (10 rows)
- **edits**: ~25 MB (5,040 rows max, full transcriptions)
- **metadata_validations**: ~500 KB (~5,000 rows)
- **entity_validations**: ~2 MB (~20,000 rows)

**Total**: ~80 MB for complete editathon

## Schema Migrations

The database schema is managed through migration scripts in the `migrations/` directory.

**Current Migrations:**
- `001_add_completion_tracking.sql` - Adds completion status, timestamps, removed metadata flag, and entity corrections

**Running Migrations:**
```bash
# Apply migration
node migrations/run_migration.js apply 001

# Test migration
node migrations/run_migration.js test 001

# Rollback migration (if needed)
node migrations/run_migration.js rollback 001
```

See `migrations/README.md` for detailed documentation.

## Backup Strategy

1. **Before editathon**: Backup empty schema
2. **During editathon**: Hourly backups
3. **After editathon**: Final backup + export

```bash
# Backup
pg_dump editathon_db > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore
psql editathon_db < backup_20240215_120000.sql
```
