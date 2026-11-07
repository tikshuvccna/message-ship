/**
 * The Garble Kraken. Three phases: the five rules, the seven layers, the PDU names.
 * Each arm has its own weakness and symptom; a right hit knocks it back, a cleaned arm calms
 * down and sinks, the next one rises. After the last phase the kraken turns friendly.
 */
import type { AmmoId } from '../contract';
import { fireBolt } from './combat';
import { HULL_RY } from './layout';
import { T } from './texts';
import type { Boss, BossArm } from './types';
import { addFire, addLeak, dropCoins, emit, hint, hullHit, setRack, sfx, toast, uid, type World } from './world';

export const PHASE_AMMO: Record<1 | 2 | 3, AmmoId[]> = {
  1: ['addr', 'code', 'fmt', 'size', 'time'],
  2: ['l1', 'l2', 'l3', 'l4', 'l5', 'l6', 'l7'],
  3: ['data', 'segment', 'packet', 'frame', 'bits'],
};
const ACTIVE: Record<1 | 2 | 3, number> = { 1: 3, 2: 4, 3: 3 };
const ARM_HP: Record<1 | 2 | 3, number> = { 1: 4, 2: 4, 3: 5 };

/** Arm slots around the ship (x, y relative to the ship center). Each lies inside one cannon's arc. */
export const ARM_SLOTS: { x: number; y: number }[] = [
  { x: 10.4, y: 1.8 }, { x: 10.8, y: -2.0 }, { x: 3.2, y: 7.2 }, { x: -1.2, y: 7.2 },
  { x: 3.2, y: -7.2 }, { x: -1.2, y: -7.2 }, { x: -11.2, y: 1.2 },
];

function armInfo(w: World, a: AmmoId): { symptom: string; hint: string } {
  const d = w.data.creatures.find((c) => c.weakness === a && c.behavior !== 'boss');
  const name = w.ammoName[a] ?? a;
  return { symptom: d?.symptom ?? '???', hint: d?.hint ?? `צריך: ${name}` };
}

function queueFor(w: World, phase: 1 | 2 | 3): Boss['queue'] {
  const list = w.rng.shuffle(PHASE_AMMO[phase].slice());
  return list.map((weakness) => ({ weakness, ...armInfo(w, weakness) }));
}

export function startBoss(w: World): void {
  let maxHp = 0;
  for (const p of [1, 2, 3] as const) maxHp += PHASE_AMMO[p].length * ARM_HP[p];
  w.boss = {
    phase: 0, arms: [], queue: [], x: 13.2, y: w.ship.y + 3.4, t: 0, calm: 2.6, friendly: false,
    hp: maxHp, maxHp, roarT: 0, spitT: 6,
  };
  setRack(w, PHASE_AMMO[1]);
  emit(w, { e: 'rackSwap' });
  sfx(w, 'kraken_roar');
  emit(w, { e: 'shake', amount: 0.7 });
}

function freeSlot(w: World, b: Boss): number {
  const used = new Set(b.arms.map((a) => a.slot));
  const free = ARM_SLOTS.map((_, i) => i).filter((i) => !used.has(i));
  if (free.length === 0) return 0;
  // prefer slots covered by a cannon nobody is jammed at; deterministic pick
  return w.rng.pick(free);
}

function raiseArm(w: World, b: Boss): void {
  const q = b.queue.shift();
  if (!q) return;
  const slot = freeSlot(w, b);
  const s = ARM_SLOTS[slot] ?? { x: 10, y: 0 };
  const hp = ARM_HP[(b.phase || 1) as 1 | 2 | 3];
  const arm: BossArm = {
    uid: uid(w), slot, weakness: q.weakness, symptom: q.symptom, hint: q.hint, hp, maxHp: hp,
    x: s.x, y: w.ship.y + s.y, baseX: s.x, baseY: s.y, state: 'rise', t: 0, cd: w.rng.range(3.5, 6), rise: 0,
    sway: w.rng.range(0, 6.28), hitFlash: 0,
  };
  b.arms.push(arm);
  sfx(w, 'splash', s.x);
  emit(w, { e: 'splash', x: s.x, y: w.ship.y + s.y, local: false });
}

export function stepBoss(w: World, dt: number): void {
  const b = w.boss;
  if (!b) return;
  b.t += dt;
  b.roarT = Math.max(0, b.roarT - dt);
  // the head keeps its place ahead of the ship, following the lane lazily
  b.y += (w.ship.y + 3.4 - b.y) * Math.min(1, dt * 0.6);

  if (b.friendly) {
    for (const a of b.arms) { a.rise = Math.max(0, a.rise - dt * 0.6); a.state = 'calm'; }
    return;
  }
  if (b.calm > 0) {
    b.calm -= dt;
    if (b.calm <= 0) nextPhase(w, b);
    return;
  }
  // keep the active count
  const live = b.arms.filter((a) => a.state !== 'calm');
  const need = ACTIVE[(b.phase || 1) as 1 | 2 | 3];
  if (live.length < need && b.queue.length > 0 && b.t > 0.6) {
    raiseArm(w, b);
    b.t = 0;
  }
  for (const a of b.arms) stepArm(w, b, a, dt);
  b.arms = b.arms.filter((a) => !(a.state === 'calm' && a.rise <= 0));
  // head spit in later phases
  b.spitT -= dt;
  if (b.phase >= 2 && b.spitT <= 0) {
    b.spitT = 7.5 - w.sched.difficulty * 2;
    fireBolt(w, -1, b.x - 1.5, b.y - 0.5, w.rng.range(-4, 5), w.ship.y + w.rng.range(-1.5, 1.5), 3.8);
  }
  if (b.queue.length === 0 && b.arms.every((a) => a.state === 'calm')) {
    if (b.phase >= 3) befriend(w, b);
    else {
      b.calm = 3.2;
      b.roarT = 1.5;
      sfx(w, 'kraken_roar');
      emit(w, { e: 'shake', amount: 0.6 });
    }
  }
}

function nextPhase(w: World, b: Boss): void {
  const p = (b.phase + 1) as 1 | 2 | 3;
  b.phase = p;
  b.queue = queueFor(w, p);
  b.t = 0;
  setRack(w, PHASE_AMMO[p]);
  emit(w, { e: 'rackSwap' });
  emit(w, { e: 'phase', phase: p });
  // balls already in hand or in a cannon from the previous phase stay usable (they just miss the rule)
  if (p === 2) toast(w, T.bossPhase2, 'info');
  if (p === 3) toast(w, T.bossPhase3, 'info');
}

function befriend(w: World, b: Boss): void {
  b.friendly = true;
  b.hp = 0;
  w.acc.cleaned.push('garble_kraken');
  emit(w, { e: 'bossFriend' });
  emit(w, { e: 'clean', uid: -1, id: 'garble_kraken', x: b.x, y: b.y, boss: true });
  toast(w, T.bossFriend, 'good');
  sfx(w, 'clean');
  const def = w.data.creatures.find((c) => c.behavior === 'boss');
  dropCoins(w, b.x - 3, b.y - 1, def?.coins ?? 100);
}

function stepArm(w: World, b: Boss, a: BossArm, dt: number): void {
  a.t += dt;
  a.hitFlash = Math.max(0, a.hitFlash - dt);
  a.sway += dt * 1.3;
  const sy = w.ship.y;
  let lean = 0;
  switch (a.state) {
    case 'rise':
      a.rise = Math.min(1, a.rise + dt / 1.1);
      if (a.rise >= 1) { a.state = 'idle'; a.t = 0; }
      break;
    case 'idle':
      a.cd -= dt;
      if (a.cd <= 0) {
        a.state = 'telegraph';
        a.t = 0;
        emit(w, { e: 'telegraph', uid: a.uid, attack: 'slam' });
      }
      break;
    case 'telegraph':
      lean = Math.min(1, a.t / 0.8) * 0.6;
      if (a.t >= 0.8) {
        a.state = 'slam';
        a.t = 0;
        slam(w, a);
      }
      break;
    case 'slam':
      lean = 1 - Math.min(1, a.t / 0.5);
      if (a.t > 0.5) { a.state = 'idle'; a.t = 0; a.cd = w.rng.range(5, 8) * (1.1 - 0.3 * w.sched.difficulty); }
      break;
    case 'hurt':
      lean = -Math.max(0, 1 - a.t / 0.6) * 0.8;
      if (a.t > 0.6) { a.state = 'idle'; a.t = 0; a.cd = Math.max(a.cd, 1.5); }
      break;
    case 'calm':
      a.rise = Math.max(0, a.rise - dt / 1.6);
      lean = -0.6;
      break;
    case 'under':
      break;
  }
  // tip position: slot + sway, leaning toward the ship center on attacks
  const l = Math.hypot(a.baseX, a.baseY) || 1;
  const nx = -a.baseX / l, ny = -a.baseY / l;
  a.x = a.baseX + Math.sin(a.sway) * 0.55 + nx * lean * 1.4;
  a.y = sy + a.baseY + Math.cos(a.sway * 0.8) * 0.4 + ny * lean * 1.4;
  void b;
}

function slam(w: World, a: BossArm): void {
  const side = a.baseY >= 0 ? 1 : -1;
  const x = Math.max(-7, Math.min(6.5, a.baseX * 0.6));
  const y = Math.abs(a.baseY) < 3 ? a.baseY * 0.5 : side * (HULL_RY - 1.2);
  emit(w, { e: 'shake', amount: 0.5 });
  if (hullHit(w, 7, x, y)) {
    sfx(w, 'wave_slam', x);
    const r = w.rng.next();
    if (r < 0.45) addLeak(w, x, y);
    else if (r < 0.65) addFire(w, x, y);
  }
}

export function armHit(w: World, a: BossArm, ammo: AmmoId, power: number, dx: number, dy: number): void {
  const right = ammo === a.weakness;
  w.acc.hits++;
  let dmg: number;
  if (right) {
    dmg = 2 * power * (1 + 0.25 * Math.min(w.combo, 4));
    w.combo++;
    w.comboT = 6;
    w.acc.rightAmmo++;
    sfx(w, 'hit_right', a.x);
    if (a.state === 'telegraph') { a.state = 'hurt'; a.t = 0; }
    else if (a.state === 'idle' || a.state === 'slam') { a.state = 'hurt'; a.t = 0; }
  } else {
    dmg = 0.5;
    w.combo = 0;
    w.acc.wrongAmmo++;
    hint(w, `arm_${a.weakness}`, a.hint);
    sfx(w, 'hit_wrong', a.x);
  }
  dmg = Math.min(dmg, a.hp);
  a.hp -= dmg;
  a.hitFlash = 0.25;
  if (w.boss) w.boss.hp = Math.max(0, w.boss.hp - dmg);
  emit(w, { e: 'hit', x: a.x, y: a.y, right, dmg, target: a.uid, ammo });
  if (a.hp <= 0.001) {
    a.state = 'calm';
    a.t = 0;
    emit(w, { e: 'clean', uid: a.uid, id: `arm_${a.weakness}`, x: a.x, y: a.y });
    sfx(w, 'clean', a.x);
    dropCoins(w, a.x, a.y, 3);
  }
  void dx; void dy;
}

export function headHit(w: World, x: number, y: number): void {
  hint(w, 'kraken_head', T.hitBody);
  emit(w, { e: 'miss', x, y });
  sfx(w, 'hit_wrong', x);
}
