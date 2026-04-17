/**
 * Vitest global test setup.
 *
 * Runs before every test file.
 */

import "@testing-library/jest-dom";

// Polyfill crypto.randomUUID for jsdom
if (typeof globalThis.crypto === "undefined" || !globalThis.crypto.randomUUID) {
  Object.defineProperty(globalThis, "crypto", {
    value: {
      randomUUID: () => "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
        const r = (Math.random() * 16) | 0;
        return (c === "x" ? r : (r & 0x3) | 0x8).toString(16);
      }),
      getRandomValues: (arr: Uint8Array) => {
        for (let i = 0; i < arr.length; i++) arr[i] = Math.floor(Math.random() * 256);
        return arr;
      },
    },
    configurable: true,
  });
}

// Silence console.error for expected React warnings in tests
// (Remove this if you want to see them during debugging)
const _consoleError = console.error;
beforeAll(() => {
  console.error = (...args: unknown[]) => {
    if (typeof args[0] === "string" && args[0].includes("Warning:")) return;
    _consoleError(...args);
  };
});
afterAll(() => {
  console.error = _consoleError;
});
