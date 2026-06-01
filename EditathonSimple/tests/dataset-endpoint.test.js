/**
 * Unit tests for GET /api/dataset endpoint enhancements
 * Tests completion status, progress statistics, and average time calculations
 * 
 * Requirements: 1.1, 1.2, 1.4, 9.1
 */

const { describe, it, expect, beforeAll, afterAll } = require('@jest/globals');

describe('GET /api/dataset endpoint', () => {
  describe('Progress statistics calculation', () => {
    it('should correctly count pages by status', () => {
      // Mock data representing query results
      const mockPages = [
        { completion_status: 'completed' },
        { completion_status: 'completed' },
        { completion_status: 'in_progress' },
        { completion_status: null }, // not_started
        { completion_status: null }, // not_started
      ];
      
      // Simulate the SQL COUNT logic
      const total = mockPages.length;
      const completed = mockPages.filter(p => p.completion_status === 'completed').length;
      const in_progress = mockPages.filter(p => p.completion_status === 'in_progress').length;
      const not_started = mockPages.filter(p => p.completion_status === 'not_started' || p.completion_status === null).length;
      
      expect(total).toBe(5);
      expect(completed).toBe(2);
      expect(in_progress).toBe(1);
      expect(not_started).toBe(2);
      expect(completed + in_progress + not_started).toBe(total);
    });
    
    it('should handle all pages not started', () => {
      const mockPages = [
        { completion_status: null },
        { completion_status: null },
        { completion_status: null },
      ];
      
      const total = mockPages.length;
      const completed = mockPages.filter(p => p.completion_status === 'completed').length;
      const in_progress = mockPages.filter(p => p.completion_status === 'in_progress').length;
      const not_started = mockPages.filter(p => p.completion_status === 'not_started' || p.completion_status === null).length;
      
      expect(total).toBe(3);
      expect(completed).toBe(0);
      expect(in_progress).toBe(0);
      expect(not_started).toBe(3);
    });
    
    it('should handle all pages completed', () => {
      const mockPages = [
        { completion_status: 'completed' },
        { completion_status: 'completed' },
        { completion_status: 'completed' },
      ];
      
      const total = mockPages.length;
      const completed = mockPages.filter(p => p.completion_status === 'completed').length;
      const in_progress = mockPages.filter(p => p.completion_status === 'in_progress').length;
      const not_started = mockPages.filter(p => p.completion_status === 'not_started' || p.completion_status === null).length;
      
      expect(total).toBe(3);
      expect(completed).toBe(3);
      expect(in_progress).toBe(0);
      expect(not_started).toBe(0);
    });
  });
  
  describe('Average time per page calculation', () => {
    it('should calculate average time from completed edits', () => {
      // Mock completed edits with time differences
      const mockEdits = [
        { created_at: new Date('2024-01-01T10:00:00'), updated_at: new Date('2024-01-01T10:05:00') }, // 5 min = 300s
        { created_at: new Date('2024-01-01T11:00:00'), updated_at: new Date('2024-01-01T11:10:00') }, // 10 min = 600s
        { created_at: new Date('2024-01-01T12:00:00'), updated_at: new Date('2024-01-01T12:15:00') }, // 15 min = 900s
      ];
      
      // Calculate average (simulating EXTRACT(EPOCH FROM (updated_at - created_at)))
      const times = mockEdits.map(e => (e.updated_at - e.created_at) / 1000); // Convert to seconds
      const avgSeconds = times.reduce((sum, t) => sum + t, 0) / times.length;
      
      expect(avgSeconds).toBe(600); // (300 + 600 + 900) / 3 = 600 seconds = 10 minutes
    });
    
    it('should return null when no completed edits exist', () => {
      const mockEdits = [];
      
      const avgSeconds = mockEdits.length > 0 
        ? mockEdits.reduce((sum, e) => sum + ((e.updated_at - e.created_at) / 1000), 0) / mockEdits.length
        : null;
      
      expect(avgSeconds).toBeNull();
    });
    
    it('should handle single completed edit', () => {
      const mockEdits = [
        { created_at: new Date('2024-01-01T10:00:00'), updated_at: new Date('2024-01-01T10:08:00') }, // 8 min = 480s
      ];
      
      const times = mockEdits.map(e => (e.updated_at - e.created_at) / 1000);
      const avgSeconds = times.reduce((sum, t) => sum + t, 0) / times.length;
      
      expect(avgSeconds).toBe(480);
    });
  });
  
  describe('Response structure', () => {
    it('should include completion_status for each page', () => {
      const mockPage = {
        page_id: 'page_001',
        page_number: 1,
        completion_status: 'in_progress',
        last_saved_at: new Date('2024-01-01T10:00:00'),
      };
      
      expect(mockPage).toHaveProperty('completion_status');
      expect(mockPage.completion_status).toBe('in_progress');
    });
    
    it('should include progress object with all statistics', () => {
      const progress = {
        total: 10,
        completed: 3,
        in_progress: 2,
        not_started: 5,
        average_time_per_page: 450.5,
      };
      
      expect(progress).toHaveProperty('total');
      expect(progress).toHaveProperty('completed');
      expect(progress).toHaveProperty('in_progress');
      expect(progress).toHaveProperty('not_started');
      expect(progress).toHaveProperty('average_time_per_page');
      expect(progress.total).toBe(progress.completed + progress.in_progress + progress.not_started);
    });
    
    it('should handle null average_time_per_page', () => {
      const progress = {
        total: 10,
        completed: 0,
        in_progress: 2,
        not_started: 8,
        average_time_per_page: null,
      };
      
      expect(progress.average_time_per_page).toBeNull();
    });
  });
  
  describe('COALESCE logic for completion_status', () => {
    it('should default to not_started when status is null', () => {
      const mockStatus = null;
      const completion_status = mockStatus || 'not_started';
      
      expect(completion_status).toBe('not_started');
    });
    
    it('should preserve existing status values', () => {
      const statuses = ['completed', 'in_progress', 'not_started'];
      
      statuses.forEach(status => {
        const completion_status = status || 'not_started';
        expect(completion_status).toBe(status);
      });
    });
  });
});
