import { setTimeout as sleep } from 'node:timers/promises';
import { test as base, vi } from 'vitest';

import type { ConsoleCapture } from './console.ts';
import type { FetchFake } from './fetch.ts';
import type { TempDir } from './fs.ts';
import type { PromptFake } from './prompt.ts';
import type { ShellFake } from './shell.ts';

import './matchers.ts';
import { createConsoleCapture } from './console.ts';
import { createFetchFake } from './fetch.ts';
import { createTempDir } from './fs.ts';
import { createPromptFake } from './prompt.ts';
import { requireMockedModule } from './require-mocked-module.ts';
import { createShellFake } from './shell.ts';

export type EnvStub = {
  set: (name: string, value: string) => void;
};

export const makeFixture =
  <Subject>(subject: Subject) =>
  async ({}: object, use: (subject: Subject) => Promise<void>) => {
    await use(subject);
  };

export type LibraryFixtures = {
  shell: ShellFake;
  tempDir: TempDir;
};

export const libraryTest = base.extend<LibraryFixtures>({
  shell: async ({}, use) => {
    const shell = createShellFake();
    const restore = shell.install();
    try {
      await use(shell);
    } finally {
      restore();
    }
  },
  tempDir: async ({}, use) => {
    const tempDir = await createTempDir();
    try {
      await use(tempDir);
    } finally {
      await tempDir.remove();
    }
  },
});

export type CliFixtures = {
  env: EnvStub;
  instantSleep: undefined;
  logs: ConsoleCapture;
  network: FetchFake;
  prompt: PromptFake;
};

export const cliTest = libraryTest.extend<CliFixtures>({
  env: async ({}, use) => {
    try {
      await use({
        set: (name, value) => {
          vi.stubEnv(name, value);
        },
      });
    } finally {
      vi.unstubAllEnvs();
    }
  },
  instantSleep: [
    async ({}, use) => {
      requireMockedModule(sleep, 'node:timers/promises', 'setTimeout');
      vi.mocked(sleep).mockResolvedValue(undefined);
      try {
        await use(undefined);
      } finally {
        vi.mocked(sleep).mockReset();
      }
    },
    { auto: true },
  ],
  logs: [
    async ({}, use) => {
      const logs = createConsoleCapture();
      const restore = logs.install();
      try {
        await use(logs);
      } finally {
        restore();
      }
    },
    { auto: true },
  ],
  network: [
    async ({}, use) => {
      const network = createFetchFake();
      const restore = network.install();
      try {
        await use(network);
      } finally {
        restore();
      }
    },
    { auto: true },
  ],
  prompt: async ({}, use) => {
    const prompt = createPromptFake();
    const restore = prompt.install();
    try {
      await use(prompt);
    } finally {
      restore();
    }
  },
});
