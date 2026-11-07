export const SAVE_KEY = 'message-ship.save.v1';
export const SAVE_VERSION = 1;

export type Look = 'girl' | 'boy';
export type UpgradeId = 'hull' | 'cannon' | 'sail' | 'pump' | 'lantern';
export const UPGRADE_IDS: readonly UpgradeId[] = ['hull', 'cannon', 'sail', 'pump', 'lantern'];
export const UPGRADE_MAX = 3;

export interface LessonProgress {
  done: boolean;
  checks: Record<string, boolean>;
  quizBest: number;
  quizPassed: boolean;
  games: Record<string, { points: number; passed: boolean }>;
}

export interface ChartState {
  leg: number;
  seed: number;
  at: string;               // node id the ship is at
  visited: string[];
}

export interface SaveData {
  v: number;
  started: boolean;
  look: Look;
  name: string;
  twoPlayers: boolean;
  coins: number;
  upgrades: Record<UpgradeId, number>;
  lessons: Record<string, LessonProgress>;
  flags: Record<string, boolean>;
  cleaned: Record<string, number>;        // creature id -> times cleaned (codex)
  bottles: Record<string, boolean>;
  cosmetics: { flag: number; paint: number };
  chart: ChartState;
  bossWon: boolean;
  playSeconds: number;
  settings: { subtitles: boolean; quality: 'auto' | 'low' | 'medium' | 'high'; showFps: boolean; musicOn: boolean; sfxOn: boolean; musicVol: number; sfxVol: number };
}

export function emptyLesson(): LessonProgress {
  return { done: false, checks: {}, quizBest: 0, quizPassed: false, games: {} };
}

export function emptySave(): SaveData {
  return {
    v: SAVE_VERSION, started: false, look: 'girl', name: '', twoPlayers: false, coins: 0,
    upgrades: { hull: 0, cannon: 0, sail: 0, pump: 0, lantern: 0 },
    lessons: {}, flags: {}, cleaned: {}, bottles: {},
    cosmetics: { flag: 0, paint: 0 },
    chart: { leg: 1, seed: 1, at: 'L1-0-0', visited: [] },
    bossWon: false, playSeconds: 0,
    settings: { subtitles: true, quality: 'auto', showFps: false, musicOn: true, sfxOn: true, musicVol: 0.5, sfxVol: 0.8 },
  };
}

export function normalize(raw: unknown): SaveData {
  const base = emptySave();
  if (!raw || typeof raw !== 'object') return base;
  const r = raw as Partial<SaveData>;
  const lessons: Record<string, LessonProgress> = {};
  for (const [k, v] of Object.entries(r.lessons ?? {})) lessons[k] = { ...emptyLesson(), ...(v as Partial<LessonProgress>) };
  return {
    ...base, ...r, v: SAVE_VERSION, lessons,
    upgrades: { ...base.upgrades, ...(r.upgrades ?? {}) },
    cosmetics: { ...base.cosmetics, ...(r.cosmetics ?? {}) },
    chart: { ...base.chart, ...(r.chart ?? {}) },
    settings: { ...base.settings, ...(r.settings ?? {}) },
  };
}

interface StoreLike { getItem(k: string): string | null; setItem(k: string, v: string): void; removeItem(k: string): void }

export class SaveStore {
  data: SaveData;
  private store: StoreLike | null;
  constructor(store?: StoreLike | null) {
    this.store = store === undefined ? safeStorage() : store;
    this.data = this.load();
  }
  private load(): SaveData {
    try {
      const s = this.store?.getItem(SAVE_KEY);
      return s ? normalize(JSON.parse(s)) : emptySave();
    } catch { return emptySave(); }
  }
  save(): void {
    try { this.store?.setItem(SAVE_KEY, JSON.stringify(this.data)); } catch { /* storage may be blocked */ }
  }
  reset(): void { this.data = emptySave(); this.save(); }
  lesson(id: string): LessonProgress {
    return (this.data.lessons[id] ??= emptyLesson());
  }
  addCoins(n: number): void { this.data.coins = Math.max(0, this.data.coins + Math.round(n)); this.save(); }
}

function safeStorage(): StoreLike | null {
  try { const s = globalThis.localStorage; s.getItem('x'); return s; } catch { return null; }
}
