/**
 * Lib barrel export
 *
 * Consolidated library utilities and services.
 * Following Next.js convention of using a single 'lib/' directory.
 */

// Utils
export { cn } from './utils';

// Auth
export { auth, handlers, signIn, signOut, authConfig, authOptions } from './auth';

// API Client
export {
  ApiClient,
  apiClient,
  createApiClient,
  isApiError,
  type ApiClientConfig,
  type RequestConfig,
  type ApiResponse,
  type ApiError,
} from './api-client';

// Logger
export {
  Logger,
  logger,
  createLogger,
  type LogLevel,
  type LogContext,
  type LogEntry,
  type LoggerConfig,
} from './logger';

// Error Handling
export {
  normalizeError,
  isAppError,
  getErrorMessage,
  isRecoverableError,
  isAuthError,
  createAppError,
  processErrorBoundaryError,
  type AppError,
  type ErrorCode,
  type ErrorBoundaryInfo,
} from './error-handling';

// Constants
export * from './constants';
