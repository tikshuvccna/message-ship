import type { Ctx } from './ui/ctx';
import { runLesson, runQuiz } from './ui/lesson';
import { runGame } from './ui/games';
import { runLighthouse } from './ui/lighthouse';
import { openCodex, openShop, showChart, startChart } from './ui/chart';
import { openCredits, openHelp, openSettings, pickHero, showTitle } from './ui/menus';
import { say } from './ui/dialogue';
import type { Level } from './learn/types';

/** Direct entry to single screens for visual checks: ?dev=lesson06 | quiz06 | game06:hard | lighthouse1 | chart | shop | codex | credits | help | settings | title | hero | say */
export async function devRoute(ctx: Ctx, what: string): Promise<boolean> {
  const [name, arg] = what.split(':');
  const n = (name ?? '').replace(/\D/g, '');
  switch ((name ?? '').replace(/\d+$/, '')) {
    case 'lesson': await runLesson(ctx, `lesson${n}`); return true;
    case 'quiz': await runQuiz(ctx, `lesson${n}`, `quiz${n}`); return true;
    case 'game': {
      const lesson = `lesson${n}`;
      await runGame(ctx, lesson, `game${n}`, (arg as Level) || 'easy');
      return true;
    }
    case 'lighthouse': await runLighthouse(ctx, Number(n) || 1); return true;
    case 'chart': await showChart(ctx, startChart(ctx)); return true;
    case 'shop': ctx.save.data.coins = 300; await openShop(ctx); return true;
    case 'codex': ctx.save.data.cleaned['garble_squid'] = 2; await openCodex(ctx); return true;
    case 'credits': await openCredits(ctx); return true;
    case 'help': await openHelp(ctx); return true;
    case 'settings': await openSettings(ctx, () => undefined); return true;
    case 'title': await showTitle(ctx, { settings: () => Promise.resolve(), help: () => Promise.resolve(), credits: () => Promise.resolve(), codex: () => Promise.resolve() }); return true;
    case 'hero': await pickHero(ctx); return true;
    case 'say': await say(ctx, ['p.03', 'p.04', 'p.05']); return true;
    default: return false;
  }
}
