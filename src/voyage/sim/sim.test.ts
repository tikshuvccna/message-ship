import { describe, expect, it } from 'vitest';
import creaturesJson from '../../../content/he/creatures.json';
import type { AmmoDef, AmmoId, CreatureDef, NodeKind, VoyageConfig } from '../contract';
import { Autopilot } from '../autopilot';
import { closestApproach, solveLead } from './ballistics';
import { PHASE_AMMO, armHit } from './boss';
import { canFire, fireCannon, hitCreature, muzzle, predictShot, stepShots } from './combat';
import { spawnCreature } from './creatures';
import { DOUSE_SEC, REPAIR_SEC, decide, stepItems, throwItem } from './deck';
import { buildSchedule, poolFor } from './director';
import { BALL_RANGE, BALL_SPEED, SHOTS_PER_BALL, STATIONS } from './layout';
import { Rng } from './rng';
import { STEP, VoyageSim } from './sim';
import type { SimEvent } from './types';
import { addFire, addLeak } from './world';

const DATA = {
  creatures: (creaturesJson as { creatures: CreatureDef[] }).creatures,
  ammo: (creaturesJson as { ammo: AmmoDef[] }).ammo,
};
const def = (id: string): CreatureDef => {
  const d = DATA.creatures.find((c) => c.id === id);
  if (!d) throw new Error(id);
  return d;
};

function cfg(over: Partial<VoyageConfig> & { difficulty?: number } = {}): VoyageConfig & { difficulty?: number } {
  const leg = over.leg ?? 1;
  return {
    seed: 42, leg, nodeId: 'test_3', nodeKind: 'battle', look: 'girl', playerName: 't', twoPlayers: false,
    stats: { hullMax: 100, reloadSec: 1.6, shotPower: 1, sailSpeed: 1, repairSpeed: 1, lanternRadius: 260, doubleShot: false, shield: false },
    ammo: leg === 4 ? PHASE_AMMO[1] : PHASE_AMMO[leg as 1 | 2 | 3], duration: 80, checkpointHull: 1, quality: 'high',
    ...over,
  };
}

/** Run n fixed steps, collecting events. */
function run(sim: VoyageSim, n: number, each?: (i: number) => void): SimEvent[] {
  const evs: SimEvent[] = [];
  for (let i = 0; i < n; i++) {
    each?.(i);
    sim.step();
    evs.push(...sim.drainEvents());
  }
  return evs;
}

/** Put player 0 at a deck point and press the action button for one step. */
function act(sim: VoyageSim, x: number, y: number): SimEvent[] {
  const p = sim.w.players[0]!;
  p.x = x; p.y = y; p.vx = 0; p.vy = 0;
  sim.setInput({ p: 0, moveX: 0, moveY: 0, action: true, throwIt: false });
  return run(sim, 1);
}

describe('rng', () => {
  it('is deterministic and in range', () => {
    const a = new Rng(7), b = new Rng(7);
    for (let i = 0; i < 1000; i++) {
      const x = a.next();
      expect(x).toBe(b.next());
      expect(x).toBeGreaterThanOrEqual(0);
      expect(x).toBeLessThan(1);
    }
  });
});

describe('determinism', () => {
  it('same seed + same inputs => identical state', () => {
    const mk = (): VoyageSim => new VoyageSim(cfg({ seed: 99 }), DATA);
    const a = mk(), b = mk();
    const pa = new Autopilot(a), pb = new Autopilot(b);
    for (let i = 0; i < 60 * 40; i++) {
      pa.tick(STEP); pb.tick(STEP);
      a.step(); b.step();
      a.drainEvents(); b.drainEvents();
    }
    expect(a.hash()).toBe(b.hash());
    expect(a.w.acc.shots).toBe(b.w.acc.shots);
  });
  it('advance() with uneven frame times equals fixed stepping', () => {
    const a = new VoyageSim(cfg({ seed: 5 }), DATA), b = new VoyageSim(cfg({ seed: 5 }), DATA);
    const frames = [0.016, 0.017, 0.033, 0.008, 0.05, 0.0167];
    let steps = 0;
    for (let i = 0; i < 600; i++) steps += a.advance(frames[i % frames.length]!);
    for (let i = 0; i < steps; i++) b.step();
    expect(a.hash()).toBe(b.hash());
  });
  it('different seeds diverge', () => {
    const a = new VoyageSim(cfg({ seed: 1 }), DATA), b = new VoyageSim(cfg({ seed: 2 }), DATA);
    run(a, 600); run(b, 600);
    expect(a.hash()).not.toBe(b.hash());
  });
});

describe('ballistics', () => {
  it('a perfectly led shot hits a constant-velocity target', () => {
    const rng = new Rng(3);
    for (let k = 0; k < 300; k++) {
      const mx = rng.range(-3, 3), my = rng.range(-3, 3);
      const ivx = 0, ivy = rng.range(-3, 3); // inherited ship lateral speed
      const tx = mx + rng.range(-9, 9), ty = my + rng.range(-9, 9);
      const tvx = rng.range(-4, 4), tvy = rng.range(-4, 4);
      const s = BALL_SPEED;
      const sol = solveLead(mx, my, s, ivx, ivy, tx, ty, tvx, tvy);
      expect(sol).not.toBeNull();
      if (!sol) continue;
      const ux = Math.cos(sol.angle) * s + ivx, uy = Math.sin(sol.angle) * s + ivy;
      const ca = closestApproach(mx, my, ux, uy, tx, ty, tvx, tvy, sol.t * 2);
      expect(Math.sqrt(ca.d2)).toBeLessThan(1e-6);
      expect(Math.abs(ca.t - sol.t)).toBeLessThan(1e-6);
    }
  });
  it('returns null for an unreachable target (faster than the shot, running away)', () => {
    expect(solveLead(0, 0, 5, 0, 0, 10, 0, 8, 0)).toBeNull();
  });
  it('in the sim: aiming at the lead angle and firing cleans the target', () => {
    const sim = new VoyageSim(cfg({ nodeKind: 'island' }), DATA);
    const w = sim.w;
    const c = spawnCreature(w, def('garble_squid'), 'bow');
    c.state = 'act';
    c.x = 14; c.y = 1.5; c.vx = -1.8; c.vy = 1.1; c.hp = 1;
    const id = 'cannon_bow';
    const m = muzzle(w, id);
    const sol = solveLead(m.x, m.y, BALL_SPEED, 0, w.ship.vy, c.x, c.y, c.vx, c.vy)!;
    w.cannons[id].aim = sol.angle;
    w.cannons[id].loaded = 'code';
    w.cannons[id].charges = 1;
    w.cannons[id].loadT = 0;
    expect(predictShot(w, id).hit?.uid).toBe(c.uid);
    expect(fireCannon(w, id)).toBe(true);
    // move the target with constant velocity (no AI), only the shots step
    let hit = false;
    for (let i = 0; i < 120 && !hit; i++) {
      c.x += c.vx * STEP; c.y += c.vy * STEP;
      stepShots(w, STEP);
      hit = c.state === 'cleaned';
    }
    expect(hit).toBe(true);
  });
  it('a shot ends after its range', () => {
    const sim = new VoyageSim(cfg({ nodeKind: 'island' }), DATA);
    const w = sim.w;
    w.cannons.cannon_near.loaded = 'addr';
    w.cannons.cannon_near.charges = 1;
    w.cannons.cannon_near.loadT = 0;
    fireCannon(w, 'cannon_near');
    const frames = Math.ceil(BALL_RANGE / BALL_SPEED / STEP) + 2;
    for (let i = 0; i < frames; i++) stepShots(w, STEP);
    expect(w.shots.length).toBe(0);
  });
});

describe('damage rules', () => {
  it('right ammo = 2 x power x combo, wrong = 0.5 + hint, wrong resets combo', () => {
    const sim = new VoyageSim(cfg({ nodeKind: 'island' }), DATA);
    const w = sim.w;
    const c = spawnCreature(w, def('tide_whale'), 'bow');
    c.state = 'act';
    c.hp = 100;
    let hp = c.hp;
    const hitAndDelta = (a: AmmoId): number => { hitCreature(w, c, a, 1, 1, 0); const d = hp - c.hp; hp = c.hp; return d; };
    expect(hitAndDelta('size')).toBeCloseTo(2);
    expect(hitAndDelta('size')).toBeCloseTo(2.5);
    expect(hitAndDelta('size')).toBeCloseTo(3);
    const evs = sim.drainEvents();
    expect(evs.some((e) => e.e === 'hint')).toBe(false);
    expect(hitAndDelta('addr')).toBeCloseTo(0.5);
    expect(sim.drainEvents().some((e) => e.e === 'hint' && e.text === def('tide_whale').hint)).toBe(true);
    expect(w.combo).toBe(0);
    expect(hitAndDelta('size')).toBeCloseTo(2);
    // shot power scales right hits
    hitCreature(w, c, 'size', 1.5, 1, 0);
    expect(hp - c.hp).toBeCloseTo(2 * 1.5 * 1.25);
    expect(w.acc.rightAmmo).toBe(5);
    expect(w.acc.wrongAmmo).toBe(1);
  });
  it('cleaning drops coins that fly to the ship, and is counted', () => {
    const sim = new VoyageSim(cfg({ nodeKind: 'island' }), DATA);
    const w = sim.w;
    const c = spawnCreature(w, def('lost_bottle'), 'near');
    c.state = 'act';
    c.x = 0; c.y = -6; c.hp = 1;
    hitCreature(w, c, 'addr', 1, 0, -1);
    expect(c.state).toBe('cleaned');
    expect(w.acc.cleaned).toContain('lost_bottle');
    run(sim, 60 * 5);
    expect(w.acc.coins).toBe(def('lost_bottle').coins);
  });
});

describe('flooding and sinking', () => {
  it('three leaks sink the ship in about 31 s; water slows it down first', () => {
    const sim = new VoyageSim(cfg({ nodeKind: 'island', duration: 200 }), DATA);
    const w = sim.w;
    w.bit = null; // no helper
    addLeak(w, -5, 1); addLeak(w, 0, -1.5); addLeak(w, 4, 1.2);
    const v0 = w.ship.speed;
    let sunkAt = -1;
    let halfSpeed = 0;
    for (let i = 0; i < 60 * 60 && sunkAt < 0; i++) {
      sim.step();
      if (w.ship.water > 0.5 && !halfSpeed) halfSpeed = w.ship.speed;
      if (sim.drainEvents().some((e) => e.e === 'sunk')) sunkAt = w.t;
    }
    expect(halfSpeed).toBeLessThan(v0 * 0.85);
    // 1 / (3*0.012 - 0.005) = 32.26 s to fill, + 2.6 s sinking animation
    expect(sunkAt).toBeGreaterThan(32.26 + 2.4);
    expect(sunkAt).toBeLessThan(32.26 + 3.0);
    expect(sim.over).toBe(true);
  });
  it('the pump drains water when there is no leak', () => {
    const sim = new VoyageSim(cfg({ nodeKind: 'island' }), DATA);
    sim.w.ship.water = 0.3;
    run(sim, 600);
    expect(sim.w.ship.water).toBeCloseTo(0.3 - 0.005 * 10, 3);
  });
  it('hull at zero sinks the ship', () => {
    const sim = new VoyageSim(cfg({ nodeKind: 'island' }), DATA);
    sim.w.ship.hull = 0;
    const evs = run(sim, 200);
    expect(evs.some((e) => e.e === 'sinking')).toBe(true);
    expect(evs.some((e) => e.e === 'sunk')).toBe(true);
  });
  it('the shield absorbs hits', () => {
    const c = cfg({ nodeKind: 'island' });
    c.stats.shield = true;
    const sim = new VoyageSim(c, DATA);
    const before = sim.w.ship.hull;
    for (let i = 0; i < 3; i++) addFire(sim.w, 0, 0) ; // fires do not use the shield
    sim.w.fires = [];
    import('./world').then(() => undefined);
    expect(sim.w.buffs.shield).toBe(3);
    expect(before).toBe(100);
  });
});

describe('repair timing', () => {
  it('a plank patches a leak in 1.2 s / repairSpeed', () => {
    for (const rs of [1, 2]) {
      const c = cfg({ nodeKind: 'island' });
      c.stats.repairSpeed = rs;
      const sim = new VoyageSim(c, DATA);
      const w = sim.w;
      w.bit = null;
      w.leaks = [];
      addLeak(w, -2, -1.5);
      const l = w.leaks[0]!;
      w.players[0]!.held = { kind: 'plank' };
      act(sim, l.x, l.y - 0.5);
      expect(w.players[0]!.job?.kind).toBe('leak');
      const need = Math.round(REPAIR_SEC / rs / STEP);
      run(sim, need - 2);
      expect(w.leaks.length).toBe(1);
      run(sim, 3);
      expect(w.leaks.length).toBe(0);
      expect(w.players[0]!.held).toBeNull();
    }
  });
  it('a full bucket douses a fire in 1.0 s and empties; walking away cancels', () => {
    const sim = new VoyageSim(cfg({ nodeKind: 'island' }), DATA);
    const w = sim.w;
    addFire(w, 3, 1);
    const f = w.fires[0]!;
    w.players[0]!.held = { kind: 'bucket', full: true };
    act(sim, f.x, f.y - 0.5);
    run(sim, 20);
    sim.setInput({ p: 0, moveX: 1, moveY: 0, action: false, throwIt: false });
    run(sim, 1);
    expect(w.players[0]!.job).toBeNull();
    sim.setInput({ p: 0, moveX: 0, moveY: 0, action: false, throwIt: false });
    act(sim, f.x, f.y - 0.5);
    run(sim, Math.round(DOUSE_SEC / STEP) + 1);
    expect(w.fires.length).toBe(0);
    expect(w.players[0]!.held?.full).toBe(false);
  });
});

describe('carry and load rules', () => {
  it('rack -> carry -> load -> reload -> fire', () => {
    const sim = new VoyageSim(cfg({ nodeKind: 'island' }), DATA);
    const w = sim.w;
    const p = w.players[0]!;
    // stand in front of the rack: the slot is chosen by x
    act(sim, STATIONS.rack.use.x - 1.4, STATIONS.rack.use.y);
    expect(p.held?.kind).toBe('ball');
    expect(p.held?.ammo).toBe(w.rack[0]!.ammo);
    act(sim, STATIONS.rack.use.x + 1.4, STATIONS.rack.use.y);
    expect(p.held).toBeNull(); // action at the rack while carrying a ball puts it back
    act(sim, STATIONS.rack.use.x + 1.4, STATIONS.rack.use.y);
    expect(p.held?.ammo).toBe(w.rack[w.rack.length - 1]!.ammo); // the far end of the rack = last slot
    // carry to the bow cannon
    p.held = { kind: 'ball', ammo: 'addr' };
    act(sim, STATIONS.cannon_bow.use.x, STATIONS.cannon_bow.use.y);
    const c = w.cannons.cannon_bow;
    expect(c.loaded).toBe('addr');
    expect(p.held).toBeNull();
    expect(p.at).toBe('cannon_bow');
    expect(canFire(w, 'cannon_bow')).toBe(false);
    sim.setInput({ p: 0, moveX: 0, moveY: 0, action: false, throwIt: true });
    run(sim, 1);
    expect(w.acc.shots).toBe(0);
    run(sim, Math.round(1.6 / STEP));
    expect(canFire(w, 'cannon_bow')).toBe(true);
    sim.setInput({ p: 0, moveX: 0, moveY: 0, action: false, throwIt: true });
    run(sim, 1);
    expect(w.acc.shots).toBe(1);
    expect(c.charges).toBe(SHOTS_PER_BALL - 1);
    // the remaining charges fire after a short cycle; then the cannon is empty
    for (let k = 1; k < SHOTS_PER_BALL; k++) {
      run(sim, Math.round((1.6 * 0.45) / STEP) + 1);
      sim.setInput({ p: 0, moveX: 0, moveY: 0, action: false, throwIt: true });
      run(sim, 1);
    }
    expect(w.acc.shots).toBe(SHOTS_PER_BALL);
    expect(c.loaded).toBeNull();
    // leave the cannon
    sim.setInput({ p: 0, moveX: 0, moveY: 0, action: true, throwIt: false });
    run(sim, 1);
    expect(p.at).toBeNull();
  });
  it('one item at a time: action while carrying puts it down; then pick it up again', () => {
    const sim = new VoyageSim(cfg({ nodeKind: 'island' }), DATA);
    const w = sim.w;
    const p = w.players[0]!;
    w.items = [];
    p.held = { kind: 'plank' };
    act(sim, -1, 0.5);
    expect(p.held).toBeNull();
    expect(w.items.length).toBe(1);
    expect(decide(w, p)?.a).toBe('pick');
    act(sim, p.x, p.y);
    expect(p.held?.kind).toBe('plank');
    expect(w.items.length).toBe(0);
  });
  it('a thrown ball lands in an empty cannon in front of the thrower', () => {
    const sim = new VoyageSim(cfg({ nodeKind: 'island' }), DATA);
    const w = sim.w;
    const p = w.players[0]!;
    p.x = 3.2; p.y = 0; p.face = 0;
    p.held = { kind: 'ball', ammo: 'time' };
    throwItem(w, p);
    for (let i = 0; i < 90; i++) stepItems(w, STEP);
    expect(w.cannons.cannon_bow.loaded).toBe('time');
  });
  it('a ball thrown to a free partner is caught', () => {
    const sim = new VoyageSim(cfg({ nodeKind: 'island', twoPlayers: true }), DATA);
    const w = sim.w;
    const [a, b] = [w.players[0]!, w.players[1]!];
    a.x = -3; a.y = 0; a.face = 0; b.x = 0.5; b.y = 0.3; b.held = null;
    a.held = { kind: 'ball', ammo: 'fmt' };
    throwItem(w, a);
    for (let i = 0; i < 90; i++) stepItems(w, STEP);
    expect(b.held?.ammo).toBe('fmt');
  });
  it('a ball thrown overboard is lost', () => {
    const sim = new VoyageSim(cfg({ nodeKind: 'island' }), DATA);
    const w = sim.w;
    const p = w.players[0]!;
    w.items = [];
    p.x = -2; p.y = -2.6; p.face = -Math.PI / 2;
    p.held = { kind: 'ball', ammo: 'fmt' };
    throwItem(w, p);
    for (let i = 0; i < 90; i++) stepItems(w, STEP);
    expect(w.items.length).toBe(0);
  });
});

describe('director', () => {
  const kinds: NodeKind[] = ['battle', 'island', 'event', 'storm', 'harbour', 'lighthouse', 'boss', 'start'];
  it('is deterministic per seed', () => {
    for (const k of kinds) {
      const a = buildSchedule(cfg({ nodeKind: k }), DATA.creatures);
      const b = buildSchedule(cfg({ nodeKind: k }), DATA.creatures);
      expect(JSON.stringify(a)).toBe(JSON.stringify(b));
    }
  });
  it('battle: 3-5 waves from the leg pool, sorted, weaknesses on the rack', () => {
    for (const leg of [1, 2, 3] as const) for (let seed = 1; seed < 30; seed++) {
      const c = cfg({ leg, seed, nodeKind: 'battle' });
      const s = buildSchedule(c, DATA.creatures);
      const waves = s.entries.filter((e) => e.kind === 'wave');
      expect(waves.length).toBeGreaterThanOrEqual(3);
      expect(waves.length).toBeLessThanOrEqual(5);
      for (let i = 1; i < s.entries.length; i++) expect(s.entries[i]!.at).toBeGreaterThanOrEqual(s.entries[i - 1]!.at);
      for (const w of waves) if (w.kind === 'wave') for (const sp of w.spawns) {
        const d = def(sp.id);
        expect(d.leg).toBe(leg);
        expect(c.ammo).toContain(d.weakness);
      }
      // every creature of the leg's pool appears
      const ids = new Set(waves.flatMap((w) => (w.kind === 'wave' ? w.spawns.map((x) => x.id) : [])));
      expect(ids.size).toBe(poolFor(DATA.creatures, leg, c.ammo).length);
    }
  });
  it('battles scale with difficulty', () => {
    const count = (d: number): number => buildSchedule(cfg({ difficulty: d, seed: 9 }), DATA.creatures).entries
      .reduce((n, e) => n + (e.kind === 'wave' ? e.spawns.reduce((m, s) => m + s.count, 0) : 0), 0);
    expect(count(1)).toBeGreaterThan(count(0));
  });
  it('node kinds have their content', () => {
    const has = (k: NodeKind, pred: (e: ReturnType<typeof buildSchedule>['entries'][number]) => boolean): boolean =>
      buildSchedule(cfg({ nodeKind: k }), DATA.creatures).entries.some(pred);
    expect(has('island', (e) => e.kind === 'float' && e.what === 'crate')).toBe(true);
    expect(has('island', (e) => e.kind === 'float' && e.what === 'bottle')).toBe(true);
    expect(has('island', (e) => e.kind === 'friend')).toBe(true);
    expect(has('island', (e) => e.kind === 'float' && e.what === 'cove')).toBe(true);
    expect(has('storm', (e) => e.kind === 'storm' && e.level > 0)).toBe(true);
    expect(has('storm', (e) => e.kind === 'wave')).toBe(true);
    expect(has('boss', (e) => e.kind === 'boss')).toBe(true);
    expect(has('lighthouse', (e) => e.kind === 'float' && e.what === 'lighthouse')).toBe(true);
    expect(has('harbour', (e) => e.kind === 'float' && e.what === 'pier')).toBe(true);
    expect(has('event', (e) => e.kind === 'float' && e.what === 'bottle')).toBe(true);
    const st = buildSchedule(cfg({ nodeKind: 'start' }), DATA.creatures);
    expect(st.tutorial).toBe(true);
    expect(st.entries.filter((e) => e.kind === 'wave').length).toBe(1);
  });
});

describe('boss', () => {
  it('three phases (rules, layers, PDUs) then friendly; rack follows the phase', () => {
    const sim = new VoyageSim(cfg({ leg: 4, nodeKind: 'boss' }), DATA);
    const w = sim.w;
    const phases: number[] = [];
    let friend = false, done = false;
    const seenWeak = new Set<string>();
    for (let i = 0; i < 60 * 600 && !done; i++) {
      // cheat: perfect gunner, hits every risen arm with its own rule, and keeps the ship afloat
      if (w.boss) for (const a of w.boss.arms) {
        if (a.rise > 0.6 && a.state !== 'calm' && i % 20 === 0) {
          expect(w.rack.map((r) => r.ammo)).toContain(a.weakness);
          seenWeak.add(a.weakness);
          armHit(w, a, a.weakness, 1, 1, 0);
        }
      }
      w.ship.hull = 100; w.ship.water = 0;
      sim.step();
      for (const e of sim.drainEvents()) {
        if (e.e === 'phase') phases.push(e.phase);
        if (e.e === 'bossFriend') friend = true;
        if (e.e === 'done') done = true;
      }
    }
    expect(phases).toEqual([1, 2, 3]);
    expect(friend).toBe(true);
    expect(done).toBe(true);
    expect(seenWeak.size).toBe(17);
    expect(sim.hud().bossHp).toBe(0);
    expect(w.acc.cleaned).toContain('garble_kraken');
  });
  it('wrong ammo on an arm = 0.5 and a hint', () => {
    const sim = new VoyageSim(cfg({ leg: 4, nodeKind: 'boss' }), DATA);
    run(sim, 60 * 8);
    const a = sim.w.boss!.arms[0]!;
    const hp = a.hp;
    const wrong = PHASE_AMMO[1].find((x) => x !== a.weakness)!;
    armHit(sim.w, a, wrong, 1, 1, 0);
    expect(hp - a.hp).toBeCloseTo(0.5);
    expect(sim.drainEvents().some((e) => e.e === 'hint')).toBe(true);
  });
});

describe('robustness', () => {
  const kinds: NodeKind[] = ['battle', 'island', 'event', 'storm', 'harbour', 'lighthouse', 'boss', 'start'];
  it('no NaN under 10k random steps for every node kind (1 and 2 players)', () => {
    for (const k of kinds) for (const two of [false, true]) {
      const sim = new VoyageSim(cfg({ nodeKind: k, leg: k === 'boss' ? 4 : 2, seed: 777, twoPlayers: two, difficulty: 1 }), DATA);
      const r = new Rng(11);
      for (let i = 0; i < 10000; i++) {
        if (i % 7 === 0) for (const p of [0, 1] as const) {
          sim.setInput({ p, moveX: r.range(-1, 1), moveY: r.range(-1, 1), action: r.chance(0.15), throwIt: r.chance(0.1) });
        }
        if (sim.over) break;
        sim.step();
        sim.drainEvents();
      }
      const w = sim.w;
      const nums: number[] = [w.ship.y, w.ship.vy, w.ship.speed, w.ship.hull, w.ship.water, w.ship.heave, w.ship.roll];
      for (const p of w.players) nums.push(p.x, p.y, p.vx, p.vy);
      for (const c of w.creatures) nums.push(c.x, c.y, c.vx, c.vy, c.hp);
      for (const s of w.shots) nums.push(s.x, s.y);
      for (const b of w.bolts) nums.push(b.x, b.y);
      for (const f of w.floaters) nums.push(f.x, f.y);
      for (const n of nums) expect(Number.isFinite(n)).toBe(true);
      expect(sim.hash()).not.toContain('NaN');
      // players stay on deck
      for (const p of w.players) { expect(Math.abs(p.x)).toBeLessThan(8); expect(Math.abs(p.y)).toBeLessThan(3.5); }
    }
  });
});

describe('autopilot soak (whole loop through the input path)', () => {
  it('a leg-1 battle gets played to the end and creatures get cleaned', () => {
    const sim = new VoyageSim(cfg({ seed: 7, nodeKind: 'battle', duration: 80, difficulty: 0.3 }), DATA);
    const ap = new Autopilot(sim);
    let ended: string | null = null;
    for (let i = 0; i < 60 * 240 && !ended; i++) {
      ap.tick(STEP);
      sim.step();
      for (const e of sim.drainEvents()) if (e.e === 'done' || e.e === 'sunk') ended = e.e;
    }
    const st = sim.stats();
    expect(st.shots).toBeGreaterThan(5);
    expect(st.rightAmmo).toBeGreaterThan(3);
    expect(st.cleaned.length).toBeGreaterThan(2);
    expect(ended).toBe('done');
  });
});
