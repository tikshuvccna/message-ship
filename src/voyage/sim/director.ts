/**
 * Node director: turns a VoyageConfig into a deterministic schedule of spawns and events.
 * Pure data; the sim plays it back (and may pull a battle wave forward when the sea is clear).
 */
import type { AmmoId, CreatureDef, NodeKind, VoyageConfig } from '../contract';
import { Rng, hashStr } from './rng';
import { T } from './texts';

export type Mood = 'day' | 'sunset' | 'storm' | 'noise' | 'night';

export interface WaveSpawn { id: string; count: number; side: number; from: 'bow' | 'far' | 'near' | 'stern' }

export type FloatSpec = 'crate' | 'bottle' | 'reef' | 'island' | 'cove' | 'lighthouse' | 'pier' | 'buoy' | 'whirlpool';

export type ScheduleEntry =
  | { at: number; kind: 'wave'; wave: number; spawns: WaveSpawn[] }
  | { at: number; kind: 'float'; what: FloatSpec; yRel: number; variant: number; value: number; tag: string }
  | { at: number; kind: 'friend'; id: string; yRel: number }
  | { at: number; kind: 'toast'; text: string; tone?: 'info' | 'good' | 'bad' }
  | { at: number; kind: 'storm'; level: number }
  | { at: number; kind: 'fog'; level: number }
  | { at: number; kind: 'boss' };

export interface Schedule {
  kind: NodeKind;
  duration: number;
  difficulty: number;
  mood: Mood;
  /** battle/boss/start: the node ends only when the hostiles are gone */
  needsClear: boolean;
  /** harbour/lighthouse: the ship slows down and arrives */
  arrival: boolean;
  tutorial: boolean;
  waves: number;
  /** base swell 0..1 */
  swell: number;
  entries: ScheduleEntry[];
}

export function difficultyOf(cfg: Pick<VoyageConfig, 'leg' | 'nodeId'> & { difficulty?: number }): number {
  if (typeof cfg.difficulty === 'number') return Math.max(0, Math.min(1, cfg.difficulty));
  // legs get harder; nodes deeper in a leg (ids ending in a number) a little harder
  const m = /(\d+)\s*$/.exec(cfg.nodeId);
  const depth = m ? Math.min(8, Number(m[1])) / 8 : 0.4;
  return Math.max(0, Math.min(1, 0.12 + (cfg.leg - 1) * 0.22 + depth * 0.2));
}

/** Creatures that may appear in a leg's battles, filtered by the ammo on the rack. */
export function poolFor(defs: readonly CreatureDef[], leg: number, ammo: readonly AmmoId[]): CreatureDef[] {
  const legOk = (d: CreatureDef): boolean => (leg >= 4 ? d.leg <= 3 : d.leg === leg);
  let pool = defs.filter((d) => d.behavior !== 'boss' && legOk(d) && (ammo.length === 0 || ammo.includes(d.weakness)));
  if (pool.length === 0) pool = defs.filter((d) => d.behavior !== 'boss' && legOk(d));
  if (pool.length === 0) pool = defs.filter((d) => d.behavior !== 'boss');
  return pool;
}

const SIDES: WaveSpawn['from'][] = ['bow', 'far', 'near', 'bow', 'stern'];

export function buildSchedule(cfg: VoyageConfig & { difficulty?: number; bottleId?: string }, defs: readonly CreatureDef[]): Schedule {
  const rng = new Rng(cfg.seed ^ hashStr(cfg.nodeId) ^ (cfg.leg * 7919));
  const diff = difficultyOf(cfg);
  const kind = cfg.nodeKind;
  const pool = poolFor(defs, cfg.leg, cfg.ammo);
  const entries: ScheduleEntry[] = [];
  const bottleId = cfg.bottleId ?? `bottle_${cfg.leg}_${hashStr(cfg.nodeId) % 1000}`;
  const crate = (at: number, yRel: number, value = rng.int(0, 99)): void => {
    entries.push({ at, kind: 'float', what: 'crate', yRel, variant: rng.int(0, 2), value, tag: '' });
  };
  const sched: Schedule = {
    kind, duration: Math.max(10, cfg.duration || 60), difficulty: diff, mood: 'day', needsClear: false, arrival: false,
    tutorial: false, waves: 0, swell: 0.25, entries,
  };
  const D = sched.duration;

  switch (kind) {
    case 'battle': {
      sched.needsClear = true;
      sched.mood = cfg.leg >= 3 ? 'sunset' : 'day';
      const n = Math.max(3, Math.min(5, 3 + Math.floor(diff * 2 + rng.next() * 1.2)));
      sched.waves = n;
      // every weakness of the pool shows up at least once, in a shuffled order
      const order = rng.shuffle(pool.slice());
      let oi = 0;
      for (let w = 0; w < n; w++) {
        const at = 3 + (w * (D * 0.72)) / n;
        const budget = 1 + w * 0.65 + diff * 1.6;
        const spawns: WaveSpawn[] = [];
        let used = 0;
        let guard = 0;
        while (used < budget && guard++ < 12) {
          const def = oi < order.length ? (order[oi++] as CreatureDef) : rng.pick(pool);
          const swarm = def.behavior === 'swarm';
          const count = swarm ? 3 + Math.round(diff * 2) : 1;
          const from = rng.pick(SIDES);
          spawns.push({ id: def.id, count, side: from === 'near' ? -1 : 1, from });
          used += swarm ? 1.3 : def.hp >= 10 ? 1.8 : 1;
        }
        entries.push({ at, kind: 'wave', wave: w, spawns });
      }
      for (let i = 0; i < 2 + Math.round(rng.next()); i++) crate(8 + rng.range(0, D * 0.8), rng.range(-6, 6));
      if (rng.chance(0.35)) entries.push({ at: rng.range(10, D * 0.6), kind: 'float', what: 'reef', yRel: rng.range(-4, 4), variant: rng.int(0, 2), value: 0, tag: '' });
      break;
    }
    case 'island': {
      sched.mood = 'day';
      sched.swell = 0.18;
      entries.push({ at: 1, kind: 'float', what: 'island', yRel: 14, variant: rng.int(0, 3), value: 0, tag: '' });
      for (let i = 0; i < 5; i++) crate(4 + i * (D * 0.16) + rng.range(0, 3), rng.range(-6.5, 6.5));
      entries.push({ at: D * 0.42, kind: 'float', what: 'bottle', yRel: rng.range(-5, 5), variant: 0, value: 0, tag: bottleId });
      entries.push({ at: D * 0.25, kind: 'friend', id: rng.pick(pool).id, yRel: -6.5 });
      // the cove: two reefs make a gate with a treasure crate inside
      const cy = rng.range(-4, 4);
      const at = D * 0.62;
      entries.push({ at, kind: 'float', what: 'cove', yRel: cy + 9.5, variant: rng.int(0, 1), value: 0, tag: '' });
      entries.push({ at, kind: 'float', what: 'reef', yRel: cy + 4.6, variant: 0, value: 0, tag: '' });
      entries.push({ at, kind: 'float', what: 'reef', yRel: cy - 4.6, variant: 1, value: 0, tag: '' });
      entries.push({ at: at + 0.4, kind: 'float', what: 'crate', yRel: cy, variant: 2, value: 200, tag: 'treasure' });
      entries.push({ at: 2, kind: 'toast', text: T.islandHello, tone: 'info' });
      break;
    }
    case 'event': {
      sched.mood = 'sunset';
      const ev = rng.pick(['reefs', 'whirlpool', 'fog'] as const);
      entries.push({ at: D * 0.5, kind: 'float', what: 'bottle', yRel: rng.range(-4, 4), variant: 0, value: 0, tag: bottleId });
      if (ev === 'reefs') {
        entries.push({ at: 2, kind: 'toast', text: T.reefsAhead, tone: 'bad' });
        for (let i = 0; i < 8; i++) {
          entries.push({ at: 5 + i * (D * 0.09), kind: 'float', what: 'reef', yRel: (i % 2 ? 1 : -1) * rng.range(1.5, 6), variant: rng.int(0, 2), value: 0, tag: '' });
        }
        for (let i = 0; i < 3; i++) crate(9 + i * (D * 0.22), rng.range(-6, 6));
      } else if (ev === 'whirlpool') {
        entries.push({ at: 2, kind: 'toast', text: T.whirlpool, tone: 'bad' });
        entries.push({ at: D * 0.3, kind: 'float', what: 'whirlpool', yRel: rng.range(-2, 2), variant: 0, value: 0, tag: '' });
        for (let i = 0; i < 4; i++) crate(D * 0.3 + i * 1.4, (i % 2 ? 1 : -1) * 6);
      } else {
        sched.mood = 'night';
        entries.push({ at: 1, kind: 'fog', level: 0.75 });
        entries.push({ at: 2, kind: 'toast', text: T.fog, tone: 'info' });
        entries.push({ at: D * 0.85, kind: 'fog', level: 0 });
        const drift = pool.filter((d) => d.behavior === 'drift');
        const p = drift.length ? drift : pool;
        sched.needsClear = false;
        entries.push({ at: D * 0.3, kind: 'wave', wave: 0, spawns: [{ id: rng.pick(p).id, count: 1, side: 1, from: 'bow' }] });
        entries.push({ at: D * 0.6, kind: 'wave', wave: 1, spawns: [{ id: rng.pick(p).id, count: 1, side: -1, from: 'bow' }] });
        sched.waves = 2;
        for (let i = 0; i < 3; i++) crate(6 + i * (D * 0.25), rng.range(-6, 6));
      }
      break;
    }
    case 'storm': {
      sched.mood = 'storm';
      sched.swell = 0.6;
      entries.push({ at: 1, kind: 'storm', level: 0.55 + diff * 0.45 });
      entries.push({ at: 2, kind: 'toast', text: T.storm, tone: 'bad' });
      entries.push({ at: D - 6, kind: 'storm', level: 0 });
      const k = 1 + (diff > 0.45 || rng.chance(0.4) ? 1 : 0);
      for (let w = 0; w < k; w++) {
        const def = rng.pick(pool);
        entries.push({ at: D * (0.25 + w * 0.35), kind: 'wave', wave: w, spawns: [{ id: def.id, count: def.behavior === 'swarm' ? 3 : 1, side: w % 2 ? -1 : 1, from: w % 2 ? 'near' : 'bow' }] });
      }
      sched.waves = k;
      for (let i = 0; i < 2; i++) crate(10 + i * (D * 0.35), rng.range(-5, 5));
      break;
    }
    case 'boss': {
      sched.mood = 'noise';
      sched.swell = 0.45;
      sched.needsClear = true;
      sched.duration = Math.max(D, 240);
      entries.push({ at: 1.5, kind: 'boss' });
      entries.push({ at: 0.5, kind: 'toast', text: T.bossHello, tone: 'bad' });
      break;
    }
    case 'harbour':
    case 'lighthouse': {
      sched.mood = kind === 'lighthouse' ? 'sunset' : 'day';
      sched.swell = 0.12;
      sched.arrival = true;
      sched.duration = Math.min(D, 26);
      const dd = sched.duration;
      entries.push({ at: Math.max(1, dd - 11), kind: 'float', what: kind === 'lighthouse' ? 'lighthouse' : 'pier', yRel: 7.5, variant: 0, value: 0, tag: '' });
      entries.push({ at: Math.max(1, dd - 11), kind: 'float', what: 'buoy', yRel: -5, variant: 0, value: 0, tag: '' });
      crate(3, rng.range(-4, 4));
      break;
    }
    case 'start': {
      sched.mood = 'day';
      sched.swell = 0.12;
      sched.tutorial = true;
      sched.needsClear = true;
      const easy = pool.filter((d) => d.behavior === 'drift').sort((a, b) => a.hp - b.hp)[0] ?? pool.slice().sort((a, b) => a.hp - b.hp)[0];
      if (easy) entries.push({ at: Math.max(30, D * 0.45), kind: 'wave', wave: 0, spawns: [{ id: easy.id, count: 1, side: 1, from: 'bow' }] });
      sched.waves = 1;
      for (let i = 0; i < 3; i++) crate(6 + i * 9, [2.5, -3.5, 4.5][i] ?? 0);
      break;
    }
  }
  entries.sort((a, b) => a.at - b.at);
  return sched;
}
