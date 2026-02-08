/**
 * Error Handling Utilities
 *
 * Provides standardized error handling for the application:
 * - Error normalization
 * - User-friendly error messages
 * - Error boundary utilities
 * - Toast/notification helpers
 */

import { isApiError, type ApiError } from "./api-client";

// ============================================================================
// Types
// ============================================================================

export interface AppError {
  /** Unique error code for programmatic handling */
  code: string;
  /** User-friendly error message */
  message: string;
  /** Technical details for debugging */
  details?: string;
  /** HTTP status code if applicable */
  status?: number;
  /** Original error for debugging */
  cause?: Error;
  /** Whether this error is recoverable */
  recoverable: boolean;
  /** Suggested action for the user */
  action?: string;
}

export type ErrorCode =
  | "NETWORK_ERROR"
  | "TIMEOUT_ERROR"
  | "AUTH_ERROR"
  | "FORBIDDEN"
  | "NOT_FOUND"
  | "VALIDATION_ERROR"
  | "CONFLICT"
  | "RATE_LIMITED"
  | "SERVER_ERROR"
  | "UNKNOWN_ERROR";

// ============================================================================
// Error Code Mappings
// ============================================================================

const ERROR_MESSAGES: Record<ErrorCode, { message: string; action?: string; recoverable: boolean }> = {
  NETWORK_ERROR: {
    message: "Unable to connect to the server. Please check your internet connection.",
    action: "Try again",
    recoverable: true,
  },
  TIMEOUT_ERROR: {
    message: "The request took too long to complete. Please try again.",
    action: "Retry",
    recoverable: true,
  },
  AUTH_ERROR: {
    message: "Your session has expired. Please sign in again.",
    action: "Sign in",
    recoverable: true,
  },
  FORBIDDEN: {
    message: "You don't have permission to perform this action.",
    recoverable: false,
  },
  NOT_FOUND: {
    message: "The requested resource was not found.",
    recoverable: false,
  },
  VALIDATION_ERROR: {
    message: "The provided data is invalid. Please check your input.",
    recoverable: true,
  },
  CONFLICT: {
    message: "This action conflicts with existing data. Please refresh and try again.",
    action: "Refresh",
    recoverable: true,
  },
  RATE_LIMITED: {
    message: "Too many requests. Please wait a moment and try again.",
    action: "Wait and retry",
    recoverable: true,
  },
  SERVER_ERROR: {
    message: "Something went wrong on our end. We're working to fix it.",
    action: "Try again later",
    recoverable: true,
  },
  UNKNOWN_ERROR: {
    message: "An unexpected error occurred. Please try again.",
    action: "Try again",
    recoverable: true,
  },
};

// ============================================================================
// Error Normalization
// ============================================================================

/**
 * Get error code from HTTP status
 */
function getErrorCodeFromStatus(status: number): ErrorCode {
  switch (status) {
    case 401:
      return "AUTH_ERROR";
    case 403:
      return "FORBIDDEN";
    case 404:
      return "NOT_FOUND";
    case 409:
      return "CONFLICT";
    case 422:
      return "VALIDATION_ERROR";
    case 429:
      return "RATE_LIMITED";
    default:
      if (status >= 500) return "SERVER_ERROR";
      return "UNKNOWN_ERROR";
  }
}

/**
 * Extract error message from API response data
 */
function extractApiErrorMessage(data: unknown): string | undefined {
  if (!data || typeof data !== "object") return undefined;

  const obj = data as Record<string, unknown>;

  // Common API error response formats
  if (typeof obj.message === "string") return obj.message;
  if (typeof obj.error === "string") return obj.error;
  if (typeof obj.detail === "string") return obj.detail;
  if (Array.isArray(obj.errors) && obj.errors.length > 0) {
    const firstError = obj.errors[0];
    if (typeof firstError === "string") return firstError;
    if (typeof firstError === "object" && firstError !== null) {
      const errObj = firstError as Record<string, unknown>;
      return (errObj.message ?? errObj.msg) as string | undefined;
    }
  }

  return undefined;
}

/**
 * Normalize any error into an AppError
 */
export function normalizeError(error: unknown): AppError {
  // Handle API errors
  if (isApiError(error)) {
    const apiError = error as ApiError;

    // Network/timeout errors
    if (apiError.isNetworkError) {
      return {
        code: "NETWORK_ERROR",
        ...ERROR_MESSAGES.NETWORK_ERROR,
        details: apiError.message,
        cause: apiError,
      };
    }

    if (apiError.isTimeoutError) {
      return {
        code: "TIMEOUT_ERROR",
        ...ERROR_MESSAGES.TIMEOUT_ERROR,
        details: apiError.message,
        cause: apiError,
      };
    }

    // HTTP status-based errors
    const errorCode = getErrorCodeFromStatus(apiError.status);
    const defaultConfig = ERROR_MESSAGES[errorCode];
    const apiMessage = extractApiErrorMessage(apiError.data);

    return {
      code: errorCode,
      message: apiMessage ?? defaultConfig.message,
      action: defaultConfig.action,
      recoverable: defaultConfig.recoverable,
      status: apiError.status,
      details: apiError.message,
      cause: apiError,
    };
  }

  // Handle standard errors
  if (error instanceof Error) {
    return {
      code: "UNKNOWN_ERROR",
      message: ERROR_MESSAGES.UNKNOWN_ERROR.message,
      action: ERROR_MESSAGES.UNKNOWN_ERROR.action,
      recoverable: ERROR_MESSAGES.UNKNOWN_ERROR.recoverable,
      details: error.message,
      cause: error,
    };
  }

  // Handle string errors
  if (typeof error === "string") {
    return {
      code: "UNKNOWN_ERROR",
      message: error,
      recoverable: true,
    };
  }

  // Unknown error type
  return {
    code: "UNKNOWN_ERROR",
    ...ERROR_MESSAGES.UNKNOWN_ERROR,
  };
}

/**
 * Type guard for AppError
 */
export function isAppError(error: unknown): error is AppError {
  return (
    error !== null &&
    typeof error === "object" &&
    "code" in error &&
    "message" in error &&
    "recoverable" in error
  );
}

// ============================================================================
// Error Handling Utilities
// ============================================================================

/**
 * Handle error and return user-friendly message
 */
export function getErrorMessage(error: unknown): string {
  const normalized = normalizeError(error);
  return normalized.message;
}

/**
 * Check if error is recoverable (user can retry)
 */
export function isRecoverableError(error: unknown): boolean {
  const normalized = normalizeError(error);
  return normalized.recoverable;
}

/**
 * Check if error requires authentication
 */
export function isAuthError(error: unknown): boolean {
  if (isApiError(error)) {
    return error.status === 401;
  }
  if (isAppError(error)) {
    return error.code === "AUTH_ERROR";
  }
  return false;
}

/**
 * Create a custom app error
 */
export function createAppError(
  code: ErrorCode,
  message?: string,
  options?: Partial<Omit<AppError, "code" | "message">>
): AppError {
  const defaultConfig = ERROR_MESSAGES[code];
  return {
    code,
    message: message ?? defaultConfig.message,
    action: options?.action ?? defaultConfig.action,
    recoverable: options?.recoverable ?? defaultConfig.recoverable,
    ...options,
  };
}

// ============================================================================
// Error Boundary Utilities
// ============================================================================

/**
 * Error info for error boundaries
 */
export interface ErrorBoundaryInfo {
  error: AppError;
  componentStack?: string;
}

/**
 * Process error for error boundary display
 */
export function processErrorBoundaryError(
  error: Error,
  errorInfo?: { componentStack?: string }
): ErrorBoundaryInfo {
  return {
    error: normalizeError(error),
    componentStack: errorInfo?.componentStack,
  };
}
