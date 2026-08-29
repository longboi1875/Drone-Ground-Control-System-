'use client';

import { useCallback, useEffect, useState } from 'react';
import { API_BASE } from '@/lib/api';
import type { GroundEvent, TelemetrySnapshot } from '@/lib/contracts';
import { useDemoTelemetry } from './use-demo-telemetry';

function websocketUrl(path: string) {
  return `${API_BASE.replace(/^http/, 'ws')}${path}`;
}

export function useSkyLink() {
  const demo = useDemoTelemetry();
  const [liveTelemetry, setLiveTelemetry] = useState<TelemetrySnapshot>();
  const [events, setEvents] = useState<GroundEvent[]>([]);
  const [serviceOnline, setServiceOnline] = useState(false);

  useEffect(() => {
    let telemetrySocket: WebSocket | undefined;
    let eventSocket: WebSocket | undefined;
    let closed = false;
    let retryTimer: number | undefined;
    let retryDelay = 500;

    async function connect() {
      try {
        const response = await fetch(`${API_BASE}/api/health`);
        if (!response.ok || closed) throw new Error('mission service unavailable');
        setServiceOnline(true);
        retryDelay = 500;
        telemetrySocket = new WebSocket(websocketUrl('/ws/telemetry'));
        eventSocket = new WebSocket(websocketUrl('/ws/events'));
        telemetrySocket.onmessage = (message) => setLiveTelemetry(JSON.parse(message.data));
        telemetrySocket.onclose = () => {
          setServiceOnline(false);
          if (!closed) {
            retryTimer = window.setTimeout(() => void connect(), retryDelay);
            retryDelay = Math.min(8000, retryDelay * 2);
          }
        };
        eventSocket.onmessage = (message) => {
          const event = JSON.parse(message.data) as GroundEvent;
          setEvents((current) => [event, ...current].slice(0, 30));
        };
      } catch {
        setServiceOnline(false);
        if (!closed) {
          retryTimer = window.setTimeout(() => void connect(), retryDelay);
          retryDelay = Math.min(8000, retryDelay * 2);
        }
      }
    }
    void connect();
    return () => {
      closed = true;
      window.clearTimeout(retryTimer);
      telemetrySocket?.close();
      eventSocket?.close();
    };
  }, []);

  const addEvent = useCallback((message: string, severity: GroundEvent['severity'] = 'info') => {
    setEvents((current) => [{ id: crypto.randomUUID(), timestamp: new Date().toISOString(), message, severity }, ...current].slice(0, 30));
  }, []);

  return {
    telemetry: liveTelemetry ?? demo.telemetry,
    events: events.length ? events : demo.events,
    home: demo.home,
    serviceOnline,
    addEvent,
  };
}
