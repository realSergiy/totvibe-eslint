# @zyplux/tests-fixtures

Story-test fixtures for Node CLIs and libraries. Fakes swap in at the lowest boundary (`node:child_process`, `node:readline/promises`, `node:timers/promises`, `fetch`, `console`, `process.env`) so tests exercise only public interfaces.

## Install

```sh
pnpm add -D @zyplux/tests-fixtures
```

Each fake needs the Node module it stands in for mocked in that project's own vitest setup file — only the modules whose fakes you use:

```ts
import { vi } from 'vitest';

vi.mock('node:child_process', async importOriginal => {
  const actual = await importOriginal<typeof import('node:child_process')>();
  return { ...actual, spawn: vi.fn(actual.spawn) }; // shell fake
});
// node:readline/promises -> createInterface (prompt fake); node:timers/promises -> setTimeout (instant sleeps)
```

Each factory wraps the original, so the module stays fully live until a fake installs an implementation. A fake whose module is unmocked says which one to add.

## Use

Pick a base per app type, extend it with suite fixtures, and keep the binding named `test`:

```ts
import { cliTest } from '@zyplux/tests-fixtures/story';

export const test = cliTest;
export { describe, expect } from 'vitest';
```

```ts
import { describe, expect, test } from '#fixtures';

describe('1.1 pushing a branch', () => {
  test('1.1.1 pushes and reports the PR url', async ({ logs, shell }) => {
    shell.on('git rev-parse --abbrev-ref HEAD', 'feat-x');
    shell.on('git push', '');

    await runPushBranch({ command: 'push-branch', hold: false, ready: false });

    expect(shell).toHaveRun('git push --set-upstream origin feat-x');
    expect(logs).toHaveLogged('PR (draft): https://github.com/acme/repo/pull/1');
  });
});
```

## Entry points

There is no barrel — import each fixture from its own subpath: `/story` (`libraryTest`, `cliTest`, `makeFixture`), `/shell`, `/console`, `/fetch`, `/fs`, `/prompt`, `/cli`, `/matchers`.

## Bases

- `libraryTest` — lazy fixtures: `shell` (fake `node:child_process` spawn, installed only when destructured), `tempDir` (auto-removed scratch directory with `path`, `write`, `exists`).
- `cliTest` — extends `libraryTest`; auto-silences and captures `console` (`logs`), makes `node:timers/promises` sleeps instant; adds lazy `network` (fake `fetch`), `prompt` (fake `node:readline/promises` interface that accepts and records every question), and `env` (`set(name, value)` stubs an env var for the test).

## Fakes

- `createShellFake()` — routes commands (`on(pattern, ...replies)`, later routes win, the last reply repeats; `otherwise(reply)` sets a fallback, unrouted commands throw) and records `calls` (`{ argv, cwd?, env?, program, stdin? }`), `commands` (rendered strings), `commandsMatching(pattern)`.
- `createConsoleCapture()` — records `logLines`/`warnLines`/`errorLines`.
- `createFetchFake()` — routes urls (`on(prefixOrRegExp, reply)`, `otherwise(reply)`) and records `requests`; `okResponse()`/`notFoundResponse()` build replies.
- `createPromptFake()` — accepts every `question()` call and records `messages`.
- `createTempDir()` — `path`, `write(relativePath, content)`, `exists(relativePath)`, `remove()`.

## Matchers

Importing a base registers domain matchers via `expect.extend`:

- `expect(shell).toHaveRun(command)` — the exact rendered command ran.
- `expect(shell).toHaveRunMatching(pattern)` — some command matches (string = command prefix at a word boundary, same as `on`; RegExp = test); negate with `.not` for "never ran".
- `expect(logs).toHaveLogged(line?)` / `toHaveWarned(line?)` / `toHaveErrored(line?)` — a captured line equals the string (or matches the RegExp); with no argument, that the channel captured anything, so `.not.toHaveWarned()` asserts silence.
