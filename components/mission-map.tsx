'use client';

import { useEffect } from 'react';
import L from 'leaflet';
import { MapContainer, Marker, Polyline, TileLayer, Tooltip, useMap } from 'react-leaflet';
import type { TelemetrySnapshot } from '@/lib/contracts';
import 'leaflet/dist/leaflet.css';

const droneIcon = L.divIcon({
  className: '',
  html: '<span class="drone-marker"><span>▲</span></span>',
  iconAnchor: [18, 18],
  iconSize: [36, 36],
});

const homeIcon = L.divIcon({
  className: '',
  html: '<span class="home-marker">H</span>',
  iconAnchor: [13, 13],
  iconSize: [26, 26],
});

function TrackVehicle({ telemetry }: { telemetry: TelemetrySnapshot }) {
  const map = useMap();
  useEffect(() => {
    map.panTo([telemetry.position.latitudeDeg, telemetry.position.longitudeDeg], { animate: true, duration: 0.4 });
  }, [map, telemetry.position.latitudeDeg, telemetry.position.longitudeDeg]);
  return null;
}

export function MissionMap({ telemetry, home }: { telemetry: TelemetrySnapshot; home: { latitudeDeg: number; longitudeDeg: number } }) {
  const aircraft: [number, number] = [telemetry.position.latitudeDeg, telemetry.position.longitudeDeg];
  const origin: [number, number] = [home.latitudeDeg, home.longitudeDeg];
  const route: [number, number][] = [origin, [49.2618, -123.2438], [49.263, -123.2472], [49.2612, -123.2495], origin];

  return (
    <MapContainer center={aircraft} zoom={16} zoomControl={false} attributionControl className="h-full w-full">
      <TileLayer attribution='&copy; OpenStreetMap contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
      <Polyline positions={route} pathOptions={{ color: '#54d6ff', weight: 2, dashArray: '8 8', opacity: 0.85 }} />
      <Polyline positions={[origin, aircraft]} pathOptions={{ color: '#f5b942', weight: 3, opacity: 0.9 }} />
      <Marker position={origin} icon={homeIcon}><Tooltip>Home</Tooltip></Marker>
      <Marker position={aircraft} icon={droneIcon}><Tooltip permanent direction="top">X500 · {telemetry.position.relativeAltitudeM.toFixed(1)} m</Tooltip></Marker>
      <TrackVehicle telemetry={telemetry} />
    </MapContainer>
  );
}
