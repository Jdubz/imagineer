/**
 * Centralized logging utility with environment-based levels
 * Provides consistent logging interface across the application
 */

type LogLevel = 'debug' | 'info' | 'warn' | 'error';

export interface LogEntry {
  level: LogLevel;
  message: string;
  args: unknown[];
  timestamp: string;
}

type LogListener = (entry: LogEntry) => void;

interface LoggerConfig {
  enabledLevels: Set<LogLevel>;
  enableConsole: boolean;
  errorReporter?: (error: Error, context?: Record<string, unknown>) => void;
}

class Logger {
  private config: LoggerConfig;
  private listeners: Set<LogListener> = new Set();

  constructor() {
    // Configure based on environment
    const mode = import.meta.env.MODE;
    const isDevelopment = mode === 'development' || mode === 'test';

    this.config = {
      // In production, only show warnings and errors
      enabledLevels: new Set(
        isDevelopment
          ? ['debug', 'info', 'warn', 'error']
          : ['warn', 'error']
      ),
      // Disable console in production only
      enableConsole: isDevelopment,
      // Error reporter will be set up later (Sentry, LogRocket, etc.)
      errorReporter: undefined,
    };
  }

  /**
   * Set error reporting service (e.g., Sentry)
   */
  setErrorReporter(reporter: (error: Error, context?: Record<string, unknown>) => void): void {
    this.config.errorReporter = reporter;
  }

  /**
   * Subscribe to log events (used by diagnostics collectors).
   */
  addListener(listener: LogListener): () => void {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  }

  /**
   * Debug logging - for detailed diagnostic information
   * Only visible in development
   */
  debug(message: string, ...args: unknown[]): void {
    if (this.shouldLog('debug')) {
      console.log(`[DEBUG] ${message}`, ...args);
      this.emit('debug', message, args);
    }
  }

  /**
   * Info logging - for general informational messages
   * Only visible in development
   */
  info(message: string, ...args: unknown[]): void {
    if (this.shouldLog('info')) {
      console.info(`[INFO] ${message}`, ...args);
      this.emit('info', message, args);
    }
  }

  /**
   * Warning logging - for potentially harmful situations
   * Visible in both development and production
   */
  warn(message: string, ...args: unknown[]): void {
    if (this.shouldLog('warn')) {
      console.warn(`[WARN] ${message}`, ...args);
      this.emit('warn', message, args);
    }
  }

  /**
   * Error logging - for error conditions
   * Visible in both development and production
   * Automatically reports to error tracking service if configured
   */
  error(message: string, error?: unknown, context?: Record<string, unknown>): void {
    if (this.shouldLog('error')) {
      // Sanitize error message for production
      const sanitizedMessage = this.sanitizeErrorMessage(message);

      if (this.config.enableConsole) {
        console.error(`[ERROR] ${sanitizedMessage}`, error, context);
      }

      // Report to error tracking service
      if (this.config.errorReporter && error instanceof Error) {
        this.config.errorReporter(error, {
          message: sanitizedMessage,
          ...context,
        });
      }

      this.emit('error', sanitizedMessage, [error, context]);
    }
  }

  /**
   * Check if a log level should be output
   */
  private shouldLog(level: LogLevel): boolean {
    return this.config.enabledLevels.has(level);
  }

  /**
   * Sanitize error messages to avoid leaking sensitive information
   * in production builds
   */
  private sanitizeErrorMessage(message: string): string {
    if (import.meta.env.MODE === 'production') {
      // Remove potential sensitive data patterns
      return message
        .replace(/\b\d{3}-\d{2}-\d{4}\b/g, '[SSN]') // SSN
        .replace(/\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/g, '[EMAIL]') // Email
        .replace(/\b(?:\d{4}[ -]?){3}\d{4}\b/g, '[CARD]') // Credit card
        .replace(/Bearer\s+[\w-_.]+/gi, 'Bearer [TOKEN]') // Bearer tokens
        .replace(/password["\s:=]+[\w!@#$%^&*()]+/gi, 'password=[REDACTED]'); // Passwords
    }
    return message;
  }

  private emit(level: LogLevel, message: string, args: unknown[]): void {
    if (this.listeners.size === 0) {
      return;
    }

    const entry: LogEntry = {
      level,
      message,
      args,
      timestamp: new Date().toISOString(),
    };

    for (const listener of this.listeners) {
      try {
        listener(entry);
      } catch (err) {
        if (this.config.enableConsole) {
          console.error('[ERROR] Logger listener failed', err);
        }
      }
    }
  }
}

// Export singleton instance
export const logger = new Logger();

// Export type for testing
export type { LogLevel, LoggerConfig };
