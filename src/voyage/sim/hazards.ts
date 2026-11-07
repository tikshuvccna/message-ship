/** Things in the water (crates, bottles, reefs, coins, whirlpool) and on the deck (leaks, fires), storm and fog. */
import { collectCrate } from './combat';
import { HULL_RX, HULL_RY, halfBeam } from './layout';
import { clamp, damp, ellipseNorm } from './math';
import { pushShip } from './ship';
import { T } from './texts';
import { addFire, addLeak, emit, hullContact, hullHit, hullMax, sfx, toast, type World } from './world';

export function stepFloaters(w: World, dt: number): void {
  const sy = w.ship.y;
  const flow = -w.ship.speed;
  for (const f of w.floaters) {
    if (!f.alive) continue;
    f.t += dt;
    if (f.anchored) {
      f.x += (flow + f.vx) * dt;
      f.y += f.vy * dt;
    }
    switch (f.kind) {
      case 'coin': {
        // pop out, then fly to the ship (magnet)
        if (f.t < 0.55) {
          f.vx *= 1 - damp(2, dt);
          f.vy *= 1 - damp(2, dt);
        } else {
          const tx = 0, ty = sy;
          const dx = tx - f.x, dy = ty - f.y;
          const d = Math.hypot(dx, dy) || 1;
          const sp = 4 + f.t * 9;
          f.vx += ((dx / d) * sp - f.vx) * damp(5, dt);
          f.vy += ((dy / d) * sp - f.vy) * damp(5, dt);
        }
        f.x += f.vx * dt;
        f.y += f.vy * dt;
        if (ellipseNorm(f.x, f.y, 0, sy, HULL_RX * 0.6, HULL_RY * 0.6) < 1 || f.t > 4) {
          f.alive = false;
          w.acc.coins += f.value;
          emit(w, { e: 'pickup', kind: 'coins', amount: f.value, x: f.x, y: f.y });
          sfx(w, 'coin', f.x);
        }
        break;
      }
      case 'crate':
        if (ellipseNorm(f.x, f.y, 0, sy, HULL_RX + f.r, HULL_RY + f.r) < 1) collectCrate(w, f, false);
        break;
      case 'bottle':
        if (ellipseNorm(f.x, f.y, 0, sy, HULL_RX + f.r + 0.2, HULL_RY + f.r + 0.2) < 1) {
          f.alive = false;
          if (!w.acc.bottles.includes(f.tag)) w.acc.bottles.push(f.tag);
          emit(w, { e: 'bottle', id: f.tag });
          emit(w, { e: 'pickup', kind: 'bottle', amount: 1, x: f.x, y: f.y });
          toast(w, T.bottle, 'good');
          sfx(w, 'pickup', f.x);
        }
        break;
      case 'reef': {
        f.value = Math.max(0, f.value - dt); // hit cooldown
        const e = ellipseNorm(f.x, f.y, 0, sy, HULL_RX + f.r - 0.3, HULL_RY + f.r - 0.3);
        if (e < 1 && f.value <= 0) {
          f.value = 1.6;
          const p = hullContact(w, f.x, f.y);
          hullHit(w, 6, p.x, p.y);
          addLeak(w, p.x, p.y * 0.75);
          const away = sy >= f.y ? 1 : -1;
          pushShip(w, away * 3.2);
          w.ship.speed *= 0.55;
          emit(w, { e: 'shake', amount: 0.8 });
          sfx(w, 'reef_hit', f.x);
        }
        break;
      }
      case 'whirlpool': {
        const dy = f.y - sy, dx = f.x;
        const d = Math.hypot(dx, dy);
        const reach = f.r + 4;
        if (d < reach) {
          const k = 1 - d / reach;
          w.ship.vy += Math.sign(dy) * k * 3.2 * dt;
          w.ship.speed *= 1 - k * 0.6 * dt;
          if (d < f.r * 0.55) {
            if (Math.floor(f.t * 2) !== Math.floor((f.t - dt) * 2)) {
              hullHit(w, 1.5, clamp(dx, -6, 6), clamp(dy, -2, 2));
              sfx(w, 'creak');
            }
          }
        }
        break;
      }
      default:
        break;
    }
    const far = f.kind === 'island' || f.kind === 'cove' || f.kind === 'lighthouse' ? -45 : -26;
    if (f.x < far) f.alive = false;
  }
  if (w.frame % 30 === 0) w.floaters = w.floaters.filter((f) => f.alive);
}

export function stepDeckHazards(w: World, dt: number): void {
  for (const l of w.leaks) l.age += dt;
  const rainy = w.storm.level > 0.3;
  for (const f of w.fires) {
    f.level = Math.min(1, f.level + (rainy ? 0.02 : 0.06) * dt);
    if (w.ship.sinking < 0) {
      w.ship.hull = Math.max(0, w.ship.hull - 0.35 * f.level * dt);
    }
    if (f.level >= 1) {
      f.spreadT += dt;
      if (f.spreadT > 9) {
        f.spreadT = 0;
        const a = w.rng.range(0, Math.PI * 2);
        addFire(w, f.x + Math.cos(a) * 1.3, f.y + Math.sin(a) * 1.0);
      }
    }
  }
  // alarms with hysteresis
  const water = w.ship.water;
  if (water > 0.6 && !w.flags.water) { w.flags.water = true; toast(w, T.lowWater, 'bad'); sfx(w, 'alarm'); }
  if (water < 0.45) w.flags.water = false;
  const hf = w.ship.hull / hullMax(w);
  if (hf < 0.25 && !w.flags.hull) { w.flags.hull = true; toast(w, T.lowHull, 'bad'); sfx(w, 'alarm'); }
  if (hf > 0.35) w.flags.hull = false;
}

export function stepWeather(w: World, dt: number): void {
  const st = w.storm;
  st.level += (st.target - st.level) * damp(0.35, dt);
  if (Math.abs(st.level - st.target) < 0.002) st.level = st.target;
  w.fog.level += (w.fog.target - w.fog.level) * damp(0.3, dt);

  // lightning
  if (st.lightning) {
    st.lightning.warn -= dt;
    if (st.lightning.warn <= 0) {
      const L = st.lightning;
      st.lightning = null;
      emit(w, { e: 'lightning', x: L.x, y: L.y, onDeck: L.onDeck, warn: false });
      emit(w, { e: 'shake', amount: 0.5 });
      sfx(w, 'thunder', L.x);
      if (L.onDeck) {
        addFire(w, L.x, L.y);
        hullHit(w, 3, L.x, L.y);
      }
    }
  } else if (st.level > 0.2) {
    st.nextLightning -= dt;
    if (st.nextLightning <= 0) {
      st.nextLightning = w.rng.range(7, 13) / Math.max(0.5, st.level);
      const onDeck = w.rng.chance(0.6);
      let x: number, y: number;
      if (onDeck) {
        x = w.rng.range(-6.5, 5.5);
        const hb = halfBeam(x) - 0.9;
        y = w.rng.range(-hb, hb);
      } else {
        x = w.rng.range(-12, 14);
        y = w.ship.y + (w.rng.chance(0.5) ? 1 : -1) * w.rng.range(5, 10);
      }
      st.lightning = { warn: 0.8, x, y, onDeck, uid: 0 };
      emit(w, { e: 'lightning', x, y, onDeck, warn: true });
    }
  }
  // wave slams
  if (st.slam) {
    st.slam.warn -= dt;
    if (st.slam.warn <= 0) {
      const side = st.slam.side;
      st.slam = null;
      pushShip(w, -side * 2.2);
      w.ship.water = clamp(w.ship.water + 0.035, 0, 1);
      emit(w, { e: 'slam', side, warn: false });
      emit(w, { e: 'shake', amount: 0.7 });
      sfx(w, 'wave_slam');
      for (const p of w.players) if (!p.at) { p.vy += -side * 2.4; }
      const p = w.ship.sail === 0 ? 0.55 : w.ship.sail === 1 ? 0.2 : 0.05;
      if (w.rng.chance(p)) addLeak(w, w.rng.range(-5, 4), side * 2.2);
    }
  } else if (st.level > 0.35) {
    st.nextSlam -= dt;
    if (st.nextSlam <= 0) {
      st.nextSlam = w.rng.range(9, 15) / st.level;
      const side = w.rng.chance(0.5) ? 1 : -1;
      st.slam = { warn: 1.1, side, uid: 0 };
      emit(w, { e: 'slam', side, warn: true });
    }
  }
}
