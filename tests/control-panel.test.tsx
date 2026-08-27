import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { CommandControls } from '@/components/control-panel';

describe('CommandControls', () => {
  it('locks aircraft commands when the service is offline', () => {
    render(<CommandControls enabled={false} addEvent={vi.fn()} />);
    for (const name of ['ARM', 'TAKEOFF', 'RTL', 'LAND']) {
      expect(screen.getByRole('button', { name })).toBeDisabled();
    }
    expect(screen.getByText(/start the mission service/i)).toBeVisible();
  });

  it('unlocks commands only when explicitly enabled', () => {
    render(<CommandControls enabled addEvent={vi.fn()} />);
    expect(screen.getByRole('button', { name: 'ARM' })).toBeEnabled();
  });
});
