import type { SaveData, UpgradeId } from '../core/save';
import { UPGRADE_IDS, UPGRADE_MAX } from '../core/save';
import { LESSON_IDS } from '../content';
import type { Level } from '../learn/types';
import type { VoyageStats } from '../voyage/contract';

/** Leg 1..3 = lessons, leg 4 = boss (after all three lessons). */
export function lessonDone(s: SaveData, id: string): boolean { return !!s.lessons[id]?.done; }

export function currentLeg(s: SaveData): number {
  for (let i = 0; i < LESSON_IDS.length; i++) if (!lessonDone(s, LESSON_IDS[i] as string)) return i + 1;
  return 4;
}

export function allLessonsDone(s: SaveData): boolean { return currentLeg(s) === 4; }

export function lessonForLeg(leg: number): string | null { return LESSON_IDS[leg - 1] ?? null; }

export const UPGRADE_HE: Record<UpgradeId, string> = {
  hull: 'גוף חזק', cannon: 'תותחי אור', sail: 'מפרשים', pump: 'משאבה ופטישים', lantern: 'פנס גילוי',
};
export const UPGRADE_DESC: Record<UpgradeId, string> = {
  hull: 'יותר חיים לספינה', cannon: 'טעינה מהירה וחזקה', sail: 'ספינה מהירה יותר', pump: 'תיקונים מהירים', lantern: 'רואים סודות מרחוק',
};
export const UPGRADE_PRICE = [40, 90, 160];

export function upgradePrice(level: number): number | null { return UPGRADE_PRICE[level] ?? null; }

export function buyUpgrade(s: SaveData, id: UpgradeId): boolean {
  const lv = s.upgrades[id];
  const price = upgradePrice(lv);
  if (price === null || lv >= UPGRADE_MAX || s.coins < price) return false;
  s.coins -= price;
  s.upgrades[id] = lv + 1;
  return true;
}

export function statsFor(s: SaveData, relics: { doubleShot?: boolean; shield?: boolean } = {}): VoyageStats {
  const u = s.upgrades;
  return {
    hullMax: 100 + 25 * u.hull,
    reloadSec: 1.6 - 0.2 * u.cannon,
    shotPower: 1 + 0.15 * u.cannon,
    sailSpeed: 1 + 0.08 * u.sail,
    repairSpeed: 1 + 0.2 * u.pump,
    lanternRadius: 260 + 60 * u.lantern,
    doubleShot: !!relics.doubleShot,
    shield: !!relics.shield,
  };
}

/** Fixed prizes (no randomness): lesson id + level -> reward. */
export interface Prize { id: string; he: string; desc: string; upgrade?: UpgradeId; flag?: number; paint?: number; coins?: number }
export const PRIZES: Record<string, Record<Level, Prize>> = {
  lesson06: {
    easy: { id: 'p06e', he: 'פטיש חדש', desc: 'תיקונים מהירים יותר', upgrade: 'pump' },
    medium: { id: 'p06m', he: 'תותח משודרג', desc: 'טעינה מהירה וחזקה', upgrade: 'cannon' },
    hard: { id: 'p06h', he: 'דגל זהב', desc: 'דגל מיוחד על התורן, ו-60 מטבעות', flag: 1, coins: 60 },
  },
  lesson07: {
    easy: { id: 'p07e', he: 'מפרש חזק', desc: 'ספינה מהירה יותר', upgrade: 'sail' },
    medium: { id: 'p07m', he: 'גוף מחוזק', desc: 'יותר חיים לספינה', upgrade: 'hull' },
    hard: { id: 'p07h', he: 'צבע תכלת', desc: 'צבע מיוחד לגוף, ו-80 מטבעות', paint: 1, coins: 80 },
  },
  lesson08: {
    easy: { id: 'p08e', he: 'פנס גילוי', desc: 'רואים סודות מרחוק', upgrade: 'lantern' },
    medium: { id: 'p08m', he: 'תותח כפול', desc: 'טעינה מהירה וחזקה', upgrade: 'cannon' },
    hard: { id: 'p08h', he: 'דגל הכתר', desc: 'דגל נדיר, ו-100 מטבעות', flag: 2, coins: 100 },
  },
};

/** Applies a prize once. Returns false when it was already granted. */
export function grantPrize(s: SaveData, lessonId: string, level: Level): Prize | null {
  const p = PRIZES[lessonId]?.[level];
  if (!p) return null;
  const key = `prize.${p.id}`;
  if (s.flags[key]) return null;
  s.flags[key] = true;
  if (p.upgrade && s.upgrades[p.upgrade] < UPGRADE_MAX) s.upgrades[p.upgrade] += 1;
  if (p.flag !== undefined) s.cosmetics.flag = Math.max(s.cosmetics.flag, p.flag);
  if (p.paint !== undefined) s.cosmetics.paint = Math.max(s.cosmetics.paint, p.paint);
  if (p.coins) s.coins += p.coins;
  return p;
}

export function totalUpgrades(s: SaveData): number { return UPGRADE_IDS.reduce((a, id) => a + s.upgrades[id], 0); }
