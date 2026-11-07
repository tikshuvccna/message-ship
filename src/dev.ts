/**
 * Dev harness for the voyage engine (dev.html). Starts a voyage directly, without the main UI.
 * Query params: leg=1..4, kind=battle|island|event|storm|harbour|lighthouse|boss|start, seed, players=1|2,
 * quality=low|medium|high, duration, look=girl|boy, diff=0..1, hud=0 (hide the debug panel).
 * window.__dev exposes { game, bus, voyage, sim() } for scripted tests (tools/*.py).
 */
import Phaser from 'phaser';
import { Bus } from './core/bus';
import creaturesJson from '../content/he/creatures.json';
import type { AmmoDef, AmmoId, NodeKind, VoyageConfig } from './voyage/contract';
import { createVoyage } from './voyage';
import { PHASE_AMMO } from './voyage/sim/boss';
import { Autopilot } from './voyage/autopilot';
import type { VoyageSim } from './voyage/sim/sim';

const q = new URLSearchParams(location.search);
const leg = Math.max(1, Math.min(4, Number(q.get('leg') ?? 1))) as 1 | 2 | 3 | 4;
const kind = (q.get('kind') ?? 'battle') as NodeKind;
const ammoAll = (creaturesJson as { ammo: AmmoDef[] }).ammo;
const ammo: AmmoId[] = leg === 4 ? PHASE_AMMO[1] : PHASE_AMMO[leg as 1 | 2 | 3];

const cfg: VoyageConfig & { difficulty?: number } = {
  seed: Number(q.get('seed') ?? 1234),
  leg,
  nodeId: q.get('node') ?? `dev_${kind}_3`,
  nodeKind: kind,
  look: q.get('look') === 'boy' ? 'boy' : 'girl',
  playerName: 'dev',
  twoPlayers: q.get('players') === '2',
  stats: { hullMax: 100, reloadSec: 1.6, shotPower: 1, sailSpeed: 1, repairSpeed: 1, lanternRadius: 260, doubleShot: false, shield: false },
  ammo,
  duration: Number(q.get('duration') ?? (kind === 'island' ? 50 : 90)),
  checkpointHull: 1,
  quality: (q.get('quality') as VoyageConfig['quality']) ?? 'high',
};
if (q.has('diff')) cfg.difficulty = Number(q.get('diff'));

const game = new Phaser.Game({
  type: Phaser.AUTO,
  parent: 'game',
  width: 1600,
  height: 900,
  backgroundColor: '#0b3556',
  scale: { mode: Phaser.Scale.FIT, autoCenter: Phaser.Scale.CENTER_BOTH },
  render: { antialias: true, roundPixels: false },
  input: { gamepad: true },
  fps: { target: 60 },
  scene: [],
});
const bus = new Bus();
const voyage = createVoyage(game, bus);

// tiny debug UI: hud, prompt, toasts
const dbg = document.getElementById('dbg')!;
const toasts = document.getElementById('toasts')!;
const prompt = document.getElementById('prompt')!;
if (q.get('hud') === '0') dbg.hidden = true;
const log: string[] = [];
const addToast = (text: string, cls: string): void => {
  const d = document.createElement('div');
  d.className = 'toast ' + cls;
  d.textContent = text;
  toasts.prepend(d);
  setTimeout(() => d.remove(), 3500);
};
bus.on('voyage:toast', (e) => addToast(e.text, e.kind ?? 'info'));
bus.on('voyage:hint', (e) => addToast('רמז: ' + e.text, 'hint'));
bus.on('voyage:prompt', (e) => { prompt.hidden = !e; prompt.textContent = e?.text ?? ''; });
for (const k of ['voyage:node-done', 'voyage:sunk', 'voyage:arrive', 'voyage:boss-phase', 'voyage:creature-cleaned', 'voyage:pickup'] as const) {
  bus.on(k, (e: unknown) => { log.push(`${k} ${JSON.stringify(e).slice(0, 120)}`); if (log.length > 6) log.shift(); });
}
const sfxCount: Record<string, number> = {};
bus.on('audio:sfx', (e) => { sfxCount[e.name] = (sfxCount[e.name] ?? 0) + 1; });
let fpsAcc = 0, fpsN = 0;
bus.on('voyage:hud', (h) => {
  fpsAcc += game.loop.actualFps; fpsN++;
  dbg.textContent = `${kind} leg ${leg} seed ${cfg.seed}  fps ${game.loop.actualFps.toFixed(0)}\n` +
    `hull ${h.hull}/${h.hullMax} water ${(h.water * 100).toFixed(0)}% coins ${h.coins} prog ${(h.progress * 100).toFixed(0)}%\n` +
    `held ${h.held ?? '-'} leaks ${h.leaks} fires ${h.fires} wind ${h.wind.toFixed(2)} combo ${h.combo}` +
    (h.bossHp !== undefined ? ` boss ${(h.bossHp * 100).toFixed(0)}%` : '') + '\n' + log.join('\n');
});

(window as unknown as { __dev: unknown }).__dev = {
  game, bus, voyage, cfg, ammoAll, sfxCount,
  sim: () => voyage.scene?.sim,
  fps: () => ({ avg: fpsN ? fpsAcc / fpsN : 0, now: game.loop.actualFps }),
  resetFps: () => { fpsAcc = 0; fpsN = 0; },
};
// ?auto=1 : the autopilot plays player 0 (through the same input path as the keyboard)
let pilot: Autopilot | null = null;
let pilotSim: VoyageSim | null = null;
let autoOn = q.get('auto') === '1';
game.events.on('poststep', (_t: number, dms: number) => {
  const sim = voyage.scene?.sim;
  if (!autoOn || !sim) return;
  if (sim !== pilotSim) { pilotSim = sim; pilot = new Autopilot(sim, 0); }
  pilot?.tick(dms / 1000);
});
(window as unknown as { __dev: Record<string, unknown> }).__dev.auto = (on: boolean) => { autoOn = on; };
bus.emit('voyage:start', cfg);
