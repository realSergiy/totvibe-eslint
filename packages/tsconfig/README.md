# @zyplux/tsconfig

TypeScript presets for solution-style monorepos.

```jsonc
{ "extends": "@zyplux/tsconfig/node.json", "include": ["src"] }
```

`node`, `bun`, `cfworker`, `web`, and `tui` are composite and emit declarations only to `.tsbuild/` for `tsc -b`.

Publishable Node packages use a separate build config:

```jsonc
{ "extends": "@zyplux/tsconfig/node-pub.json", "include": ["src"] }
```

`node-pub` emits installable JavaScript and declarations to `dist/`.
