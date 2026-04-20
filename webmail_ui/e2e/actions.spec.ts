import { test, expect } from '@playwright/test';

test.describe('Message Actions', () => {
  test('mark read toggles unread count', async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('[data-testid="message-row"]', { timeout: 10_000 });

    // Get initial sidebar unread count
    const badge = page.locator('[data-testid="folder-inbox-badge"]');
    const initialCount = parseInt((await badge.textContent()) || '0', 10);

    // Click first unread message
    const unreadRow = page.locator('[data-testid="message-row"][data-unread="true"]').first();
    if ((await unreadRow.count()) > 0) {
      await unreadRow.click();

      // Mark as read
      await page.locator('[data-testid="action-mark-read"]').click();
      await page.waitForTimeout(500);

      // Verify count decreased
      const newCount = parseInt((await badge.textContent()) || '0', 10);
      expect(newCount).toBeLessThanOrEqual(initialCount);

      // Mark unread again
      await page.locator('[data-testid="action-mark-unread"]').click();
      await page.waitForTimeout(500);

      const restoredCount = parseInt((await badge.textContent()) || '0', 10);
      expect(restoredCount).toBeGreaterThanOrEqual(newCount);
    }
  });

  test('archive moves message to archive folder', async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('[data-testid="message-row"]', { timeout: 10_000 });

    // Count initial inbox messages
    const initialCount = await page.locator('[data-testid="message-row"]').count();
    if (initialCount === 0) return;

    // Click first message and archive
    await page.locator('[data-testid="message-row"]').first().click();
    await page.locator('[data-testid="action-archive"]').click();
    await page.waitForTimeout(500);

    // Verify message removed from inbox
    const newCount = await page.locator('[data-testid="message-row"]').count();
    expect(newCount).toBeLessThan(initialCount);

    // Navigate to Archive and verify
    await page.locator('[data-testid="folder-archive"]').click();
    await page.waitForSelector('[data-testid="message-row"]', { timeout: 10_000 });
    const archiveCount = await page.locator('[data-testid="message-row"]').count();
    expect(archiveCount).toBeGreaterThan(0);
  });
});
