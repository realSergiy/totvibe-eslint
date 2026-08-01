import type { ESLint } from 'eslint';

import pkg from '#package.json' with { type: 'json' };

import { rules } from './rules/index.ts';

export const plugin: ESLint.Plugin = {
  meta: {
    name: '@zyplux/eslint-config',
    version: pkg.version,
  },
  rules,
};
