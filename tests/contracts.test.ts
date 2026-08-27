import { describe, expect, it } from 'vitest';
import { SCHEMA_VERSION, type TelemetrySnapshot } from '@/lib/contracts';

describe('telemetry contract', () => {
  it('pins the public schema version', () => {
    const snapshot: TelemetrySnapshot = {
      schemaVersion: SCHEMA_VERSION,
      timestamp: new Date(0).toISOString(),
      source: 'demo',
      connection: 'healthy',
      heartbeatAgeMs: 40,
      position: { latitudeDeg: 49.26, longitudeDeg: -123.24, relativeAltitudeM: 20 },
      groundSpeedMps: 8,
      headingDeg: 90,
      batteryPercent: 92,
      gps: { fixType: '3D FIX', satellites: 18 },
      armed: false,
      flightMode: 'HOLD',
    };
    expect(snapshot.schemaVersion).toBe(1);
  });
});
