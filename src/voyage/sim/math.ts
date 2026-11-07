export interface V2 { x: number; y: number }

export const clamp = (v: number, a: number, b: number): number => (v < a ? a : v > b ? b : v);
export const lerp = (a: number, b: number, t: number): number => a + (b - a) * t;
export const len = (x: number, y: number): number => Math.hypot(x, y);
export const dist = (a: V2, b: V2): number => Math.hypot(a.x - b.x, a.y - b.y);
export const dist2 = (ax: number, ay: number, bx: number, by: number): number => (ax - bx) ** 2 + (ay - by) ** 2;

/** Wrap an angle to (-PI, PI]. */
export function wrapAngle(a: number): number {
  a = (a + Math.PI) % (Math.PI * 2);
  if (a < 0) a += Math.PI * 2;
  return a - Math.PI;
}

/** Move `cur` toward `target` by at most `step` (angles, shortest way). */
export function approachAngle(cur: number, target: number, step: number): number {
  const d = wrapAngle(target - cur);
  if (Math.abs(d) <= step) return target;
  return cur + Math.sign(d) * step;
}

export function approach(cur: number, target: number, step: number): number {
  if (cur < target) return Math.min(target, cur + step);
  return Math.max(target, cur - step);
}

/** Frame-rate independent exponential smoothing factor. */
export const damp = (rate: number, dt: number): number => 1 - Math.exp(-rate * dt);

/** Limit a vector's length in place. */
export function limit(v: V2, max: number): V2 {
  const l = Math.hypot(v.x, v.y);
  if (l > max && l > 0) {
    v.x *= max / l;
    v.y *= max / l;
  }
  return v;
}

/** True if the segment a->b passes within r of point c. */
export function segCircle(ax: number, ay: number, bx: number, by: number, cx: number, cy: number, r: number): boolean {
  const dx = bx - ax, dy = by - ay;
  const l2 = dx * dx + dy * dy;
  let t = l2 > 0 ? ((cx - ax) * dx + (cy - ay) * dy) / l2 : 0;
  t = clamp(t, 0, 1);
  const px = ax + dx * t - cx, py = ay + dy * t - cy;
  return px * px + py * py <= r * r;
}

/**
 * Segment vs axis-aligned ellipse (semi-axes rx, ry) inflated by r.
 * Solved by scaling space so the inflated ellipse becomes a unit circle (exact for circles,
 * a close approximation for an inflated ellipse, which is what we want for gameplay).
 */
export function segEllipse(ax: number, ay: number, bx: number, by: number, cx: number, cy: number, rx: number, ry: number, r: number): boolean {
  const sx = 1 / (rx + r), sy = 1 / (ry + r);
  return segCircle(ax * sx, ay * sy, bx * sx, by * sy, cx * sx, cy * sy, 1);
}

/** Normalised distance of p from ellipse center (1 = on the edge). */
export function ellipseNorm(px: number, py: number, cx: number, cy: number, rx: number, ry: number): number {
  return Math.hypot((px - cx) / rx, (py - cy) / ry);
}
