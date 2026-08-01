import { setTimeout } from 'node:timers/promises';

type PollOptions = { attempts: number; intervalMs: number };

export const poll = async <T>(probe: () => Promise<T | undefined>, { attempts, intervalMs }: PollOptions) => {
  for (let attempt = 0; attempt < attempts; attempt++) {
    const found = await probe();
    if (found !== undefined) {
      return found;
    }
    await setTimeout(intervalMs);
  }
  return;
};
