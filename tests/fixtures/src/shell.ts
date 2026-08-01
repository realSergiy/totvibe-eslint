import type { $ } from '@zyplux/util';

import { run } from '@zyplux/util/exec';
import { vi } from 'vitest';

import { isPatternMatch } from './pattern-match.ts';

vi.mock('@zyplux/util/exec', async importOriginal => {
  const actual = await importOriginal<typeof import('@zyplux/util/exec')>();
  return { ...actual, run: vi.fn(actual.run) };
});

type ShellOutput = Awaited<ReturnType<typeof $.git.status>>;
type ShellPromise = ReturnType<typeof run>;

export const fakeShellOutput = (stdout: string, exitCode = 0): ShellOutput => ({
  exitCode,
  stderr: Buffer.alloc(0),
  stdout: Buffer.from(stdout),
  text: () => stdout,
});

type ShellPromiseHooks = {
  onCwd?: (dir: string) => void;
  onEnv?: (env: Record<string, string | undefined>) => void;
};

export const fakeShellPromise = (result: ShellOutput, { onCwd, onEnv }: ShellPromiseHooks = {}): ShellPromise => {
  const chainMethod = () => promise;
  const promise: ShellPromise = Object.assign(Promise.resolve(result), {
    cwd: (dir?: string) => {
      if (dir !== undefined) onCwd?.(dir);
      return promise;
    },
    env: (newEnv?: Record<string, string | undefined>) => {
      if (newEnv !== undefined) onEnv?.(newEnv);
      return promise;
    },
    nothrow: chainMethod,
    quiet: chainMethod,
    text: (encoding?: BufferEncoding) => Promise.resolve(result.text(encoding)),
  }) satisfies ShellPromise;
  return promise;
};

export type ShellCall = {
  argv: string[];
  cwd?: string;
  env?: Record<string, string | undefined>;
  program: string;
  stdin?: string;
};
export type ShellFake = {
  calls: ShellCall[];
  commands: string[];
  commandsMatching: (pattern: RegExp | string) => string[];
  install: () => () => void;
  on: (pattern: RegExp | string, ...replies: [ShellReply, ...ShellReply[]]) => void;
  otherwise: (...replies: [ShellReply, ...ShellReply[]]) => void;
};

export type ShellReply = ((command: string) => string) | string | { exitCode: number; stdout: string };

type ShellRoute = { pattern: RegExp | string; replies: ShellReply[] };

const isCommandMatch = (command: string, pattern: RegExp | string) => {
  if (typeof pattern === 'string') {
    if (!command.startsWith(pattern)) return false;
    return command.length === pattern.length || command[pattern.length] === ' ';
  }
  return isPatternMatch(command, pattern);
};

const takeReply = ({ replies }: ShellRoute) => {
  const reply = replies.length > 1 ? replies.shift() : replies[0];
  if (reply === undefined) throw new Error('shell route has no replies left');
  return reply;
};

export const createShellFake = (): ShellFake => {
  const calls: ShellCall[] = [];
  const commands: string[] = [];
  const routes: ShellRoute[] = [];
  let fallback: ShellRoute | undefined;

  const resolveReply = (command: string) => {
    const route = routes.findLast(candidate => isCommandMatch(command, candidate.pattern)) ?? fallback;
    if (route === undefined) {
      const registered = routes.map(known => `  ${String(known.pattern)}`).join('\n');
      throw new Error(`no shell route matches: ${command}\nregistered routes:\n${registered}`);
    }
    return takeReply(route);
  };

  return {
    calls,
    commands,
    commandsMatching: pattern => commands.filter(command => isCommandMatch(command, pattern)),
    install: () => {
      const runMock = vi.mocked(run);
      runMock.mockImplementation((argv, opts) => {
        const command = argv.join(' ');
        const [program = '', ...args] = argv;
        const call: ShellCall = {
          argv: args,
          program,
          ...(opts?.cwd !== undefined && { cwd: opts.cwd }),
          ...(opts?.env !== undefined && { env: opts.env }),
          ...(opts?.stdin !== undefined && { stdin: String(opts.stdin) }),
        };
        calls.push(call);
        commands.push(command);
        const reply = resolveReply(command);
        const resolved = typeof reply === 'function' ? reply(command) : reply;
        const output =
          typeof resolved === 'string'
            ? fakeShellOutput(resolved)
            : fakeShellOutput(resolved.stdout, resolved.exitCode);
        return fakeShellPromise(output, {
          onCwd: dir => {
            call.cwd = dir;
          },
          onEnv: env => {
            call.env = env;
          },
        });
      });
      return () => {
        runMock.mockReset();
      };
    },
    on: (pattern, ...replies) => {
      routes.push({ pattern, replies: [...replies] });
    },
    otherwise: (...replies) => {
      fallback = { pattern: '', replies: [...replies] };
    },
  };
};
