/// <reference types="vitest/config" />
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  test: {
    // Environment
    environment: 'jsdom',
    globals: true,

    // Setup files
    setupFiles: ['./tests/unit/setup-minimal.ts'],

    // Test file patterns
    include: ['tests/unit/**/*.{test,spec}.{ts,tsx}'],
    exclude: ['**/node_modules/**', '**/dist/**', 'tests/e2e/**', 'tests/integration/**'],

    // Coverage configuration
    coverage: {
      provider: 'v8',
      enabled: false, // Enable with --coverage flag
      reporter: ['text', 'json', 'html', 'lcov'],
      reportsDirectory: './coverage',
      include: ['src/**/*.{ts,tsx}'],
      exclude: [
        'src/**/*.d.ts',
        'src/**/*.test.{ts,tsx}',
        'src/**/*.spec.{ts,tsx}',
        'src/types/**',
        'src/app/**/layout.tsx',
        'src/app/**/loading.tsx',
        'src/app/**/error.tsx',
        'src/app/**/not-found.tsx',
      ],
      thresholds: {
        lines: 60, // Start with lower threshold, increase as coverage grows
        functions: 60,
        branches: 60,
        statements: 60,
      },
    },

    // Reporter configuration
    reporters: ['default'],

    // Timeouts
    testTimeout: 10000,
    hookTimeout: 10000,

    // Mock behavior
    clearMocks: true,
    restoreMocks: true,
    mockReset: true,

    // Snapshot
    snapshotFormat: {
      escapeString: true,
      printBasicPrototype: true,
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
});
