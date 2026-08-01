import vitest from '@vitest/eslint-plugin';

import type { ConfigWithExtends } from './types.ts';

export const vitestConfig = {
  extends: [vitest.configs.recommended],
  files: ['**/*.{test,spec}.{ts,tsx}'],
  rules: {
    'vitest/expect-expect': ['error', { assertFunctionNames: ['expect', 'expect*'] }],
  },
} satisfies ConfigWithExtends;

export const testHarnessMocksConfig = {
  files: ['tests/**/src/**/*.{ts,tsx}', 'tests/**/fixtures/**/*.{ts,tsx}'],
  rules: {
    'unicorn/no-top-level-side-effects': 'off',
  },
} satisfies ConfigWithExtends;
