# Schema Changes Documentation

## Migration 001: Completion Tracking and Enhanced Validations

### Overview

This migration extends the database schema to support the editing interface enhancements specified in the requirements. The changes enable:

1. **Progress Tracking**: Track page completion status (not_started, in_progress, completed)
2. **Auto-Save**: Record timestamps for save operations
3. **Removed Metadata**: Flag metadata fields as removed vs active
4. **Entity Corrections**: Store corrected entity names and types
5. **Time Tracking**: Calculate average time per page for estimates

### Detailed Changes

#### 1. edits Table

**New Columns:**

| Column | Type | Default | Description |
|--------|------|---------|-------------|
| `completed_status` | VARCHAR(20) | 'not_started' | Page completion status enum |
| `last_saved_at` | TIMESTAMP | CURRENT_TIMESTAMP | Last save time (auto or manual) |
| `created_at` | TIMESTAMP | CURRENT_TIMESTAMP | When edit record was created |
| `updated_at` | TIMESTAMP | CURRENT_TIMESTAMP | Last modification time (auto-updated) |

**Constraints:**
- `completed_status` CHECK constraint: Must be 'not_started', 'in_progress', or 'completed'

**Indexes:**
- `idx_edits_completed_status` ON (username, completed_status) - For filtering by status
- `idx_edits_last_saved` ON (last_saved_at) - For sorting by save time

**Data Migration:**
- Existing `completed = TRUE` → `completed_status = 'completed'`
- Existing `transcription_edited = TRUE` → `completed_status = 'in_progress'`
- Otherwise → `completed_status = 'not_started'`
- Existing `timestamp` → copied to `created_at`, `last_saved_at`, `updated_at`

**Backward Compatibility:**
- Old `completed` boolean column is preserved
- Existing queries continue to work
- New code should use `completed_status`

**Example Queries:**

```sql
-- Get all in-progress pages for a user
SELECT page_id, page_number, last_saved_at
FROM edits
WHERE username = 'user1' AND completed_status = 'in_progress'
ORDER BY last_saved_at DESC;

-- Calculate time spent on completed pages
SELECT 
  page_id,
  EXTRACT(EPOCH FROM (updated_at - created_at)) / 60 as minutes_spent
FROM edits
WHERE username = 'user1' AND completed_status = 'completed';

-- Find pages not saved recently
SELECT page_id, page_number, last_saved_at
FROM edits
WHERE username = 'user1' 
  AND completed_status = 'in_progress'
  AND last_saved_at < NOW() - INTERVAL '1 hour';
```

#### 2. metadata_validations Table

**New Columns:**

| Column | Type | Default | Description |
|--------|------|---------|-------------|
| `removed` | BOOLEAN | FALSE | Whether field is in removed section |
| `validated_at` | TIMESTAMP | CURRENT_TIMESTAMP | When validation was performed |

**Indexes:**
- `idx_metadata_removed` ON (edit_id, removed) - For filtering removed metadata

**Data Migration:**
- Existing `timestamp` → copied to `validated_at`
- All existing records → `removed = FALSE`

**Example Queries:**

```sql
-- Get active metadata for an edit
SELECT field_name, original_value, validation_status
FROM metadata_validations
WHERE edit_id = 123 AND removed = FALSE
ORDER BY field_name;

-- Get removed metadata for an edit
SELECT field_name, original_value, validation_status
FROM metadata_validations
WHERE edit_id = 123 AND removed = TRUE
ORDER BY field_name;

-- Move field to removed section
UPDATE metadata_validations
SET removed = TRUE, validated_at = NOW()
WHERE edit_id = 123 AND field_name = 'creator';

-- Restore field to active section
UPDATE metadata_validations
SET removed = FALSE, validated_at = NOW()
WHERE edit_id = 123 AND field_name = 'creator';
```

#### 3. entity_validations Table

**New Columns:**

| Column | Type | Default | Description |
|--------|------|---------|-------------|
| `validated_at` | TIMESTAMP | CURRENT_TIMESTAMP | When validation was performed |

**Note:** The `corrected_name` and `corrected_type` columns already exist in the schema.

**Indexes:**
- `idx_entity_corrected` ON (entity_id, validation_status) - For querying corrected entities

**Data Migration:**
- Existing `timestamp` → copied to `validated_at`

**Example Queries:**

```sql
-- Get all corrected entities for an edit
SELECT 
  e.entity_name as original_name,
  e.entity_type as original_type,
  ev.corrected_name,
  ev.corrected_type,
  ev.validated_at
FROM entity_validations ev
JOIN entities e ON ev.entity_id = e.id
WHERE ev.edit_id = 123 AND ev.validation_status = 'corrected';

-- Save entity correction
INSERT INTO entity_validations (edit_id, entity_id, validation_status, corrected_name, corrected_type)
VALUES (123, 456, 'corrected', 'Jane Doe', 'PERSON')
ON CONFLICT (edit_id, entity_id)
DO UPDATE SET
  validation_status = EXCLUDED.validation_status,
  corrected_name = EXCLUDED.corrected_name,
  corrected_type = EXCLUDED.corrected_type,
  validated_at = NOW();
```

#### 4. user_progress View

**Updated View Definition:**

The view now includes:
- `pages_in_progress` - Count of pages with status 'in_progress'
- `pages_not_started` - Count of pages with status 'not_started'
- `avg_seconds_per_page` - Average time to complete a page

**Example Query:**

```sql
SELECT 
  username,
  total_assigned,
  pages_completed,
  pages_in_progress,
  pages_not_started,
  completion_percentage,
  ROUND(avg_seconds_per_page / 60, 1) as avg_minutes_per_page,
  ROUND((pages_not_started + pages_in_progress) * avg_seconds_per_page / 3600, 1) as estimated_hours_remaining
FROM user_progress
WHERE username = 'user1';
```

#### 5. Automatic Timestamp Updates

**New Function:**
```sql
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

**New Trigger:**
```sql
CREATE TRIGGER update_edits_updated_at
    BEFORE UPDATE ON edits
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

**Behavior:**
- Automatically updates `updated_at` column on any UPDATE to edits table
- No manual timestamp management needed in application code

### API Integration Examples

#### Save with Auto-Save Flag

```javascript
// Backend: POST /api/save
app.post('/api/save', verifySession, async (req, res) => {
  const { 
    page_id, 
    page_number, 
    transcription, 
    metadata_validations, 
    entity_validations,
    auto_save  // New flag
  } = req.body;
  
  const client = await pool.connect();
  
  try {
    await client.query('BEGIN');
    
    // Determine completion status
    const hasContent = transcription && transcription.trim().length > 0;
    const completedStatus = hasContent ? 'in_progress' : 'not_started';
    
    // Insert or update edit with new columns
    const editResult = await client.query(`
      INSERT INTO edits (
        username, page_id, page_number, 
        transcription, completed_status, 
        last_saved_at, created_at, updated_at
      )
      VALUES ($1, $2, $3, $4, $5, NOW(), NOW(), NOW())
      ON CONFLICT (username, page_id) 
      DO UPDATE SET 
        transcription = $4,
        completed_status = CASE 
          WHEN edits.completed_status = 'completed' THEN 'completed'
          ELSE $5
        END,
        last_saved_at = NOW()
      RETURNING id, completed_status, last_saved_at
    `, [username, page_id, page_number, transcription, completedStatus]);
    
    const { id: edit_id, completed_status, last_saved_at } = editResult.rows[0];
    
    // Save metadata validations with removed flag
    for (const validation of metadata_validations) {
      await client.query(`
        INSERT INTO metadata_validations (
          edit_id, field_name, original_value, 
          validation_status, removed, validated_at
        )
        VALUES ($1, $2, $3, $4, $5, NOW())
        ON CONFLICT (edit_id, field_name)
        DO UPDATE SET
          validation_status = $4,
          removed = $5,
          validated_at = NOW()
      `, [
        edit_id, 
        validation.field_name, 
        validation.original_value,
        validation.status,
        validation.removed || false
      ]);
    }
    
    // Save entity validations with corrections
    for (const validation of entity_validations) {
      await client.query(`
        INSERT INTO entity_validations (
          edit_id, entity_id, validation_status,
          corrected_name, corrected_type, validated_at
        )
        VALUES ($1, $2, $3, $4, $5, NOW())
        ON CONFLICT (edit_id, entity_id)
        DO UPDATE SET
          validation_status = $3,
          corrected_name = $4,
          corrected_type = $5,
          validated_at = NOW()
      `, [
        edit_id,
        validation.entity_id,
        validation.status,
        validation.corrected_name || null,
        validation.corrected_type || null
      ]);
    }
    
    await client.query('COMMIT');
    
    res.json({ 
      success: true,
      completed_status,
      last_saved_at
    });
    
  } catch (err) {
    await client.query('ROLLBACK');
    console.error('Save error:', err);
    res.status(500).json({ success: false, message: 'Failed to save' });
  } finally {
    client.release();
  }
});
```

#### Mark Complete Endpoint

```javascript
// Backend: POST /api/complete
app.post('/api/complete', verifySession, async (req, res) => {
  const { page_id } = req.body;
  const username = req.session.username;
  
  try {
    // Update status to completed
    await pool.query(`
      UPDATE edits
      SET completed_status = 'completed',
          last_saved_at = NOW()
      WHERE username = $1 AND page_id = $2
    `, [username, page_id]);
    
    // Find next incomplete page
    const nextPage = await pool.query(`
      SELECT p.page_number
      FROM pages p
      LEFT JOIN edits e ON p.page_id = e.page_id AND e.username = $1
      WHERE p.page_number >= $2 AND p.page_number <= $3
        AND (e.completed_status IS NULL 
             OR e.completed_status IN ('not_started', 'in_progress'))
      ORDER BY p.page_number
      LIMIT 1
    `, [username, assigned_start, assigned_end]);
    
    res.json({
      success: true,
      next_incomplete_page: nextPage.rows[0]?.page_number || null
    });
    
  } catch (err) {
    console.error('Complete error:', err);
    res.status(500).json({ success: false, message: 'Failed to mark complete' });
  }
});
```

#### Progress Statistics Endpoint

```javascript
// Backend: GET /api/progress
app.get('/api/progress', verifySession, async (req, res) => {
  try {
    const result = await pool.query(`
      SELECT 
        total_assigned,
        pages_completed,
        pages_in_progress,
        pages_not_started,
        completion_percentage,
        avg_seconds_per_page,
        CASE 
          WHEN avg_seconds_per_page IS NOT NULL AND pages_completed >= 3
          THEN (pages_not_started + pages_in_progress) * avg_seconds_per_page
          ELSE NULL
        END as estimated_seconds_remaining
      FROM user_progress
      WHERE username = $1
    `, [req.session.username]);
    
    res.json(result.rows[0] || {});
    
  } catch (err) {
    console.error('Progress error:', err);
    res.status(500).json({ success: false, message: 'Failed to get progress' });
  }
});
```

### Performance Considerations

**Query Performance:**
- New indexes improve filtering by completion status
- Timestamp indexes enable efficient sorting by save time
- Removed flag index speeds up metadata section queries

**Storage Impact:**
- ~50 bytes per edit record for new timestamp columns
- ~10 bytes per metadata validation for removed flag and timestamp
- ~10 bytes per entity validation for timestamp
- Total: ~70 bytes per page edit (negligible)

**Trigger Overhead:**
- Single timestamp update on each edit UPDATE
- Negligible performance impact (<1ms)

### Testing Checklist

After running the migration, verify:

- [ ] New columns exist in all tables
- [ ] Indexes were created successfully
- [ ] Existing data was migrated correctly
- [ ] Completion status constraint works (rejects invalid values)
- [ ] Timestamp trigger updates `updated_at` automatically
- [ ] user_progress view returns new columns
- [ ] Metadata can be marked as removed and restored
- [ ] Entity corrections can be saved and retrieved
- [ ] Backward compatibility: old `completed` column still works

### Rollback Impact

**Data Loss Warning:**
Rolling back this migration will:
- ✗ Delete all completion status data
- ✗ Delete all timestamp data (created_at, updated_at, last_saved_at)
- ✗ Delete all removed metadata flags
- ✗ Delete all validated_at timestamps
- ✓ Preserve entity corrections (corrected_name, corrected_type already existed)
- ✓ Preserve old completed boolean values

**Recommendation:** Only rollback if absolutely necessary. Consider fixing forward instead.

### Next Steps

1. **Update Backend API**: Modify save and load endpoints to use new columns
2. **Update Frontend**: Add UI for progress tracking and completion status
3. **Implement Auto-Save**: Use last_saved_at for auto-save logic
4. **Add Progress Dashboard**: Display statistics from user_progress view
5. **Test Thoroughly**: Verify all workflows with new schema
