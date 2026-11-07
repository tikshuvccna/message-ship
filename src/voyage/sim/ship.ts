/** Ship dynamics: sail speed, helm with inertia and slip, lateral position in the sea lane, waves, flooding. */
import { LANE_Y } from './layout';
import { approach, clamp, damp } from './math';
import type { World } from './world';

export const BASE_SPEED = 3.0; // m/s forward with the sail spread
export const SAIL_FACTOR = [1, 0.62, 0.28] as const;
const HELM_ACCEL = 3.6;        // m/s^2 at full wheel
const LATERAL_DRAG = 0.9;      // 1/s (slip: the ship keeps drifting after the wheel returns)
const WHEEL_RATE = 1.9;        // wheel units per second (inertia of the wheel)
const WHEEL_RETURN = 0.7;

/** Layered swell: [amplitude, angular frequency, phase] */
const HEAVE: [number, number, number][] = [[0.16, 0.9, 0], [0.09, 1.7, 1.3], [0.05, 2.9, 2.1]];
const ROLL: [number, number, number][] = [[0.025, 0.7, 0.4], [0.012, 1.45, 2.2], [0.006, 2.6, 1.0]];
const PITCH: [number, number, number][] = [[0.012, 0.55, 1.1], [0.006, 1.3, 0.2]];

function waves(table: [number, number, number][], t: number): number {
  let s = 0;
  for (const [a, f, p] of table) s += a * Math.sin(f * t + p);
  return s;
}

export function seaState(w: World): number {
  return clamp(w.sched.swell + w.storm.level * 0.9, 0, 1.4);
}

export function targetSpeed(w: World): number {
  const s = w.ship;
  let v = BASE_SPEED * SAIL_FACTOR[s.sail] * (w.stats.sailSpeed || 1);
  if (w.buffs.speed > 0) v *= 1.3;
  v *= 1 - 0.6 * clamp(s.water, 0, 1);
  // storm: a spread sail catches gusts (faster but wilder)
  v *= 1 + w.storm.level * (s.sail === 0 ? 0.25 : 0.05);
  if (w.sched.arrival && w.arrived) v = 0;
  if (s.sinking >= 0) v = 0;
  return v;
}

export function stepShip(w: World, dt: number): void {
  const s = w.ship;
  // helm input: the player holding the wheel
  let helmIn = 0;
  let manned = false;
  for (const p of w.players) {
    if (p.at === 'wheel') {
      manned = true;
      const inp = w.inputs[p.idx];
      if (inp) helmIn = clamp(inp.my, -1, 1);
    }
  }
  if (manned) s.wheel = approach(s.wheel, helmIn, WHEEL_RATE * dt);
  else s.wheel = approach(s.wheel, 0, WHEEL_RETURN * dt);

  s.speed += (targetSpeed(w) - s.speed) * damp(0.8, dt);
  const speedNorm = clamp(s.speed / BASE_SPEED, 0, 1.4);

  let ay = s.wheel * HELM_ACCEL * (0.45 + 0.55 * speedNorm) - s.vy * LATERAL_DRAG;
  // a gentle current when nobody steers
  if (!manned) ay += Math.sin(w.t * 0.23 + 1.7) * 0.18;
  // soft walls at the edge of the lane (shallows)
  const over = Math.abs(s.y) - LANE_Y;
  if (over > 0) ay -= Math.sign(s.y) * over * 6;
  s.vy += ay * dt;
  s.y += s.vy * dt;
  s.dist += s.speed * dt;

  // motion: heave, roll and pitch from layered waves, plus helm lean
  const sea = seaState(w);
  const amp = 0.35 + sea * 1.6;
  s.heave = waves(HEAVE, w.t) * amp;
  const lean = -s.wheel * 0.05 * speedNorm - ay * 0.006;
  const sailWild = s.sail === 0 ? 1 + w.storm.level * 0.8 : 1;
  s.roll = lean + waves(ROLL, w.t) * amp * sailWild;
  s.pitch = waves(PITCH, w.t) * amp;
  s.shake = Math.max(0, s.shake - dt * 2.2);
  s.knock = Math.max(0, s.knock - dt * 2);

  // flooding: leaks add water, the pump removes a little
  let inflow = 0;
  for (const l of w.leaks) inflow += 0.012 * l.size;
  const pump = 0.005 * (w.stats.repairSpeed || 1);
  s.water = clamp(s.water + (inflow - pump) * dt, 0, 1);
}

/** Impulse sideways (reef bounce, wave slam, charges). */
export function pushShip(w: World, dvy: number): void {
  w.ship.vy += dvy;
  w.ship.knock = Math.min(1, w.ship.knock + Math.abs(dvy) / 3);
}
