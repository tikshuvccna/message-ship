/** Noise creatures: spawning and behaviours (smooth steering, separation, telegraphed attacks, boarding). */
import type { CreatureDef } from '../contract';
import { cleanCreature, fireBolt } from './combat';
import { HULL_RX, HULL_RY, PX_PER_M, STATIONS, halfBeam, CANNON_IDS, type CannonId } from './layout';
import { clamp, damp, ellipseNorm, limit } from './math';
import { pushShip } from './ship';
import { T } from './texts';
import type { Creature } from './types';
import { addFire, addLeak, dropCoins, emit, hullContact, hullHit, sfx, toast, uid, type World } from './world';

export const TELEGRAPH = 0.8;

export function spawnCreature(
  w: World, def: CreatureDef, from: 'bow' | 'far' | 'near' | 'stern', group = 0, wave = 0, friendly = false, yRel?: number,
): Creature {
  const rng = w.rng;
  const sy = w.ship.y;
  let x = 0, y = 0;
  switch (from) {
    case 'bow': x = rng.range(15, 17); y = sy + rng.range(-5, 5); break;
    case 'stern': x = -rng.range(15, 17); y = sy + rng.range(-4, 4); break;
    case 'far': x = rng.range(-6, 9); y = sy + rng.range(13, 15); break;
    case 'near': x = rng.range(-6, 9); y = sy - rng.range(13, 15); break;
  }
  if (yRel !== undefined) y = sy + yRel;
  const diff = w.sched.difficulty;
  const r = def.radius / PX_PER_M;
  const isCharge = def.behavior === 'charge';
  const c: Creature = {
    uid: uid(w), def, x, y, z: def.behavior === 'swarm' && def.id.includes('gull') ? 1.4 : 0, vx: 0, vy: 0,
    hp: def.hp * (friendly ? 1 : 1 + diff * 0.35), maxHp: 0,
    r, rx: isCharge ? r * 1.25 : r, ry: isCharge ? r * 0.85 : r,
    maxSpeed: (def.speed / PX_PER_M) * (1 + 0.2 * diff),
    state: friendly ? 'act' : 'enter', t: 0, cd: rng.range(5, 8), ang: rng.range(0, Math.PI * 2),
    side: y >= sy ? 1 : -1, attack: null, tx: 0, ty: 0, group, dx: 0, dy: 0, jamming: null, stun: 0, hitFlash: 0,
    face: x > 0 ? -1 : 1, wave, friendly, hostile: !friendly,
    sec: from === 'bow' ? 0 : from === 'far' ? 1 : from === 'stern' ? 2 : 3, secT: rng.range(8, 13),
  };
  c.maxHp = c.hp;
  if (def.behavior === 'drift') {
    // pass by the ship at a fixed lateral offset, from ahead
    c.x = rng.range(15, 17);
    c.side = rng.chance(0.5) ? 1 : -1;
    c.ty = sy + c.side * rng.range(6, 7.6);
    c.y = c.ty + rng.range(-0.8, 0.8);
  }
  if (def.behavior === 'skitter') {
    c.side = from === 'near' ? -1 : from === 'far' ? 1 : rng.chance(0.5) ? 1 : -1;
    c.tx = rng.range(-5, 3.5);
  }
  w.creatures.push(c);
  return c;
}

function inArena(w: World, c: Creature): boolean {
  return Math.abs(c.x) < 13.5 && Math.abs(c.y - w.ship.y) < 11.5;
}

function steerTo(c: Creature, tx: number, ty: number, speed: number, dt: number, arrive = 1.8, accel = 5): void {
  const dx = tx - c.x, dy = ty - c.y;
  const d = Math.hypot(dx, dy);
  const s = d < arrive ? (speed * d) / arrive : speed;
  const dvx = d > 1e-6 ? (dx / d) * s : 0, dvy = d > 1e-6 ? (dy / d) * s : 0;
  const a = limit({ x: (dvx - c.vx) * 3, y: (dvy - c.vy) * 3 }, accel);
  c.vx += a.x * dt;
  c.vy += a.y * dt;
}

function brake(c: Creature, dt: number, rate = 3): void {
  const k = 1 - damp(rate, dt);
  c.vx *= k;
  c.vy *= k;
}

function startTelegraph(w: World, c: Creature, attack: Creature['attack'], tx: number, ty: number): void {
  c.state = 'telegraph';
  c.t = 0;
  c.attack = attack;
  c.tx = tx;
  c.ty = ty;
  emit(w, { e: 'telegraph', uid: c.uid, attack: attack ?? '' });
}

/** A random point on the hull to aim at (world-relative). */
function hullAim(w: World): { x: number; y: number } {
  return { x: w.rng.range(-5.5, 5.5), y: w.ship.y + w.rng.range(-1.6, 1.6) };
}

function cdFor(w: World, base: number, spread: number): number {
  return (base + w.rng.next() * spread) * (1.15 - 0.35 * w.sched.difficulty);
}

export function stepCreatures(w: World, dt: number): void {
  const sy = w.ship.y;
  const list = w.creatures;
  for (const c of list) {
    if (c.state === 'gone') continue;
    c.t += dt;
    c.cd -= dt;
    c.stun = Math.max(0, c.stun - dt);
    c.hitFlash = Math.max(0, c.hitFlash - dt);
    const sp = c.maxSpeed;

    if (c.state === 'cleaned') {
      c.z = Math.min(0.7, c.z + dt * 0.5);
      steerTo(c, c.x + (c.side >= 0 ? 0.5 : -0.5), c.y + c.side * 2, 1, dt);
      if (c.t > 3.2) c.state = 'gone';
      integrate(c, dt);
      continue;
    }
    if (c.state === 'flee') {
      steerTo(c, c.x + 10, c.y + c.side * 10, sp * 2.2, dt, 0.1, 8);
      integrate(c, dt);
      if (Math.abs(c.x) > 24 || Math.abs(c.y - sy) > 19) c.state = 'gone';
      continue;
    }
    if (c.state === 'deck') {
      stepDeckCreature(w, c, dt);
      continue;
    }
    if (c.friendly) {
      // island visitor: swims alongside, waves hello, leaves a gift
      steerTo(c, 1.5 + Math.sin(c.t * 0.4) * 2.5, sy - 5.6 + Math.sin(c.t * 0.9) * 0.4, sp * 2, dt);
      if (c.t > 3 && c.cd > -50) {
        toast(w, T.friendHello, 'good');
        dropCoins(w, c.x, c.y, 6);
        c.cd = -99;
      }
      if (c.t > 18) { c.state = 'flee'; c.side = -1; }
      integrate(c, dt);
      continue;
    }
    if (c.state === 'enter') {
      const tx = clamp(c.x, -10, 10), ty = clamp(c.y, sy - 8, sy + 8);
      steerTo(c, tx, ty, Math.max(sp * 2.2, 2.5), dt, 0.5, 8);
      if (c.def.behavior === 'drift') c.state = 'act';
      else if (inArena(w, c)) { c.state = 'act'; c.t = 0; }
    } else if (c.stun > 0) {
      brake(c, dt, 2);
    } else {
      behave(w, c, dt);
    }
    separate(w, c, dt);
    if (c.state !== 'attack' && !(c.state === 'telegraph' && c.attack === 'board') && c.def.behavior !== 'skitter') avoidHull(w, c, dt);
    integrate(c, dt);
    if (Math.abs(c.x) > 32 || Math.abs(c.y - sy) > 26) c.state = 'gone';
  }
  if (list.some((c) => c.state === 'gone')) w.creatures = list.filter((c) => c.state !== 'gone');
}

function integrate(c: Creature, dt: number): void {
  c.x += c.vx * dt;
  c.y += c.vy * dt;
  if (Math.abs(c.vx) > 0.15) c.face = c.vx > 0 ? 1 : -1;
}

function behave(w: World, c: Creature, dt: number): void {
  const sy = w.ship.y;
  const sp = c.maxSpeed;
  const diff = w.sched.difficulty;
  const b = c.def.behavior;

  if (c.state === 'telegraph') {
    brake(c, dt, 4);
    if (c.t >= TELEGRAPH) doAttack(w, c);
    return;
  }
  if (c.state === 'attack') {
    stepAttack(w, c, dt);
    return;
  }
  if (c.state === 'recover') {
    brake(c, dt, 1.5);
    // drift back out a bit
    const n = hullNormal(w, c);
    c.vx += n.x * 1.2 * dt;
    c.vy += n.y * 1.2 * dt;
    if (c.t > (b === 'charge' ? 1.8 : 0.9)) { c.state = 'act'; c.t = 0; }
    return;
  }
  // 'act'
  const catchUp = (tx: number, ty: number): number => (Math.hypot(tx - c.x, ty - c.y) > 5 ? 1.9 : 1);
  // hover in one cannon's sector for a while, then move to another (readable: "it's on the near side!")
  c.secT -= dt;
  if (b === 'swarm') {
    // a flock moves as one: the sector is a function of the flock id and the clock
    const id = c.wave * 10 + c.group;
    c.sec = (id + Math.floor((w.t + id * 2.7) / 11)) % 4;
  } else if (c.secT <= 0) {
    c.secT = w.rng.range(9, 14);
    const step = w.rng.chance(0.5) ? 1 : 3;
    c.sec = (c.sec + step) % 4;
  }
  const sector = (dist: number): { x: number; y: number } => {
    const j = Math.sin(c.t * 0.35 + c.uid * 1.7);
    const k = Math.cos(c.t * 0.27 + c.uid);
    switch (c.sec) {
      case 0: return { x: 7.6 + dist * 0.75, y: sy + j * 2.6 };
      case 1: return { x: 1 + j * 3.2, y: sy + 3.2 + dist * 0.55 + k * 0.6 };
      case 2: return { x: -7.4 - dist * 0.7, y: sy + 1.6 + j * 2.2 };
      default: return { x: 1 + j * 3.2, y: sy - 3.2 - dist * 0.55 - k * 0.6 };
    }
  };
  switch (b) {
    case 'orbit': {
      const q = sector(7);
      const tx = q.x, ty = q.y;
      steerTo(c, tx, ty, sp * catchUp(tx, ty), dt);
      if (c.cd <= 0 && inArena(w, c)) { const h = hullAim(w); startTelegraph(w, c, 'bolt', h.x, h.y); }
      break;
    }
    case 'shooter': {
      // keep distance on its own side, strafe slowly
      const q = sector(8.5);
      const tx = q.x, ty = q.y;
      steerTo(c, tx, ty, sp * catchUp(tx, ty), dt);
      if (c.cd <= 0 && inArena(w, c)) { const h = hullAim(w); startTelegraph(w, c, 'bolt', h.x, h.y); }
      break;
    }
    case 'charge': {
      const q = sector(8);
      const tx = q.x, ty = q.y;
      steerTo(c, tx, ty, sp * 1.6 * catchUp(tx, ty), dt);
      if (c.cd <= 0 && inArena(w, c) && Math.hypot(tx - c.x, ty - c.y) < 2.5) {
        startTelegraph(w, c, 'charge', 0, sy);
      }
      break;
    }
    case 'drift': {
      const flow = -w.ship.speed * (w.sched.tutorial ? 0.32 : 0.5);
      c.vx += (flow - c.vx) * damp(1.2, dt);
      const ty = c.ty + Math.sin(c.t * 0.7 + c.uid) * 0.6;
      c.vy += ((ty - c.y) * 0.8 - c.vy) * damp(1.5, dt);
      const e = ellipseNorm(c.x, c.y, 0, sy, HULL_RX + c.r + 3.2, HULL_RY + c.r + 3.2);
      if (e < 1 && c.cd <= 0) startTelegraph(w, c, 'shock', c.x, c.y);
      if (c.x < -18) c.state = 'gone';
      break;
    }
    case 'swarm': {
      // a flock hovers together in one sector, members jittering around the flock point
      const q = sector(6);
      const tx = q.x + Math.sin(c.t * 1.9 + c.uid * 2.1) * 1.3, ty = q.y + Math.cos(c.t * 1.6 + c.uid * 1.3) * 0.9;
      steerTo(c, tx, ty, sp * catchUp(tx, ty), dt, 1.2, 9);
      if (c.cd <= 0 && inArena(w, c)) { const h = hullAim(w); startTelegraph(w, c, 'peck', h.x, h.y); }
      break;
    }
    case 'skitter': {
      const tx = c.tx, ty = sy + c.side * (HULL_RY + 0.1 + c.r * 0.5);
      steerTo(c, tx, ty, sp * catchUp(tx, ty), dt, 0.8, 6);
      if (Math.hypot(tx - c.x, ty - c.y) < 0.55 + c.r * 0.5) startTelegraph(w, c, 'board', tx, ty);
      break;
    }
    default:
      break;
  }
  void diff;
}

function doAttack(w: World, c: Creature): void {
  const diff = w.sched.difficulty;
  const b = c.def.behavior;
  c.t = 0;
  switch (c.attack) {
    case 'bolt': {
      const spd = 3.6 + diff * 1.2;
      fireBolt(w, c.uid, c.x, c.y, c.tx, c.ty, spd);
      if (b === 'shooter' && diff > 0.55) {
        const a = Math.atan2(c.ty - c.y, c.tx - c.x) + 0.25;
        fireBolt(w, c.uid, c.x, c.y, c.x + Math.cos(a) * 10, c.y + Math.sin(a) * 10, spd);
      }
      c.state = 'recover';
      c.cd = b === 'shooter' ? cdFor(w, 5.5, 2.5) : cdFor(w, 7, 3);
      break;
    }
    case 'charge': {
      const sy = w.ship.y;
      const dx = 0 - c.x, dy = sy - c.y;
      const l = Math.hypot(dx, dy) || 1;
      const v = Math.max(4.2, c.maxSpeed * 3.4);
      c.vx = (dx / l) * v;
      c.vy = (dy / l) * v;
      c.state = 'attack';
      sfx(w, 'wave_slam', c.x);
      break;
    }
    case 'peck': {
      const dx = c.tx - c.x, dy = c.ty - c.y;
      const l = Math.hypot(dx, dy) || 1;
      c.vx = (dx / l) * 6.5;
      c.vy = (dy / l) * 6.5;
      c.state = 'attack';
      break;
    }
    case 'shock': {
      const e = ellipseNorm(c.x, c.y, 0, w.ship.y, HULL_RX + c.r + 3.8, HULL_RY + c.r + 3.8);
      if (e < 1) {
        const p = hullContact(w, c.x, c.y);
        if (hullHit(w, 3, p.x, p.y)) {
          sfx(w, 'thunder', c.x);
          if (w.rng.chance(0.3)) addFire(w, p.x, p.y * 0.8);
        }
      }
      emit(w, { e: 'telegraph', uid: c.uid, attack: 'zap' });
      c.state = 'recover';
      c.cd = cdFor(w, 5, 2);
      break;
    }
    case 'board': {
      boardShip(w, c);
      break;
    }
    default:
      c.state = 'act';
  }
}

function stepAttack(w: World, c: Creature, dt: number): void {
  const sy = w.ship.y;
  const e = ellipseNorm(c.x, c.y, 0, sy, HULL_RX + c.r * 0.6, HULL_RY + c.r * 0.6);
  if (e < 1) {
    const p = hullContact(w, c.x, c.y);
    const n = hullNormal(w, c);
    if (c.attack === 'charge') {
      if (hullHit(w, 7, p.x, p.y)) {
        if (w.rng.chance(0.6)) addLeak(w, p.x, p.y * 0.8);
        sfx(w, 'wave_slam', c.x);
      }
      pushShip(w, -n.y * 1.6);
      c.vx = n.x * 3;
      c.vy = n.y * 3;
      c.cd = cdFor(w, 9, 3);
    } else {
      if (hullHit(w, 1, p.x, p.y)) sfx(w, 'hit_wrong', c.x);
      c.vx = n.x * 4;
      c.vy = n.y * 4;
      c.cd = cdFor(w, 6, 4);
    }
    c.state = 'recover';
    c.t = 0;
    c.attack = null;
    return;
  }
  if (c.t > 2.6) {
    c.state = 'recover';
    c.t = 0;
    c.attack = null;
    c.cd = cdFor(w, 3, 2);
  }
  void dt;
}

function hullNormal(w: World, c: Creature): { x: number; y: number } {
  const dx = c.x / (HULL_RX * HULL_RX), dy = (c.y - w.ship.y) / (HULL_RY * HULL_RY);
  const l = Math.hypot(dx, dy) || 1;
  return { x: dx / l, y: dy / l };
}

function avoidHull(w: World, c: Creature, dt: number): void {
  const m = c.r + 0.9;
  const e = ellipseNorm(c.x, c.y, 0, w.ship.y, HULL_RX + m, HULL_RY + m);
  if (e >= 1) return;
  const n = hullNormal(w, c);
  const k = (1 - e) * 22;
  c.vx += n.x * k * dt;
  c.vy += n.y * k * dt;
}

function separate(w: World, c: Creature, dt: number): void {
  for (const o of w.creatures) {
    if (o === c || o.state === 'gone' || o.state === 'cleaned' || o.state === 'deck') continue;
    const dx = c.x - o.x, dy = c.y - o.y;
    const min = c.r + o.r + 0.35;
    const d2 = dx * dx + dy * dy;
    if (d2 >= min * min || d2 < 1e-8) continue;
    const d = Math.sqrt(d2);
    const k = ((min - d) / min) * 9;
    c.vx += (dx / d) * k * dt;
    c.vy += (dy / d) * k * dt;
  }
}

// ---- boarding ---------------------------------------------------------------

function boardShip(w: World, c: Creature): void {
  c.state = 'deck';
  c.t = 0;
  c.dx = clamp(c.x, -6.5, 5.2);
  c.dy = c.side * Math.max(0.6, halfBeam(c.dx) - 0.6);
  c.vx = 0;
  c.vy = 0;
  c.cd = 2;
  c.attack = null;
  emit(w, { e: 'board', uid: c.uid });
  toast(w, T.boarded, 'bad');
  sfx(w, 'alarm', c.dx);
}

function stepDeckCreature(w: World, c: Creature, dt: number): void {
  // walk to the nearest free cannon and jam it; chew the deck meanwhile
  if (!c.jamming) {
    let best: CannonId | null = null;
    let bd = 1e9;
    for (const id of CANNON_IDS) {
      const cn = w.cannons[id];
      if (cn.jam && cn.jam !== c.uid) continue;
      const u = STATIONS[id].use;
      const d = Math.hypot(u.x - c.dx, u.y - c.dy);
      if (d < bd) { bd = d; best = id; }
    }
    if (best) {
      // stand beside the cannon (not on the gunner's spot)
      const st = STATIONS[best];
      const u = { x: (st.use.x + st.x) / 2 + (st.y === 0 ? 0 : -0.75), y: (st.use.y + st.y) / 2 + (st.y === 0 ? 0.75 : 0) };
      const dx = u.x - c.dx, dy = u.y - c.dy;
      const d = Math.hypot(dx, dy);
      if (d < 0.45) {
        c.jamming = best;
        w.cannons[best].jam = c.uid;
      } else {
        const s = 0.9;
        c.dx += (dx / d) * s * dt;
        c.dy += (dy / d) * s * dt;
        c.face = dx >= 0 ? 1 : -1;
      }
    }
  }
  if (c.cd <= 0) {
    c.cd = 2;
    hullHit(w, 1, c.dx, c.dy);
    if (w.rng.chance(0.18)) addLeak(w, c.dx + w.rng.range(-0.8, 0.8), c.dy * 0.7);
  }
  c.x = c.dx;
  c.y = w.ship.y + c.dy;
}

/** Bucket splash: knocks a boarded creature back into the sea (not cleaned). */
export function splashOff(w: World, c: Creature): void {
  if (c.state !== 'deck') return;
  if (c.jamming) { w.cannons[c.jamming].jam = 0; c.jamming = null; }
  const side = c.dy >= 0 ? 1 : -1;
  c.side = side;
  c.x = c.dx;
  c.y = w.ship.y + side * (HULL_RY + 1.4);
  c.vx = 0;
  c.vy = side * 2.5;
  c.state = 'recover';
  c.t = 0;
  c.stun = 2.5;
  c.tx = w.rng.range(-5, 3.5);
  emit(w, { e: 'splashOff', uid: c.uid });
  emit(w, { e: 'splash', x: c.x, y: c.y, local: false });
  sfx(w, 'splash', c.x);
}

/** A ball pressed / thrown onto a boarded creature: the right rule cleans it at once. */
export function shooDeck(w: World, c: Creature, ammo: import('../contract').AmmoId): boolean {
  if (c.state !== 'deck') return false;
  const right = ammo === c.def.weakness;
  w.acc.hits++;
  if (right) {
    w.acc.rightAmmo++;
    w.combo++;
    w.comboT = 6;
    sfx(w, 'hit_right', c.dx);
    emit(w, { e: 'hit', x: c.dx, y: w.ship.y + c.dy, right: true, dmg: c.hp, target: c.uid, ammo });
    cleanCreature(w, c);
  } else {
    w.acc.wrongAmmo++;
    w.combo = 0;
    sfx(w, 'hit_wrong', c.dx);
    emit(w, { e: 'hit', x: c.dx, y: w.ship.y + c.dy, right: false, dmg: 0, target: c.uid, ammo });
    if ((w.hintCd[c.def.id] ?? -99) <= w.t) {
      w.hintCd[c.def.id] = w.t + 7;
      emit(w, { e: 'hint', text: c.def.hint });
    }
  }
  return right;
}
