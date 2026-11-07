import { GAMES, LESSONS } from '../content';
import { LEVELS, type Level } from '../learn/types';
import { PRIZES } from '../game/progress';
import { btn, clear, h, overlay } from './dom';
import { type Ctx, portraitImg } from './ctx';
import { say } from './dialogue';
import { keeperName, runLesson, runQuiz } from './lesson';
import { LEVEL_HE, runGame } from './games';

const LEG_IDS: Record<number, { lesson: string; quiz: string; game: string; arrive: string[]; done: string[] }> = {
  1: { lesson: 'lesson06', quiz: 'quiz06', game: 'game06', arrive: ['a1.01', 'a1.02', 'a1.03'], done: ['d1.01', 'd1.02', 'd1.03'] },
  2: { lesson: 'lesson07', quiz: 'quiz07', game: 'game07', arrive: ['a2.01', 'a2.02', 'a2.03'], done: ['d2.01', 'd2.02', 'd2.03'] },
  3: { lesson: 'lesson08', quiz: 'quiz08', game: 'game08', arrive: ['a3.01', 'a3.02', 'a3.03'], done: ['d3.01', 'd3.02'] },
};

/** The lighthouse stop: dialogue, then lesson -> quiz -> mini-game. Resolves when the player leaves; true if the leg is complete. */
export async function runLighthouse(ctx: Ctx, leg: number): Promise<boolean> {
  const ids = LEG_IDS[leg];
  if (!ids) return false;
  const lesson = LESSONS[ids.lesson];
  if (!lesson) return false;
  const lp = ctx.save.lesson(ids.lesson);
  ctx.audio.mood('lighthouse');
  if (!ctx.save.data.flags[`arrived.${leg}`]) {
    ctx.save.data.flags[`arrived.${leg}`] = true;
    ctx.save.save();
    await say(ctx, ids.arrive);
  }
  return new Promise((resolve) => {
    const { root, close } = overlay('lighthouse-screen');
    const draw = (): void => {
      clear(root);
      const wasDone = lp.done;
      const card = h('div', 'lh');
      const top = h('div', 'lh-top');
      top.appendChild(portraitImg(lesson.keeper, 'neutral', 'portrait big'));
      const tt = h('div', 'lh-title');
      tt.append(h('div', 'lh-name', keeperName(lesson.keeper)), h('h1', null, lesson.where), h('div', 'dim', lesson.title));
      top.appendChild(tt);
      card.appendChild(top);

      const steps = h('div', 'lh-steps');
      const lessonDone = Object.keys(lp.checks).length >= lesson.steps.length;
      steps.appendChild(stepBtn('1', 'שיעור', lessonDone ? 'הושלם' : `${lesson.estimatedMinutes} דקות בערך`, lessonDone, true, async () => {
        const ok = await runLesson(ctx, ids.lesson);
        if (ok) lp.checks['all'] = true;
        ctx.save.save();
        draw();
      }));
      steps.appendChild(stepBtn('2', 'חידון', lp.quizPassed ? `עברתם (${lp.quizBest}/8)` : 'צריך 5 מתוך 8', lp.quizPassed, lessonDone, async () => {
        const r = await runQuiz(ctx, ids.lesson, ids.quiz);
        if (r.passed) { lp.done = true; ctx.save.save(); }
        draw();
      }));
      const games = h('div', 'lh-games');
      const gdata = GAMES[ids.game];
      for (const lv of LEVELS) {
        const best = lp.games[lv];
        const prize = PRIZES[ids.lesson]?.[lv];
        const b = stepBtn(LEVEL_HE[lv], `${gdata?.title ?? 'משחקון'}`, best?.passed ? `עברתם, שיא ${best.points}` : prize ? `פרס: ${prize.he}` : '', !!best?.passed, lp.quizPassed, async () => {
          await runGame(ctx, ids.lesson, ids.game, lv as Level);
          ctx.audio.mood('lighthouse');
          draw();
        });
        games.appendChild(b);
      }
      steps.append(h('div', 'lh-sub', 'משחקון (שלוש רמות, פרס אחר לכל אחת)'), games);
      card.appendChild(steps);

      const foot = h('div', 'lfoot');
      foot.appendChild(btn(lp.done ? 'חזרה לים' : 'חזרה לים (בלי להתקדם)', async () => {
        close();
        if (lp.done && !wasDone) await say(ctx, ids.done);
        resolve(lp.done);
      }, lp.done ? 'btn primary' : 'btn'));
      card.appendChild(foot);
      root.appendChild(card);
    };
    draw();
  });
}

function stepBtn(num: string, title: string, sub: string, done: boolean, enabled: boolean, onClick: () => void | Promise<void>): HTMLElement {
  const b = h('button', `lh-step${done ? ' done' : ''}${enabled ? '' : ' locked'}`, null, { type: 'button' });
  b.appendChild(h('span', 'lh-num', done ? '' : num));
  const t = h('span', 'lh-text');
  t.append(h('b', null, title), h('small', null, enabled ? sub : 'נעול'));
  b.appendChild(t);
  b.disabled = !enabled;
  b.addEventListener('click', () => { void onClick(); });
  return b;
}
