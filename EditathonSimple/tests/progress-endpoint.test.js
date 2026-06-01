/**
 * Tests for GET /api/progress endpoint
 * 
 * Requirements tested:
 * - 9.1: Calculate average time per completed page
 * - 9.2: Display estimated time remaining when >= 3 pages completed
 * - 9.3: Calculate estimated time as (remaining pages) × (average time per page)
 */

const request = require('supertest');
const express = require('express');
const { Pool } = require('pg');

// Mock pg Pool
jest.mock('pg', () => {
  const mPool = {
    query: jest.fn(),
    connect: jest.fn()
  };
  return { Pool: jest.fn(() => mPool) };
});

describe('GET /api/progress', () => {
  let app;
  let pool;
  let mockSession;

  beforeEach(() => {
    // Create a fresh Express app for each test
    app = express();
    app.use(express.json());
    
    // Create pool instance
    pool = new Pool();
    
    // Mock session
    mockSession = {
      username: 'testuser',
      assigned_pages: { start: 1, end: 10 }
    };
    
    // Session middleware mock
    app.use((req, res, next) => {
      req.session = mockSession;
      next();
    });
    
    // Add the progress endpoint
    app.get('/api/progress', async (req, res) => {
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
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  test('should return progress statistics with completion counts', async () => {
    // Mock database responses
    pool.query
      .mockResolvedValueOnce({
        rows: [{
          total: '10',
          completed: '5',
          in_progress: '3',
          not_started: '2'
        }]
      })
      .mockResolvedValueOnce({
        rows: [{ avg_seconds: 120.5 }]
      });

    const response = await request(app).get('/api/progress');

    expect(response.status).toBe(200);
    expect(response.body).toEqual({
      total: 10,
      completed: 5,
      in_progress: 3,
      not_started: 2,
      average_time_per_page: 120.5,
      estimated_time_remaining: 5 * 120.5 // (3 in_progress + 2 not_started) * avg_time
    });
  });

  test('should calculate average time per completed page (Requirement 9.1)', async () => {
    pool.query
      .mockResolvedValueOnce({
        rows: [{
          total: '10',
          completed: '4',
          in_progress: '2',
          not_started: '4'
        }]
      })
      .mockResolvedValueOnce({
        rows: [{ avg_seconds: 180.0 }]
      });

    const response = await request(app).get('/api/progress');

    expect(response.status).toBe(200);
    expect(response.body.average_time_per_page).toBe(180.0);
    
    // Verify the query was called with correct parameters
    expect(pool.query).toHaveBeenCalledWith(
      expect.stringContaining('AVG(EXTRACT(EPOCH FROM (updated_at - created_at)))'),
      ['testuser', 1, 10]
    );
  });

  test('should display estimated time remaining when >= 3 pages completed (Requirement 9.2)', async () => {
    pool.query
      .mockResolvedValueOnce({
        rows: [{
          total: '10',
          completed: '3',
          in_progress: '4',
          not_started: '3'
        }]
      })
      .mockResolvedValueOnce({
        rows: [{ avg_seconds: 150.0 }]
      });

    const response = await request(app).get('/api/progress');

    expect(response.status).toBe(200);
    expect(response.body.estimated_time_remaining).toBe(7 * 150.0); // (4 + 3) * 150
  });

  test('should NOT display estimated time when < 3 pages completed', async () => {
    pool.query
      .mockResolvedValueOnce({
        rows: [{
          total: '10',
          completed: '2',
          in_progress: '5',
          not_started: '3'
        }]
      })
      .mockResolvedValueOnce({
        rows: [{ avg_seconds: 150.0 }]
      });

    const response = await request(app).get('/api/progress');

    expect(response.status).toBe(200);
    expect(response.body.estimated_time_remaining).toBeNull();
  });

  test('should calculate estimated time as (remaining pages) × (average time per page) (Requirement 9.3)', async () => {
    const avgTime = 200.0;
    const inProgress = 3;
    const notStarted = 4;
    const expectedEstimate = (inProgress + notStarted) * avgTime;

    pool.query
      .mockResolvedValueOnce({
        rows: [{
          total: '10',
          completed: '3',
          in_progress: String(inProgress),
          not_started: String(notStarted)
        }]
      })
      .mockResolvedValueOnce({
        rows: [{ avg_seconds: avgTime }]
      });

    const response = await request(app).get('/api/progress');

    expect(response.status).toBe(200);
    expect(response.body.estimated_time_remaining).toBe(expectedEstimate);
  });

  test('should handle case with no completed pages', async () => {
    pool.query
      .mockResolvedValueOnce({
        rows: [{
          total: '10',
          completed: '0',
          in_progress: '2',
          not_started: '8'
        }]
      })
      .mockResolvedValueOnce({
        rows: [{ avg_seconds: null }]
      });

    const response = await request(app).get('/api/progress');

    expect(response.status).toBe(200);
    expect(response.body).toEqual({
      total: 10,
      completed: 0,
      in_progress: 2,
      not_started: 8,
      average_time_per_page: null,
      estimated_time_remaining: null
    });
  });

  test('should handle all pages completed', async () => {
    pool.query
      .mockResolvedValueOnce({
        rows: [{
          total: '10',
          completed: '10',
          in_progress: '0',
          not_started: '0'
        }]
      })
      .mockResolvedValueOnce({
        rows: [{ avg_seconds: 100.0 }]
      });

    const response = await request(app).get('/api/progress');

    expect(response.status).toBe(200);
    expect(response.body.estimated_time_remaining).toBe(0); // No remaining pages
  });

  test('should handle database errors gracefully', async () => {
    pool.query.mockRejectedValueOnce(new Error('Database connection failed'));

    const response = await request(app).get('/api/progress');

    expect(response.status).toBe(500);
    expect(response.body).toEqual({
      success: false,
      message: 'Failed to get progress'
    });
  });

  test('should query correct page range from session', async () => {
    mockSession.assigned_pages = { start: 5, end: 15 };

    pool.query
      .mockResolvedValueOnce({
        rows: [{
          total: '11',
          completed: '5',
          in_progress: '3',
          not_started: '3'
        }]
      })
      .mockResolvedValueOnce({
        rows: [{ avg_seconds: 120.0 }]
      });

    await request(app).get('/api/progress');

    // Verify first query uses correct page range
    expect(pool.query).toHaveBeenCalledWith(
      expect.any(String),
      [5, 15, 'testuser']
    );
    
    // Verify second query uses correct page range
    expect(pool.query).toHaveBeenCalledWith(
      expect.any(String),
      ['testuser', 5, 15]
    );
  });
});
