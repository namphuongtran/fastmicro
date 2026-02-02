/**
 * Debounce Hook
 *
 * Custom hook that debounces a value, delaying updates until after
 * the specified delay has passed without changes.
 */
import { useState, useEffect } from "react";

/**
 * Returns a debounced version of the provided value.
 *
 * @param value - The value to debounce
 * @param delay - The delay in milliseconds (default: 300ms)
 * @returns The debounced value
 *
 * @example
 * ```tsx
 * const [searchTerm, setSearchTerm] = useState("");
 * const debouncedSearch = useDebounce(searchTerm, 500);
 *
 * useEffect(() => {
 *   // This will only run 500ms after the user stops typing
 *   fetchResults(debouncedSearch);
 * }, [debouncedSearch]);
 * ```
 */
export function useDebounce<T>(value: T, delay: number = 300): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    // Set up a timer to update the debounced value after delay
    const timer = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    // Clean up the timer if value changes before delay completes
    return () => {
      clearTimeout(timer);
    };
  }, [value, delay]);

  return debouncedValue;
}

/**
 * Returns a debounced callback function.
 *
 * @param callback - The callback to debounce
 * @param delay - The delay in milliseconds (default: 300ms)
 * @returns A debounced version of the callback
 *
 * @example
 * ```tsx
 * const debouncedSave = useDebouncedCallback(
 *   (value: string) => saveToServer(value),
 *   500
 * );
 *
 * // Call debouncedSave whenever input changes
 * <input onChange={(e) => debouncedSave(e.target.value)} />
 * ```
 */
export function useDebouncedCallback<T extends (...args: Parameters<T>) => void>(
  callback: T,
  delay: number = 300
): T {
  const [timeoutId, setTimeoutId] = useState<NodeJS.Timeout | null>(null);

  useEffect(() => {
    return () => {
      if (timeoutId) {
        clearTimeout(timeoutId);
      }
    };
  }, [timeoutId]);

  const debouncedCallback = ((...args: Parameters<T>) => {
    if (timeoutId) {
      clearTimeout(timeoutId);
    }

    const newTimeoutId = setTimeout(() => {
      callback(...args);
    }, delay);

    setTimeoutId(newTimeoutId);
  }) as T;

  return debouncedCallback;
}
