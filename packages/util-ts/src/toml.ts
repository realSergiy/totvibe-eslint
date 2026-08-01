import type { ZodType } from 'zod';

import { parse } from 'smol-toml';

import { attempt } from './result.ts';

export const parseToml = <T>(text: string, schema: ZodType<T>) => schema.parse(parse(text));

export const tryParseToml = <T>(text: string, schema: ZodType<T>): T | undefined => {
  const result = attempt(() => parseToml(text, schema));
  return result.ok ? result.data : undefined;
};
