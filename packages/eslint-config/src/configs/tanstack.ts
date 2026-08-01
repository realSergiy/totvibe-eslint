import type { ConfigWithExtends } from './types.ts';

export const tanstackRoutes: ConfigWithExtends = {
  files: ['**/routes/**/*.{ts,tsx}'],
  rules: {
    'unicorn/filename-case': [
      'error',
      {
        case: 'kebabCase',
        ignore: [/^\$[a-z][\dA-Za-z]*\.tsx?$/],
      },
    ],
  },
};
