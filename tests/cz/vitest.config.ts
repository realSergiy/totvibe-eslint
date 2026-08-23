import { defineProject } from 'vitest/config';

export default defineProject({
  test: {
    setupFiles: ['../vitest.setup.ts'],
    testTimeout: 90_000,
  },
});
