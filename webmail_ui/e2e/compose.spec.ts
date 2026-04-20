import { test, expect } from '@playwright/test';

test.describe('Compose — Send Message', () => {
  test('composes and sends a message', async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('[data-testid="message-list"]', { timeout: 10_000 });

    // Open compose
    const composeBtn = page.locator('[data-testid="compose-button"]');
    await composeBtn.click();

    // Fill in recipient, subject, body
    const toField = page.locator('[data-testid="compose-to"]');
    await toField.fill('test@example.com');
    await page.locator('[data-testid="compose-subject"]').fill('E2E Test Subject');
    await page.locator('[data-testid="compose-body"]').fill('This is an E2E test message.');

    // Send
    await page.locator('[data-testid="compose-send"]').click();

    // Navigate to Sent folder and verify
    await page.locator('[data-testid="folder-sent"]').click();
    await page.waitForSelector('[data-testid="message-row"]', { timeout: 10_000 });
    await expect(page.locator('text=E2E Test Subject')).toBeVisible();
  });
});
