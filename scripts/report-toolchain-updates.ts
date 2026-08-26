#!/usr/bin/env node
import { execFile } from 'node:child_process';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { createInterface } from 'node:readline/promises';
import { promisify } from 'node:util';

import { NodeReleaseIndexSchema, ToolchainManifestSchema } from './src/contracts.ts';

const REPO_ROOT = path.resolve(import.meta.dirname, '..');
const execFileAsync = promisify(execFile);

const fetchLatestDeployableNode = async () => {
  const response = await fetch('https://nodejs.org/dist/index.json');
  const releases = NodeReleaseIndexSchema.parse(await response.json());
  for (const release of releases) {
    const version = release.version.replace(/^v/u, '');
    const image = await fetch(`https://hub.docker.com/v2/repositories/library/node/tags/${version}-slim`, {
      method: 'HEAD',
    });
    if (image.ok) return version;
  }
  throw new Error('no Node release has a matching official slim image');
};

const readDeclaredNode = async () => {
  const manifestText = await readFile(path.join(REPO_ROOT, 'package.json'), 'utf8');
  const manifest = ToolchainManifestSchema.parse(JSON.parse(manifestText));
  return manifest.devEngines.runtime.version;
};

const shouldUpgradeNode = async (version: string) => {
  if (!process.stdin.isTTY) return false;
  const prompt = createInterface({ input: process.stdin, output: process.stdout });
  const answer = await prompt.question(`  upgrade the project Node runtime to ${version}? [y/N] `);
  prompt.close();
  return answer.trim().toLowerCase() === 'y';
};

try {
  const [declared, latest] = await Promise.all([readDeclaredNode(), fetchLatestDeployableNode()]);
  const hasUpdate = declared !== latest;
  console.log(`node: declared ${declared}, latest deployable ${latest} — ${hasUpdate ? 'NEW VERSION' : 'up to date'}`);
  if (hasUpdate && (process.argv.includes('--update') || (await shouldUpgradeNode(latest)))) {
    await execFileAsync('pnpm', ['runtime', 'set', 'node', latest], { cwd: REPO_ROOT });
    console.log(`node: set project runtime to ${latest}`);
  }
} catch (error) {
  console.error(`toolchain update failed: ${error instanceof Error ? error.message : String(error)}`);
  process.exitCode = 1;
}
