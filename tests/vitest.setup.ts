import { vi } from 'vitest';

vi.mock('node:child_process', async importOriginal => {
  const actual = await importOriginal<typeof import('node:child_process')>();
  return { ...actual, spawn: vi.fn(actual.spawn) };
});

vi.mock('node:readline/promises', async importOriginal => {
  const actual = await importOriginal<typeof import('node:readline/promises')>();
  return { ...actual, createInterface: vi.fn(actual.createInterface) };
});

vi.mock('node:timers/promises', async importOriginal => {
  const actual = await importOriginal<typeof import('node:timers/promises')>();
  return { ...actual, setTimeout: vi.fn(actual.setTimeout) };
});
