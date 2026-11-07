/**
 * Ballistics for the light-cannons. Shots fly in 2D (the arc is display only), with a fixed
 * muzzle speed relative to the ship plus the ship's own velocity (inherited), for BALL_RANGE metres.
 */

export interface LeadSolution { angle: number; t: number; x: number; y: number }

/**
 * Lead (intercept) solution: the direction to fire from muzzle (mx, my) with speed s, adding the
 * inherited velocity (ivx, ivy), to hit a target at (tx, ty) moving with constant (tvx, tvy).
 * Works in the frame that moves with the inherited velocity: the target's relative velocity is
 * (tv - iv) and the shot is then a plain constant-speed ray. Returns null when no positive time exists.
 */
export function solveLead(
  mx: number, my: number, s: number, ivx: number, ivy: number,
  tx: number, ty: number, tvx: number, tvy: number,
): LeadSolution | null {
  const rx = tx - mx, ry = ty - my;
  const vx = tvx - ivx, vy = tvy - ivy;
  // |r + v t| = s t  ->  (v.v - s^2) t^2 + 2 (r.v) t + r.r = 0
  const a = vx * vx + vy * vy - s * s;
  const b = 2 * (rx * vx + ry * vy);
  const c = rx * rx + ry * ry;
  let t: number;
  if (Math.abs(a) < 1e-9) {
    if (Math.abs(b) < 1e-9) return null;
    t = -c / b;
  } else {
    const disc = b * b - 4 * a * c;
    if (disc < 0) return null;
    const sq = Math.sqrt(disc);
    const t1 = (-b - sq) / (2 * a), t2 = (-b + sq) / (2 * a);
    const lo = Math.min(t1, t2), hi = Math.max(t1, t2);
    t = lo > 1e-6 ? lo : hi;
  }
  if (!(t > 1e-6) || !Number.isFinite(t)) return null;
  // aim point in the inherited-velocity frame
  const ax = rx + vx * t, ay = ry + vy * t;
  return { angle: Math.atan2(ay, ax), t, x: tx + tvx * t, y: ty + tvy * t };
}

/**
 * Time of closest approach between a shot (p0 + u t) and a target (q0 + w t) within [0, T].
 * Returns the time and the squared distance at that time.
 */
export function closestApproach(
  px: number, py: number, ux: number, uy: number,
  qx: number, qy: number, wx: number, wy: number, T: number,
): { t: number; d2: number } {
  const rx = qx - px, ry = qy - py, vx = wx - ux, vy = wy - uy;
  const vv = vx * vx + vy * vy;
  let t = vv > 1e-12 ? -(rx * vx + ry * vy) / vv : 0;
  if (t < 0) t = 0;
  if (t > T) t = T;
  const dx = rx + vx * t, dy = ry + vy * t;
  return { t, d2: dx * dx + dy * dy };
}

/** Display height of a shot along its flight (light arc). */
export function shotHeight(z0: number, t: number, T: number): number {
  const u = T > 0 ? Math.min(1, t / T) : 1;
  return z0 * (1 - u) + 1.6 * 4 * u * (1 - u);
}
