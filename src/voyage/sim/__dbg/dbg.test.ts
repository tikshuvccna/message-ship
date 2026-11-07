import { it } from 'vitest';
import { writeFileSync } from 'node:fs';
import creaturesJson from '../../../../content/he/creatures.json';
import { Autopilot } from '../../autopilot';
import { PHASE_AMMO } from '../boss';
import { STEP, VoyageSim } from '../sim';
import type { VoyageConfig } from '../../contract';

it('dbg', () => {
  const L: string[] = [];
  const DATA = { creatures: (creaturesJson as never as { creatures: never[] }).creatures, ammo: (creaturesJson as never as { ammo: never[] }).ammo };
  const cfg = { seed: Number(process.env.SEED ?? 7), leg: Number(process.env.LEG ?? 1), nodeId: 'test_3', nodeKind: process.env.KIND ?? 'battle', look: 'girl', playerName: 't', twoPlayers: false,
    stats: { hullMax: 100, reloadSec: 1.6, shotPower: 1, sailSpeed: 1, repairSpeed: 1, lanternRadius: 260, doubleShot: false, shield: false },
    ammo: PHASE_AMMO[1], duration: 80, checkpointHull: 1, quality: 'high', difficulty: 0.3 } as unknown as VoyageConfig;
  const sim = new VoyageSim(cfg, DATA);
  const ap = new Autopilot(sim);
  let k = 0;
  ap.debug = (m) => { if (k++ % 15 === 0) L.push(`${sim.w.t.toFixed(1)} AP ${m}`); };
  for (let i = 0; i < 60 * 240; i++) {
    ap.tick(STEP);
    sim.step();
    for (const e of sim.drainEvents()) if (['done', 'sunk', 'shot', 'clean', 'board', 'toast', 'hint', 'hullhit', 'leak', 'fire', 'bolt', 'telegraph'].includes(e.e)) L.push(`${sim.w.t.toFixed(1)} ${JSON.stringify(e)}`);
    if (i % 120 === 0) {
      const p = sim.w.players[0]!;
      L.push(`t ${sim.w.t.toFixed(0)} p ${p.x.toFixed(1)},${p.y.toFixed(1)} at=${p.at} held=${JSON.stringify(p.held)} hull ${sim.w.ship.hull.toFixed(0)} water ${sim.w.ship.water.toFixed(2)} cr ${sim.w.creatures.map((c) => `${c.def.id}:${c.state}:${c.x.toFixed(0)},${(c.y - sim.w.ship.y).toFixed(0)}`).join(' ')}`);
    }
    if (sim.over) break;
  }
  writeFileSync(process.env.TMP + '/dbg.txt', L.join('\n'));
});
