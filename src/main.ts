import Phaser from 'phaser';
import './styles.css';
import { makeCtx } from './ctxFactory';
import { Flow } from './game/flow';
import { createVoyage } from './voyage';

declare const __BUILD__: string;

const ctx = makeCtx();
const { save, bus } = ctx;

const game = new Phaser.Game({
  type: Phaser.AUTO,
  parent: 'game',
  width: 1600,
  height: 900,
  backgroundColor: '#0b3556',
  scale: { mode: Phaser.Scale.FIT, autoCenter: Phaser.Scale.CENTER_BOTH },
  render: { antialias: true, roundPixels: false },
  fps: { target: 60 },
  scene: [],
});
createVoyage(game, bus);

const flow = new Flow(ctx);
const dev = new URLSearchParams(location.search).get('dev');
if (new URLSearchParams(location.search).has('fresh')) save.reset();
if (dev) {
  save.data.started = true;
  void import('./devui').then((m) => m.devRoute(ctx, dev));
} else {
  void flow.boot();
}

(window as unknown as { __ms: unknown }).__ms = { game, bus, ctx, flow, build: __BUILD__ };
