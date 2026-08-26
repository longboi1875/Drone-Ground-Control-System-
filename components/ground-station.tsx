'use client';

import dynamic from 'next/dynamic';
import { useState } from 'react';
import { BatteryMedium, Crosshair, Gauge, MapPin, Navigation, Radio, Satellite, ShieldCheck } from 'lucide-react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { CommandControls, FlightHistory, LinkPanel, MissionPanel } from '@/components/control-panel';
import { useSkyLink } from '@/hooks/use-skylink';
import type { Waypoint } from '@/lib/contracts';

const MissionMap = dynamic(() => import('./mission-map').then((module) => module.MissionMap), { ssr: false });

function Metric({ label, value, unit, icon: Icon }: { label: string; value: string; unit?: string; icon: typeof Gauge }) {
  return <div className="metric-card"><div className="metric-label"><Icon size={15} />{label}</div><div><span className="metric-value">{value}</span>{unit && <span className="metric-unit"> {unit}</span>}</div></div>;
}

export function GroundStation() {
  const { telemetry, events, home, serviceOnline, addEvent } = useSkyLink();
  const [waypoints, setWaypoints] = useState<Waypoint[]>([
    { id: crypto.randomUUID(), latitudeDeg: 49.2618, longitudeDeg: -123.2438, relativeAltitudeM: 30, speedMps: 8, acceptanceRadiusM: 3, flyThrough: false },
    { id: crypto.randomUUID(), latitudeDeg: 49.263, longitudeDeg: -123.2472, relativeAltitudeM: 35, speedMps: 8, acceptanceRadiusM: 3, flyThrough: true },
    { id: crypto.randomUUID(), latitudeDeg: 49.2612, longitudeDeg: -123.2495, relativeAltitudeM: 25, speedMps: 6, acceptanceRadiusM: 3, flyThrough: false },
  ]);
  const time = new Date(telemetry.timestamp).toLocaleTimeString([], { hour12: false });
  const stateLabel = serviceOnline ? telemetry.connection.toUpperCase() : 'DEMO FALLBACK';

  function addWaypoint(latitudeDeg: number, longitudeDeg: number) {
    setWaypoints([...waypoints, { id: crypto.randomUUID(), latitudeDeg, longitudeDeg, relativeAltitudeM: 30, speedMps: 8, acceptanceRadiusM: 3, flyThrough: false }]);
    addEvent(`Waypoint ${waypoints.length + 1} added`);
  }

  function moveWaypoint(id: string, latitudeDeg: number, longitudeDeg: number) {
    setWaypoints(waypoints.map((item) => item.id === id ? { ...item, latitudeDeg, longitudeDeg } : item));
  }

  return (
    <main className="station-shell">
      <header className="topbar">
        <div className="brand-mark"><Navigation size={20} fill="currentColor" /><span>SKYLINK</span></div>
        <div className="vehicle-title"><span>X500 /</span> UBC TEST RANGE</div>
        <div className="topbar-status"><span className="sim-badge"><ShieldCheck size={14} /> SIMULATION</span><span className="clock">{time} PDT</span></div>
      </header>

      <section className="status-strip">
        <div className={`link-state ${serviceOnline ? '' : 'fallback'}`}><span className="pulse-dot" /> {stateLabel} <small>{telemetry.heartbeatAgeMs} ms heartbeat</small></div>
        <div className="status-item">MODE <strong>{telemetry.flightMode}</strong></div>
        <div className="status-item">STATE <strong className={telemetry.armed ? 'armed' : ''}>{telemetry.armed ? 'ARMED' : 'DISARMED'}</strong></div>
        <div className="status-item">SOURCE <strong>{telemetry.source.toUpperCase()}</strong></div>
      </section>

      <div className="workspace">
        <section className="map-panel" aria-label="Aircraft and mission map">
          <MissionMap telemetry={telemetry} home={home} waypoints={waypoints} onAddWaypoint={addWaypoint} onMoveWaypoint={moveWaypoint} />
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

          <Tabs defaultValue="operate" className="station-tabs">
            <TabsList variant="line" className="station-tab-list">
              <TabsTrigger value="operate">OPERATE</TabsTrigger><TabsTrigger value="mission">MISSION</TabsTrigger><TabsTrigger value="flights">FLIGHTS</TabsTrigger><TabsTrigger value="link">LINK</TabsTrigger>
            </TabsList>
            <TabsContent value="operate">
              <CommandControls enabled={serviceOnline && telemetry.source !== 'replay'} addEvent={addEvent} />
              <div className="panel-heading event-heading"><span>EVENT STREAM</span><small>LIVE</small></div>
              <ol className="event-list">{events.slice(0, 8).map((event) => <li key={event.id}><time>{new Date(event.timestamp).toLocaleTimeString([], { hour12: false })}</time><span className={`event-dot ${event.severity}`} /><p>{event.message}</p></li>)}</ol>
            </TabsContent>
            <TabsContent value="mission"><MissionPanel waypoints={waypoints} setWaypoints={setWaypoints} addEvent={addEvent} enabled={serviceOnline && telemetry.source !== 'replay'} /></TabsContent>
            <TabsContent value="flights"><FlightHistory addEvent={addEvent} /></TabsContent>
            <TabsContent value="link"><LinkPanel addEvent={addEvent} /></TabsContent>
          </Tabs>
        </aside>
      </div>
    </main>
  );
}
