'use client';

import { useEffect, useMemo, useState } from 'react';
import { SCHEMA_VERSION, type GroundEvent, type TelemetrySnapshot } from '@/lib/contracts';

const HOME = { latitudeDeg: 49.2606, longitudeDeg: -123.246 };

export function useDemoTelemetry() {
  const [tick, setTick] = useState(0);

  useEffect(() => {
    const timer = window.setInterval(() => setTick((value) => value + 1), 500);
    return () => window.clearInterval(timer);
  }, []);

  const telemetry = useMemo<TelemetrySnapshot>(() => {
    const angle = tick / 24;
    const climb = Math.min(tick * 0.45, 32);
    return {
      schemaVersion: SCHEMA_VERSION,
      timestamp: new Date().toISOString(),
      source: 'demo',
      connection: 'healthy',
      heartbeatAgeMs: 86 + (tick % 4) * 11,
      position: {
        latitudeDeg: HOME.latitudeDeg + Math.sin(angle) * 0.0018,
        longitudeDeg: HOME.longitudeDeg + Math.cos(angle) * 0.0027,
        relativeAltitudeM: climb + Math.sin(angle * 1.7) * 1.2,
      },
      groundSpeedMps: 8.4 + Math.sin(angle) * 1.1,
      headingDeg: (tick * 7.5) % 360,
      batteryPercent: Math.max(22, 94 - tick * 0.035),
      gps: { fixType: '3D FIX', satellites: 18 + (tick % 3) },
      armed: true,
      flightMode: 'MISSION',
    };
  }, [tick]);

  const events = useMemo<GroundEvent[]>(() => [
    { id: 'e1', timestamp: telemetry.timestamp, severity: 'success', message: 'Telemetry link healthy' },
    { id: 'e2', timestamp: new Date(Date.parse(telemetry.timestamp) - 18_000).toISOString(), severity: 'info', message: 'Mission uploaded · 4 waypoints' },
    { id: 'e3', timestamp: new Date(Date.parse(telemetry.timestamp) - 31_000).toISOString(), severity: 'info', message: 'Demo vehicle connected' },
  ], [telemetry.timestamp]);

  return { telemetry, events, home: HOME };
}
