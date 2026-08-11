import type { ExecPromise } from './exec.ts';

import { run } from './exec.ts';

type ShArg = (number | string)[] | number | string | undefined;

const sh = (strings: TemplateStringsArray, ...values: ShArg[]) => {
  const argv: string[] = [];
  for (const [index, chunk] of strings.entries()) {
    for (const token of chunk.split(/\s+/)) {
      if (token.length > 0) argv.push(token);
    }
    if (index >= values.length) continue;
    const value = values[index];
    if (Array.isArray(value)) {
      for (const item of value) argv.push(String(item));
    } else if (value !== undefined) {
      argv.push(String(value));
    }
  }
  return run(argv);
};

type ApiFlags = { input?: string; jq?: string; method?: string; paginate?: boolean };

type BranchFlags = { delete?: boolean; force?: boolean };

type CleanFlags = { dryRun?: boolean; protect?: string[] };

type CloneFlags = { branch?: string; depth?: number; singleBranch?: boolean };

type CommandOutput = Awaited<ExecPromise>;

type FlagValue = boolean | number | string | undefined;

type PrCreateFlags = { base: string; body: string; draft?: boolean; title: string };

type PrListFlags = { head?: string; jq?: string; json?: string; state?: string };

type PrMergeFlags = { auto?: boolean; deleteBranch?: boolean; squash?: boolean };

type PrReadyFlags = { undo?: boolean };

type PrViewFlags = { jq?: string; json?: string };

type PullFlags = { ffOnly?: boolean };

type PushFlags = { setUpstream?: boolean };

type ReleaseCreateFlags = { generateNotes?: boolean; target?: string; title?: string };

type ReleaseDeleteFlags = { cleanupTag?: boolean; yes?: boolean };

type ReleaseListFlags = { jq?: string; json?: string };

type RepoViewFlags = { jq?: string; json?: string };

type RevParseFlags = { abbrevRef?: boolean };

type RunListFlags = { event?: string; jq?: string; json?: string; workflow?: string };

type RunViewFlags = { jq?: string; json?: string };

type StatusFlags = { porcelain?: boolean };

const toKebab = (name: string) => name.replaceAll(/[A-Z]/g, char => `-${char.toLowerCase()}`);

const flag = (name: string, value: FlagValue) => {
  if (value === undefined || value === false) return [];
  if (value === true) return [`--${toKebab(name)}`];
  return [`--${toKebab(name)}`, String(value)];
};

const toArgs = (flags: Record<string, FlagValue>) =>
  Object.entries(flags).flatMap(([name, value]) => flag(name, value));

const gh = {
  api: async (endpoint: string, flags: ApiFlags = {}) => sh`gh ${['api', ...toArgs(flags), endpoint]}`.quiet(),
  pr: {
    create: async (flags: PrCreateFlags) => sh`gh ${['pr', 'create', ...toArgs(flags)]}`,
    disableAutoMerge: async () => sh`gh ${['pr', 'merge', '--disable-auto']}`.nothrow().quiet(),
    list: async (flags: PrListFlags = {}) => sh`gh ${['pr', 'list', ...toArgs(flags)]}`.quiet(),
    merge: async (flags: PrMergeFlags = {}) => sh`gh ${['pr', 'merge', ...toArgs(flags)]}`,
    ready: async (flags: PrReadyFlags = {}) => sh`gh ${['pr', 'ready', ...toArgs(flags)]}`,
    view: async (flags: PrViewFlags = {}) => sh`gh ${['pr', 'view', ...toArgs(flags)]}`.quiet(),
  },
  release: {
    create: async (tag: string, flags: ReleaseCreateFlags = {}) =>
      sh`gh ${['release', 'create', tag, ...toArgs(flags)]}`,
    delete: async (tag: string, flags: ReleaseDeleteFlags = {}) =>
      sh`gh ${['release', 'delete', tag, ...toArgs(flags)]}`,
    list: async (flags: ReleaseListFlags = {}) => sh`gh ${['release', 'list', ...toArgs(flags)]}`.quiet(),
  },
  repo: {
    view: async (flags: RepoViewFlags = {}) => sh`gh ${['repo', 'view', ...toArgs(flags)]}`.quiet(),
  },
  run: {
    list: async (flags: RunListFlags = {}) => sh`gh ${['run', 'list', ...toArgs(flags)]}`.quiet(),
    view: async (runId: string, flags: RunViewFlags = {}) => sh`gh ${['run', 'view', runId, ...toArgs(flags)]}`.quiet(),
  },
};

const git = {
  branch: async (name: string, flags: BranchFlags = {}) => sh`git ${['branch', ...toArgs(flags), name]}`,
  checkout: async (ref: string) => sh`git ${['checkout', ref]}`,
  clean: async (cwd: string, { dryRun = false, protect = [] }: CleanFlags = {}) =>
    sh`git ${['clean', '-d', '-f', '-f', '-X', ...(dryRun ? ['-n'] : []), ...protect.flatMap(pattern => ['-e', `!${pattern}`])]}`
      .cwd(cwd)
      .quiet(),
  clone: async (url: string, dest: string, flags: CloneFlags = {}) => sh`git ${['clone', ...toArgs(flags), url, dest]}`,
  fetch: async (remote: string, branch: string) => sh`git ${['fetch', remote, branch]}`,
  isInsideWorkTree: async (cwd: string) => sh`git ${['rev-parse', '--is-inside-work-tree']}`.cwd(cwd).quiet().nothrow(),
  lsFiles: async (cwd: string, pathspec: string[] = ['.']) =>
    sh`git ${['ls-files', '-z', '--', ...pathspec]}`.cwd(cwd).quiet(),
  lsRemote: async (remote: string, ref: string) => sh`git ${['ls-remote', remote, ref]}`.quiet(),
  pull: async (flags: PullFlags = {}) => sh`git ${['pull', ...toArgs(flags)]}`,
  push: async (remote: string, branch: string, flags: PushFlags = {}) =>
    sh`git ${['push', ...toArgs(flags), remote, branch]}`,
  revParse: async (rev: string, flags: RevParseFlags = {}) => sh`git ${['rev-parse', ...toArgs(flags), rev]}`.quiet(),
  showToplevel: async (cwd: string = process.cwd()) => sh`git ${['rev-parse', '--show-toplevel']}`.cwd(cwd).quiet(),
  status: async (flags: StatusFlags = {}) => sh`git ${['status', ...toArgs(flags)]}`,
};

export const $ = Object.assign(sh, { gh, git });

export const captureMerged = (argv: string[], env?: Record<string, string | undefined>): ExecPromise => {
  const merged = run(argv, { merge: true }).nothrow().quiet();
  return env === undefined ? merged : merged.env(env);
};

export const readTrimmed = async (command: Promise<CommandOutput>) => {
  const output = await command;
  return output.text().trim();
};
