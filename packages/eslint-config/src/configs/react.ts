import eslintReact from '@eslint-react/eslint-plugin';

import type { ConfigWithExtends } from './types.ts';

export type ReactRenderer = 'dom' | 'ink' | 'opentui' | 'r3f' | 'react-pdf';

export type RendererGlobs = Partial<Record<ReactRenderer, string[]>>;

const reactRenderers: ReactRenderer[] = ['dom', 'ink', 'opentui', 'r3f', 'react-pdf'];

const domRule = '@eslint-react/dom-no-unknown-property';
const strictTypeScript = eslintReact.configs['strict-typescript'];
const reactStrict = {
  plugins: strictTypeScript.plugins ?? {},
  rules: strictTypeScript.rules ?? {},
};

const reactBase = (files: string[], version: string) =>
  ({
    extends: [reactStrict],
    files,
    rules: { [domRule]: 'error' },
    settings: { 'react-x': { version } },
  }) satisfies ConfigWithExtends;

export const reactPresets = (renderers: RendererGlobs, version: string): ConfigWithExtends[] =>
  reactRenderers.flatMap(renderer => {
    const files = renderers[renderer];
    if (files === undefined || files.length === 0) return [];
    const blocks: ConfigWithExtends[] = [reactBase(files, version)];
    if (renderer !== 'dom') {
      blocks.push({ extends: [eslintReact.configs['disable-dom']], files, rules: { [domRule]: 'off' } });
    }
    return blocks;
  });
