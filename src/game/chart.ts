import type { NodeKind } from '../voyage/contract';
import { pick, rng } from '../learn/rng';

export interface ChartNode {
  id: string;
  kind: NodeKind;
  col: number;
  row: number;
  next: string[];
  duration: number;       // seconds of sailing (0 = no sailing, a menu)
}

export interface Chart { leg: number; nodes: ChartNode[]; start: string; end: string }

export const DURATION: Record<NodeKind, number> = {
  start: 45, battle: 90, island: 55, event: 60, storm: 80, harbour: 0, lighthouse: 35, boss: 200,
};

export const KIND_HE: Record<NodeKind, string> = {
  start: 'יציאה', battle: 'רעש', island: 'אי', event: 'אירוע', storm: 'סערה', harbour: 'נמל', lighthouse: 'מגדלור', boss: 'עין הים',
};

export function nodeId(leg: number, col: number, row: number): string { return `L${leg}-${col}-${row}`; }

/** Deterministic chart of a leg. Legs 1 to 3 have 5 columns (two choices in the middle), leg 4 is the short road to the boss. */
export function generateChart(leg: number, seed: number): Chart {
  const r = rng(seed * 101 + leg * 7919);
  const cols: NodeKind[][] = [];
  if (leg >= 4) {
    cols.push(['start'], ['battle', 'storm'], ['boss']);
  } else {
    cols.push(['start']);
    cols.push(r() < 0.5 ? ['battle', 'island'] : ['island', 'battle']);
    cols.push(r() < 0.5 ? ['battle', 'storm'] : ['storm', 'event']);
    cols.push(r() < 0.5 ? ['harbour', 'battle'] : ['harbour', 'event']);
    cols.push(['lighthouse']);
  }
  const nodes: ChartNode[] = [];
  cols.forEach((kinds, c) => kinds.forEach((kind, row) => {
    nodes.push({ id: nodeId(leg, c, row), kind, col: c, row, next: [], duration: DURATION[kind] });
  }));
  for (const n of nodes) {
    n.next = nodes.filter((m) => m.col === n.col + 1).map((m) => m.id);
  }
  // make sure a harbour is on the road: the harbour column offers a pick, never a dead end
  void pick;
  const last = nodes[nodes.length - 1] as ChartNode;
  return { leg, nodes, start: nodeId(leg, 0, 0), end: last.id };
}

export function nodeById(chart: Chart, id: string): ChartNode | undefined {
  return chart.nodes.find((n) => n.id === id);
}

/** Nodes the ship may sail to from `at`. */
export function reachable(chart: Chart, at: string): ChartNode[] {
  const n = nodeById(chart, at);
  if (!n) return [];
  return n.next.map((id) => nodeById(chart, id)).filter((x): x is ChartNode => !!x);
}
