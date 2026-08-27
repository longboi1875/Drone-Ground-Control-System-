'use client';

import { useEffect } from 'react';
import { setLinkProfile } from '@/lib/api';
import type { GroundEvent, LinkProfile } from '@/lib/contracts';

declare global {
  interface Document {
    modelContext?: {
      registerTool(tool: {
        name: string;
        title: string;
        description: string;
        inputSchema: object;
        annotations: { readOnlyHint: boolean; untrustedContentHint: boolean };
        execute(input: unknown): Promise<unknown>;
      }, options: { signal: AbortSignal }): void | Promise<void>;
    };
  }
}

const PRESETS: Record<string, LinkProfile> = {
  clean: { name: 'Clean', lossPercent: 0, delayMs: 0, jitterMs: 0, duplicatePercent: 0, seed: 481 },
  weak_wifi: { name: 'Weak Wi-Fi', lossPercent: 5, delayMs: 80, jitterMs: 30, duplicatePercent: 1, seed: 481 },
  high_latency: { name: 'High Latency', lossPercent: 1, delayMs: 500, jitterMs: 100, duplicatePercent: 0, seed: 481 },
  severe_loss: { name: 'Severe Loss', lossPercent: 30, delayMs: 200, jitterMs: 80, duplicatePercent: 8, seed: 481 },
};

export function useWebMcp(addEvent: (message: string, severity?: GroundEvent['severity']) => void) {
  useEffect(() => {
    const context = document.modelContext;
    if (!context?.registerTool) return;
    const lifecycle = new AbortController();
    const registration = context.registerTool({
      name: 'configure_skylink_link_profile',
      title: 'Configure SkyLink link profile',
      description: 'Apply one of SkyLink’s deterministic MAVLink impairment presets.',
      inputSchema: {
        type: 'object',
        properties: { preset: { type: 'string', enum: Object.keys(PRESETS) } },
        required: ['preset'],
        additionalProperties: false,
      },
      annotations: { readOnlyHint: false, untrustedContentHint: false },
      async execute(input) {
        const preset = typeof input === 'object' && input !== null && 'preset' in input ? String(input.preset) : '';
        const profile = PRESETS[preset];
        if (!profile) throw new Error('Unknown link profile preset');
        await setLinkProfile(profile);
        addEvent(`Link profile: ${profile.name}`, 'info');
        return { applied: true, profile };
      },
    }, { signal: lifecycle.signal });
    void Promise.resolve(registration).catch(() => undefined);
    return () => lifecycle.abort();
  }, [addEvent]);
}
