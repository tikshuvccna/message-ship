import type { Ctx } from '../ui/ctx';
import { showChart, openShop, openCodex } from '../ui/chart';
import { runLighthouse } from '../ui/lighthouse';
import { say } from '../ui/dialogue';
import { Hud } from '../ui/hud';
import { openCredits, openHelp, openSettings, pickHero, showTitle } from '../ui/menus';
import { btn, h, overlay, ui } from '../ui/dom';
import { ammoForLeg, AMMO } from '../content';
import type { NodeStats, VoyageConfig } from '../voyage/contract';
import { generateChart, nodeById, type Chart, type ChartNode } from './chart';
import { currentLeg, lessonForLeg, statsFor } from './progress';
import { emptySave } from '../core/save';

const FOG_WARN_SEC = 8 * 60;
const FOG_CAP_SEC = 10 * 60;

type Outcome = { type: 'done'; stats: NodeStats } | { type: 'sunk' } | { type: 'quit' };

export class Flow {
  /** Sailing seconds since the last finished lesson (the 10 minute rule). */
  private sailSec = 0;
  private hud: Hud | null = null;

  constructor(private ctx: Ctx) {}

  private get s() { return this.ctx.save.data; }
  private get chart(): Chart { return generateChart(this.s.chart.leg, this.s.chart.seed); }

  async boot(): Promise<void> {
    for (;;) {
      const choice = await showTitle(this.ctx, {
        settings: () => openSettings(this.ctx, () => { this.ctx.save.reset(); }),
        help: () => openHelp(this.ctx),
        credits: () => openCredits(this.ctx),
        codex: () => openCodex(this.ctx),
      });
      if (choice === 'new') {
        const hero = await pickHero(this.ctx);
        if (!hero) continue;
        this.ctx.save.reset();
        Object.assign(this.s, { started: true, look: hero.look, name: hero.name });
        this.ctx.save.save();
        await say(this.ctx, ['p.01', 'p.02', 'p.03', 'p.04', 'p.05', 'p.06', 'p.07']);
        await openHelp(this.ctx);
      } else if (!this.s.started) {
        continue;
      }
      await this.mainLoop();
    }
  }

  /** The chart loop. Returns to the title when the player leaves via the menu or finishes the game. */
  private async mainLoop(): Promise<void> {
    for (;;) {
      this.syncLeg();
      const chart = this.chart;
      const choice = await showChart(this.ctx, chart);
      if (choice.type === 'menu') {
        if (await this.pauseMenu(false)) return;
        continue;
      }
      if (choice.type === 'lighthouse') { await this.lighthouse(); continue; }
      if (choice.type === 'sail') {
        const finished = await this.visit(choice.node, chart);
        if (finished) return;
      }
    }
  }

  /** Makes sure the chart in the save matches the leg the lessons say we are on. */
  private syncLeg(): void {
    const want = currentLeg(this.s);
    if (this.s.chart.leg !== want) {
      this.s.chart = { leg: want, seed: this.s.chart.seed + 1, at: generateChart(want, this.s.chart.seed + 1).start, visited: [] };
      this.ctx.save.save();
    }
  }

  private async visit(node: ChartNode, chart: Chart): Promise<boolean> {
    this.s.chart.at = node.id;
    if (node.kind === 'harbour') {
      this.markVisited(node.id);
      await openShop(this.ctx);
      this.ctx.save.save();
      return false;
    }
    let hull = 1;
    for (;;) {
      const out = await this.sail(node, hull);
      if (out.type === 'quit') { this.s.chart.at = this.previousNode(chart, node)?.id ?? chart.start; this.ctx.save.save(); return false; }
      if (out.type === 'sunk') {
        await say(this.ctx, ['s.01']);
        hull = 0.6;
        continue;
      }
      this.reward(out.stats);
      this.markVisited(node.id);
      this.sailSec += out.stats.secondsPlayed;
      if (node.kind === 'boss') { await this.ending(); return true; }
      if (this.sailSec >= FOG_CAP_SEC && chart.leg < 4) await this.fog(chart);
      return false;
    }
  }

  private previousNode(chart: Chart, node: ChartNode): ChartNode | undefined {
    return chart.nodes.find((n) => n.next.includes(node.id) && this.s.chart.visited.includes(n.id)) ?? chart.nodes.find((n) => n.id === chart.start);
  }

  private markVisited(id: string): void {
    if (!this.s.chart.visited.includes(id)) this.s.chart.visited.push(id);
    this.ctx.save.save();
  }

  private reward(st: NodeStats): void {
    this.s.coins += Math.round(st.coins);
    for (const id of st.cleaned) this.s.cleaned[id] = (this.s.cleaned[id] ?? 0) + 1;
    for (const b of st.bottles) this.s.bottles[b] = true;
    this.ctx.save.save();
  }

  /** Fog: after ten minutes of sailing the ship is towed to the lighthouse (nothing is lost). */
  private async fog(chart: Chart): Promise<void> {
    await say(this.ctx, ['f.01', 'f.02']);
    this.s.chart.at = chart.end;
    this.markVisited(chart.end);
    this.sailSec = 0;
    this.ctx.save.save();
  }

  private async lighthouse(): Promise<void> {
    const leg = this.s.chart.leg;
    if (leg > 3) return;
    const done = await runLighthouse(this.ctx, leg);
    if (done) this.sailSec = 0;
    this.ctx.save.save();
    void lessonForLeg;
  }

  private sail(node: ChartNode, hull: number): Promise<Outcome> {
    const leg = this.s.chart.leg;
    const q = this.s.settings.quality;
    const cfg: VoyageConfig = {
      seed: this.s.chart.seed * 1000 + node.col * 10 + node.row,
      leg: leg as VoyageConfig['leg'],
      nodeId: node.id,
      nodeKind: node.kind,
      look: this.s.look,
      playerName: this.s.name,
      twoPlayers: this.s.twoPlayers,
      stats: statsFor(this.s),
      ammo: leg >= 4 ? AMMO.map((a) => a.id) : ammoForLeg(leg).map((a) => a.id),
      duration: node.duration,
      checkpointHull: hull,
      quality: q === 'auto' ? 'high' : q,
    };
    const bus = this.ctx.bus;
    this.ctx.audio.mood(node.kind === 'storm' ? 'storm' : node.kind === 'battle' ? 'battle' : node.kind === 'boss' ? 'boss' : node.kind === 'island' ? 'island' : 'calm');
    const hud = new Hud(bus, () => { void this.pauseMenu(true).then((quit) => { if (quit) bus.emit('voyage:quit', undefined); }); });
    this.hud = hud;
    hud.mount(ui());
    return new Promise<Outcome>((resolve) => {
      const offs: (() => void)[] = [];
      const finish = (o: Outcome): void => { offs.forEach((f) => f()); hud.destroy(); this.hud = null; resolve(o); };
      offs.push(
        bus.on('voyage:node-done', (e) => { if (e.nodeId === node.id) finish({ type: 'done', stats: e.stats }); }),
        bus.on('voyage:sunk', () => finish({ type: 'sunk' })),
        bus.on('voyage:quit', () => finish({ type: 'quit' })),
        bus.on('audio:sfx', (e) => this.ctx.audio.sfx(e.name)),
      );
      bus.emit('voyage:start', cfg);
      if (this.sailSec > FOG_WARN_SEC) hud.toast('ערפל מתקרב. בקרוב נחזור למגדלור.', 'info', 4000);
    });
  }

  /** Pause overlay. Resolves true when the player asked to leave. `inVoyage` pauses the engine. */
  private async pauseMenu(inVoyage: boolean): Promise<boolean> {
    if (inVoyage) this.ctx.bus.emit('ui:pause', { paused: true });
    const { root, close } = overlay('pause-screen');
    const leave = await new Promise<boolean>((resolve) => {
      const card = h('div', 'lcard');
      card.appendChild(h('h2', null, 'הפסקה'));
      const col = h('div', 'menu');
      col.append(
        btn('המשך', () => { close(); resolve(false); }, 'btn primary big'),
        btn('הגדרות', () => { void openSettings(this.ctx); }, 'btn'),
        btn('עזרה', () => { void openHelp(this.ctx); }, 'btn'),
        btn('קרדיטים', () => { void openCredits(this.ctx); }, 'btn'),
        btn(inVoyage ? 'חזרה למפה' : 'לתפריט הראשי', () => { close(); resolve(true); }, 'btn ghost'),
      );
      card.appendChild(col);
      root.appendChild(card);
    });
    if (inVoyage) this.ctx.bus.emit('ui:pause', { paused: false });
    return leave;
  }

  private async ending(): Promise<void> {
    this.s.bossWon = true;
    this.ctx.save.save();
    this.ctx.audio.mood('ending');
    await say(this.ctx, ['w.01', 'w.02', 'w.03', 'w.04']);
    await openCredits(this.ctx);
  }

  /** For tests and a debug hook: reset to a clean save. */
  reset(): void { Object.assign(this.s, emptySave()); }
  nodeOf(id: string): ChartNode | undefined { return nodeById(this.chart, id); }
}
