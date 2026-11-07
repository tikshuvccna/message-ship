import type { AmmoDef, AmmoId, CreatureDef, NodeStats, VoyageConfig, VoyageStats } from '../contract';
import type { Schedule } from './director';
import { CANNON_IDS, HULL_RX, HULL_RY, STATIONS, halfBeam, onDeck, type CannonId } from './layout';
import { clamp } from './math';
import { Rng } from './rng';
import { T } from './texts';
import type {
  Boss, Bolt, Cannon, Creature, Fire, Floater, FloatKind, Leak, LooseItem, Player, Projectile, RackSlot, SimEvent, Lightning, WaveSlam,
} from './types';

export interface InputState { mx: number; my: number; action: boolean; throwIt: boolean }

export interface ShipState {
  y: number; vy: number;
  wheel: number;            // -1..1
  speed: number;            // forward m/s (scroll speed)
  dist: number;             // metres sailed in this node
  heave: number; roll: number; pitch: number;
  hull: number; water: number;
  sail: 0 | 1 | 2;          // 0 spread, 1 half, 2 furled
  sinking: number;          // -1 not sinking, else seconds
  shake: number;
  knock: number;            // recent knock (display)
}

export interface BitState {
  x: number; y: number; z: number;
  vx: number; vy: number;
  carry: AmmoId | null;
  task: 'idle' | 'leak' | 'ball' | 'return';
  target: number;           // uid
  t: number;
  cool: number;
  work: number;
}

export interface SimData { creatures: readonly CreatureDef[]; ammo: readonly AmmoDef[] }

export type FullConfig = VoyageConfig & { difficulty?: number; bottleId?: string };

export interface World {
  cfg: FullConfig;
  stats: VoyageStats;
  data: SimData;
  sched: Schedule;
  rng: Rng;
  t: number;
  frame: number;
  uidN: number;
  ship: ShipState;
  players: Player[];
  inputs: InputState[];
  bit: BitState | null;
  cannons: Record<CannonId, Cannon>;
  rack: RackSlot[];
  items: LooseItem[];
  leaks: Leak[];
  fires: Fire[];
  creatures: Creature[];
  shots: Projectile[];
  bolts: Bolt[];
  floaters: Floater[];
  storm: { level: number; target: number; lightning: Lightning | null; nextLightning: number; slam: WaveSlam | null; nextSlam: number };
  fog: { level: number; target: number };
  boss: Boss | null;
  events: SimEvent[];
  acc: NodeStats;
  combo: number;
  comboT: number;
  schedIdx: number;
  wavesSpawned: number;
  buffs: { shield: number; double: number; speed: number };
  hintCd: Record<string, number>;
  flags: { water: boolean; hull: boolean };
  over: boolean;
  doneT: number;            // -1 until the node is finished, then countdown to 'done'
  arrived: boolean;
  tutorial: { step: number; t: number };
  /** ammo id -> Hebrew label */
  ammoName: Record<string, string>;
  /** assist target per cannon (uid, 0 none) for the renderer */
  assist: Record<CannonId, number>;
}

export function uid(w: World): number {
  return ++w.uidN;
}

export function emit(w: World, ev: SimEvent): void {
  w.events.push(ev);
}

export function sfx(w: World, name: string, x?: number): void {
  w.events.push(x === undefined ? { e: 'sfx', name } : { e: 'sfx', name, x });
}

export function createWorld(cfg: FullConfig, data: SimData, sched: Schedule): World {
  const rng = new Rng(cfg.seed);
  const twoP = !!cfg.twoPlayers;
  const mkPlayer = (idx: number, x: number, y: number): Player => ({
    idx, x, y, vx: 0, vy: 0, face: -Math.PI / 2, held: null, at: null, job: null, walk: 0, stepT: 0,
  });
  const cannons = {} as Record<CannonId, Cannon>;
  for (const id of CANNON_IDS) {
    const base = id === 'cannon_bow' ? 0 : id === 'cannon_stern' ? Math.PI : id === 'cannon_far' ? Math.PI / 2 : -Math.PI / 2;
    cannons[id] = { id, aim: base, loaded: null, loadT: 0, charges: 0, jam: 0, recoil: 0, fireCd: 0 };
  }
  const ammoName: Record<string, string> = {};
  for (const a of data.ammo) ammoName[a.id] = a.he;
  const stats = { ...cfg.stats };
  const hullMax = Math.max(1, stats.hullMax || 100);
  const w: World = {
    cfg, stats, data, sched, rng, t: 0, frame: 0, uidN: 0,
    ship: {
      y: 0, vy: 0, wheel: 0, speed: 3, dist: 0, heave: 0, roll: 0, pitch: 0,
      hull: hullMax * clamp(cfg.checkpointHull || 1, 0.05, 1), water: 0, sail: 0, sinking: -1, shake: 0, knock: 0,
    },
    players: twoP ? [mkPlayer(0, -2.2, 0.6), mkPlayer(1, -2.2, -1.2)] : [mkPlayer(0, -2.4, 0.2)],
    inputs: [{ mx: 0, my: 0, action: false, throwIt: false }, { mx: 0, my: 0, action: false, throwIt: false }],
    bit: twoP ? null : { x: -0.6, y: 1.2, z: 1.3, vx: 0, vy: 0, carry: null, task: 'idle', target: 0, t: 0, cool: 0, work: 0 },
    cannons,
    rack: [],
    items: [],
    leaks: [], fires: [], creatures: [], shots: [], bolts: [], floaters: [],
    storm: { level: 0, target: 0, lightning: null, nextLightning: 8, slam: null, nextSlam: 10 },
    fog: { level: 0, target: 0 },
    boss: null,
    events: [],
    acc: { shots: 0, hits: 0, rightAmmo: 0, wrongAmmo: 0, cleaned: [], coins: 0, hullLeft: 0, secondsPlayed: 0, bottles: [] },
    combo: 0, comboT: 0,
    schedIdx: 0, wavesSpawned: 0,
    buffs: { shield: stats.shield ? 3 : 0, double: 0, speed: 0 },
    hintCd: {},
    flags: { water: false, hull: false },
    over: false, doneT: -1, arrived: false,
    tutorial: { step: sched.tutorial ? 0 : 99, t: 0 },
    ammoName,
    assist: { cannon_bow: 0, cannon_stern: 0, cannon_far: 0, cannon_near: 0 },
  };
  setRack(w, cfg.ammo.length ? cfg.ammo : (['addr', 'code', 'fmt', 'size', 'time'] as AmmoId[]));
  // a bucket and a plank lie ready on deck
  w.items.push(mkItem(w, 'bucket', 3.3, -2.35, { full: true }));
  return w;
}

export function mkItem(w: World, kind: LooseItem['kind'], x: number, y: number, extra: Partial<LooseItem> = {}): LooseItem {
  return { uid: uid(w), kind, x, y, z: 0, vx: 0, vy: 0, vz: 0, from: -1, rest: 0, ...extra };
}

export function setRack(w: World, ammo: readonly AmmoId[]): void {
  const list = ammo.slice(0, 7);
  w.rack = list.map((a) => ({ ammo: a, has: true, refill: 0 }));
}

export function hullMax(w: World): number {
  return Math.max(1, w.stats.hullMax || 100);
}

/** Convert a world-relative point to ship-local (deck) coordinates. */
export function toLocal(w: World, x: number, y: number): { x: number; y: number } {
  return { x, y: y - w.ship.y };
}

/** Nearest point on the deck edge (ship-local) for a world point outside the hull. */
export function hullContact(w: World, x: number, y: number): { x: number; y: number } {
  const lx = clamp(x, -7.2, 6.8);
  const side = y - w.ship.y >= 0 ? 1 : -1;
  return { x: lx, y: side * Math.max(0.5, halfBeam(lx) - 0.6) };
}

/** Damage the hull (absorbed by the shield buff). x/y are ship-local. */
export function hullHit(w: World, dmg: number, x: number, y: number): boolean {
  if (w.over || w.ship.sinking >= 0) return false;
  if (w.buffs.shield > 0) {
    w.buffs.shield--;
    emit(w, { e: 'hullhit', dmg: 0, x, y, shield: true });
    sfx(w, 'hit_wrong', x);
    return false;
  }
  w.ship.hull = Math.max(0, w.ship.hull - dmg);
  w.ship.shake = Math.min(1, w.ship.shake + dmg / 14);
  emit(w, { e: 'hullhit', dmg, x, y });
  return true;
}

export function addLeak(w: World, x: number, y: number, size = 1): void {
  if (w.leaks.length >= 7) return;
  // keep it on the walkable deck, away from colliders
  const p = deckPoint(w, x, y);
  for (const l of w.leaks) if (Math.hypot(l.x - p.x, l.y - p.y) < 0.7) { l.size = Math.min(2, l.size + 0.5); return; }
  w.leaks.push({ uid: uid(w), x: p.x, y: p.y, size, age: 0 });
  emit(w, { e: 'leak', x: p.x, y: p.y });
  sfx(w, 'creak', p.x);
}

export function addFire(w: World, x: number, y: number): void {
  if (w.fires.length >= 5) return;
  const p = deckPoint(w, x, y);
  for (const f of w.fires) if (Math.hypot(f.x - p.x, f.y - p.y) < 0.8) { f.level = Math.min(1, f.level + 0.3); return; }
  w.fires.push({ uid: uid(w), x: p.x, y: p.y, level: 0.25, spreadT: 0 });
  emit(w, { e: 'fire', x: p.x, y: p.y });
  sfx(w, 'fire', p.x);
}

/** A walkable deck point near (x, y), outside the station colliders. */
export function deckPoint(w: World, x: number, y: number): { x: number; y: number } {
  let px = clamp(x, -7.0, 6.2);
  const hb = halfBeam(px) - 0.75;
  let py = clamp(y, -hb, hb);
  for (let k = 0; k < 6; k++) {
    let hit = false;
    for (const s of Object.values(STATIONS)) {
      const r = s.rect;
      if (!r) continue;
      if (px > r.x0 - 0.35 && px < r.x1 + 0.35 && py > r.y0 - 0.35 && py < r.y1 + 0.35) {
        hit = true;
        px += (w.rng.next() - 0.5) * 1.6;
        py = clamp(py * 0.7, -hb, hb);
      }
    }
    if (!hit) break;
  }
  if (!onDeck(px, py, 0.5)) { px = clamp(px, -6, 4); py = clamp(py, -2.5, 2.5); }
  return { x: px, y: py };
}

export function hostileAlive(w: World): number {
  let n = 0;
  for (const c of w.creatures) if (c.hostile && c.state !== 'cleaned' && c.state !== 'gone' && c.state !== 'flee') n++;
  return n;
}

export function hint(w: World, key: string, text: string): void {
  if ((w.hintCd[key] ?? -99) > w.t) return;
  w.hintCd[key] = w.t + 7;
  emit(w, { e: 'hint', text });
}

export function toast(w: World, text: string, kind: 'info' | 'good' | 'bad' = 'info'): void {
  emit(w, { e: 'toast', text, kind });
}

export function shipEllipse(w: World): { cx: number; cy: number; rx: number; ry: number } {
  return { cx: 0, cy: w.ship.y, rx: HULL_RX, ry: HULL_RY };
}

export function spawnFloater(w: World, kind: FloatKind, x: number, y: number, extra: Partial<Floater> = {}): Floater {
  const f: Floater = {
    uid: uid(w), kind, x, y, vx: 0, vy: 0, r: 0.5, variant: 0, value: 0, tag: '', t: 0, alive: true, anchored: true, ...extra,
  };
  w.floaters.push(f);
  return f;
}

/** Spawn coins (they fly to the ship on their own). */
export function dropCoins(w: World, x: number, y: number, total: number): void {
  if (total <= 0) return;
  const n = clamp(Math.round(total / 3), 1, 6);
  let left = total;
  for (let i = 0; i < n; i++) {
    const v = i === n - 1 ? left : Math.floor(total / n);
    left -= v;
    const a = w.rng.range(0, Math.PI * 2);
    const sp = w.rng.range(1.2, 2.6);
    spawnFloater(w, 'coin', x, y, { vx: Math.cos(a) * sp, vy: Math.sin(a) * sp, r: 0.25, value: v, anchored: false });
  }
}

export function labelOf(w: World, held: Player['held']): string | null {
  if (!held) return null;
  if (held.kind === 'ball') return held.ammo ? (w.ammoName[held.ammo] ?? held.ammo) : null;
  if (held.kind === 'plank') return T.plank;
  return held.full ? T.bucket : T.bucketEmpty;
}

export { CANNON_IDS };
