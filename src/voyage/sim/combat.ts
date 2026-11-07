/** Light-cannon shots, aiming (lead + assist), hit rules, noise bolts. */
import type { AmmoId } from '../contract';
import { closestApproach, solveLead } from './ballistics';
import {
  BALL_RADIUS, BALL_RANGE, BALL_SPEED, BOLT_RADIUS, CANNONS, HULL_RX, HULL_RY, STATIONS, type CannonId,
} from './layout';
import { segCircle, segEllipse, wrapAngle } from './math';
import type { BossArm, Creature, Floater } from './types';
import {
  addFire, addLeak, dropCoins, emit, hint, hullContact, hullHit, sfx, uid, type World,
} from './world';
import { armHit, headHit } from './boss';

export interface Target {
  kind: 'creature' | 'arm' | 'crate';
  uid: number;
  x: number; y: number;
  vx: number; vy: number;
  rx: number; ry: number;
}

const HITTABLE = new Set(['enter', 'act', 'telegraph', 'attack', 'recover', 'board']);

export function creatureHittable(c: Creature): boolean {
  return c.hostile && HITTABLE.has(c.state);
}

/** Everything a light-shot can hit (crates optional: they are not aim-assist targets). */
export function targets(w: World, withCrates = false): Target[] {
  const out: Target[] = [];
  for (const c of w.creatures) {
    if (!creatureHittable(c)) continue;
    out.push({ kind: 'creature', uid: c.uid, x: c.x, y: c.y, vx: c.vx, vy: c.vy, rx: c.rx, ry: c.ry });
  }
  if (w.boss) {
    for (const a of w.boss.arms) {
      if (!armHittable(a)) continue;
      out.push({ kind: 'arm', uid: a.uid, x: a.x, y: a.y, vx: 0, vy: w.ship.vy, rx: 0.8, ry: 0.8 });
    }
  }
  if (withCrates) {
    for (const f of w.floaters) {
      if (f.kind !== 'crate' || !f.alive) continue;
      out.push({ kind: 'crate', uid: f.uid, x: f.x, y: f.y, vx: f.vx, vy: f.vy, rx: f.r, ry: f.r });
    }
  }
  return out;
}

export function armHittable(a: BossArm): boolean {
  return a.rise > 0.55 && a.state !== 'under' && a.state !== 'calm';
}

/** Muzzle position of a cannon in world-relative coordinates. */
export function muzzle(w: World, id: CannonId, aim = w.cannons[id].aim): { x: number; y: number } {
  const st = STATIONS[id];
  const m = CANNONS[id].muzzle;
  return { x: st.x + Math.cos(aim) * m, y: w.ship.y + st.y + Math.sin(aim) * m };
}

export function clampAim(id: CannonId, a: number): number {
  const d = CANNONS[id];
  const off = wrapAngle(a - d.base);
  return d.base + Math.max(-d.arc, Math.min(d.arc, off));
}

export interface ShotPrediction {
  x0: number; y0: number;
  x1: number; y1: number;    // end of the path (hit point or splash point)
  t: number; T: number;
  hit: Target | null;
  lead: { x: number; y: number; angle: number; uid: number } | null;
}

function firstHit(w: World, x0: number, y0: number, ux: number, uy: number, T: number, list: Target[]): { t: number; tg: Target } | null {
  let best: { t: number; tg: Target } | null = null;
  for (const tg of list) {
    // closest approach in the space where the (inflated) ellipse is a unit circle
    const sx = 1 / (tg.rx + BALL_RADIUS), sy = 1 / (tg.ry + BALL_RADIUS);
    const ca = closestApproach(x0 * sx, y0 * sy, ux * sx, uy * sy, tg.x * sx, tg.y * sy, tg.vx * sx, tg.vy * sy, T);
    if (ca.d2 > 1) continue;
    // back up to the first contact time (entry into the unit circle)
    const rx = (tg.x - x0) * sx, ry = (tg.y - y0) * sy, vx = (tg.vx - ux) * sx, vy = (tg.vy - uy) * sy;
    const a = vx * vx + vy * vy, b = 2 * (rx * vx + ry * vy), c = rx * rx + ry * ry - 1;
    let t = ca.t;
    if (a > 1e-9) {
      const disc = b * b - 4 * a * c;
      if (disc >= 0) t = Math.max(0, (-b - Math.sqrt(disc)) / (2 * a));
    }
    if (!best || t < best.t) best = { t, tg };
  }
  return best;
}

/** Where would a shot fired now from this cannon go? Used by the aim reticle and the assist. */
export function predictShot(w: World, id: CannonId): ShotPrediction {
  const c = w.cannons[id];
  const m = muzzle(w, id);
  const ux = Math.cos(c.aim) * BALL_SPEED, uy = Math.sin(c.aim) * BALL_SPEED + w.ship.vy;
  const T = BALL_RANGE / BALL_SPEED;
  const fh = firstHit(w, m.x, m.y, ux, uy, T, targets(w, true));
  const t = fh ? fh.t : T;
  const leadTg = assistTarget(w, id);
  return {
    x0: m.x, y0: m.y, x1: m.x + ux * t, y1: m.y + uy * t, t, T, hit: fh ? fh.tg : null,
    lead: leadTg,
  };
}

/** Best target near the current aim line: its lead point and angle. */
export function assistTarget(w: World, id: CannonId, maxErr = (16 * Math.PI) / 180): ShotPrediction['lead'] {
  const c = w.cannons[id];
  const T = BALL_RANGE / BALL_SPEED;
  let best: ShotPrediction['lead'] = null;
  let bestErr = maxErr;
  for (const tg of targets(w)) {
    const m = muzzle(w, id, Math.atan2(tg.y - w.ship.y - STATIONS[id].y, tg.x - STATIONS[id].x));
    const sol = solveLead(m.x, m.y, BALL_SPEED, 0, w.ship.vy, tg.x, tg.y, tg.vx, tg.vy);
    if (!sol || sol.t > T * 1.02) continue;
    const clamped = clampAim(id, sol.angle);
    if (Math.abs(wrapAngle(clamped - sol.angle)) > 1e-3) continue; // outside the arc
    const err = Math.abs(wrapAngle(sol.angle - c.aim));
    if (err < bestErr) {
      bestErr = err;
      best = { x: sol.x, y: sol.y, angle: sol.angle, uid: tg.uid };
    }
  }
  return best;
}

export function canFire(w: World, id: CannonId): boolean {
  const c = w.cannons[id];
  return !!c.loaded && c.loadT <= 0 && c.jam === 0 && c.fireCd <= 0;
}

export function fireCannon(w: World, id: CannonId): boolean {
  const c = w.cannons[id];
  if (!canFire(w, id) || !c.loaded) return false;
  const ammo = c.loaded;
  const dbl = w.stats.doubleShot || w.buffs.double > 0;
  const spread = dbl ? [-0.06, 0.06] : [0];
  for (const da of spread) {
    const a = c.aim + da;
    const m = muzzle(w, id, a);
    const vx = Math.cos(a) * BALL_SPEED, vy = Math.sin(a) * BALL_SPEED + w.ship.vy;
    const u = uid(w);
    w.shots.push({ uid: u, ammo, x: m.x, y: m.y, prevX: m.x, prevY: m.y, vx, vy, t: 0, T: BALL_RANGE / BALL_SPEED, z0: 0.85, cannon: id, power: w.stats.shotPower || 1 });
    emit(w, { e: 'shot', uid: u, cannon: id, ammo });
  }
  c.charges--;
  if (c.charges <= 0) { c.loaded = null; c.charges = 0; }
  else c.loadT = Math.max(0.15, (w.stats.reloadSec || 1.6) * 0.45);
  c.recoil = 1;
  c.fireCd = 0.25;
  w.acc.shots++;
  sfx(w, 'shot', STATIONS[id].x);
  return true;
}

export function comboMult(w: World): number {
  return 1 + 0.25 * Math.min(w.combo, 4);
}

/** Apply a light-hit to a creature. dir = travel direction of the shot. Returns true if it was the right ammo. */
export function hitCreature(w: World, c: Creature, ammo: AmmoId, power: number, dx: number, dy: number): boolean {
  const right = ammo === c.def.weakness;
  let dmg: number;
  if (right) {
    dmg = 2 * power * comboMult(w);
    w.combo++;
    w.comboT = 6;
    w.acc.rightAmmo++;
    sfx(w, 'hit_right', c.x);
  } else {
    dmg = 0.5;
    w.combo = 0;
    w.acc.wrongAmmo++;
    hint(w, c.def.id, c.def.hint);
    sfx(w, 'hit_wrong', c.x);
  }
  w.acc.hits++;
  c.hp -= dmg;
  c.hitFlash = 0.25;
  const kb = right ? 2.6 : 1.0;
  const l = Math.hypot(dx, dy) || 1;
  c.vx += (dx / l) * kb;
  c.vy += (dy / l) * kb;
  // a right hit staggers a telegraphed attack; any hit stops boarding
  if ((right && c.state === 'telegraph') || c.state === 'board') {
    c.state = 'recover';
    c.t = 0;
    c.attack = null;
    c.cd = Math.max(c.cd, 1.5);
  }
  emit(w, { e: 'hit', x: c.x, y: c.y, right, dmg, target: c.uid, ammo });
  if (c.hp <= 0) cleanCreature(w, c);
  return right;
}

export function cleanCreature(w: World, c: Creature): void {
  if (c.state === 'cleaned' || c.state === 'gone') return;
  if (c.state === 'deck') {
    c.x = c.dx;
    c.y = w.ship.y + c.dy;
  }
  if (c.jamming) {
    w.cannons[c.jamming].jam = 0;
    c.jamming = null;
  }
  c.state = 'cleaned';
  c.t = 0;
  c.hp = 0;
  c.attack = null;
  w.acc.cleaned.push(c.def.id);
  dropCoins(w, c.x, c.y, c.def.coins);
  emit(w, { e: 'clean', uid: c.uid, id: c.def.id, x: c.x, y: c.y });
  sfx(w, 'clean', c.x);
}

function breakCrate(w: World, f: Floater): void {
  f.alive = false;
  collectCrate(w, f, true);
}

/** Crate contents (deterministic from its value). */
export function collectCrate(w: World, f: Floater, shot: boolean): void {
  f.alive = false;
  const v = f.value;
  if (f.tag === 'treasure' || v >= 100) {
    dropCoins(w, f.x, f.y, 40);
    emit(w, { e: 'toast', text: 'אוצר!', kind: 'good' });
  } else if (v < 60) {
    dropCoins(w, f.x, f.y, 4 + (v % 9));
  } else if (v < 74) {
    w.buffs.shield += 2;
    emit(w, { e: 'pickup', kind: 'shield', amount: 2, x: f.x, y: f.y });
    emit(w, { e: 'toast', text: 'מגן אור!', kind: 'good' });
  } else if (v < 87) {
    w.buffs.double = 20;
    emit(w, { e: 'pickup', kind: 'double', amount: 20, x: f.x, y: f.y });
    emit(w, { e: 'toast', text: 'ירי כפול!', kind: 'good' });
  } else {
    w.buffs.speed = 15;
    emit(w, { e: 'pickup', kind: 'speed', amount: 15, x: f.x, y: f.y });
    emit(w, { e: 'toast', text: 'רוח גבית!', kind: 'good' });
  }
  sfx(w, shot ? 'hit_right' : 'pickup', f.x);
}

export function stepShots(w: World, dt: number): void {
  for (const s of w.shots) {
    s.prevX = s.x;
    s.prevY = s.y;
    s.x += s.vx * dt;
    s.y += s.vy * dt;
    s.t += dt;
    let done = false;
    // creatures (earliest along the segment wins: they are few, first match is fine)
    for (const c of w.creatures) {
      if (!creatureHittable(c)) continue;
      if (segEllipse(s.prevX, s.prevY, s.x, s.y, c.x, c.y, c.rx, c.ry, BALL_RADIUS)) {
        hitCreature(w, c, s.ammo, s.power, s.vx, s.vy);
        done = true;
        break;
      }
    }
    if (!done && w.boss) {
      for (const a of w.boss.arms) {
        if (!armHittable(a)) continue;
        if (segCircle(s.prevX, s.prevY, s.x, s.y, a.x, a.y, 0.8 + BALL_RADIUS)) {
          armHit(w, a, s.ammo, s.power, s.vx, s.vy);
          done = true;
          break;
        }
      }
      if (!done && !w.boss.friendly && segCircle(s.prevX, s.prevY, s.x, s.y, w.boss.x, w.boss.y, 2.0)) {
        headHit(w, s.x, s.y);
        done = true;
      }
    }
    if (!done) {
      for (const b of w.bolts) {
        if (segCircle(s.prevX, s.prevY, s.x, s.y, b.x, b.y, BOLT_RADIUS + BALL_RADIUS + 0.1)) {
          b.life = 0;
          emit(w, { e: 'boltpop', x: b.x, y: b.y });
          sfx(w, 'hit_right', b.x);
          done = true;
          break;
        }
      }
    }
    if (!done) {
      for (const f of w.floaters) {
        if (f.kind !== 'crate' || !f.alive) continue;
        if (segCircle(s.prevX, s.prevY, s.x, s.y, f.x, f.y, f.r + BALL_RADIUS)) {
          breakCrate(w, f);
          done = true;
          break;
        }
      }
    }
    if (!done && s.t >= s.T) {
      emit(w, { e: 'miss', x: s.x, y: s.y });
      sfx(w, 'splash', s.x);
      done = true;
    }
    if (done) s.t = 1e9;
  }
  w.shots = w.shots.filter((s) => s.t < 1e8);
}

export function fireBolt(w: World, fromUid: number, x: number, y: number, tx: number, ty: number, speed = 4.2): void {
  const dx = tx - x, dy = ty - y;
  const l = Math.hypot(dx, dy) || 1;
  const u = uid(w);
  w.bolts.push({ uid: u, x, y, vx: (dx / l) * speed, vy: (dy / l) * speed, t: 0, life: Math.min(7, l / speed + 1.5), from: fromUid });
  emit(w, { e: 'bolt', uid: u });
  sfx(w, 'bolt', x);
}

export function stepBolts(w: World, dt: number): void {
  for (const b of w.bolts) {
    if (b.life <= 0) continue;
    const px = b.x, py = b.y;
    b.x += b.vx * dt;
    b.y += b.vy * dt;
    b.t += dt;
    if (b.t >= b.life) { b.life = 0; continue; }
    if (segEllipse(px, py, b.x, b.y, 0, w.ship.y, HULL_RX - 0.4, HULL_RY - 0.3, BOLT_RADIUS)) {
      b.life = 0;
      const p = hullContact(w, b.x, b.y);
      emit(w, { e: 'boltpop', x: b.x, y: b.y });
      if (hullHit(w, 4, p.x, p.y)) {
        sfx(w, 'hit_wrong', p.x);
        const r = w.rng.next();
        if (r < 0.3) addLeak(w, p.x, p.y * 0.85);
        else if (r < 0.45) addFire(w, p.x, p.y * 0.8);
      }
    }
  }
  w.bolts = w.bolts.filter((b) => b.life > 0);
}
