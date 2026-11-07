import type { GameData, LessonData, QuizData } from '../learn/types';
import type { AmmoDef, CreatureDef } from '../voyage/contract';
import creaturesJson from '../../content/he/creatures.json';
import lesson06 from '../../content/he/lesson06.json';
import lesson07 from '../../content/he/lesson07.json';
import lesson08 from '../../content/he/lesson08.json';
import quiz06 from '../../content/he/quiz06.json';
import quiz07 from '../../content/he/quiz07.json';
import quiz08 from '../../content/he/quiz08.json';
import game06 from '../../content/he/game06.json';
import game07 from '../../content/he/game07.json';
import game08 from '../../content/he/game08.json';
import linesJson from '../../content/he/lines.json';

export const LESSONS: Record<string, LessonData> = {
  lesson06: lesson06 as unknown as LessonData,
  lesson07: lesson07 as unknown as LessonData,
  lesson08: lesson08 as unknown as LessonData,
};
export const QUIZZES: Record<string, QuizData> = {
  quiz06: quiz06 as unknown as QuizData,
  quiz07: quiz07 as unknown as QuizData,
  quiz08: quiz08 as unknown as QuizData,
};
export const GAMES: Record<string, GameData> = {
  game06: game06 as unknown as GameData,
  game07: game07 as unknown as GameData,
  game08: game08 as unknown as GameData,
};
export const LESSON_IDS = ['lesson06', 'lesson07', 'lesson08'] as const;
export type LessonId = (typeof LESSON_IDS)[number];

export const AMMO: AmmoDef[] = (creaturesJson as { ammo: AmmoDef[] }).ammo;
export const CREATURES: CreatureDef[] = (creaturesJson as { creatures: CreatureDef[] }).creatures;
export const AMMO_BY_ID = new Map(AMMO.map((a) => [a.id, a]));

/** Ammo shelf for a leg. */
export function ammoForLeg(leg: number): AmmoDef[] {
  const ids = leg === 1 ? ['addr', 'code', 'fmt', 'size', 'time']
    : leg === 2 ? ['l1', 'l2', 'l3', 'l4', 'l5', 'l6', 'l7']
      : ['data', 'segment', 'packet', 'frame', 'bits'];
  return ids.map((id) => AMMO_BY_ID.get(id as AmmoDef['id'])).filter((x): x is AmmoDef => !!x);
}

export type LineMap = Record<string, { who: string; text: string }>;
export const LINES = linesJson as unknown as LineMap;
export function line(id: string): { who: string; text: string } {
  return LINES[id] ?? { who: 'narrator', text: id };
}

export const SPEAKERS: Record<string, string> = {
  naama: 'קברניטה נעמה', bit: 'ביט', uri: 'אורי', talia: 'טליה', barak: 'ברק', carpenter: 'הנגר',
  trader: 'הסוחר', narrator: '', player: '', tamir: 'תמיר', kraken: 'הקראקן',
};
