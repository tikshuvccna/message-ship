/**
 * Public API of the voyage engine.
 *   createVoyage(game, bus, getData?) — registers the scenes; then the UI emits 'voyage:start' (VoyageConfig).
 * Events out: voyage:hud (10 Hz), voyage:prompt, voyage:toast, voyage:hint, voyage:pickup, voyage:creature-cleaned,
 * voyage:boss-phase, voyage:arrive, voyage:node-done, voyage:sunk, audio:sfx.
 * Events in: voyage:start, voyage:quit, ui:pause, ui:input.
 */
import Phaser from 'phaser';
import type { Bus } from '../core/bus';
import creaturesJson from '../../content/he/creatures.json';
import type { AmmoDef, CreatureDef, VoyageConfig } from './contract';
import { VoyageBoot } from '../scenes/VoyageBoot';
import { VOYAGE_SCENE, VoyageScene } from '../scenes/VoyageScene';

export { VOYAGE_SCENE, VoyageScene };
export { VoyageSim } from './sim/sim';

export interface VoyageData { creatures: CreatureDef[]; ammo: AmmoDef[] }

const defaultData = (): VoyageData => ({
  creatures: (creaturesJson as { creatures: CreatureDef[] }).creatures,
  ammo: (creaturesJson as { ammo: AmmoDef[] }).ammo,
});

export interface VoyageHandle {
  start(cfg: VoyageConfig): void;
  stop(): void;
  readonly scene: VoyageScene | null;
}

export function createVoyage(game: Phaser.Game, bus: Bus, getData: () => VoyageData = defaultData): VoyageHandle {
  if (!game.scene.getScene(VoyageBoot.KEY)) game.scene.add(VoyageBoot.KEY, VoyageBoot, true);
  if (!game.scene.getScene(VOYAGE_SCENE)) game.scene.add(VOYAGE_SCENE, VoyageScene, false);
  let pending: VoyageConfig | null = null;
  const run = (cfg: VoyageConfig): void => {
    const d = getData();
    const sm = game.scene;
    if (sm.isActive(VOYAGE_SCENE) || sm.isPaused(VOYAGE_SCENE)) sm.stop(VOYAGE_SCENE);
    sm.start(VOYAGE_SCENE, { cfg, bus, creatures: d.creatures, ammo: d.ammo });
  };
  const start = (cfg: VoyageConfig): void => {
    if (VoyageBoot.ready) { run(cfg); return; }
    const first = pending === null;
    pending = cfg;
    if (first) VoyageBoot.whenReady(() => { if (pending) { const c = pending; pending = null; run(c); } });
  };
  const stop = (): void => {
    pending = null;
    if (game.scene.isActive(VOYAGE_SCENE) || game.scene.isPaused(VOYAGE_SCENE)) game.scene.stop(VOYAGE_SCENE);
  };
  bus.on('voyage:start', (cfg) => start(cfg));
  bus.on('voyage:quit', () => stop());
  return {
    start, stop,
    get scene() {
      const s = game.scene.getScene(VOYAGE_SCENE) as VoyageScene | null;
      return s && game.scene.isActive(VOYAGE_SCENE) ? s : null;
    },
  };
}
