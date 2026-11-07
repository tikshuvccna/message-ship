import { describe, expect, it } from 'vitest';
import { generateChart, reachable } from './chart';
import { buyUpgrade, currentLeg, grantPrize, statsFor } from './progress';
import { emptySave, normalize, SaveStore } from '../core/save';
import { CREATURES, ammoForLeg, AMMO_BY_ID } from '../content';

describe('chart', () => {
  it('is deterministic and connected', () => {
    for (const leg of [1, 2, 3, 4]) {
      const a = generateChart(leg, 5), b = generateChart(leg, 5);
      expect(a).toEqual(b);
      let at = [a.start];
      for (let i = 0; i < 6; i++) at = at.flatMap((id) => reachable(a, id).map((n) => n.id));
      const reachedEnd = (function walk(ids: string[]): boolean {
        if (ids.includes(a.end)) return true;
        const next = ids.flatMap((id) => reachable(a, id).map((n) => n.id));
        return next.length ? walk(next) : false;
      })([a.start]);
      expect(reachedEnd).toBe(true);
    }
  });
  it('legs 1-3 end in a lighthouse and contain a harbour', () => {
    const c = generateChart(1, 2);
    expect(c.nodes.find((n) => n.id === c.end)?.kind).toBe('lighthouse');
    expect(c.nodes.some((n) => n.kind === 'harbour')).toBe(true);
  });
});

describe('progress and upgrades', () => {
  it('current leg follows done lessons', () => {
    const s = emptySave();
    expect(currentLeg(s)).toBe(1);
    s.lessons['lesson06'] = { done: true, checks: {}, quizBest: 0, quizPassed: true, games: {} };
    expect(currentLeg(s)).toBe(2);
  });
  it('buying needs coins and caps at 3', () => {
    const s = emptySave();
    expect(buyUpgrade(s, 'hull')).toBe(false);
    s.coins = 1000;
    expect(buyUpgrade(s, 'hull')).toBe(true);
    expect(buyUpgrade(s, 'hull')).toBe(true);
    expect(buyUpgrade(s, 'hull')).toBe(true);
    expect(buyUpgrade(s, 'hull')).toBe(false);
    expect(statsFor(s).hullMax).toBe(175);
  });
  it('prizes are granted once and deterministic', () => {
    const s = emptySave();
    expect(grantPrize(s, 'lesson06', 'easy')?.id).toBe('p06e');
    expect(s.upgrades.pump).toBe(1);
    expect(grantPrize(s, 'lesson06', 'easy')).toBeNull();
    grantPrize(s, 'lesson06', 'hard');
    expect(s.cosmetics.flag).toBe(1);
    expect(s.coins).toBe(60);
  });
});

describe('save', () => {
  it('survives corrupt data and old shapes', () => {
    const mem = { v: '', getItem() { return this.v || null; }, setItem(_k: string, v: string) { this.v = v; }, removeItem() { this.v = ''; } };
    mem.v = '{not json';
    expect(new SaveStore(mem).data.coins).toBe(0);
    mem.v = JSON.stringify({ coins: 12, lessons: { lesson06: { done: true } } });
    const st = new SaveStore(mem);
    expect(st.data.coins).toBe(12);
    expect(st.lesson('lesson06').checks).toEqual({});
    expect(normalize(null).upgrades.hull).toBe(0);
  });
});

describe('creature data', () => {
  it('every weakness exists in ammo, every leg ammo is covered', () => {
    for (const c of CREATURES) expect(AMMO_BY_ID.has(c.weakness)).toBe(true);
    for (const leg of [1, 2, 3]) {
      const ids = new Set(CREATURES.filter((c) => c.leg === leg).map((c) => c.weakness));
      for (const a of ammoForLeg(leg)) expect(ids.has(a.id)).toBe(true);
    }
  });
});
