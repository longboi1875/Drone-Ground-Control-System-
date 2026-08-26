export const SCHEMA_VERSION = 1 as const;

export type ConnectionState = 'connecting' | 'healthy' | 'degraded' | 'lost';
export type VehicleSource = 'demo' | 'px4' | 'replay';

export interface TelemetrySnapshot {
  schemaVersion: typeof SCHEMA_VERSION;
  timestamp: string;
  source: VehicleSource;
  connection: ConnectionState;
  heartbeatAgeMs: number;
  position: {
    latitudeDeg: number;
    longitudeDeg: number;
    relativeAltitudeM: number;
  };
  groundSpeedMps: number;
  headingDeg: number;
  batteryPercent: number;
  gps: { fixType: string; satellites: number };
  armed: boolean;
  flightMode: string;
}

export interface GroundEvent {
  id: string;
  timestamp: string;
  severity: 'info' | 'success' | 'warning';
  message: string;
}

export interface Waypoint {
  id: string;
  latitudeDeg: number;
  longitudeDeg: number;
  relativeAltitudeM: number;
  speedMps: number;
  acceptanceRadiusM: number;
  flyThrough: boolean;
}

export type CommandType = 'arm' | 'takeoff' | 'land' | 'rtl' | 'start_mission' | 'set_current_waypoint';
export type CommandState = 'queued' | 'sent' | 'acknowledged' | 'failed' | 'timed_out';

export interface CommandRecord {
  id: string;
  type: CommandType;
  parameters: Record<string, unknown>;
  state: CommandState;
  attempts: number;
  acknowledgement?: string;
  error?: string;
}

export interface FlightSummary {
  id: string;
  name: string;
  source: string;
  started_at: string;
  ended_at?: string;
  outcome: string;
  telemetry_count: number;
  command_count: number;
}

export interface LinkProfile {
  name: string;
  lossPercent: number;
  delayMs: number;
  jitterMs: number;
  duplicatePercent: number;
  seed: number;
}
