import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { logger } from './logger';

describe('Logger', () => {
  // Save original console methods
  const originalConsole = {
    log: console.log,
    info: console.info,
    warn: console.warn,
    error: console.error,
  };

  beforeEach(() => {
    // Mock console methods
    console.log = vi.fn();
    console.info = vi.fn();
    console.warn = vi.fn();
    console.error = vi.fn();
  });

  afterEach(() => {
    // Restore original console methods
    console.log = originalConsole.log;
    console.info = originalConsole.info;
    console.warn = originalConsole.warn;
    console.error = originalConsole.error;
    vi.clearAllMocks();
  });

  describe('debug()', () => {
    it('should log debug messages', () => {
      logger.debug('Test debug message', { foo: 'bar' });

      // In test/development mode, debug logs should be visible
      expect(console.log).toHaveBeenCalledWith(
        '[DEBUG] Test debug message',
        { foo: 'bar' }
      );
    });
  });

  describe('info()', () => {
    it('should log info messages', () => {
      logger.info('Test info message');

      // In test/development mode, info logs should be visible
      expect(console.info).toHaveBeenCalledWith('[INFO] Test info message');
    });
  });

  describe('warn()', () => {
    it('should log warning messages', () => {
      logger.warn('Test warning message');
      expect(console.warn).toHaveBeenCalledWith('[WARN] Test warning message');
    });

    it('should work with additional arguments', () => {
      const context = { status: 404 };
      logger.warn('API warning', context);
      expect(console.warn).toHaveBeenCalledWith('[WARN] API warning', context);
    });
  });

  describe('error()', () => {
    it('should log error messages', () => {
      const error = new Error('Test error');
      logger.error('Test error message', error);

      // In test/development mode, errors should be logged to console
      expect(console.error).toHaveBeenCalledWith(
        '[ERROR] Test error message',
        error,
        undefined
      );
    });

    it('should work with context object', () => {
      const error = new Error('API failed');
      const context = { endpoint: '/api/test', status: 500 };
      logger.error('API error', error, context);

      // In test/development mode, errors should be logged with context
      expect(console.error).toHaveBeenCalledWith(
        '[ERROR] API error',
        error,
        context
      );
    });

    it('should log errors without throwing', () => {
      const message = 'Error with email test@example.com and password=secret123';

      // Should not throw
      expect(() => logger.error(message)).not.toThrow();

      // Should log to console in test mode
      expect(console.error).toHaveBeenCalled();
    });

    it('should report to error reporter if configured', () => {
      const errorReporter = vi.fn();
      logger.setErrorReporter(errorReporter);

      const error = new Error('Test error');
      const context = { foo: 'bar' };
      logger.error('Error message', error, context);

      expect(errorReporter).toHaveBeenCalledWith(error, {
        message: 'Error message',
        ...context,
      });
    });
  });

  describe('setErrorReporter()', () => {
    it('should set error reporter function', () => {
      const mockReporter = vi.fn();
      logger.setErrorReporter(mockReporter);

      const error = new Error('Test');
      logger.error('Test error', error);

      expect(mockReporter).toHaveBeenCalledWith(error, {
        message: 'Test error',
      });
    });
  });

  describe('sanitization', () => {
    it('should handle messages without sensitive data', () => {
      logger.error('Simple error message');
      expect(console.error).toHaveBeenCalled();
    });

    it('should handle null and undefined errors', () => {
      logger.error('Error without exception object');
      expect(console.error).toHaveBeenCalled();
    });
  });
});
