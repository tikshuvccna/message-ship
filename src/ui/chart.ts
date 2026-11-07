import { generateChart, KIND_HE, reachable, type Chart, type ChartNode } from '../game/chart';
import { UPGRADE_HE, UPGRADE_PRICE, buyUpgrade } from '../game/progress';
import { UPGRADE_IDS, UPGRADE_MAX, type UpgradeId } from '../core/save';
import { CREATURES } from '../content';
import { btn, clear, h, overlay } from './dom';
import type { Ctx } from './ctx';

export type ChartChoice =
  | { type: 'sail'; node: ChartNode }
  | { type: 'menu' }
  | { type: 'lighthouse' }
  | { type: 'quit' };

const ICON: Record<string, string> = {
  start: 'k-start', battle: 'k-battle', island: 'k-island', event: 'k-event', storm: 'k-storm', harbour: 'k-harbour', lighthouse: 'k-lighthouse', boss: 'k-boss',
};

/** The sea chart: pick the next node. Resolves with the choice. */
export function showChart(ctx: Ctx, chart: Chart): Promise<ChartChoice> {
  const s = ctx.save.data;
  const { root, close } = overlay('chart-screen');
  ctx.audio.mood('chart');
  return new Promise((resolve) => {
    const draw = (): void => {
      clear(root);
      const head = h('div', 'chart-head');
      head.appendChild(h('h1', null, chart.leg >= 4 ? 'הדרך לעין הים' : `מסע ${chart.leg}`));
      const coin = h('div', 'coinpill');
      coin.append(h('span', 'coin'), h('b', null, String(s.coins)));
      head.appendChild(coin);
      head.appendChild(btn('תפריט', () => { close(); resolve({ type: 'menu' }); }, 'btn small ghost'));
      root.appendChild(head);

      const board = h('div', 'board');
      const cols = Math.max(...chart.nodes.map((n) => n.col)) + 1;
      const next = new Set(reachable(chart, s.chart.at).map((n) => n.id));
      const pos = (n: ChartNode): { x: number; y: number } => {
        const rows = chart.nodes.filter((m) => m.col === n.col).length;
        return { x: 8 + (n.col / (cols - 1)) * 84, y: rows === 1 ? 50 : 28 + n.row * 44 };
      };
      const svgNS = 'http://www.w3.org/2000/svg';
      const svg = document.createElementNS(svgNS, 'svg');
      svg.setAttribute('viewBox', '0 0 100 100');
      svg.setAttribute('preserveAspectRatio', 'none');
      svg.classList.add('routes');
      for (const n of chart.nodes) for (const id of n.next) {
        const m = chart.nodes.find((x) => x.id === id) as ChartNode;
        const a = pos(n), b = pos(m);
        const line = document.createElementNS(svgNS, 'path');
        line.setAttribute('d', `M ${a.x} ${a.y} C ${a.x + 12} ${a.y}, ${b.x - 12} ${b.y}, ${b.x} ${b.y}`);
        const used = s.chart.visited.includes(n.id) && (s.chart.visited.includes(m.id) || s.chart.at === m.id);
        line.setAttribute('class', used ? 'route used' : next.has(m.id) && s.chart.at === n.id ? 'route open' : 'route');
        svg.appendChild(line);
      }
      board.appendChild(svg);
      for (const n of chart.nodes) {
        const p = pos(n);
        const here = s.chart.at === n.id;
        const visited = s.chart.visited.includes(n.id);
        const can = next.has(n.id);
        const b = h('button', `node ${ICON[n.kind] ?? ''}${here ? ' here' : ''}${visited ? ' visited' : ''}${can ? ' open' : ''}`, null, { type: 'button' });
        b.style.left = `${p.x}%`;
        b.style.top = `${p.y}%`;
        b.appendChild(h('span', 'node-ico'));
        b.appendChild(h('span', 'node-name', KIND_HE[n.kind]));
        b.disabled = !can;
        b.addEventListener('click', () => { close(); resolve({ type: 'sail', node: n }); });
        board.appendChild(b);
      }
      const ship = h('div', 'chart-ship');
      const here = chart.nodes.find((n) => n.id === s.chart.at);
      if (here) { const p = pos(here); ship.style.left = `${p.x}%`; ship.style.top = `${p.y}%`; }
      board.appendChild(ship);
      root.appendChild(board);
      const atNode = chart.nodes.find((n) => n.id === s.chart.at);
      if (atNode?.kind === 'lighthouse') {
        root.appendChild(btn('כניסה למגדלור', () => { close(); resolve({ type: 'lighthouse' }); }, 'btn primary big pulse'));
      }
      root.appendChild(h('div', 'panel dim chart-tip', next.size ? 'בחרו לאן להפליג. נתיב אחד מסוכן ועשיר, השני רגוע.' : 'הגעתם לסוף הקטע.'));
    };
    draw();
  });
}

export function startChart(ctx: Ctx): Chart {
  const c = ctx.save.data.chart;
  return generateChart(c.leg, c.seed);
}

/* ------------------------------------------------------------------ shop (the carpenter) */

export function openShop(ctx: Ctx): Promise<void> {
  const s = ctx.save.data;
  const { root, close } = overlay('shop-screen');
  ctx.audio.mood('harbour');
  return new Promise((resolve) => {
    const draw = (): void => {
      clear(root);
      const card = h('div', 'lcard shop');
      card.appendChild(h('h2', null, 'הנגר של הנמל'));
      const coin = h('div', 'coinpill');
      coin.append(h('span', 'coin'), h('b', null, String(s.coins)));
      card.appendChild(coin);
      const list = h('div', 'shoplist');
      for (const id of UPGRADE_IDS) {
        const lv = s.upgrades[id as UpgradeId];
        const price = UPGRADE_PRICE[lv];
        const row = h('div', 'shoprow');
        const t = h('div', 'shoptext');
        t.append(h('b', null, UPGRADE_HE[id as UpgradeId]), h('small', null, `רמה ${lv} מתוך ${UPGRADE_MAX}`));
        row.appendChild(t);
        const pips = h('div', 'pips');
        for (let k = 0; k < UPGRADE_MAX; k++) pips.appendChild(h('span', k < lv ? 'pip on' : 'pip'));
        row.appendChild(pips);
        const b = btn(price === undefined ? 'מלא' : String(price), () => {
          if (buyUpgrade(s, id as UpgradeId)) { ctx.save.save(); ctx.audio.sfx('coin'); draw(); } else ctx.audio.sfx('bad');
        }, 'btn buy');
        b.disabled = price === undefined || s.coins < price;
        row.appendChild(b);
        list.appendChild(row);
      }
      card.appendChild(list);
      card.appendChild(btn('יציאה', () => { close(); resolve(); }, 'btn primary'));
      root.appendChild(card);
    };
    draw();
  });
}

/* ------------------------------------------------------------------ codex */

export function openCodex(ctx: Ctx): Promise<void> {
  const s = ctx.save.data;
  const { root, close } = overlay('codex-screen');
  return new Promise((resolve) => {
    const card = h('div', 'lcard codex');
    card.appendChild(h('h2', null, 'אוסף היצורים'));
    const total = CREATURES.filter((c) => c.leg < 4).length;
    const have = CREATURES.filter((c) => (s.cleaned[c.id] ?? 0) > 0).length;
    card.appendChild(h('div', 'panel dim', `${have} מתוך ${total + 1} יצורים הפכו לחברים`));
    const grid = h('div', 'codexgrid');
    for (const c of CREATURES) {
      const n = s.cleaned[c.id] ?? 0;
      const cell = h('div', n > 0 ? 'ccell got' : 'ccell');
      const img = h('img', 'cimg', null, { alt: '' });
      img.src = `assets/creatures/${c.id}.png`;
      img.addEventListener('error', () => img.remove());
      cell.appendChild(img);
      cell.appendChild(h('b', null, n > 0 ? c.friend : '???'));
      cell.appendChild(h('small', null, n > 0 ? `נוקה ${n} פעמים` : c.symptom));
      grid.appendChild(cell);
    }
    card.appendChild(grid);
    card.appendChild(btn('סגירה', () => { close(); resolve(); }, 'btn primary'));
    root.appendChild(card);
  });
}
