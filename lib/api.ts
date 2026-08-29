import type { CommandRecord, CommandType, FlightSummary, LinkProfile, Waypoint } from './contracts';

export const API_BASE = process.env.NEXT_PUBLIC_SKYLINK_API ?? 'http://127.0.0.1:8000';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  headers.set('Content-Type', 'application/json');
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
  });
  if (!response.ok) {
    const body: unknown = await response.json().catch(() => undefined);
    const detail = typeof body === 'object' && body !== null && 'detail' in body ? String(body.detail) : response.statusText;
    throw new Error(detail || `request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export async function sendCommand(type: CommandType, parameters: Record<string, unknown> = {}) {
  const id = crypto.randomUUID();
  const body = JSON.stringify({ id, type, parameters, createdAt: new Date().toISOString() });
  let lastError: unknown;
  for (let attempt = 0; attempt < 3; attempt += 1) {
    try {
      const result = await request<{ command: CommandRecord }>('/api/commands', {
        method: 'POST',
        body,
      });
      return result.command;
    } catch (error) {
      lastError = error;
      if (attempt < 2) await new Promise((resolve) => window.setTimeout(resolve, 250 * 2 ** attempt));
    }
  }
  throw lastError;
}

export async function commandStatus(id: string) {
  return request<CommandRecord>(`/api/commands/${id}`);
}

export async function saveMission(name: string, waypoints: Waypoint[]) {
  return request<{ id: string }>('/api/missions', {
    method: 'POST',
    body: JSON.stringify({ name, waypoints }),
  });
}

export async function uploadMission(id: string) {
  return request<{ acknowledgement: string }>(`/api/missions/${id}/upload`, { method: 'POST' });
}

export async function listFlights() {
  return request<FlightSummary[]>('/api/flights');
}

export async function startReplay(id: string) {
  return request(`/api/flights/${id}/replay`, { method: 'POST' });
}

export async function controlReplay(action: string, speed = 1, positionSeconds = 0) {
  return request('/api/replay', {
    method: 'PUT',
    body: JSON.stringify({ action, speed, positionSeconds }),
  });
}

export async function getLinkProfile() {
  return request<{ profile: LinkProfile; stats: Record<string, Record<string, number>> }>('/api/link-profile');
}

export async function setLinkProfile(profile: LinkProfile) {
  return request<LinkProfile>('/api/link-profile', { method: 'PUT', body: JSON.stringify(profile) });
}
