/**
 * Deck geometry shared by the sim and the renderer. Units: metres, ship-local frame
 * (x forward / bow = +x, y away from the camera, z up, deck at z = 0). See specs/message-ship/01_CONTRACT.md.
 */

export const PX_PER_M = 56;
export const SIN35 = Math.sin((35 * Math.PI) / 180);
export const COS35 = Math.cos((35 * Math.PI) / 180);
/** Screen px per metre of y (depth) and of z (height). */
export const PY = PX_PER_M * SIN35; // 32.12
export const PZ = PX_PER_M * COS35; // 45.87

/** Projection of a ship-local / world-relative point to screen offset (px). */
export function project(x: number, y: number, z = 0): { sx: number; sy: number } {
  return { sx: x * PX_PER_M, sy: -y * PY - z * PZ };
}

export const SHIP_HALF_LEN = 8;
export const SHIP_HALF_BEAM = 3.5;
export const RAIL_H = 0.9;
/** Hull footprint as an ellipse in the water (for bolts, charges, reefs, pickups). */
export const HULL_RX = 8.2;
export const HULL_RY = 3.7;

/** Half width of the deck at x (pointed bow, broad stern). */
export function halfBeam(x: number): number {
  if (x <= -7.6) return SHIP_HALF_BEAM - (x + 7.6) * -0.6; // stern rounding: 3.26 at -8
  if (x <= 3) return SHIP_HALF_BEAM;
  if (x >= 8) return 0;
  const t = (x - 3) / 5;
  return SHIP_HALF_BEAM * Math.sqrt(Math.max(0, 1 - t * t));
}

/** Walkable half width (rail thickness + body radius taken off). */
export const WALK_MARGIN = 0.42;
export const WALK_X_MIN = -7.55;
export const WALK_X_MAX = 7.2;

export interface Rect { x0: number; y0: number; x1: number; y1: number }

export type StationId =
  | 'wheel' | 'cannon_bow' | 'cannon_stern' | 'cannon_far' | 'cannon_near'
  | 'mast' | 'rack' | 'planks' | 'barrel' | 'hatch';

export interface StationDef {
  id: StationId;
  x: number; y: number;
  /** collider (null = flat, walkable) */
  rect: Rect | null;
  /** where the player has to be to use it, and how close (m) */
  use: { x: number; y: number; r: number };
}

const R = (cx: number, cy: number, hx: number, hy: number): Rect => ({ x0: cx - hx, y0: cy - hy, x1: cx + hx, y1: cy + hy });

export const STATIONS: Record<StationId, StationDef> = {
  wheel: { id: 'wheel', x: -6.2, y: 0, rect: R(-6.2, 0, 0.32, 0.55), use: { x: -5.55, y: 0, r: 0.95 } },
  cannon_bow: { id: 'cannon_bow', x: 6.8, y: 0, rect: R(6.75, 0, 0.5, 0.42), use: { x: 5.85, y: 0, r: 1.0 } },
  cannon_stern: { id: 'cannon_stern', x: -7.4, y: 1.8, rect: R(-7.35, 1.8, 0.45, 0.45), use: { x: -6.45, y: 1.8, r: 1.0 } },
  cannon_far: { id: 'cannon_far', x: 1.0, y: 3.2, rect: R(1.0, 3.15, 0.45, 0.45), use: { x: 1.0, y: 2.25, r: 1.0 } },
  cannon_near: { id: 'cannon_near', x: 1.0, y: -3.2, rect: R(1.0, -3.15, 0.45, 0.45), use: { x: 1.0, y: -1.75, r: 1.0 } },
  mast: { id: 'mast', x: 1.0, y: 0, rect: R(1.0, 0, 0.28, 0.28), use: { x: 1.0, y: 0, r: 1.05 } },
  rack: { id: 'rack', x: -3.2, y: 2.9, rect: R(-3.2, 3.0, 1.3, 0.32), use: { x: -3.2, y: 2.25, r: 1.55 } },
  planks: { id: 'planks', x: -4.6, y: -2.8, rect: R(-4.6, -2.85, 0.6, 0.4), use: { x: -4.6, y: -2.05, r: 0.95 } },
  barrel: { id: 'barrel', x: 4.2, y: -2.8, rect: R(4.2, -2.75, 0.4, 0.4), use: { x: 4.2, y: -1.95, r: 0.95 } },
  hatch: { id: 'hatch', x: -1.4, y: -0.6, rect: null, use: { x: -1.4, y: -0.6, r: 0.8 } },
};

export type CannonId = 'cannon_bow' | 'cannon_stern' | 'cannon_far' | 'cannon_near';
export const CANNON_IDS: CannonId[] = ['cannon_bow', 'cannon_far', 'cannon_near', 'cannon_stern'];

export interface CannonDef { id: CannonId; base: number; arc: number; muzzle: number }
const D = Math.PI / 180;
/**
 * Aim arc (half angle). The contract says +-35 deg; playtesting the geometry showed that a side cannon then
 * covers only ~3 m along the hull at typical creature distances, so creatures sat outside every arc most of
 * the time. +-50 deg keeps the "each cannon has its own sector" feel and is logged in REQUESTS.md.
 */
export const ARC = 50 * D;
export const CANNONS: Record<CannonId, CannonDef> = {
  cannon_bow: { id: 'cannon_bow', base: 0, arc: ARC, muzzle: 0.85 },
  cannon_stern: { id: 'cannon_stern', base: Math.PI, arc: ARC, muzzle: 0.8 },
  cannon_far: { id: 'cannon_far', base: Math.PI / 2, arc: ARC, muzzle: 0.75 },
  cannon_near: { id: 'cannon_near', base: -Math.PI / 2, arc: ARC, muzzle: 0.75 },
};
/** Height of the cannon muzzles above the deck (display only). */
export const MUZZLE_Z = 0.85;

/** The rack art has 7 cups 0.3 m apart; n balls use the middle n cups. */
export const RACK_CUPS = 7;
export const RACK_CUP_DX = 0.3;
export function rackCup(i: number, n: number): number {
  return Math.floor((RACK_CUPS - Math.min(n, RACK_CUPS)) / 2) + i;
}
export function rackSlotX(i: number, n: number): number {
  return STATIONS.rack.x + (rackCup(i, n) - (RACK_CUPS - 1) / 2) * RACK_CUP_DX;
}
/** Walking along the rack picks a ball: the selection zone is wider than the rack itself. */
export const RACK_ZONE = 3.0;
export function rackSlotAtX(x: number, n: number): number {
  if (n <= 1) return 0;
  const u = (x - (STATIONS.rack.x - RACK_ZONE / 2)) / RACK_ZONE;
  return Math.max(0, Math.min(n - 1, Math.floor(u * n)));
}
export const RACK_SLOT_Y = 2.98;

/** Is a ship-local point inside the hull footprint (on deck)? */
export function onDeck(x: number, y: number, margin = 0): boolean {
  if (x < -SHIP_HALF_LEN + margin || x > SHIP_HALF_LEN - margin) return false;
  return Math.abs(y) <= halfBeam(x) - margin;
}

/** Ballistics constants. */
/** One lantern ball gives this many light shots. */
export const SHOTS_PER_BALL = 3;
export const BALL_SPEED = 15; // m/s relative to the ship
export const BALL_RANGE = 12; // m
export const BALL_RADIUS = 0.16;
export const BOLT_SPEED = 4.2;
export const BOLT_RADIUS = 0.34;

/** Sea lane limits for the ship's lateral position. */
export const LANE_Y = 11;
