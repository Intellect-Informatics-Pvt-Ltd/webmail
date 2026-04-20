import { test, expect } from '@playwright/test';

test.describe('Inbox — Message List', () => {
  test('renders seeded messages in the inbox', async ({ page }) => {
    await page.goto('/');
    // Wait for the message list to load
    await page.waitForSelector('[data-testid="message-list"]', { timeout: 10_000 });

    // At least one message should be visible from demo seed data
    const rows = page.locator('[data-testid="message-row"]');
    await expect(rows.first()).toBeVisible();
    const count = await rows.count();
    expect(count).toBeGreaterThan(0);
  });

  test('opens a message and shows subject in reading pane', async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('[data-testid="message-row"]', { timeout: 10_000 });

    // Click the first message
    const firstRow = page.locator('[data-testid="message-row"]').first();
    const subject = await firstRow.locator('[data-testid="message-subject"]').textContent();
    await firstRow.click();

    // Reading pane should show the subject
    const pane = page.locator('[data-testid="reading-pane"]');
    await expect(pane).toBeVisible();
    if (subject) {
      await expect(pane).toContainText(subject);
    }
  });
});
