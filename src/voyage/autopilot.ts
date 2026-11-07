/**
 * Dev/test autopilot: plays player 0 through the real input path (setInput), so screenshots and
 * soak tests exercise the whole loop: walk to the rack, take the right ball for the nearest noise,
 * carry it to a cannon whose arc covers the target, load, aim with lead, fire; patch leaks and douse fires.
 * Not used by the game itself.
 */
import { solveLead } from './sim/ballistics';
import { canFire, clampAim, muzzle, targets } from './sim/combat';
import { decide } from './sim/deck';
import { BALL_RANGE, BALL_SPEED, CANNONS, CANNON_IDS, RACK_ZONE, STATIONS, type CannonId } from './sim/layout';
import { segCircle, wrapAngle } from './sim/math';
import type { VoyageSim } from './sim/sim';
import type { AmmoId } from './contract';

interface Goal { x: number; y: number; act: boolean }

export class Autopilot {
  private stuck = 0;
  private lastX = 0;
  private lastY = 0;
  private side = 1;
  private wait = 0;
  private lock: AmmoId | null = null;
  private lockT = 0;
  debug: ((s: string) => void) | null = null;
  constructor(private sim: VoyageSim, private p = 0) {}

  /** Called once per frame (or per step). */
  tick(dt: number): void {
    const w = this.sim.w;
    const pl = w.players[this.p];
    if (!pl || w.over) return;
    if (pl.job) { this.sim.setInput({ p: this.p as 0 | 1, moveX: 0, moveY: 0, action: false, throwIt: false }); return; }
    let tg = this.pickTarget();
    // hysteresis: stick to the chosen rule for a while (players do not change their mind every frame)
    this.lockT -= dt;
    if (this.lock && this.lockT > 0) {
      const same = this.allTargets().filter((t) => t.weakness === this.lock);
      if (same.length) tg = same.reduce((a, b) => (Math.hypot(a.x, a.y - w.ship.y) < Math.hypot(b.x, b.y - w.ship.y) ? a : b));
      else this.lock = null;
    }
    if (tg && tg.weakness !== this.lock) { this.lock = tg.weakness; this.lockT = 6; }
    const need: AmmoId | null = tg ? tg.weakness : null;

    // at a cannon: aim & fire, or leave
    if (pl.at && pl.at !== 'wheel') {
      const id = pl.at;
      const c = w.cannons[id];
      const boarded = w.creatures.some((k) => k.state === 'deck');
      if (!c.loaded || c.jam || boarded) { this.press(0, 0, true, false); return; }
      // best target for the loaded rule inside this cannon's arc
      const m = muzzle(w, id);
      let sol: ReturnType<typeof solveLead> = null;
      let bestErr = 1e9;
      for (const t of this.allTargets()) {
        if (t.weakness !== c.loaded) continue;
        const s = solveLead(m.x, m.y, BALL_SPEED, 0, w.ship.vy, t.x, t.y, t.vx, t.vy);
        if (!s || s.t > BALL_RANGE / BALL_SPEED * 0.95) continue;
        if (Math.abs(wrapAngle(clampAim(id, s.angle) - s.angle)) > 1e-3) continue;
        const err = Math.abs(wrapAngle(s.angle - c.aim));
        if (err < bestErr) { bestErr = err; sol = s; }
      }
      if (!sol) {
        if (this.debug) this.debug(`nosol ${id} loaded=${c.loaded} wait=${this.wait.toFixed(1)}`);
        this.wait += dt;
        if (this.wait > 6) { this.wait = 0; this.press(0, 0, true, false); } else this.press(0, 0, false, false);
        return;
      }
      this.wait = 0;
      if (this.debug) this.debug(`aim ${id} err=${wrapAngle(clampAim(id, sol.angle) - c.aim).toFixed(3)} can=${canFire(w, id)} loadT=${c.loadT.toFixed(2)} t=${sol.t.toFixed(2)}`);
      const want = clampAim(id, sol.angle);
      const err = wrapAngle(want - c.aim);
      const fire = canFire(w, id) && Math.abs(err) < 0.03 && Math.abs(wrapAngle(want - sol.angle)) < 0.01;
      // push the stick toward the wanted angle (slower when close)
      const a = c.aim + Math.sign(err) * Math.min(Math.abs(err) * 4, 1.2);
      const k = Math.abs(err) > 0.01 ? 1 : 0;
      this.press(Math.cos(a) * k, Math.sin(a) * k, false, fire);
      return;
    }
    if (pl.at === 'wheel') { this.press(0, 0, true, false); return; }

    let goal: Goal | null = null;
    const held = pl.held;
    const boarder = w.creatures.find((k) => k.state === 'deck');
    // deck jobs first: fires with a bucket, leaks with a plank (Bit helps with leaks)
    if (boarder && (!held || held.kind === 'ball')) {
      // a creature on deck: bring it the ball of its rule
      if (held && held.ammo === boarder.def.weakness) goal = { x: boarder.dx, y: boarder.dy - 0.7 * Math.sign(boarder.dy || 1), act: true };
      else if (held) goal = { x: STATIONS.rack.use.x, y: STATIONS.rack.use.y, act: true };
      else {
        const i = w.rack.findIndex((s) => s.ammo === boarder.def.weakness);
        const n = w.rack.length;
        if (i >= 0) goal = { x: STATIONS.rack.x - RACK_ZONE / 2 + ((i + 0.5) * RACK_ZONE) / n, y: 2.15, act: !!w.rack[i]?.has };
      }
    } else if (w.fires.length > 0 && (!held || held.kind === 'bucket')) {
      if (!held) goal = { x: STATIONS.barrel.use.x, y: STATIONS.barrel.use.y, act: true };
      else if (!held.full) goal = { x: STATIONS.barrel.use.x, y: STATIONS.barrel.use.y, act: true };
      else { const f = w.fires[0]!; goal = { x: f.x, y: f.y - 0.6, act: true }; }
    } else if (w.leaks.length > 1 && (!held || held.kind === 'plank')) {
      if (!held) goal = { x: STATIONS.planks.use.x, y: STATIONS.planks.use.y, act: true };
      else { const l = w.leaks[0]!; goal = { x: l.x, y: l.y - 0.6, act: true }; }
    } else if (held && held.kind !== 'ball') {
      goal = { x: pl.x, y: pl.y, act: true }; // put it down
    } else if (held && held.kind === 'ball') {
      if (need && held.ammo !== need) goal = { x: STATIONS.rack.use.x, y: STATIONS.rack.use.y, act: true }; // return it
      else if (tg) {
        const id = this.cannonFor(tg.x, tg.y, true);
        const u = STATIONS[id].use;
        goal = { x: u.x, y: u.y, act: true };
      }
    } else if (need) {
      const i = w.rack.findIndex((s) => s.ammo === need);
      if (i >= 0) {
        const n = w.rack.length;
        const x = STATIONS.rack.x - RACK_ZONE / 2 + ((i + 0.5) * RACK_ZONE) / n;
        goal = { x, y: 2.15, act: !!w.rack[i]?.has };
      }
    }
    if (!goal) { this.press(0, 0, false, false); return; }
    // detour around the mast (the only collider in the middle of the deck)
    const mx0 = STATIONS.mast.x, my0 = STATIONS.mast.y;
    if (segCircle(pl.x, pl.y, goal.x, goal.y, mx0, my0, 0.75) && Math.hypot(pl.x - mx0, pl.y - my0) > 0.3) {
      const ux = goal.x - pl.x, uy = goal.y - pl.y;
      const ul = Math.hypot(ux, uy) || 1;
      let nx = -uy / ul, ny = ux / ul;
      if ((pl.x - mx0) * nx + (pl.y - my0) * ny < 0) { nx = -nx; ny = -ny; }
      goal = { x: mx0 + nx * 1.05, y: my0 + ny * 1.05, act: false };
    }
    const dx = goal.x - pl.x, dy = goal.y - pl.y;
    const d = Math.hypot(dx, dy);
    if (d < 0.35) {
      if (!goal.act) { this.press(dx, dy, false, false); return; }
      const act = decide(w, pl);
      this.press(0, 0, goal.act && !!act && act.a !== 'busy', false);
      return;
    }
    // walk (with a little sidestep when stuck on a collider)
    const moved = Math.hypot(pl.x - this.lastX, pl.y - this.lastY);
    this.lastX = pl.x; this.lastY = pl.y;
    this.stuck = moved < 0.01 ? this.stuck + dt : Math.max(0, this.stuck - dt);
    let mx = dx / d, my = dy / d;
    if (this.stuck > 0.25) { const t = mx; mx = -my * this.side; my = t * this.side; if (this.stuck > 1) { this.side *= -1; this.stuck = 0; } }
    this.press(mx, my, false, false);
  }

  private press(mx: number, my: number, action: boolean, throwIt: boolean): void {
    this.sim.setInput({ p: this.p as 0 | 1, moveX: mx, moveY: my, action, throwIt });
  }

  private allTargets(): { x: number; y: number; vx: number; vy: number; weakness: AmmoId }[] {
    const w = this.sim.w;
    const out: { x: number; y: number; vx: number; vy: number; weakness: AmmoId }[] = [];
    for (const t of targets(w)) {
      let weakness: AmmoId | undefined;
      if (t.kind === 'creature') weakness = w.creatures.find((c) => c.uid === t.uid)?.def.weakness;
      else weakness = w.boss?.arms.find((a) => a.uid === t.uid)?.weakness;
      if (weakness) out.push({ x: t.x, y: t.y, vx: t.vx, vy: t.vy, weakness });
    }
    return out;
  }

  private pickTarget(): { x: number; y: number; vx: number; vy: number; weakness: AmmoId } | null {
    const w = this.sim.w;
    let best: { x: number; y: number; vx: number; vy: number; weakness: AmmoId } | null = null;
    let bd = 1e9;
    for (const t of targets(w)) {
      if (Math.abs(t.x) > 13 || Math.abs(t.y - w.ship.y) > 10.5) continue;
      let weakness: AmmoId | undefined;
      if (t.kind === 'creature') weakness = w.creatures.find((c) => c.uid === t.uid)?.def.weakness;
      else weakness = w.boss?.arms.find((a) => a.uid === t.uid)?.weakness;
      if (!weakness || !w.rack.some((s) => s.ammo === weakness)) continue;
      const fast = t.kind === 'creature' && w.creatures.find((c) => c.uid === t.uid)?.def.behavior === 'swarm';
      // prefer what a cannon can reach in ~3 s (where it will be when we get there)
      const fx = t.x + t.vx * 3, fy = t.y + t.vy * 3;
      const id = this.cannonFor(fx, fy);
      const st = STATIONS[id];
      const off = Math.abs(wrapAngle(Math.atan2(fy - w.ship.y - st.y, fx - st.x) - CANNONS[id].base));
      const inArc = off <= CANNONS[id].arc && Math.hypot(fx - st.x, fy - w.ship.y - st.y) < BALL_RANGE * 0.85;
      const d = Math.hypot(t.x, t.y - w.ship.y) + (fast ? 4 : 0) + (inArc ? 0 : 12);
      if (d < bd) { bd = d; best = { x: t.x, y: t.y, vx: t.vx, vy: t.vy, weakness }; }
    }
    return best;
  }

  private cannonFor(x: number, y: number, empty = false): CannonId {
    const w = this.sim.w;
    let best: CannonId = 'cannon_bow';
    let bs = 1e9;
    for (const id of CANNON_IDS) {
      const st = STATIONS[id];
      const a = Math.atan2(y - w.ship.y - st.y, x - st.x);
      const off = Math.abs(wrapAngle(a - CANNONS[id].base));
      let score = off > CANNONS[id].arc ? 100 + off : Math.hypot(st.use.x - (w.players[this.p]?.x ?? 0), st.use.y - (w.players[this.p]?.y ?? 0));
      if (w.cannons[id].jam) continue;
      if (empty && w.cannons[id].loaded && w.cannons[id].charges > 1) score += 4;
      if (score < bs) { bs = score; best = id; }
    }
    return best;
  }
}
