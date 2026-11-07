/**
 * The deck: walking with rectangle colliders, carrying one item, context actions at stations,
 * throwing, hold-to-repair jobs, cannon loading/aiming (with aim assist) and Bit the companion.
 */
import { assistTarget, canFire, clampAim, fireCannon } from './combat';
import { shooDeck, splashOff } from './creatures';
import {
  CANNON_IDS, CANNONS, RACK_SLOT_Y, SHOTS_PER_BALL, STATIONS, WALK_MARGIN, WALK_X_MAX, WALK_X_MIN, halfBeam, onDeck, rackSlotAtX,
  type CannonId, type StationId,
} from './layout';
import { approachAngle, clamp, wrapAngle } from './math';
import { T } from './texts';
import type { Creature, Held, LooseItem, Player } from './types';
import { emit, hullMax, labelOf, mkItem, sfx, type World } from './world';

export const WALK_SPEED = 3.3;
const WALK_ACCEL = 24;
const BODY_R = 0.3;
const AIM_RATE = 1.6;            // rad/s with the stick
const ASSIST_RATE = 0.9;         // rad/s toward the lead when the stick is idle
const ASSIST_RATE_ACTIVE = 0.22; // while the player steers the aim
const GRAV = 9.8;
export const REPAIR_SEC = 1.2;
export const DOUSE_SEC = 1.0;

export type Act =
  | { a: 'leave' }
  | { a: 'man'; c: CannonId }
  | { a: 'helm' }
  | { a: 'load'; c: CannonId }
  | { a: 'loaded' }
  | { a: 'jammed' }
  | { a: 'sail' }
  | { a: 'take'; slot: number }
  | { a: 'return' }
  | { a: 'plank' }
  | { a: 'bucket' }
  | { a: 'fill' }
  | { a: 'repair'; uid: number }
  | { a: 'douse'; uid: number }
  | { a: 'splash'; uid: number }
  | { a: 'shoo'; uid: number }
  | { a: 'pick'; uid: number }
  | { a: 'drop' }
  | { a: 'busy' };

const near = (p: Player, x: number, y: number, r: number): boolean => Math.hypot(p.x - x, p.y - y) <= r;

function stationAt(p: Player): StationId | null {
  let best: StationId | null = null;
  let bd = 1e9;
  for (const s of Object.values(STATIONS)) {
    const d = Math.hypot(p.x - s.use.x, p.y - s.use.y);
    if (d <= s.use.r && d < bd) { bd = d; best = s.id; }
  }
  return best;
}

function deckCreatureNear(w: World, p: Player, r: number): Creature | null {
  let best: Creature | null = null;
  let bd = r;
  for (const c of w.creatures) {
    if (c.state !== 'deck') continue;
    const d = Math.hypot(c.dx - p.x, c.dy - p.y);
    if (d <= bd + c.r) { bd = d - c.r; best = c; }
  }
  return best;
}

/** Rack slot picked by the player's x position (the nearest full one to it). */
export function rackSlotFor(w: World, p: Player): number {
  const n = w.rack.length;
  const want = rackSlotAtX(p.x, n);
  let best = -1;
  let bd = 1e9;
  w.rack.forEach((s, i) => {
    const d = Math.abs(i - want);
    if (s.has && d < bd) { bd = d; best = i; }
  });
  return best;
}

/** What the action button would do for this player right now. */
export function decide(w: World, p: Player): Act | null {
  if (p.job) return { a: 'busy' };
  if (p.at) return { a: 'leave' };
  const h = p.held;
  if (h?.kind === 'plank') {
    let best = -1, bd = 1.15;
    for (const l of w.leaks) { const d = Math.hypot(l.x - p.x, l.y - p.y); if (d < bd) { bd = d; best = l.uid; } }
    if (best >= 0) return { a: 'repair', uid: best };
  }
  if (h?.kind === 'bucket' && h.full) {
    const c = deckCreatureNear(w, p, 1.3);
    if (c) return { a: 'splash', uid: c.uid };
    let best = -1, bd = 1.25;
    for (const f of w.fires) { const d = Math.hypot(f.x - p.x, f.y - p.y); if (d < bd) { bd = d; best = f.uid; } }
    if (best >= 0) return { a: 'douse', uid: best };
  }
  if (h?.kind === 'ball') {
    const c = deckCreatureNear(w, p, 1.3);
    if (c) return { a: 'shoo', uid: c.uid };
  }
  const st = stationAt(p);
  if (st) {
    switch (st) {
      case 'cannon_bow': case 'cannon_stern': case 'cannon_far': case 'cannon_near': {
        const c = w.cannons[st];
        if (c.jam) return { a: 'jammed' };
        if (h?.kind === 'ball') return { a: 'load', c: st }; // loads, refills or swaps the rule
        if (!h) return { a: 'man', c: st };
        break;
      }
      case 'wheel':
        if (!h) return { a: 'helm' };
        break;
      case 'mast':
        return { a: 'sail' };
      case 'rack': {
        if (!h) {
          const s = rackSlotFor(w, p);
          if (s >= 0) return { a: 'take', slot: s };
        } else if (h.kind === 'ball') return { a: 'return' };
        break;
      }
      case 'planks':
        if (!h) return { a: 'plank' };
        break;
      case 'barrel':
        if (!h) return { a: 'bucket' };
        if (h.kind === 'bucket' && !h.full) return { a: 'fill' };
        break;
      case 'hatch':
        break;
    }
  }
  if (!h) {
    let best: LooseItem | null = null, bd = 0.95;
    for (const it of w.items) {
      if (it.z > 0.2 || it.bit) continue;
      const d = Math.hypot(it.x - p.x, it.y - p.y);
      if (d < bd) { bd = d; best = it; }
    }
    if (best) return { a: 'pick', uid: best.uid };
    return null;
  }
  return { a: 'drop' };
}

export function promptOf(w: World, p: Player, act: Act | null): string | null {
  if (!act) return null;
  switch (act.a) {
    case 'leave': {
      if (p.at === 'wheel') return T.leave;
      if (p.at) {
        const c = w.cannons[p.at];
        return canFire(w, p.at) ? T.fire : c.jam ? T.jammed : T.leave;
      }
      return T.leave;
    }
    case 'man': return T.man;
    case 'helm': return T.helm;
    case 'load': return T.load;
    case 'loaded': return T.loaded;
    case 'jammed': return T.jammed;
    case 'sail': return T.sail(w.ship.sail);
    case 'take': { const s = w.rack[act.slot]; return s ? T.takeBall(w.ammoName[s.ammo] ?? s.ammo) : null; }
    case 'return': return T.returnBall;
    case 'plank': return T.takePlank;
    case 'bucket': return T.takeBucket;
    case 'fill': return T.fillBucket;
    case 'repair': return T.repair;
    case 'douse': return T.douse;
    case 'splash': return T.splash;
    case 'shoo': return T.shoo;
    case 'pick': { const it = w.items.find((i) => i.uid === act.uid); return it ? `${T.pick}: ${labelOf(w, it) ?? ''}` : T.pick; }
    case 'drop': return T.drop;
    case 'busy': return p.job?.kind === 'fire' ? T.dousing : T.repairing;
  }
}

function perform(w: World, p: Player, act: Act): void {
  switch (act.a) {
    case 'leave':
      p.at = null;
      break;
    case 'man':
      p.at = act.c;
      p.face = w.cannons[act.c].aim;
      break;
    case 'helm':
      p.at = 'wheel';
      break;
    case 'load': {
      const c = w.cannons[act.c];
      if (p.held?.kind === 'ball' && p.held.ammo) {
        c.loaded = p.held.ammo;
        c.charges = SHOTS_PER_BALL;
        c.loadT = Math.max(0.2, w.stats.reloadSec || 1.6);
        p.held = null;
        p.at = act.c;
        sfx(w, 'load', STATIONS[act.c].x);
      }
      break;
    }
    case 'sail':
      w.ship.sail = ((w.ship.sail + 1) % 3) as 0 | 1 | 2;
      sfx(w, 'creak', STATIONS.mast.x);
      break;
    case 'take': {
      const s = w.rack[act.slot];
      if (s && s.has) {
        s.has = false;
        s.refill = 1.6;
        p.held = { kind: 'ball', ammo: s.ammo };
        sfx(w, 'pickup', p.x);
      }
      break;
    }
    case 'return': {
      const am = p.held?.ammo;
      const s = w.rack.find((r) => r.ammo === am && !r.has);
      if (s) { s.has = true; s.refill = 0; }
      p.held = null;
      sfx(w, 'drop', p.x);
      break;
    }
    case 'plank':
      p.held = { kind: 'plank' };
      sfx(w, 'plank', p.x);
      break;
    case 'bucket':
      p.held = { kind: 'bucket', full: true };
      sfx(w, 'pickup', p.x);
      break;
    case 'fill':
      if (p.held) p.held.full = true;
      sfx(w, 'splash', p.x);
      break;
    case 'repair':
      p.job = { kind: 'leak', uid: act.uid, t: 0, need: REPAIR_SEC / (w.stats.repairSpeed || 1) };
      break;
    case 'douse':
      p.job = { kind: 'fire', uid: act.uid, t: 0, need: DOUSE_SEC / (w.stats.repairSpeed || 1) };
      break;
    case 'splash': {
      const c = w.creatures.find((k) => k.uid === act.uid);
      if (c && p.held) { splashOff(w, c); p.held.full = false; }
      break;
    }
    case 'shoo': {
      const c = w.creatures.find((k) => k.uid === act.uid);
      if (c && p.held?.ammo) { shooDeck(w, c, p.held.ammo); p.held = null; }
      break;
    }
    case 'pick': {
      const i = w.items.findIndex((it) => it.uid === act.uid);
      const it = w.items[i];
      if (it) {
        p.held = heldOf(it);
        w.items.splice(i, 1);
        sfx(w, 'pickup', p.x);
      }
      break;
    }
    case 'drop': {
      if (p.held) {
        const fx = Math.cos(p.face) * 0.45, fy = Math.sin(p.face) * 0.45;
        const it = mkItem(w, p.held.kind, p.x + fx, p.y + fy, { ...p.held });
        settleItem(it);
        w.items.push(it);
        p.held = null;
        sfx(w, 'drop', p.x);
      }
      break;
    }
    case 'loaded': case 'jammed': case 'busy':
      break;
  }
}

function heldOf(it: LooseItem): Held {
  const h: Held = { kind: it.kind };
  if (it.ammo) h.ammo = it.ammo;
  if (it.kind === 'bucket') h.full = !!it.full;
  return h;
}

/** Keep a resting item on the walkable deck, outside colliders. */
function settleItem(it: LooseItem): void {
  it.x = clamp(it.x, WALK_X_MIN, WALK_X_MAX);
  const hb = halfBeam(it.x) - WALK_MARGIN;
  it.y = clamp(it.y, -hb, hb);
  for (const s of Object.values(STATIONS)) {
    const r = s.rect;
    if (!r) continue;
    if (it.x > r.x0 - 0.15 && it.x < r.x1 + 0.15 && it.y > r.y0 - 0.15 && it.y < r.y1 + 0.15) {
      const dl = it.x - (r.x0 - 0.15), dr = r.x1 + 0.15 - it.x, dd = it.y - (r.y0 - 0.15), du = r.y1 + 0.15 - it.y;
      const m = Math.min(dl, dr, dd, du);
      if (m === dl) it.x = r.x0 - 0.16;
      else if (m === dr) it.x = r.x1 + 0.16;
      else if (m === dd) it.y = r.y0 - 0.16;
      else it.y = r.y1 + 0.16;
    }
  }
}

// ---- throwing ---------------------------------------------------------------

export function throwItem(w: World, p: Player): void {
  if (!p.held) return;
  const z0 = 1.1;
  const fx = Math.cos(p.face), fy = Math.sin(p.face);
  // auto target: a free partner, or (for a ball) an empty cannon, in front of us
  let tx = p.x + fx * 3.6, ty = p.y + fy * 3.6, tz = 0;
  let bestScore = 1e9;
  const consider = (x: number, y: number, z: number): void => {
    const dx = x - p.x, dy = y - p.y;
    const d = Math.hypot(dx, dy);
    if (d < 0.8 || d > 6.5) return;
    const ang = Math.abs(wrapAngle(Math.atan2(dy, dx) - p.face));
    if (ang > (45 * Math.PI) / 180) return;
    const score = ang * 4 + d * 0.3;
    if (score < bestScore) { bestScore = score; tx = x; ty = y; tz = z; }
  };
  for (const o of w.players) if (o !== p && !o.held && !o.job) consider(o.x, o.y, 0.95);
  if (p.held.kind === 'ball') {
    for (const id of CANNON_IDS) {
      const c = w.cannons[id];
      if (!c.loaded && !c.jam) consider(STATIONS[id].x, STATIONS[id].y, 0.7);
    }
    for (const c of w.creatures) if (c.state === 'deck') consider(c.dx, c.dy, 0.4);
  }
  const dx = tx - p.x, dy = ty - p.y;
  const d = Math.hypot(dx, dy);
  const Tt = clamp(d / 6.5, 0.32, 0.85);
  const vz = (tz - z0 + 0.5 * GRAV * Tt * Tt) / Tt;
  const it = mkItem(w, p.held.kind, p.x + fx * 0.3, p.y + fy * 0.3, { ...p.held, z: z0, vx: dx / Tt, vy: dy / Tt, vz, from: p.idx });
  w.items.push(it);
  p.held = null;
  sfx(w, 'drop', p.x);
}

export function stepItems(w: World, dt: number): void {
  for (const it of w.items) {
    if (it.bit) continue;
    const flying = it.z > 0 || it.vz !== 0;
    if (!flying) { it.rest += dt; continue; }
    it.vz -= GRAV * dt;
    it.x += it.vx * dt;
    it.y += it.vy * dt;
    it.z += it.vz * dt;
    // catch by a free player
    for (const o of w.players) {
      if (o.held || o.job || o.at) continue;
      if (o.idx === it.from && it.vz > -1) continue;
      if (it.z > 0.25 && it.z < 1.9 && Math.hypot(o.x - it.x, o.y - it.y) < 0.62) {
        o.held = heldOf(it);
        it.uid = -1;
        sfx(w, 'pickup', o.x);
        break;
      }
    }
    if (it.uid < 0) continue;
    if (it.kind === 'ball' && it.ammo) {
      // lands in an empty cannon
      for (const id of CANNON_IDS) {
        const c = w.cannons[id];
        if (c.loaded || c.jam) continue;
        if (it.z < 1.4 && Math.hypot(STATIONS[id].x - it.x, STATIONS[id].y - it.y) < 0.75) {
          c.loaded = it.ammo;
          c.charges = SHOTS_PER_BALL;
          c.loadT = Math.max(0.2, w.stats.reloadSec || 1.6);
          it.uid = -1;
          sfx(w, 'load', STATIONS[id].x);
          break;
        }
      }
      if (it.uid < 0) continue;
      // hits a boarded creature
      for (const c of w.creatures) {
        if (c.state !== 'deck') continue;
        if (it.z < 1.5 && Math.hypot(c.dx - it.x, c.dy - it.y) < c.r + 0.25) {
          shooDeck(w, c, it.ammo);
          it.uid = -1;
          break;
        }
      }
      if (it.uid < 0) continue;
    }
    // bump into station blocks: drop straight down
    if (it.z < 0.9) {
      for (const s of Object.values(STATIONS)) {
        const r = s.rect;
        if (r && it.x > r.x0 && it.x < r.x1 && it.y > r.y0 && it.y < r.y1) { it.vx *= -0.2; it.vy *= -0.2; }
      }
    }
    if (it.z <= 0) {
      it.z = 0;
      if (!onDeck(it.x, it.y, 0.15)) {
        // overboard
        emit(w, { e: 'splash', x: it.x, y: w.ship.y + it.y, local: true });
        sfx(w, 'splash', it.x);
        it.uid = -1;
        continue;
      }
      if (it.vz < -2.5) {
        it.vz = -it.vz * 0.28;
        it.vx *= 0.45;
        it.vy *= 0.45;
        sfx(w, 'drop', it.x);
      } else {
        it.vz = 0;
        it.vx = 0;
        it.vy = 0;
        it.rest = 0;
        settleItem(it);
      }
    }
  }
  if (w.items.some((i) => i.uid < 0)) w.items = w.items.filter((i) => i.uid >= 0);
}

// ---- players ---------------------------------------------------------------

export function stepPlayers(w: World, dt: number): void {
  for (const p of w.players) {
    const inp = w.inputs[p.idx] ?? { mx: 0, my: 0, action: false, throwIt: false };
    let mx = inp.mx, my = inp.my;
    const ml = Math.hypot(mx, my);
    if (ml > 1) { mx /= ml; my /= ml; }

    // action button
    if (inp.action) {
      inp.action = false;
      if (w.ship.sinking < 0) {
        const act = decide(w, p);
        if (act) perform(w, p, act);
      }
    }
    // throw / fire button
    if (inp.throwIt) {
      inp.throwIt = false;
      if (p.at && p.at !== 'wheel') fireCannon(w, p.at);
      else if (p.held && !p.at) throwItem(w, p);
    }

    // hold-to-repair job: stay put; moving away cancels
    if (p.job) {
      const job = p.job;
      if (ml > 0.35) { p.job = null; }
      else {
        const target = job.kind === 'leak' ? w.leaks.find((l) => l.uid === job.uid) : w.fires.find((f) => f.uid === job.uid);
        if (!target) p.job = null;
        else {
          p.face = Math.atan2(target.y - p.y, target.x - p.x);
          job.t += dt;
          if (job.t >= job.need) {
            if (job.kind === 'leak') {
              w.leaks = w.leaks.filter((l) => l.uid !== job.uid);
              w.ship.hull = Math.min(hullMax(w), w.ship.hull + 3);
              p.held = null;
              sfx(w, 'plank', target.x);
            } else {
              w.fires = w.fires.filter((f) => f.uid !== job.uid);
              if (p.held) p.held.full = false;
              sfx(w, 'extinguish', target.x);
            }
            emit(w, { e: 'fixed', kind: job.kind, x: target.x, y: target.y });
            p.job = null;
          }
        }
      }
      p.vx = 0;
      p.vy = 0;
      continue;
    }

    if (p.at) {
      // stand at the station's use point
      const st = STATIONS[p.at];
      p.x += (st.use.x - p.x) * Math.min(1, dt * 12);
      p.y += (st.use.y - p.y) * Math.min(1, dt * 12);
      p.vx = 0;
      p.vy = 0;
      if (p.at === 'wheel') {
        p.face = Math.PI;
      } else {
        const id = p.at;
        const c = w.cannons[id];
        const lead = assistTarget(w, id);
        w.assist[id] = lead ? lead.uid : 0;
        if (ml > 0.2) {
          const want = clampAim(id, Math.atan2(my, mx));
          c.aim = clampAim(id, approachAngle(c.aim, want, AIM_RATE * dt * Math.min(1, ml)));
          if (lead) c.aim = clampAim(id, approachAngle(c.aim, lead.angle, ASSIST_RATE_ACTIVE * dt));
        } else if (lead) {
          c.aim = clampAim(id, approachAngle(c.aim, lead.angle, ASSIST_RATE * dt));
        }
        p.face = c.aim;
      }
      continue;
    }

    // walking
    const tvx = mx * WALK_SPEED, tvy = my * WALK_SPEED;
    const ax = tvx - p.vx, ay = tvy - p.vy;
    const al = Math.hypot(ax, ay);
    const maxA = WALK_ACCEL * dt;
    if (al > maxA) { p.vx += (ax / al) * maxA; p.vy += (ay / al) * maxA; }
    else { p.vx = tvx; p.vy = tvy; }
    // a rolling deck nudges people a little
    p.vy += -w.ship.roll * 3 * dt;
    p.x += p.vx * dt;
    p.y += p.vy * dt;
    collideBody(p);
    const sp = Math.hypot(p.vx, p.vy);
    if (ml > 0.2) p.face = Math.atan2(my, mx);
    if (sp > 0.4) {
      p.walk += dt * sp * 2.2;
      p.stepT -= dt;
      if (p.stepT <= 0) { p.stepT = 0.34; sfx(w, 'step', p.x); }
    } else p.stepT = 0;
  }
  // players push each other apart
  const [a, b] = w.players;
  if (a && b) {
    const dx = b.x - a.x, dy = b.y - a.y;
    const d = Math.hypot(dx, dy);
    const min = BODY_R * 2;
    if (d < min && d > 1e-6) {
      const k = (min - d) / 2;
      if (!a.at) { a.x -= (dx / d) * k; a.y -= (dy / d) * k; }
      if (!b.at) { b.x += (dx / d) * k; b.y += (dy / d) * k; }
      collideBody(a);
      collideBody(b);
    }
  }
}

/** Push a body out of station rectangles and keep it inside the rails. */
export function collideBody(p: { x: number; y: number; vx: number; vy: number }): void {
  for (let iter = 0; iter < 2; iter++) {
    for (const s of Object.values(STATIONS)) {
      const r = s.rect;
      if (!r) continue;
      const x0 = r.x0 - BODY_R, x1 = r.x1 + BODY_R, y0 = r.y0 - BODY_R, y1 = r.y1 + BODY_R;
      if (p.x <= x0 || p.x >= x1 || p.y <= y0 || p.y >= y1) continue;
      const dl = p.x - x0, dr = x1 - p.x, dd = p.y - y0, du = y1 - p.y;
      const m = Math.min(dl, dr, dd, du);
      if (m === dl) { p.x = x0; p.vx = Math.min(0, p.vx); }
      else if (m === dr) { p.x = x1; p.vx = Math.max(0, p.vx); }
      else if (m === dd) { p.y = y0; p.vy = Math.min(0, p.vy); }
      else { p.y = y1; p.vy = Math.max(0, p.vy); }
    }
    if (p.x < WALK_X_MIN) { p.x = WALK_X_MIN; p.vx = Math.max(0, p.vx); }
    if (p.x > WALK_X_MAX) { p.x = WALK_X_MAX; p.vx = Math.min(0, p.vx); }
    const hb = Math.max(0.3, halfBeam(p.x) - WALK_MARGIN);
    if (p.y > hb) { p.y = hb; p.vy = Math.min(0, p.vy); }
    if (p.y < -hb) { p.y = -hb; p.vy = Math.max(0, p.vy); }
  }
}

// ---- cannons & rack --------------------------------------------------------

export function stepCannons(w: World, dt: number): void {
  for (const id of CANNON_IDS) {
    const c = w.cannons[id];
    c.loadT = Math.max(0, c.loadT - dt);
    c.recoil = Math.max(0, c.recoil - dt * 3);
    c.fireCd = Math.max(0, c.fireCd - dt);
    if (c.jam && !w.creatures.some((k) => k.uid === c.jam && k.state === 'deck')) c.jam = 0;
    if (!w.players.some((p) => p.at === id)) {
      w.assist[id] = 0;
      // unmanned barrels slowly return to center
      const base = CANNONS[id].base;
      c.aim = approachAngle(c.aim, base, 0.3 * dt);
    }
  }
  for (const s of w.rack) {
    if (s.has) continue;
    s.refill -= dt;
    if (s.refill <= 0) s.has = true;
  }
}

// ---- Bit, the lantern companion (single player) ------------------------------

const BIT_SPEED = 2.4;
const BIT_REPAIR = 0.4; // fraction of a player's repair speed

export function stepBit(w: World, dt: number): void {
  const b = w.bit;
  if (!b) return;
  b.t += dt;
  b.cool = Math.max(0, b.cool - dt);
  const moveTo = (x: number, y: number): number => {
    const dx = x - b.x, dy = y - b.y;
    const d = Math.hypot(dx, dy);
    const s = Math.min(BIT_SPEED, d * 3);
    const tvx = d > 1e-4 ? (dx / d) * s : 0, tvy = d > 1e-4 ? (dy / d) * s : 0;
    b.vx += (tvx - b.vx) * Math.min(1, dt * 5);
    b.vy += (tvy - b.vy) * Math.min(1, dt * 5);
    b.x += b.vx * dt;
    b.y += b.vy * dt;
    return d;
  };
  b.z = 1.25 + Math.sin(b.t * 2.4) * 0.12;
  if (b.task === 'leak') {
    const l = w.leaks.find((k) => k.uid === b.target);
    const takenByPlayer = w.players.some((p) => p.job?.uid === b.target);
    if (!l || takenByPlayer) { b.task = 'idle'; b.t = 0; return; }
    const d = moveTo(l.x, l.y - 0.1);
    if (d < 0.35) {
      b.work += dt * BIT_REPAIR * (w.stats.repairSpeed || 1);
      if (b.work >= REPAIR_SEC) {
        b.work = 0;
        w.leaks = w.leaks.filter((k) => k.uid !== l.uid);
        emit(w, { e: 'fixed', kind: 'leak', x: l.x, y: l.y });
        sfx(w, 'plank', l.x);
        b.task = 'idle';
        b.cool = 1.5;
      }
    }
    return;
  }
  if (b.task === 'ball') {
    const it = w.items.find((i) => i.uid === b.target);
    if (!it || it.z > 0.05) { b.task = 'idle'; return; }
    const d = moveTo(it.x, it.y);
    if (d < 0.3) {
      b.carry = it.ammo ?? null;
      w.items = w.items.filter((i) => i.uid !== it.uid);
      b.task = 'return';
      sfx(w, 'pickup', b.x);
    }
    return;
  }
  if (b.task === 'return') {
    const d = moveTo(STATIONS.rack.use.x, RACK_SLOT_Y - 0.5);
    if (d < 0.4) {
      const s = w.rack.find((r) => r.ammo === b.carry && !r.has);
      if (s) { s.has = true; s.refill = 0; }
      b.carry = null;
      b.task = 'idle';
      b.cool = 0.8;
      sfx(w, 'drop', b.x);
    }
    return;
  }
  // idle: pick a job
  if (b.cool <= 0) {
    const leak = w.leaks.find((l) => !w.players.some((p) => p.job?.uid === l.uid));
    if (leak) { b.task = 'leak'; b.target = leak.uid; b.work = 0; return; }
    const stray = w.items.find((i) => i.kind === 'ball' && i.z <= 0.01 && i.rest > 1.5);
    if (stray) { b.task = 'ball'; b.target = stray.uid; return; }
  }
  const p = w.players[0];
  if (p) moveTo(p.x - 0.9, p.y + 0.9);
}

