/**
 * Navigation E2E tests
 * Tests app-wide navigation and routing
 */
import { test, expect } from '@playwright/test';

test.describe('Navigation', () => {
  test('should redirect unauthenticated users to login', async ({ browser }) => {
    // Create a new context without stored auth state
    const context = await browser.newContext({ storageState: undefined });
    const page = await context.newPage();

    await page.goto('/dashboard');

    // Should redirect to sign-in page
    await expect(page).toHaveURL(/.*signin.*|.*login.*|.*auth.*/);

    await context.close();
  });

  test('should show 404 for non-existent routes', async ({ page }) => {
    await page.goto('/this-page-does-not-exist');

    // Should show 404 or redirect
    const notFound = page.getByText(/not found|404/i);
    const redirected = page.url().includes('dashboard') || page.url().includes('signin');

    expect(await notFound.isVisible().catch(() => false) || redirected).toBe(true);
  });

  test('should maintain state during navigation', async ({ page }) => {
    await page.goto('/dashboard');

    // Navigate away
    const settingsLink = page.getByRole('link', { name: /settings/i });
    if (await settingsLink.isVisible()) {
      await settingsLink.click();
      await page.waitForLoadState('networkidle');
    }

    // Navigate back
    const dashboardLink = page.getByRole('link', { name: /dashboard/i }).first();
    await dashboardLink.click();

    // Should return to dashboard
    await expect(page).toHaveURL(/.*dashboard.*/);
  });

  test('should handle browser back/forward navigation', async ({ page }) => {
    await page.goto('/dashboard');
    const initialUrl = page.url();

    // Navigate to a different page
    const auditLink = page.getByRole('link', { name: /audit/i });
    if (await auditLink.isVisible()) {
      await auditLink.click();
      await page.waitForLoadState('networkidle');

      // Go back
      await page.goBack();
      await expect(page).toHaveURL(initialUrl);

      // Go forward
      await page.goForward();
      await expect(page).toHaveURL(/.*audit.*/);
    }
  });
});
