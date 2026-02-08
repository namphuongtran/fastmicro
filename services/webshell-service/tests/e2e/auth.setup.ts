/**
 * Playwright authentication setup
 * Performs login and saves authenticated state for reuse across tests
 */
import { test as setup, expect } from '@playwright/test';
import path from 'path';

const authFile = path.join(__dirname, '.auth/user.json');

setup('authenticate', async ({ page }) => {
  // Navigate to the login page
  await page.goto('/');

  // Check if we need to authenticate
  // If already on dashboard, skip authentication
  const url = page.url();
  if (url.includes('/dashboard')) {
    // Already authenticated, save current state
    await page.context().storageState({ path: authFile });
    return;
  }

  // Wait for redirect to identity service or login page
  // This will be customized based on your actual auth flow
  await page.waitForLoadState('networkidle');

  // If redirected to identity service login
  const currentUrl = page.url();

  if (currentUrl.includes('/auth/signin') || currentUrl.includes('/login')) {
    // Fill in test credentials
    // Note: In CI, these should come from environment variables
    const username = process.env.E2E_TEST_USERNAME || 'testuser@example.com';
    const password = process.env.E2E_TEST_PASSWORD || 'testpassword123';

    // Look for email/username field
    const emailInput = page.getByLabel(/email|username/i).first();
    if (await emailInput.isVisible()) {
      await emailInput.fill(username);
    }

    // Look for password field
    const passwordInput = page.getByLabel(/password/i).first();
    if (await passwordInput.isVisible()) {
      await passwordInput.fill(password);
    }

    // Click sign in button
    const signInButton = page.getByRole('button', { name: /sign in|log in|submit/i });
    if (await signInButton.isVisible()) {
      await signInButton.click();
    }

    // Wait for successful authentication
    await page.waitForURL('**/dashboard**', { timeout: 30000 });
  }

  // Verify we're now authenticated
  await expect(page).toHaveURL(/.*dashboard.*/);

  // Save authentication state
  await page.context().storageState({ path: authFile });
});
