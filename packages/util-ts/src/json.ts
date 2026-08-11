import type { ZodType } from 'zod';

import { readFileSync } from 'node:fs';
import { readFile } from 'node:fs/promises';

import { attempt } from './result.ts';

export const parseJson = <T>(text: string, schema: ZodType<T>) => schema.parse(JSON.parse(text));

export const readJson = async <T>(path: string | URL, schema: ZodType<T>) =>
  parseJson(await readFile(path, 'utf8'), schema);

export const readJsonSync = <T>(path: string | URL, schema: ZodType<T>) =>
  parseJson(readFileSync(path, 'utf8'), schema);

export const tryParseJson = <T>(text: string, schema: ZodType<T>): T | undefined => {
  const result = attempt(() => parseJson(text, schema));
  return result.ok ? result.data : undefined;
};
