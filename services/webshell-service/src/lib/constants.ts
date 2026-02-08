/**
 * Application Constants
 *
 * Centralized constants for the application.
 */

// API Configuration
export const API_VERSION = "v1";
export const DEFAULT_PAGE_SIZE = 20;
export const MAX_PAGE_SIZE = 100;

// Cache TTL (in seconds)
export const CACHE_TTL_SHORT = 60;
export const CACHE_TTL_MEDIUM = 300;
export const CACHE_TTL_LONG = 3600;

// Timeout Configuration (in milliseconds)
export const DEFAULT_TIMEOUT = 30000;
export const LONG_TIMEOUT = 60000;

// Retry Configuration
export const DEFAULT_RETRIES = 3;
export const RETRY_DELAY = 1000;

// Date Formats
export const DATE_FORMAT = "yyyy-MM-dd";
export const DATETIME_FORMAT = "yyyy-MM-dd HH:mm:ss";
export const ISO_FORMAT = "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'";
