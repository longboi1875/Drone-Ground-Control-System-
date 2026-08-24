'use client';

import dynamic from 'next/dynamic';
import { BatteryMedium, Crosshair, Gauge, MapPin, Navigation, Radio, Satellite, ShieldCheck } from 'lucide-react';
import { useDemoTelemetry } from '@/hooks/use-demo-telemetry';

const MissionMap = dynamic(() => import('./mission-map').then((module) => module.MissionMap), { ssr: false });

function Metric({ label, value, unit, icon: Icon }: { label: string; value: string; unit?: string; icon: typeof Gauge }) {
  return (
    <div className="metric-card">
      <div className="metric-label"><Icon size={15} />{label}</div>
      <div><span className="metric-value">{value}</span>{unit && <span className="metric-unit"> {unit}</span>}</div>
    </div>
  );
}

export function GroundStation() {
  const { telemetry, events, home } = useDemoTelemetry();
  const time = new Date(telemetry.timestamp).toLocaleTimeString([], { hour12: false });

  return (
    <main className="station-shell">
      <header className="topbar">
        <div className="brand-mark"><Navigation size={20} fill="currentColor" /><span>SKYLINK</span></div>
        <div className="vehicle-title"><span>X500 /</span> UBC TEST RANGE</div>
        <div className="topbar-status">
          <span className="sim-badge"><ShieldCheck size={14} /> SIMULATION</span>
          <span className="clock">{time} PDT</span>
        </div>
      </header>

      <section className="status-strip">
        <div className="link-state"><span className="pulse-dot" /> LINK HEALTHY <small>{telemetry.heartbeatAgeMs} ms heartbeat</small></div>
        <div className="status-item">MODE <strong>{telemetry.flightMode}</strong></div>
        <div className="status-item">STATE <strong className="armed">ARMED</strong></div>
        <div className="status-item">SOURCE <strong>DEMO</strong></div>
      </section>

      <div className="workspace">
        <section className="map-panel" aria-label="Aircraft map">
          <MissionMap telemetry={telemetry} home={home} />
          <div className="map-readout"><Crosshair size={14} /> {telemetry.position.latitudeDeg.toFixed(5)}, {telemetry.position.longitudeDeg.toFixed(5)}</div>
          <div className="map-legend"><span><i className="legend-aircraft" /> AIRCRAFT</span><span><i className="legend-route" /> ROUTE</span><span><i className="legend-home" /> HOME</span></div>
        </section>

        <aside className="telemetry-panel">
          <div className="panel-heading"><span>LIVE TELEMETRY</span><Radio size={16} /></div>
          <div className="metric-grid">
            <Metric label="ALTITUDE" value={telemetry.position.relativeAltitudeM.toFixed(1)} unit="m AGL" icon={Gauge} />
            <Metric label="GROUND SPEED" value={telemetry.groundSpeedMps.toFixed(1)} unit="m/s" icon={Navigation} />
            <Metric label="HEADING" value={telemetry.headingDeg.toFixed(0).padStart(3, '0')} unit="°" icon={Crosshair} />
            <Metric label="BATTERY" value={telemetry.batteryPercent.toFixed(0)} unit="%" icon={BatteryMedium} />
            <Metric label="GPS FIX" value={telemetry.gps.fixType} icon={MapPin} />
            <Metric label="SATELLITES" value={String(telemetry.gps.satellites)} icon={Satellite} />
          </div>

          <div className="panel-heading event-heading"><span>EVENT STREAM</span><small>LIVE</small></div>
          <ol className="event-list">
            {events.map((event) => (
              <li key={event.id}><time>{new Date(event.timestamp).toLocaleTimeString([], { hour12: false })}</time><span className={`event-dot ${event.severity}`} /><p>{event.message}</p></li>
            ))}
          </ol>

          <div className="command-bar">
            <button type="button" disabled>ARM</button>
            <button type="button" disabled>TAKEOFF</button>
            <button type="button" disabled>RTL</button>
            <button type="button" disabled>LAND</button>
          </div>
          <p className="command-note">Commands unlock when the mission service is connected.</p>
        </aside>
      </div>
    </main>
  );
}
