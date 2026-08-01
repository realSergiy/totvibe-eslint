# @zyplux/tsconfig

Shared TypeScript configs for the zyplux org. Project-reference ready — `composite`, emitting `.js` + `.d.ts` to `dist/`, run with `tsc -b`.

## Use

`tsconfig.json`:

```jsonc
{ "extends": "@zyplux/tsconfig/node.json", "include": ["src"] }
```

Variants, all extending `base`:

| Variant | Environment                          |
| ------- | ------------------------------------ |
| `node`  | Node                                 |
| `bun`   | Bun                                  |
| `web`   | browser + React DOM                  |
| `tui`   | terminal React (`@opentui/react`)    |
| `iso`   | none — isomorphic, no env globals    |

`base` is abstract; extend a variant, not `base`. Add `dist/` to `.gitignore`.
