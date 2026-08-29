import { afterEach, describe, expect, it, vi } from 'vitest';
import { sendCommand } from '@/lib/api';

describe('command submission', () => {
  afterEach(() => vi.restoreAllMocks());

  it('reuses one command id after a transient request failure', async () => {
    vi.spyOn(globalThis.crypto, 'randomUUID').mockReturnValue('48100000-0000-4000-8000-000000000000');
    const fetchMock = vi.spyOn(globalThis, 'fetch')
      .mockRejectedValueOnce(new TypeError('network reset'))
      .mockResolvedValueOnce(new Response(JSON.stringify({
        command: {
          id: '48100000-0000-4000-8000-000000000000',
          type: 'arm',
          parameters: {},
          state: 'queued',
          attempts: 0,
        },
      }), { status: 202, headers: { 'Content-Type': 'application/json' } }));

    await sendCommand('arm');

    expect(fetchMock).toHaveBeenCalledTimes(2);
    const firstBody = fetchMock.mock.calls[0][1]?.body;
    const secondBody = fetchMock.mock.calls[1][1]?.body;
    expect(typeof firstBody).toBe('string');
    expect(typeof secondBody).toBe('string');
    if (typeof firstBody !== 'string' || typeof secondBody !== 'string') throw new Error('expected JSON command bodies');
    expect(JSON.parse(firstBody).id).toBe('48100000-0000-4000-8000-000000000000');
    expect(secondBody).toBe(firstBody);
  });
});
