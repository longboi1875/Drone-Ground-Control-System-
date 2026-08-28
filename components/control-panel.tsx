'use client';

import { useEffect, useState } from 'react';
import { ChevronDown, ChevronUp, Download, Pause, Play, RotateCcw, Trash2, Upload } from 'lucide-react';
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import { Slider } from '@/components/ui/slider';
import { commandStatus, controlReplay, getLinkProfile, listFlights, saveMission, sendCommand, setLinkProfile, startReplay, uploadMission } from '@/lib/api';
import type { CommandType, FlightSummary, GroundEvent, LinkProfile, Waypoint } from '@/lib/contracts';

export function CommandControls({ enabled, addEvent }: { enabled: boolean; addEvent: (message: string, severity?: GroundEvent['severity']) => void }) {
  const [busy, setBusy] = useState<string>();
  async function issue(type: CommandType) {
    setBusy(type);
    try {
      const record = await sendCommand(type);
      addEvent(`${type.toUpperCase()} queued · #${record.id.slice(0, 8)}`);
      for (let poll = 0; poll < 40; poll += 1) {
        await new Promise((resolve) => window.setTimeout(resolve, 100));
        const current = await commandStatus(record.id);
        if (['acknowledged', 'failed', 'timed_out'].includes(current.state)) {
          addEvent(`${type.toUpperCase()} ${current.state}`, current.state === 'acknowledged' ? 'success' : 'warning');
          break;
        }
      }
    } catch (error) {
      addEvent(error instanceof Error ? error.message : 'Command failed', 'warning');
    } finally {
      setBusy(undefined);
    }
  }

  return (
    <div className="operation-panel">
      <p className="section-kicker">FLIGHT COMMANDS</p>
      <div className="operation-grid">
        {(['arm', 'takeoff', 'rtl', 'land'] as const).map((type) => (
          <AlertDialog key={type}>
            <AlertDialogTrigger render={<button aria-label={type.toUpperCase()} className={type === 'land' ? 'danger-command' : ''} disabled={!enabled || Boolean(busy)} />}>
              {busy === type ? 'SENDING…' : type.toUpperCase()}
            </AlertDialogTrigger>
            <AlertDialogContent className="confirm-dialog">
              <AlertDialogHeader>
                <AlertDialogTitle>Confirm {type.toUpperCase()}</AlertDialogTitle>
                <AlertDialogDescription>This command will be sent to the simulated aircraft. Verify the map and vehicle state first.</AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction onClick={() => void issue(type)}>Send command</AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        ))}
      </div>
      <p className="command-note">{enabled ? 'Service connected · command IDs and ACKs are recorded.' : 'Start the mission service to unlock commands.'}</p>
    </div>
  );
}

export function MissionPanel({ waypoints, setWaypoints, addEvent, enabled }: {
  waypoints: Waypoint[];
  setWaypoints: (waypoints: Waypoint[]) => void;
  addEvent: (message: string, severity?: GroundEvent['severity']) => void;
  enabled: boolean;
}) {
  const [missionId, setMissionId] = useState<string>();
  const [name, setName] = useState('Campus perimeter');

  function move(index: number, offset: number) {
    const next = [...waypoints];
    const target = index + offset;
    if (target < 0 || target >= next.length) return;
    [next[index], next[target]] = [next[target], next[index]];
    setWaypoints(next);
  }

  async function persist() {
    try {
      const mission = await saveMission(name, waypoints);
      setMissionId(mission.id);
      addEvent(`Mission saved · ${waypoints.length} waypoints`, 'success');
    } catch (error) {
      addEvent(error instanceof Error ? error.message : 'Mission save failed', 'warning');
    }
  }

  async function upload() {
    try {
      let id = missionId;
      if (!id) {
        const mission = await saveMission(name, waypoints);
        id = mission.id;
        setMissionId(id);
      }
      const result = await uploadMission(id);
      addEvent(result.acknowledgement, 'success');
    } catch (error) {
      addEvent(error instanceof Error ? error.message : 'Mission upload failed', 'warning');
    }
  }

  function exportMission() {
    const blob = new Blob([JSON.stringify({ name, waypoints }, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'skylink-mission.json';
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="mission-editor">
      <label>MISSION NAME<input value={name} onChange={(event) => setName(event.target.value)} /></label>
      <p className="editor-help">Click the map to add a waypoint. Drag markers to refine the route.</p>
      <ol className="waypoint-list">
        {waypoints.map((waypoint, index) => (
          <li key={waypoint.id}>
            <span className="waypoint-number">{index + 1}</span>
            <div><strong>{waypoint.relativeAltitudeM} m AGL</strong><small>{waypoint.latitudeDeg.toFixed(5)}, {waypoint.longitudeDeg.toFixed(5)}</small></div>
            <button aria-label="Move waypoint up" onClick={() => move(index, -1)}><ChevronUp size={14} /></button>
            <button aria-label="Move waypoint down" onClick={() => move(index, 1)}><ChevronDown size={14} /></button>
            <button aria-label="Delete waypoint" onClick={() => setWaypoints(waypoints.filter((item) => item.id !== waypoint.id))}><Trash2 size={14} /></button>
          </li>
        ))}
      </ol>
      {!waypoints.length && <div className="empty-state">No waypoints yet</div>}
      <div className="panel-actions">
        <button onClick={exportMission} disabled={!waypoints.length}><Download size={14} /> EXPORT</button>
        <button onClick={() => void persist()} disabled={!enabled || !waypoints.length}>SAVE</button>
        <button className="primary-action" onClick={() => void upload()} disabled={!enabled || !waypoints.length}><Upload size={14} /> UPLOAD</button>
      </div>
    </div>
  );
}

export function FlightHistory({ addEvent }: { addEvent: (message: string, severity?: GroundEvent['severity']) => void }) {
  const [flights, setFlights] = useState<FlightSummary[]>([]);
  const [speed, setSpeed] = useState(1);
  const [playing, setPlaying] = useState(false);
  useEffect(() => { void listFlights().then(setFlights).catch(() => setFlights([])); }, []);

  async function replay(id: string) {
    try {
      await startReplay(id);
      setPlaying(true);
      addEvent('Replay started · commands locked', 'info');
    } catch (error) {
      addEvent(error instanceof Error ? error.message : 'Replay failed', 'warning');
    }
  }

  return (
    <div className="history-panel">
      <div className="replay-controls">
        <button onClick={() => { setPlaying(!playing); void controlReplay(playing ? 'pause' : 'play', speed); }}>{playing ? <Pause size={15} /> : <Play size={15} />}</button>
        <button onClick={() => void controlReplay('restart', speed)}><RotateCcw size={15} /></button>
        {[0.5, 1, 2, 4].map((value) => <button className={speed === value ? 'active' : ''} key={value} onClick={() => { setSpeed(value); void controlReplay('play', value); }}>{value}×</button>)}
      </div>
      <ol className="flight-list">
        {flights.map((flight) => (
          <li key={flight.id}>
            <div><strong>{flight.name}</strong><small>{new Date(flight.started_at).toLocaleString()} · {flight.telemetry_count} frames</small></div>
            <button onClick={() => void replay(flight.id)}><Play size={13} /> REPLAY</button>
          </li>
        ))}
      </ol>
      {!flights.length && <div className="empty-state">No recorded flights yet</div>}
    </div>
  );
}

const PRESETS: Record<string, LinkProfile> = {
  Clean: { name: 'Clean', lossPercent: 0, delayMs: 0, jitterMs: 0, duplicatePercent: 0, seed: 481 },
  'Weak Wi-Fi': { name: 'Weak Wi-Fi', lossPercent: 5, delayMs: 80, jitterMs: 30, duplicatePercent: 1, seed: 481 },
  'High Latency': { name: 'High Latency', lossPercent: 1, delayMs: 500, jitterMs: 100, duplicatePercent: 0, seed: 481 },
  'Severe Loss': { name: 'Severe Loss', lossPercent: 30, delayMs: 200, jitterMs: 80, duplicatePercent: 8, seed: 481 },
};

export function LinkPanel({ addEvent }: { addEvent: (message: string, severity?: GroundEvent['severity']) => void }) {
  const [profile, setProfile] = useState(PRESETS.Clean);
  const [stats, setStats] = useState<Record<string, Record<string, number>>>({});
  useEffect(() => { void getLinkProfile().then((result) => { setProfile(result.profile); setStats(result.stats); }).catch(() => undefined); }, []);

  async function apply(next: LinkProfile) {
    setProfile(next);
    try { await setLinkProfile(next); addEvent(`Link profile: ${next.name}`, 'info'); }
    catch { addEvent('Mission service is offline', 'warning'); }
  }

  return (
    <div className="link-panel">
      <div className="preset-grid">{Object.entries(PRESETS).map(([name, value]) => <button key={name} className={profile.name === name ? 'active' : ''} onClick={() => void apply(value)}>{name}</button>)}</div>
      <label>PACKET LOSS <output>{profile.lossPercent}%</output><Slider min={0} max={60} step={1} value={profile.lossPercent} onValueChange={(value) => setProfile({ ...profile, name: 'Custom', lossPercent: value as number })} onValueCommitted={() => void apply(profile)} /></label>
      <label>FIXED DELAY <output>{profile.delayMs} ms</output><Slider min={0} max={1000} step={10} value={profile.delayMs} onValueChange={(value) => setProfile({ ...profile, name: 'Custom', delayMs: value as number })} onValueCommitted={() => void apply(profile)} /></label>
      <label>DUPLICATES <output>{profile.duplicatePercent}%</output><Slider min={0} max={30} step={1} value={profile.duplicatePercent} onValueChange={(value) => setProfile({ ...profile, name: 'Custom', duplicatePercent: value as number })} onValueCommitted={() => void apply(profile)} /></label>
      <div className="link-stats">{Object.entries(stats).map(([direction, values]) => <div key={direction}><strong>{direction.replaceAll('_', ' → ')}</strong><span>{values.received ?? 0} RX</span><span>{values.dropped ?? 0} DROP</span><span>{values.duplicated ?? 0} DUP</span></div>)}</div>
      <p className="editor-help">Seed {profile.seed} makes every impairment run repeatable.</p>
    </div>
  );
}
