import { ExecError } from '@zyplux/util';
import { run } from '@zyplux/util/exec';
import { tmpdir } from 'node:os';
import { describe, expect, test } from 'vitest';

const node = process.execPath;

describe('7.1 capturing process output', () => {
  test('7.1.1 resolves with stdout, stderr, and the exit code', async () => {
    const script = `process.stdout.write('out'); process.stderr.write('err');`;

    const result = await run([node, '-e', script]).quiet();

    expect(result.exitCode).toBe(0);
    expect(result.stdout.toString()).toBe('out');
    expect(result.stderr.toString()).toBe('err');
  });

  test('7.1.2 decodes text with an explicit encoding', async () => {
    const text = await run([node, '-e', `process.stdout.write('hi')`])
      .quiet()
      .text('hex');

    expect(text).toBe(Buffer.from('hi').toString('hex'));
  });
});

describe('7.2 configuring the spawn through chained calls', () => {
  test('7.2.1 runs in a chained working directory', async () => {
    const dir = tmpdir();

    const cwdSeenByChild = await run([node, '-e', `process.stdout.write(process.cwd())`])
      .cwd(dir)
      .quiet()
      .text();

    expect(cwdSeenByChild).toBe(dir);
  });

  test('7.2.2 overlays chained environment variables onto the parent environment', async () => {
    const script = `process.stdout.write(process.env.STORY_PROBE + ':' + typeof process.env.PATH)`;

    const probe = await run([node, '-e', script])
      .env({ STORY_PROBE: '42' })
      .quiet()
      .text();

    expect(probe).toBe('42:string');
  });
});

describe('7.3 feeding stdin and merging streams', () => {
  test('7.3.1 pipes a provided stdin into the process', async () => {
    const echoed = await run([node, '-e', `process.stdin.pipe(process.stdout)`], { stdin: 'ping' })
      .quiet()
      .text();

    expect(echoed).toBe('ping');
  });

  test('7.3.2 interleaves stdout and stderr when merge is requested', async () => {
    const script = `process.stdout.write('a'); process.stderr.write('b');`;

    const result = await run([node, '-e', script], { merge: true }).quiet();

    expect([...result.stdout.toString()].sort()).toEqual(['a', 'b']);
    expect(result.stderr.length).toBe(0);
  });
});

describe('7.4 failing commands', () => {
  test('7.4.1 rejects with an ExecError carrying the exit code', async () => {
    const failing = run([node, '-e', `process.stderr.write('boom'); process.exit(3)`]).quiet();

    await expect(failing).rejects.toThrow(ExecError);
    await expect(failing).rejects.toMatchObject({ exitCode: 3 });
  });

  test('7.4.2 resolves a failing command when nothrow is chained', async () => {
    const result = await run([node, '-e', `process.exit(3)`])
      .nothrow()
      .quiet();

    expect(result.exitCode).toBe(3);
  });

  test('7.4.3 rejects when argv is empty', async () => {
    await expect(run([]).quiet()).rejects.toThrow('argv must contain at least a command');
  });

  test('7.4.4 rejects when the command does not exist', async () => {
    await expect(run(['zyplux-missing-command-probe']).quiet()).rejects.toThrow();
  });
});
