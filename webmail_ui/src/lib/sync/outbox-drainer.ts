/**
 * PSense Mail — OutboxDrainer class.
 *
 * Instantiated once in __root.tsx. Manages the lifecycle of the outbox
 * drain worker, handling online/offline transitions and providing
 * status information to the UI.
 *
 * @see outbox.ts for the low-level drain implementation.
 */

import { attachOutboxDrainer, drainOutbox, outboxPendingCount } from "@/lib/sync/outbox";

export class OutboxDrainer {
  private _teardown: (() => void) | null = null;
  private _accountId: string;

  constructor(accountId: string) {
    this._accountId = accountId;
  }

  /** Start the drainer — attach event listeners and begin initial drain. */
  start(): void {
    if (this._teardown) return; // already running
    this._teardown = attachOutboxDrainer(this._accountId);
  }

  /** Stop the drainer — remove event listeners and timers. */
  stop(): void {
    if (this._teardown) {
      this._teardown();
      this._teardown = null;
    }
  }

  /** Trigger an immediate drain (e.g., when a new item is queued). */
  async drain(): Promise<void> {
    await drainOutbox(this._accountId);
  }

  /** Get the count of pending outbox items. */
  async pendingCount(): Promise<number> {
    return outboxPendingCount(this._accountId);
  }
}
