import { createInterface, Interface } from 'node:readline/promises';
import { PassThrough } from 'node:stream';
import { vi } from 'vitest';

vi.mock('node:readline/promises', async importOriginal => {
  const actual = await importOriginal<typeof import('node:readline/promises')>();
  return { ...actual, createInterface: vi.fn(actual.createInterface) };
});

export type PromptFake = {
  install: () => () => void;
  messages: string[];
};

class PromptProbe extends Interface {
  private readonly messages: string[];

  constructor(messages: string[]) {
    super({ input: new PassThrough() });
    this.messages = messages;
  }

  override question(message: string) {
    this.messages.push(message);
    return Promise.resolve('');
  }
}

export const createPromptFake = (): PromptFake => {
  const messages: string[] = [];
  const createInterfaceMock = vi.mocked(createInterface);

  return {
    install: () => {
      createInterfaceMock.mockImplementation(() => new PromptProbe(messages));
      return () => {
        createInterfaceMock.mockReset();
      };
    },
    messages,
  };
};
