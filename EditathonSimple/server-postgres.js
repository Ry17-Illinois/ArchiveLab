const express = require('express');
const path = require('path');
const crypto = require('crypto');
const { Pool } = require('pg');

// Load environment variables from .env.local if it exists
try {
  require('dotenv').config({ path: path.join(__dirname, '.env.local') });
} catch (e) {
  // dotenv not installed, will use system environment variables
  console.log('Note: dotenv not available, using system environment variables');
}

const app = express();

app.use(express.static(path.join(__dirname, 'dist')));
app.use(express.json());

// Serve data files (images only, data comes from DB)
app.use('/data/images', express.static(path.join(__dirname, 'data/images')));

// PostgreSQL connection pool
const pool = new Pool({
  host: process.env.DB_HOST || 'localhost',
  database: process.env.DB_NAME || 'editathon_db',
  user: process.env.DB_USER || 'editathon_user',
  password: process.env.DB_PASSWORD || 'your_password',
  port: process.env.DB_PORT || 5432,
  max: 20,
  idleTimeoutMillis: 30000
});

// Test database connection
pool.query('SELECT NOW()', (err, res) => {
  if (err) {
    console.error('Database connection error:', err);
  } else {
    console.log('Database connected successfully');
  }
});

// Clean up expired sessions every hour
setInterval(async () => {
  try {
    const result = await pool.query('DELETE FROM sessions WHERE expires_at < NOW()');
    if (result.rowCount > 0) {
      console.log(`Cleaned up ${result.rowCount} expired sessions`);
    }
  } catch (err) {
    console.error('Session cleanup error:', err);
  }
}, 60 * 60 * 1000); // Run every hour

// Session storage moved to PostgreSQL (see sessions table)
// Sessions now persist across server restarts

// Hash password for comparison
function hashPassword(password) {
  return crypto.createHash('sha256').update(password).digest('hex');
}

// Login endpoint
app.post('/api/login', async (req, res) => {
  const { username, password } = req.body;
  
  try {
    const result = await pool.query(
      'SELECT username, password_hash, name, assigned_start, assigned_end, is_admin FROM users WHERE username = $1',
      [username]
    );
    
    if (result.rows.length > 0 && result.rows[0].password_hash === hashPassword(password)) {
      const user = result.rows[0];
      const sessionId = crypto.randomBytes(32).toString('hex');
      const expiresAt = new Date(Date.now() + 24 * 60 * 60 * 1000); // 24 hours
      
      // Store session in database
      await pool.query(
        'INSERT INTO sessions (session_id, username, assigned_start, assigned_end, expires_at) VALUES ($1, $2, $3, $4, $5) ON CONFLICT (session_id) DO UPDATE SET expires_at = $5',
        [sessionId, user.username, user.assigned_start, user.assigned_end, expiresAt]
      );
      
      // Update last login
      await pool.query(
        'UPDATE users SET last_login = NOW() WHERE username = $1',
        [username]
      );
      
      res.json({
        success: true,
        sessionId,
        username: user.username,
        is_admin: user.is_admin || false,
        assigned_pages: {
          start: user.assigned_start,
          end: user.assigned_end
        }
      });
    } else {
      res.status(401).json({ success: false, message: 'Invalid credentials' });
    }
  } catch (err) {
    console.error('Login error:', err);
    res.status(500).json({ success: false, message: 'Server error' });
  }
});

// Verify session middleware
async function verifySession(req, res, next) {
  const sessionId = req.headers['x-session-id'];
  
  if (!sessionId) {
    return res.status(401).json({ success: false, message: 'Unauthorized' });
  }
  
  try {
    // Get session from database
    const result = await pool.query(
      'SELECT session_id, username, assigned_start, assigned_end, expires_at FROM sessions WHERE session_id = $1',
      [sessionId]
    );
    
    if (result.rows.length === 0) {
      return res.status(401).json({ success: false, message: 'Unauthorized' });
    }
    
    const session = result.rows[0];
    
    // Check if session expired
    if (new Date(session.expires_at) < new Date()) {
      await pool.query('DELETE FROM sessions WHERE session_id = $1', [sessionId]);
      return res.status(401).json({ success: false, message: 'Session expired' });
    }
    
    // Attach session to request
    req.session = {
      username: session.username,
      assigned_pages: {
        start: session.assigned_start,
        end: session.assigned_end
      }
    };
    
    next();
  } catch (err) {
    console.error('Session verification error:', err);
    res.status(500).json({ success: false, message: 'Server error' });
  }
}

// Get dataset from database
app.get('/api/dataset', verifySession, async (req, res) => {
  try {
    const { assigned_pages } = req.session;
    const username = req.session.username;
    
    // Get pages with OCR versions, entities, completion status, AND saved edits
    const pagesResult = await pool.query(`
      SELECT 
        p.page_id,
        p.page_number,
        p.json_file,
        p.image_path,
        p.document_filename,
        p.dublin_core,
        p.archival_context,
        COALESCE(ed.completed_status, 'not_started') as completion_status,
        ed.last_saved_at,
        ed.ocr_selected as saved_ocr_selected,
        ed.transcription as saved_transcription,
        ed.transcription_edited as saved_transcription_edited,
        json_agg(DISTINCT jsonb_build_object(
          'engine_name', o.engine_name,
          'ocr_text', o.ocr_text
        )) FILTER (WHERE o.engine_name IS NOT NULL) as ocr_versions,
        json_agg(DISTINCT jsonb_build_object(
          'id', e.id,
          'entity_type', e.entity_type,
          'entity_name', e.entity_name
        )) FILTER (WHERE e.id IS NOT NULL) as entities,
        json_agg(DISTINCT jsonb_build_object(
          'field_name', mv.field_name,
          'status', mv.validation_status
        )) FILTER (WHERE mv.id IS NOT NULL) as metadata_validations,
        json_agg(DISTINCT jsonb_build_object(
          'entity_id', ev.entity_id,
          'status', ev.validation_status
        )) FILTER (WHERE ev.id IS NOT NULL) as entity_validations
      FROM pages p
      LEFT JOIN ocr_versions o ON p.page_id = o.page_id
      LEFT JOIN entities e ON p.page_id = e.page_id
      LEFT JOIN edits ed ON p.page_id = ed.page_id AND ed.username = $3
      LEFT JOIN metadata_validations mv ON ed.id = mv.edit_id
      LEFT JOIN entity_validations ev ON ed.id = ev.edit_id
      WHERE p.page_number >= $1 AND p.page_number <= $2
      GROUP BY p.id, p.page_id, p.page_number, p.json_file, p.image_path, p.document_filename, p.dublin_core, p.archival_context, ed.completed_status, ed.last_saved_at, ed.ocr_selected, ed.transcription, ed.transcription_edited
      ORDER BY p.page_number
    `, [assigned_pages.start, assigned_pages.end, username]);
    
    // Calculate progress statistics
    const progressResult = await pool.query(`
      SELECT 
        COUNT(*) as total,
        COUNT(CASE WHEN ed.completed_status = 'completed' THEN 1 END) as completed,
        COUNT(CASE WHEN ed.completed_status = 'in_progress' THEN 1 END) as in_progress,
        COUNT(CASE WHEN ed.completed_status = 'not_started' OR ed.completed_status IS NULL THEN 1 END) as not_started
      FROM pages p
      LEFT JOIN edits ed ON p.page_id = ed.page_id AND ed.username = $3
      WHERE p.page_number >= $1 AND p.page_number <= $2
    `, [assigned_pages.start, assigned_pages.end, username]);
    
    // Calculate average time per page from completed edits
    const avgTimeResult = await pool.query(`
      SELECT 
        AVG(EXTRACT(EPOCH FROM (updated_at - created_at))) as avg_seconds
      FROM edits
      WHERE username = $1 
        AND completed_status = 'completed'
        AND page_number >= $2 
        AND page_number <= $3
    `, [username, assigned_pages.start, assigned_pages.end]);
    
    const progress = {
      total: parseInt(progressResult.rows[0].total),
      completed: parseInt(progressResult.rows[0].completed),
      in_progress: parseInt(progressResult.rows[0].in_progress),
      not_started: parseInt(progressResult.rows[0].not_started),
      average_time_per_page: avgTimeResult.rows[0].avg_seconds ? parseFloat(avgTimeResult.rows[0].avg_seconds) : null
    };
    
    // Extract document identifier from json_file
    let documentTitle = 'Archive Editathon';
    if (pagesResult.rows.length > 0 && pagesResult.rows[0].json_file) {
      const jsonFile = pagesResult.rows[0].json_file;
      // Extract the part before "_Page" and format it
      // Example: "0811004_Correspondence_HomeEconomicsCourseMaterial_Page17.json"
      // Becomes: "0811004 - Correspondence - Home Economics Course Material"
      const match = jsonFile.match(/^(.+?)_Page\d+\.json$/);
      if (match) {
        const parts = match[1].split('_');
        // First part is the identifier (0811004)
        // Rest are the document name parts
        if (parts.length > 1) {
          const identifier = parts[0];
          const nameParts = parts.slice(1).map(part => {
            // Add spaces before capital letters (camelCase to Title Case)
            return part.replace(/([A-Z])/g, ' $1').trim();
          });
          documentTitle = `${identifier} - ${nameParts.join(' - ')}`;
        } else {
          documentTitle = parts[0];
        }
      }
    }
    
    // Transform OCR versions from array to object
    const pages = pagesResult.rows.map(page => {
      const ocr_versions = {};
      if (page.ocr_versions) {
        page.ocr_versions.forEach(ocr => {
          ocr_versions[ocr.engine_name] = ocr.ocr_text;
        });
      }
      
      // Note: We no longer overwrite OCR versions with saved transcriptions
      // The Human-Reviewed version is already in the ocr_versions table
      
      // Transform entities to grouped object
      const entities_grouped = {};
      if (page.entities) {
        page.entities.forEach(ent => {
          if (!entities_grouped[ent.entity_type]) {
            entities_grouped[ent.entity_type] = [];
          }
          entities_grouped[ent.entity_type].push({
            id: ent.id,
            name: ent.entity_name
          });
        });
      }
      
      // Transform metadata validations to object
      const metadata_validations_obj = {};
      if (page.metadata_validations && page.metadata_validations[0]?.field_name) {
        page.metadata_validations.forEach(mv => {
          metadata_validations_obj[mv.field_name] = mv.status;
        });
      }
      
      // Transform entity validations to object
      const entity_validations_obj = {};
      if (page.entity_validations && page.entity_validations[0]?.entity_id) {
        page.entity_validations.forEach(ev => {
          entity_validations_obj[ev.entity_id] = ev.status;
        });
      }
      
      return {
        page_id: page.page_id,
        page_number: page.page_number,
        json_file: page.json_file,
        ocr_versions,
        entities: entities_grouped,
        metadata: {
          dublin_core: page.dublin_core || {},
          archival_context: page.archival_context || {}
        },
        completion_status: page.completion_status,
        last_saved_at: page.last_saved_at,
        // Include saved edit state
        saved_state: page.saved_ocr_selected ? {
          ocr_selected: page.saved_ocr_selected,
          transcription_edited: page.saved_transcription_edited || false,
          metadata_validations: metadata_validations_obj,
          entity_validations: entity_validations_obj
        } : null
      };
    });
    
    res.json({
      document: {
        filename: documentTitle
      },
      pages,
      progress
    });
  } catch (err) {
    console.error('Dataset error:', err);
    res.status(500).json({ success: false, message: 'Failed to load dataset' });
  }
});

// Save edit
app.post('/api/save', verifySession, async (req, res) => {
  const { page_id, page_number, base_model, transcription, transcription_edited, metadata_validations, entity_validations } = req.body;
  const username = req.session.username;
  
  const client = await pool.connect();
  
  try {
    await client.query('BEGIN');
    
    // If transcription was edited, save it as a new "Human-Reviewed" OCR version
    if (transcription_edited && base_model) {
      await client.query(`
        INSERT INTO ocr_versions (page_id, engine_name, ocr_text)
        VALUES ($1, $2, $3)
        ON CONFLICT (page_id, engine_name)
        DO UPDATE SET ocr_text = $3, created_at = NOW()
      `, [page_id, 'Human-Reviewed', transcription]);
    }
    
    // Insert or update edit record
    const editResult = await client.query(`
      INSERT INTO edits (username, page_id, page_number, ocr_selected, transcription, transcription_edited, completed, timestamp)
      VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
      ON CONFLICT (username, page_id) 
      DO UPDATE SET 
        ocr_selected = $4,
        transcription = $5,
        transcription_edited = $6,
        completed = $7,
        timestamp = NOW()
      RETURNING id
    `, [username, page_id, page_number, base_model, transcription, transcription_edited || false, true]);
    
    const edit_id = editResult.rows[0].id;
    
    // Save metadata validations
    if (metadata_validations && Array.isArray(metadata_validations)) {
      // Delete existing validations for this edit
      await client.query('DELETE FROM metadata_validations WHERE edit_id = $1', [edit_id]);
      
      for (const validation of metadata_validations) {
        await client.query(`
          INSERT INTO metadata_validations (edit_id, field_name, original_value, validation_status, notes)
          VALUES ($1, $2, $3, $4, $5)
        `, [edit_id, validation.field_name, validation.original_value, validation.status, validation.notes || null]);
      }
    }
    
    // Save entity validations
    if (entity_validations && Array.isArray(entity_validations)) {
      // Delete existing validations for this edit
      await client.query('DELETE FROM entity_validations WHERE edit_id = $1', [edit_id]);
      
      for (const validation of entity_validations) {
        await client.query(`
          INSERT INTO entity_validations (edit_id, entity_id, validation_status, corrected_name, corrected_type, notes)
          VALUES ($1, $2, $3, $4, $5, $6)
          ON CONFLICT (edit_id, entity_id) 
          DO UPDATE SET 
            validation_status = $3,
            corrected_name = $4,
            corrected_type = $5,
            notes = $6,
            timestamp = NOW()
        `, [edit_id, validation.entity_id, validation.status, validation.corrected_name || null, validation.corrected_type || null, validation.notes || null]);
      }
    }
    
    await client.query('COMMIT');
    res.json({ success: true });
    
  } catch (err) {
    await client.query('ROLLBACK');
    console.error('Save error:', err);
    res.status(500).json({ success: false, message: 'Failed to save' });
  } finally {
    client.release();
  }
});

// Add custom entity
app.post('/api/add-entity', verifySession, async (req, res) => {
  const { page_id, entity_type, entity_name } = req.body;
  
  if (!page_id || !entity_type || !entity_name) {
    return res.status(400).json({ success: false, message: 'Missing required fields' });
  }
  
  try {
    const result = await pool.query(
      'INSERT INTO entities (page_id, entity_type, entity_name) VALUES ($1, $2, $3) RETURNING id',
      [page_id, entity_type.toUpperCase(), entity_name.trim()]
    );
    
    res.json({ 
      success: true, 
      entity: {
        id: result.rows[0].id,
        entity_type: entity_type.toUpperCase(),
        entity_name: entity_name.trim()
      }
    });
  } catch (err) {
    console.error('Add entity error:', err);
    res.status(500).json({ success: false, message: 'Failed to add entity' });
  }
});

// Report issue
app.post('/api/report-issue', verifySession, async (req, res) => {
  const { page_id, issue_type, description } = req.body;
  const username = req.session.username;
  
  if (!page_id || !issue_type) {
    return res.status(400).json({ success: false, message: 'Missing required fields' });
  }
  
  try {
    await pool.query(
      'INSERT INTO page_issues (page_id, username, issue_type, description) VALUES ($1, $2, $3, $4)',
      [page_id, username, issue_type, description || null]
    );
    
    res.json({ success: true, message: 'Issue reported successfully' });
  } catch (err) {
    console.error('Report issue error:', err);
    res.status(500).json({ success: false, message: 'Failed to report issue' });
  }
});

// Get user progress
app.get('/api/progress', verifySession, async (req, res) => {
  try {
    const { assigned_pages } = req.session;
    const username = req.session.username;
    
    // Query database for user's page completion counts by status
    const statusResult = await pool.query(`
      SELECT 
        COUNT(*) as total,
        COUNT(CASE WHEN ed.completed_status = 'completed' THEN 1 END) as completed,
        COUNT(CASE WHEN ed.completed_status = 'in_progress' THEN 1 END) as in_progress,
        COUNT(CASE WHEN ed.completed_status = 'not_started' OR ed.completed_status IS NULL THEN 1 END) as not_started
      FROM pages p
      LEFT JOIN edits ed ON p.page_id = ed.page_id AND ed.username = $3
      WHERE p.page_number >= $1 AND p.page_number <= $2
    `, [assigned_pages.start, assigned_pages.end, username]);
    
    // Calculate average time per completed page
    const avgTimeResult = await pool.query(`
      SELECT 
        AVG(EXTRACT(EPOCH FROM (updated_at - created_at))) as avg_seconds
      FROM edits
      WHERE username = $1 
        AND completed_status = 'completed'
        AND page_number >= $2 
        AND page_number <= $3
    `, [username, assigned_pages.start, assigned_pages.end]);
    
    const total = parseInt(statusResult.rows[0].total);
    const completed = parseInt(statusResult.rows[0].completed);
    const in_progress = parseInt(statusResult.rows[0].in_progress);
    const not_started = parseInt(statusResult.rows[0].not_started);
    const average_time_per_page = avgTimeResult.rows[0].avg_seconds ? parseFloat(avgTimeResult.rows[0].avg_seconds) : null;
    
    // Calculate estimated time remaining (only if >= 3 pages completed)
    let estimated_time_remaining = null;
    if (completed >= 3 && average_time_per_page !== null) {
      const remaining_pages = not_started + in_progress;
      estimated_time_remaining = remaining_pages * average_time_per_page;
    }
    
    res.json({
      total,
      completed,
      in_progress,
      not_started,
      average_time_per_page,
      estimated_time_remaining
    });
  } catch (err) {
    console.error('Progress error:', err);
    res.status(500).json({ success: false, message: 'Failed to get progress' });
  }
});

// Admin middleware
async function verifyAdmin(req, res, next) {
  const sessionId = req.headers['x-session-id'];
  
  if (!sessionId) {
    return res.status(401).json({ success: false, message: 'Unauthorized' });
  }
  
  try {
    const sessionResult = await pool.query(
      'SELECT session_id, username, expires_at FROM sessions WHERE session_id = $1',
      [sessionId]
    );
    
    if (sessionResult.rows.length === 0) {
      return res.status(401).json({ success: false, message: 'Unauthorized' });
    }
    
    const session = sessionResult.rows[0];
    
    if (new Date(session.expires_at) < new Date()) {
      await pool.query('DELETE FROM sessions WHERE session_id = $1', [sessionId]);
      return res.status(401).json({ success: false, message: 'Session expired' });
    }
    
    // Check if user is admin
    const userResult = await pool.query(
      'SELECT is_admin FROM users WHERE username = $1',
      [session.username]
    );
    
    if (userResult.rows.length === 0 || !userResult.rows[0].is_admin) {
      return res.status(403).json({ success: false, message: 'Forbidden: Admin access required' });
    }
    
    req.session = { username: session.username };
    next();
  } catch (err) {
    console.error('Admin verification error:', err);
    res.status(500).json({ success: false, message: 'Server error' });
  }
}

// Admin: Get all users
app.get('/api/admin/users', verifyAdmin, async (req, res) => {
  try {
    const result = await pool.query(`
      SELECT 
        u.id,
        u.username,
        u.name,
        u.assigned_start,
        u.assigned_end,
        u.is_admin,
        u.last_login,
        COUNT(DISTINCT p.page_id) as total,
        COUNT(DISTINCT CASE WHEN e.completed_status = 'completed' THEN e.page_id END) as completed
      FROM users u
      LEFT JOIN pages p ON p.page_number >= u.assigned_start AND p.page_number <= u.assigned_end
      LEFT JOIN edits e ON e.page_id = p.page_id AND e.username = u.username
      GROUP BY u.id, u.username, u.name, u.assigned_start, u.assigned_end, u.is_admin, u.last_login
      ORDER BY u.username
    `);
    
    res.json({ success: true, users: result.rows });
  } catch (err) {
    console.error('Get users error:', err);
    res.status(500).json({ success: false, message: 'Failed to get users' });
  }
});

// Admin: Add new user
app.post('/api/admin/users', verifyAdmin, async (req, res) => {
  const { username, password, name, assigned_start, assigned_end } = req.body;
  
  if (!username || !password || !assigned_start || !assigned_end) {
    return res.status(400).json({ success: false, message: 'Missing required fields' });
  }
  
  try {
    const passwordHash = hashPassword(password);
    
    await pool.query(
      'INSERT INTO users (username, password_hash, name, assigned_start, assigned_end) VALUES ($1, $2, $3, $4, $5)',
      [username, passwordHash, name || null, parseInt(assigned_start), parseInt(assigned_end)]
    );
    
    res.json({ success: true, message: 'User created successfully' });
  } catch (err) {
    console.error('Add user error:', err);
    if (err.code === '23505') { // Unique violation
      res.status(400).json({ success: false, message: 'Username already exists' });
    } else {
      res.status(500).json({ success: false, message: 'Failed to add user' });
    }
  }
});

// Admin: Update user
app.put('/api/admin/users/:id', verifyAdmin, async (req, res) => {
  const { id } = req.params;
  const { assigned_start, assigned_end, name } = req.body;
  
  try {
    const updates = [];
    const values = [];
    let paramCount = 1;
    
    if (assigned_start !== undefined) {
      updates.push(`assigned_start = $${paramCount++}`);
      values.push(parseInt(assigned_start));
    }
    if (assigned_end !== undefined) {
      updates.push(`assigned_end = $${paramCount++}`);
      values.push(parseInt(assigned_end));
    }
    if (name !== undefined) {
      updates.push(`name = $${paramCount++}`);
      values.push(name);
    }
    
    if (updates.length === 0) {
      return res.status(400).json({ success: false, message: 'No fields to update' });
    }
    
    values.push(parseInt(id));
    
    await pool.query(
      `UPDATE users SET ${updates.join(', ')} WHERE id = $${paramCount}`,
      values
    );
    
    res.json({ success: true, message: 'User updated successfully' });
  } catch (err) {
    console.error('Update user error:', err);
    res.status(500).json({ success: false, message: 'Failed to update user' });
  }
});

// Admin: Delete user
app.delete('/api/admin/users/:id', verifyAdmin, async (req, res) => {
  const { id } = req.params;
  
  try {
    // Check if user is admin
    const userCheck = await pool.query('SELECT is_admin FROM users WHERE id = $1', [parseInt(id)]);
    if (userCheck.rows.length > 0 && userCheck.rows[0].is_admin) {
      return res.status(400).json({ success: false, message: 'Cannot delete admin user' });
    }
    
    await pool.query('DELETE FROM users WHERE id = $1', [parseInt(id)]);
    res.json({ success: true, message: 'User deleted successfully' });
  } catch (err) {
    console.error('Delete user error:', err);
    res.status(500).json({ success: false, message: 'Failed to delete user' });
  }
});

// Admin: Auto-distribute pages
app.post('/api/admin/auto-distribute', verifyAdmin, async (req, res) => {
  try {
    // Get total pages from database
    const pageCountResult = await pool.query('SELECT COUNT(*) as total FROM pages');
    const totalPages = parseInt(pageCountResult.rows[0].total);
    
    if (totalPages === 0) {
      return res.status(400).json({ success: false, message: 'No pages in database to distribute' });
    }
    
    // Get all non-admin users
    const usersResult = await pool.query(
      'SELECT id, username FROM users WHERE is_admin = FALSE OR is_admin IS NULL ORDER BY id'
    );
    
    const users = usersResult.rows;
    if (users.length === 0) {
      return res.status(400).json({ success: false, message: 'No users to distribute pages to' });
    }
    
    const pagesPerUser = Math.floor(totalPages / users.length);
    let currentPage = 1;
    
    // Update each user's page assignment
    for (let i = 0; i < users.length; i++) {
      const startPage = currentPage;
      const endPage = (i === users.length - 1) ? totalPages : currentPage + pagesPerUser - 1;
      
      await pool.query(
        'UPDATE users SET assigned_start = $1, assigned_end = $2 WHERE id = $3',
        [startPage, endPage, users[i].id]
      );
      
      currentPage = endPage + 1;
    }
    
    res.json({ 
      success: true, 
      message: `Distributed ${totalPages} pages among ${users.length} users`,
      totalPages: totalPages,
      usersUpdated: users.length,
      pagesPerUser: pagesPerUser
    });
  } catch (err) {
    console.error('Auto-distribute error:', err);
    res.status(500).json({ success: false, message: 'Failed to distribute pages' });
  }
});

// Admin: Export data
app.get('/api/admin/export', verifyAdmin, async (req, res) => {
  const { format } = req.query;
  
  try {
    const result = await pool.query(`
      SELECT 
        p.page_id,
        p.page_number,
        p.json_file,
        p.document_filename,
        p.dublin_core,
        p.archival_context,
        e.username as editor,
        e.ocr_selected as ground_truth_model,
        e.transcription,
        e.transcription_edited,
        e.completed_status,
        e.created_at as edit_created,
        e.updated_at as edit_updated,
        e.timestamp,
        json_agg(DISTINCT jsonb_build_object(
          'field_name', mv.field_name,
          'original_value', mv.original_value,
          'validation_status', mv.validation_status,
          'notes', mv.notes,
          'timestamp', mv.timestamp
        )) FILTER (WHERE mv.id IS NOT NULL) as metadata_validations,
        json_agg(DISTINCT jsonb_build_object(
          'entity_id', ev.entity_id,
          'entity_name', ent.entity_name,
          'entity_type', ent.entity_type,
          'validation_status', ev.validation_status,
          'corrected_name', ev.corrected_name,
          'corrected_type', ev.corrected_type,
          'notes', ev.notes,
          'timestamp', ev.timestamp
        )) FILTER (WHERE ev.id IS NOT NULL) as entity_validations
      FROM pages p
      LEFT JOIN edits e ON p.page_id = e.page_id
      LEFT JOIN metadata_validations mv ON e.id = mv.edit_id
      LEFT JOIN entity_validations ev ON e.id = ev.edit_id
      LEFT JOIN entities ent ON ev.entity_id = ent.id
      WHERE e.id IS NOT NULL
      GROUP BY p.page_id, p.page_number, p.json_file, p.document_filename, p.dublin_core, p.archival_context, 
               e.username, e.ocr_selected, e.transcription, e.transcription_edited, 
               e.completed_status, e.created_at, e.updated_at, e.timestamp
      ORDER BY p.page_number
    `);
    
    if (format === 'csv') {
      // Generate CSV
      const rows = [
        ['Page ID', 'Page Number', 'JSON File', 'Document', 'Editor', 'Ground Truth Model', 'Transcription', 'Edited', 'Status', 'Metadata Approved', 'Metadata Rejected', 'Entities Approved', 'Entities Rejected', 'Created', 'Updated']
      ];
      
      result.rows.forEach(row => {
        const metadataApproved = row.metadata_validations?.filter(m => m.validation_status === 'approved').length || 0;
        const metadataRejected = row.metadata_validations?.filter(m => m.validation_status === 'rejected').length || 0;
        const entitiesApproved = row.entity_validations?.filter(e => e.validation_status === 'approved').length || 0;
        const entitiesRejected = row.entity_validations?.filter(e => e.validation_status === 'rejected').length || 0;
        
        rows.push([
          row.page_id,
          row.page_number,
          row.json_file || '',
          row.document_filename || '',
          row.editor || '',
          row.ground_truth_model || '',
          (row.transcription || '').replace(/"/g, '""').substring(0, 500),
          row.transcription_edited ? 'Yes' : 'No',
          row.completed_status || '',
          metadataApproved,
          metadataRejected,
          entitiesApproved,
          entitiesRejected,
          row.edit_created || '',
          row.edit_updated || ''
        ]);
      });
      
      const csv = rows.map(row => row.map(cell => `"${cell}"`).join(',')).join('\n');
      res.setHeader('Content-Type', 'text/csv');
      res.setHeader('Content-Disposition', 'attachment; filename=editathon-export.csv');
      res.send(csv);
    } else {
      // Return JSON with resolved entity names (ready for merge script)
      res.json(result.rows);
    }
  } catch (err) {
    console.error('Export error:', err);
    res.status(500).json({ success: false, message: 'Failed to export' });
  }
});

// Admin: Get all progress (requires admin check - simplified here)
app.get('/api/admin/progress', async (req, res) => {
  try {
    const result = await pool.query('SELECT * FROM user_progress ORDER BY username');
    res.json(result.rows);
  } catch (err) {
    console.error('Admin progress error:', err);
    res.status(500).json({ success: false, message: 'Failed to get progress' });
  }
});

// Admin: Export all edits
app.get('/api/admin/export', async (req, res) => {
  try {
    const result = await pool.query(`
      SELECT 
        e.*,
        json_agg(DISTINCT mv.*) FILTER (WHERE mv.id IS NOT NULL) as metadata_validations,
        json_agg(DISTINCT ev.*) FILTER (WHERE ev.id IS NOT NULL) as entity_validations
      FROM edits e
      LEFT JOIN metadata_validations mv ON e.id = mv.edit_id
      LEFT JOIN entity_validations ev ON e.id = ev.edit_id
      GROUP BY e.id
      ORDER BY e.username, e.page_number
    `);
    
    res.json(result.rows);
  } catch (err) {
    console.error('Export error:', err);
    res.status(500).json({ success: false, message: 'Failed to export' });
  }
});

app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'dist', 'index.html'));
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
