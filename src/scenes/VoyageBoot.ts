import Phaser from 'phaser';
import { makeFxTextures } from './textures';

/**
 * Loads whatever art exists. Every atlas is optional: before queueing a file we probe it with fetch
 * (a dev server or static host may answer a missing file with index.html), and the renderer draws a
 * placeholder for each frame it cannot find (see textures.ts). When the art agent drops a new atlas
 * into public/assets, it is picked up on the next load with no code change.
 */
export const ATLASES: [key: string, path: string][] = [
  ['ship', 'ship/ship'],
  ['creatures', 'creatures/creatures'],
  ['env', 'env/env'],
  ['skin_girl_sea', 'characters/skin_girl_sea'],
  ['skin_boy_navy', 'characters/skin_boy_navy'],
  ['apprentice_girl', 'characters/apprentice_girl'],
  ['apprentice_boy', 'characters/apprentice_boy'],
  ['bit', 'characters/bit'],
  ['kraken', 'creatures/kraken'],
];
export const SEA_TILES = ['day', 'dusk', 'sunset', 'storm', 'noise', 'night'];

async function jsonOk(url: string): Promise<boolean> {
  try {
    const r = await fetch(url, { cache: 'no-cache' });
    if (!r.ok) return false;
    const txt = await r.text();
    if (txt.trimStart().startsWith('<')) return false;
    const j = JSON.parse(txt) as { frames?: unknown };
    return !!j && typeof j === 'object' && !!j.frames;
  } catch {
    return false;
  }
}

async function imageOk(url: string): Promise<boolean> {
  try {
    const r = await fetch(url, { method: 'GET', cache: 'no-cache' });
    if (!r.ok) return false;
    const ct = r.headers.get('content-type') ?? '';
    return ct.startsWith('image/');
  } catch {
    return false;
  }
}

export class VoyageBoot extends Phaser.Scene {
  static readonly KEY = 'VoyageBoot';
  /** true once any boot finished (scenes are created lazily by Phaser, so this is static) */
  static ready = false;
  private static waiting: (() => void)[] = [];
  static whenReady(cb: () => void): void {
    if (VoyageBoot.ready) cb();
    else VoyageBoot.waiting.push(cb);
  }
  readonly loaded: string[] = [];

  constructor() {
    super(VoyageBoot.KEY);
  }

  create(): void {
    makeFxTextures(this);
    void this.loadArt();
  }

  private async loadArt(): Promise<void> {
    const base = (import.meta.env?.BASE_URL as string | undefined) ?? './';
    const checks = await Promise.all([
      ...ATLASES.map(async ([k, p]) => ({ kind: 'atlas' as const, k, p, ok: await jsonOk(`${base}assets/${p}.json`) })),
      ...SEA_TILES.map(async (m) => ({ kind: 'img' as const, k: `sea_tile_${m}`, p: `env/sea_tile_${m}`, ok: await imageOk(`${base}assets/env/sea_tile_${m}.png`) })),
    ]);
    let n = 0;
    for (const c of checks) {
      if (!c.ok || this.textures.exists(c.k)) continue;
      if (c.kind === 'atlas') this.load.atlas(c.k, `${base}assets/${c.p}.png`, `${base}assets/${c.p}.json`);
      else this.load.image(c.k, `${base}assets/${c.p}.png`);
      this.loaded.push(c.k);
      n++;
    }
    if (n > 0) {
      await new Promise<void>((res) => {
        this.load.once(Phaser.Loader.Events.COMPLETE, () => res());
        this.load.start();
      });
    }
    VoyageBoot.ready = true;
    const list = VoyageBoot.waiting;
    VoyageBoot.waiting = [];
    for (const cb of list) cb();
  }
}
