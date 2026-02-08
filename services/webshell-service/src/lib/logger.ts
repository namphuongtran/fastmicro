/**
 * Structured Logger for Browser/Client-Side
 *
 * Features:
 * - Log levels (debug, info, warn, error)
 * - Structured metadata
 * - Correlation ID support
 * - Console output with formatting
 * - Integration with observability (future: send to backend)
 */

import { clientEnv } from "@/config/env";

// ============================================================================
// Types
// ============================================================================

export type LogLevel = "debug" | "info" | "warn" | "error";

export interface LogContext {
  /** Correlation/trace ID for request tracing */
  correlationId?: string;
  /** User ID if authenticated */
  userId?: string;
  /** Current tenant ID */
  tenantId?: string;
  /** Component or module name */
  component?: string;
  /** Additional metadata */
  [key: string]: unknown;
}

export interface LogEntry {
  level: LogLevel;
  message: string;
  timestamp: string;
  context: LogContext;
  error?: {
    name: string;
    message: string;
    stack?: string;
  };
}

export interface LoggerConfig {
  /** Minimum log level to output */
  level: LogLevel;
  /** Whether to output to console */
  console: boolean;
  /** Whether to send logs to backend */
  remote: boolean;
  /** Remote endpoint for log shipping */
  remoteEndpoint?: string;
}

// ============================================================================
// Constants
// ============================================================================

const LOG_LEVEL_PRIORITY: Record<LogLevel, number> = {
  debug: 0,
  info: 1,
  warn: 2,
  error: 3,
};

const LOG_LEVEL_COLORS: Record<LogLevel, string> = {
  debug: "#9CA3AF", // gray
  info: "#3B82F6", // blue
  warn: "#F59E0B", // amber
  error: "#EF4444", // red
};

// ============================================================================
// Logger Class
// ============================================================================

export class Logger {
  private config: LoggerConfig;
  private defaultContext: LogContext;

  constructor(config: Partial<LoggerConfig> = {}, defaultContext: LogContext = {}) {
    this.config = {
      level: (clientEnv.NEXT_PUBLIC_LOG_LEVEL as LogLevel) || "info",
      console: true,
      remote: false,
      ...config,
    };
    this.defaultContext = defaultContext;
  }

  /**
   * Check if a log level should be output
   */
  private shouldLog(level: LogLevel): boolean {
    return LOG_LEVEL_PRIORITY[level] >= LOG_LEVEL_PRIORITY[this.config.level];
  }

  /**
   * Format and output a log entry
   */
  private log(level: LogLevel, message: string, context: LogContext = {}, error?: Error): void {
    if (!this.shouldLog(level)) {
      return;
    }

    const entry: LogEntry = {
      level,
      message,
      timestamp: new Date().toISOString(),
      context: { ...this.defaultContext, ...context },
    };

    if (error) {
      entry.error = {
        name: error.name,
        message: error.message,
        stack: error.stack,
      };
    }

    // Console output
    if (this.config.console) {
      this.outputToConsole(entry);
    }

    // Remote logging (future implementation)
    if (this.config.remote && this.config.remoteEndpoint) {
      this.sendToRemote(entry);
    }
  }

  /**
   * Output log entry to console with formatting
   */
  private outputToConsole(entry: LogEntry): void {
    const color = LOG_LEVEL_COLORS[entry.level];
    const timestamp = new Date(entry.timestamp).toLocaleTimeString();
    const prefix = `%c[${entry.level.toUpperCase()}]%c ${timestamp}`;
    const contextStr = Object.keys(entry.context).length > 0
      ? ` | ${JSON.stringify(entry.context)}`
      : "";

    const args: unknown[] = [
      `${prefix} ${entry.message}${contextStr}`,
      `color: ${color}; font-weight: bold`,
      "color: inherit",
    ];

    if (entry.error) {
      args.push("\n", entry.error);
    }

    switch (entry.level) {
      case "debug":
        console.debug(...args);
        break;
      case "info":
        console.info(...args);
        break;
      case "warn":
        console.warn(...args);
        break;
      case "error":
        console.error(...args);
        break;
    }
  }

  /**
   * Send log entry to remote endpoint
   */
  private async sendToRemote(entry: LogEntry): Promise<void> {
    if (!this.config.remoteEndpoint) return;

    try {
      // Use sendBeacon for reliability (doesn't block unload)
      if (typeof navigator !== "undefined" && navigator.sendBeacon) {
        navigator.sendBeacon(
          this.config.remoteEndpoint,
          JSON.stringify(entry)
        );
      } else {
        // Fallback to fetch
        await fetch(this.config.remoteEndpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(entry),
          keepalive: true,
        });
      }
    } catch {
      // Silently fail for remote logging
    }
  }

  /**
   * Debug level log
   */
  debug(message: string, context?: LogContext): void {
    this.log("debug", message, context);
  }

  /**
   * Info level log
   */
  info(message: string, context?: LogContext): void {
    this.log("info", message, context);
  }

  /**
   * Warning level log
   */
  warn(message: string, context?: LogContext): void {
    this.log("warn", message, context);
  }

  /**
   * Error level log
   */
  error(message: string, error?: Error | unknown, context?: LogContext): void {
    const errorObj = error instanceof Error ? error : undefined;
    this.log("error", message, context, errorObj);
  }

  /**
   * Create a child logger with additional context
   */
  child(context: LogContext): Logger {
    return new Logger(this.config, { ...this.defaultContext, ...context });
  }

  /**
   * Create a logger for a specific component
   */
  forComponent(component: string): Logger {
    return this.child({ component });
  }
}

// ============================================================================
// Default Logger Instance
// ============================================================================

/**
 * Default logger instance
 */
export const logger = new Logger();

/**
 * Create a logger for a specific component
 */
export function createLogger(component: string, context?: LogContext): Logger {
  return logger.forComponent(component).child(context ?? {});
}
