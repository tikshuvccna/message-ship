/**
 * VoyageSim: the pure, deterministic simulation of one sea node.
 * Fixed step 1/60 s with an accumulator; seeded RNG; no Phaser. The renderer reads the state
 * and drains `events` every frame.
 */
import type { HudState, NodeStats, VirtualInput } from '../contract';
import { startBoss, stepBoss } from './boss';
import { stepBolts, stepShots } from './combat';
import { spawnCreature, stepCreatures } from './creatures';
import { decide, promptOf, stepBit, stepCannons, stepItems, stepPlayers } from './deck';
import { buildSchedule, type Schedule, type ScheduleEntry } from './director';
import { stepDeckHazards, stepFloaters, stepWeather } from './hazards';
import { stepShip } from './ship';
import { T } from './texts';
import type { SimEvent } from './types';
import {
  createWorld, emit, hostileAlive, hullMax, labelOf, sfx, spawnFloater, toast, type FullConfig, type SimData, type World,
} from './world';

export const STEP = 1 / 60;
const MAX_FRAME = 0.25;
const SPAWN_X = 18;

export class VoyageSim {
  readonly w: World;
  readonly sched: Schedule;
  private acc = 0;

  constructor(cfg: FullConfig, data: SimData) {
    this.sched = buildSchedule(cfg, data.creatures);
    this.w = createWorld(cfg, data, this.sched);
  }

  /** Advance by real elapsed seconds; runs whole fixed steps. Returns the number of steps run. */
  advance(dt: number): number {
    this.acc += Math.min(MAX_FRAME, Math.max(0, dt));
    let n = 0;
    while (this.acc >= STEP) {
      this.acc -= STEP;
      this.step();
      n++;
    }
    return n;
  }

  /** Interpolation factor between the last two steps (0..1), for smooth rendering. */
  get alpha(): number {
    return this.acc / STEP;
  }

  /** Latch input for a player: move axes persist, buttons are edge-triggered until consumed. */
  setInput(v: VirtualInput): void {
    const i = this.w.inputs[v.p];
    if (!i) return;
    i.mx = Math.max(-1, Math.min(1, v.moveX || 0));
    i.my = Math.max(-1, Math.min(1, v.moveY || 0));
    if (v.action) i.action = true;
    if (v.throwIt) i.throwIt = true;
  }

  drainEvents(): SimEvent[] {
    const e = this.w.events;
    this.w.events = [];
    return e;
  }

  get over(): boolean {
    return this.w.over;
  }

  step(): void {
    const w = this.w;
    if (w.over) return;
    const dt = STEP;
    w.frame++;
    w.t += dt;
    w.acc.secondsPlayed = w.t;
    this.playSchedule();
    stepShip(w, dt);
    stepPlayers(w, dt);
    stepBit(w, dt);
    stepItems(w, dt);
    stepCannons(w, dt);
    stepShots(w, dt);
    stepCreatures(w, dt);
    stepBolts(w, dt);
    if (w.boss) stepBoss(w, dt);
    stepFloaters(w, dt);
    stepDeckHazards(w, dt);
    stepWeather(w, dt);
    // buffs & combo
    w.buffs.double = Math.max(0, w.buffs.double - dt);
    w.buffs.speed = Math.max(0, w.buffs.speed - dt);
    if (w.combo > 0) {
      w.comboT -= dt;
      if (w.comboT <= 0) w.combo = 0;
    }
    if (w.tutorial.step < 99) this.tutorial(dt);
    this.checkEnd(dt);
  }

  // ---- schedule playback -------------------------------------------------

  private playSchedule(): void {
    const w = this.w;
    const list = this.sched.entries;
    // battle: when the sea is clear, pull the next wave forward
    if (this.sched.kind === 'battle' && hostileAlive(w) === 0 && w.wavesSpawned > 0) {
      for (let i = w.schedIdx; i < list.length; i++) {
        const e = list[i];
        if (e && e.kind === 'wave') {
          if (e.at > w.t + 3) {
            e.at = w.t + 3;
            toast(w, T.waveIncoming, 'info');
            list.sort((a, b) => a.at - b.at);
          }
          break;
        }
      }
    }
    while (w.schedIdx < list.length) {
      const e = list[w.schedIdx];
      if (!e || e.at > w.t) break;
      w.schedIdx++;
      this.run(e);
    }
  }

  private run(e: ScheduleEntry): void {
    const w = this.w;
    const sy = w.ship.y;
    switch (e.kind) {
      case 'wave': {
        w.wavesSpawned++;
        let g = 0;
        for (const s of e.spawns) {
          const def = w.data.creatures.find((d) => d.id === s.id);
          if (!def) continue;
          g++;
          const base = w.rng.range(0, Math.PI * 2);
          for (let i = 0; i < s.count; i++) {
            const c = spawnCreature(w, def, s.from, g, e.wave);
            c.ang = base + (s.count > 1 ? (i / s.count) * 0.9 : 0);
            if (s.count > 1) { c.x += i * 0.7; c.y += (i % 2 ? 0.6 : -0.6); }
          }
        }
        if (e.wave > 0) sfx(w, 'alarm');
        break;
      }
      case 'float': {
        const y = clampLane(sy + e.yRel, e.what);
        const r = e.what === 'reef' ? 1.1 + e.variant * 0.25 : e.what === 'crate' ? 0.55 : e.what === 'bottle' ? 0.4 : e.what === 'whirlpool' ? 3.2 : 2;
        spawnFloater(w, e.what, SPAWN_X + (e.what === 'island' || e.what === 'cove' ? 10 : 0), y, {
          r, variant: e.variant, value: e.what === 'reef' ? 0 : e.value, tag: e.tag,
        });
        break;
      }
      case 'friend': {
        const def = w.data.creatures.find((d) => d.id === e.id);
        if (def) spawnCreature(w, def, 'near', 0, 0, true, e.yRel);
        break;
      }
      case 'toast':
        toast(w, e.text, e.tone ?? 'info');
        break;
      case 'storm':
        w.storm.target = e.level;
        if (e.level > 0) { w.storm.nextLightning = 3; w.storm.nextSlam = 6; }
        break;
      case 'fog':
        w.fog.target = e.level;
        break;
      case 'boss':
        startBoss(w);
        break;
    }
  }

  // ---- tutorial (start node) ---------------------------------------------

  private tutorial(dt: number): void {
    const w = this.w;
    const tu = w.tutorial;
    tu.t += dt;
    const p = w.players[0];
    if (!p) return;
    const anyHeld = w.players.some((q) => q.held?.kind === 'ball');
    const anyLoaded = Object.values(w.cannons).some((c) => c.loaded);
    const say = (text: string): void => { toast(w, text, 'info'); tu.t = 0; };
    switch (tu.step) {
      case 0:
        if (tu.t > 1) { say(T.tut0); tu.step = 1; }
        break;
      case 1:
        if (w.players.some((q) => Math.hypot(q.x + 3.2, q.y - 2.25) < 1.6) || anyHeld) { say(T.tut1); tu.step = 2; }
        break;
      case 2:
        if (anyHeld || anyLoaded) { say(T.tut2); tu.step = 3; }
        break;
      case 3:
        if (anyLoaded) { say(T.tut3); tu.step = 4; }
        break;
      case 4:
        if (w.acc.shots > 0 && tu.t > 2.5) {
          // bring the first creature now
          const e = this.sched.entries.find((x) => x.kind === 'wave');
          if (e && e.at > w.t + 2) { e.at = w.t + 2; this.sched.entries.sort((a, b) => a.at - b.at); }
          tu.step = 5;
        }
        break;
      case 5:
        if (w.creatures.some((c) => c.hostile)) { say(T.tut4); tu.step = 6; }
        break;
      case 6:
        if (w.wavesSpawned > 0 && hostileAlive(w) === 0) {
          say(T.tut5);
          for (let i = 0; i < 3; i++) spawnFloater(w, 'crate', SPAWN_X + i * 4, w.ship.y + [3.5, -3, 5][i]!, { r: 0.55, value: 10 + i * 20 });
          tu.step = 7;
        }
        break;
      case 7:
        if (tu.t > 12) { say(T.tutDone); tu.step = 99; }
        break;
    }
  }

  // ---- end of node -------------------------------------------------------

  private checkEnd(dt: number): void {
    const w = this.w;
    const s = w.ship;
    if (s.sinking < 0 && (s.water >= 1 || s.hull <= 0)) {
      s.sinking = 0;
      emit(w, { e: 'sinking' });
      toast(w, T.sinking, 'bad');
      sfx(w, 'alarm');
      for (const p of w.players) { p.at = null; p.job = null; }
    }
    if (s.sinking >= 0) {
      s.sinking += dt;
      if (s.sinking >= 2.6) {
        w.over = true;
        w.acc.hullLeft = 0;
        emit(w, { e: 'sunk' });
      }
      return;
    }
    if (w.doneT >= 0) {
      w.doneT -= dt;
      if (w.doneT <= 0) this.finish();
      return;
    }
    const sc = this.sched;
    if (sc.arrival) {
      const mark = w.floaters.find((f) => f.alive && (f.kind === 'lighthouse' || f.kind === 'pier'));
      if (!w.arrived && mark && mark.x <= 9.5) {
        w.arrived = true;
        toast(w, T.arrived, 'good');
      }
      if (w.arrived && w.ship.speed < 0.35) {
        emit(w, { e: 'arrive' });
        w.doneT = 1.2;
      } else if (w.t > sc.duration + 20) {
        w.arrived = true;
        emit(w, { e: 'arrive' });
        w.doneT = 0.5;
      }
      return;
    }
    if (sc.kind === 'boss') {
      if (w.boss?.friendly) w.doneT = 4.5;
      return;
    }
    const allSpawned = !this.sched.entries.slice(w.schedIdx).some((e) => e.kind === 'wave');
    const tutorialDone = w.tutorial.step >= 99;
    if (w.t >= sc.duration && allSpawned && tutorialDone) {
      const alive = hostileAlive(w);
      if (sc.needsClear && alive > 0 && w.t < sc.duration + 30) return;
      if (alive > 0) for (const c of w.creatures) if (c.hostile && c.state !== 'cleaned' && c.state !== 'gone' && c.state !== 'deck') c.state = 'flee';
      if (sc.needsClear && alive === 0) toast(w, T.cleared, 'good');
      w.doneT = 1.5;
    }
  }

  private finish(): void {
    const w = this.w;
    w.over = true;
    w.acc.hullLeft = w.ship.hull / hullMax(w);
    emit(w, { e: 'done' });
  }

  // ---- views for the UI --------------------------------------------------

  progress(): number {
    const w = this.w;
    if (this.sched.kind === 'boss') return w.boss ? 1 - w.boss.hp / w.boss.maxHp : 0;
    return Math.max(0, Math.min(1, w.t / this.sched.duration));
  }

  hud(): HudState {
    const w = this.w;
    const p0 = w.players[0];
    const h: HudState = {
      hull: Math.round(w.ship.hull), hullMax: hullMax(w), water: w.ship.water, coins: w.acc.coins,
      progress: this.progress(), held: p0 ? labelOf(w, p0.held) : null,
      fires: w.fires.length, leaks: w.leaks.length,
      wind: Math.max(0, Math.min(1, w.ship.speed / 3.9)), combo: w.combo,
    };
    if (w.boss) h.bossHp = w.boss.hp / w.boss.maxHp;
    return h;
  }

  prompt(p = 0): string | null {
    const pl = this.w.players[p];
    if (!pl || this.w.over) return null;
    return promptOf(this.w, pl, decide(this.w, pl));
  }

  stats(): NodeStats {
    const a = this.w.acc;
    return { ...a, cleaned: a.cleaned.slice(), bottles: a.bottles.slice(), hullLeft: this.w.ship.hull / hullMax(this.w), secondsPlayed: Math.round(this.w.t) };
  }

  /** A small hash of the important state (determinism tests). */
  hash(): string {
    const w = this.w;
    const parts: number[] = [w.frame, w.ship.y, w.ship.vy, w.ship.hull, w.ship.water, w.acc.coins, w.rng.state];
    for (const p of w.players) parts.push(p.x, p.y);
    for (const c of w.creatures) parts.push(c.uid, c.x, c.y, c.hp);
    for (const s of w.shots) parts.push(s.x, s.y);
    for (const f of w.floaters) parts.push(f.x, f.y);
    return parts.map((v) => v.toFixed(6)).join(',');
  }
}

function clampLane(y: number, what: string): number {
  if (what === 'island' || what === 'cove' || what === 'lighthouse' || what === 'pier') return y;
  return Math.max(-10.5, Math.min(10.5, y));
}
