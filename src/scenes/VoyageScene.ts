/**
 * VoyageScene: renders the pure VoyageSim (src/voyage/sim) and feeds it input.
 * The ship sits centre-left; the sea scrolls right to left. All ship-attached sprites live in one
 * container (tilted and heaved together) and are depth-sorted by deck depth (y).
 */
import Phaser from 'phaser';
import type { Bus } from '../core/bus';
import type { AmmoDef, AmmoId, CreatureDef, VoyageConfig } from '../voyage/contract';
import { shotHeight } from '../voyage/sim/ballistics';
import { predictShot } from '../voyage/sim/combat';
import { decide } from '../voyage/sim/deck';
import type { Mood } from '../voyage/sim/director';
import {
  CANNONS, CANNON_IDS, MUZZLE_Z, PX_PER_M, PY, PZ, RACK_CUPS, RACK_CUP_DX, STATIONS, halfBeam, project, rackCup,
  type CannonId,
} from '../voyage/sim/layout';
import { VoyageSim } from '../voyage/sim/sim';
import type { Creature, Floater, SimEvent } from '../voyage/sim/types';
import { bitPh, charPh, creaturePh, envPh, frameOf, seaTile, setTex, type Tex } from './textures';

export const VOYAGE_SCENE = 'Voyage';
const W = 1600, H = 900;
const CX = 760, CY = 515;
/** uniform camera zoom: a little more sea around the ship */
const ZOOM = 0.86;
const VW = W / ZOOM, VH = H / ZOOM;
const VX0 = W / 2 - VW / 2, VY0 = H / 2 - VH / 2, VX1 = VX0 + VW, VY1 = VY0 + VH;
const FONT = 'Rubik, "Segoe UI", Arial, sans-serif';

const D = {
  sea: 0, crest: 2, far: 10, armsFar: 19.5, shipShadow: 20, ship: 30, near: 50, armsNear: 58.5, shots: 60, fx: 65,
  weather: 70, mood: 75, aim: 85, bubble: 88, flash: 95,
};

const MOOD_TINT: Record<Mood, [number, number]> = {
  day: [0xffffff, 0], sunset: [0xffc8a0, 0.28], storm: [0x5a6a90, 0.5], noise: [0x9278d0, 0.38], night: [0x4a64a8, 0.45],
};

export interface VoyageSceneData { cfg: VoyageConfig; bus: Bus; creatures: CreatureDef[]; ammo: AmmoDef[] }

interface PView { spr: Phaser.GameObjects.Image; held: Phaser.GameObjects.Image; tag: Phaser.GameObjects.Text | null; sheet: string }
interface CView { spr: Phaser.GameObjects.Image; shadow: Phaser.GameObjects.Image; ring: Phaser.GameObjects.Image; bubble: Phaser.GameObjects.Text; onDeck: boolean; jx: number }
interface Part {
  img: Phaser.GameObjects.Image; x: number; y: number; z: number; vx: number; vy: number; vz: number;
  life: number; max: number; s0: number; s1: number; a0: number; g: number; mode: 'world' | 'screen'; spin: number;
}
interface Num { t: Phaser.GameObjects.Text; x: number; y: number; life: number }

const DIRS = ['E', 'SE', 'S', 'SW', 'W', 'NW', 'N', 'NE'] as const;

function hexNum(c: string): number {
  return parseInt(c.replace('#', ''), 16) || 0xffffff;
}

export class VoyageScene extends Phaser.Scene {
  sim!: VoyageSim;
  bus!: Bus;
  cfg!: VoyageConfig;
  private creatureDefs: CreatureDef[] = [];
  private ammoColor: Record<string, number> = {};
  private paused = false;
  private hitStop = 0;
  private camY = 0;
  private scroll = 0;
  private hudT = 0;
  private lastPrompt: string | null | undefined = undefined;
  private quality: 'low' | 'medium' | 'high' = 'high';
  private ended = false;
  private wheelRot = 0;
  private flashA = 0;
  private lightningLine: { x: number; y: number; t: number } | null = null;
  private slamWarn: { side: number; t: number } | null = null;
  private unsub: (() => void)[] = [];

  // layers
  private sea!: Phaser.GameObjects.TileSprite;
  private seaGlint!: Phaser.GameObjects.TileSprite;
  private shipC!: Phaser.GameObjects.Container;
  private shipShadow!: Phaser.GameObjects.Image;
  private hull!: Phaser.GameObjects.Image;
  private hullFront!: Phaser.GameObjects.Image;
  private mast!: Phaser.GameObjects.Image;
  private sail!: Phaser.GameObjects.Image;
  private flag!: Phaser.GameObjects.Sprite;
  private wheelBase!: Phaser.GameObjects.Image;
  private wheelDisc!: Phaser.GameObjects.Image;
  private rack!: Phaser.GameObjects.Image;
  private rackBalls: Phaser.GameObjects.Image[] = [];
  private cannonV = {} as Record<CannonId, { base: Phaser.GameObjects.Image; barrel: Phaser.GameObjects.Image; glow: Phaser.GameObjects.Image; ball: Phaser.GameObjects.Image }>;
  private waterGfx!: Phaser.GameObjects.Graphics;
  private deckGfx!: Phaser.GameObjects.Graphics;
  private topGfx!: Phaser.GameObjects.Graphics;
  private aimGfx!: Phaser.GameObjects.Graphics;
  private trailGfx!: Phaser.GameObjects.Graphics;
  private armsFar!: Phaser.GameObjects.Graphics;
  private armsNear!: Phaser.GameObjects.Graphics;
  private moodRect!: Phaser.GameObjects.Rectangle;
  private flashRect!: Phaser.GameObjects.Rectangle;
  private vignette!: Phaser.GameObjects.Image;
  private fogImgs: Phaser.GameObjects.Image[] = [];
  private rain: { img: Phaser.GameObjects.Image; x: number; y: number; v: number }[] = [];
  private crests: { img: Phaser.GameObjects.Image; x: number; y: number; t: number; p: number }[] = [];

  private pv: PView[] = [];
  private bitV: { spr: Phaser.GameObjects.Image; glow: Phaser.GameObjects.Image } | null = null;
  private itemV = new Map<number, Phaser.GameObjects.Image>();
  private leakV = new Map<number, Phaser.GameObjects.Sprite>();
  private fireV = new Map<number, { spr: Phaser.GameObjects.Sprite; glow: Phaser.GameObjects.Image }>();
  private crV = new Map<number, CView>();
  private shotV = new Map<number, { img: Phaser.GameObjects.Image; glow: Phaser.GameObjects.Image; trail: { x: number; y: number }[]; color: number }>();
  private boltV = new Map<number, { img: Phaser.GameObjects.Image; sh: Phaser.GameObjects.Image }>();
  private flV = new Map<number, Phaser.GameObjects.Image>();
  private armBubbles = new Map<number, Phaser.GameObjects.Text>();
  private head: Phaser.GameObjects.Image | null = null;
  private highlights: Phaser.GameObjects.Image[] = [];
  private parts: Part[] = [];
  private partPool: Phaser.GameObjects.Image[] = [];
  private nums: Num[] = [];

  constructor() {
    super(VOYAGE_SCENE);
  }

  init(data: VoyageSceneData): void {
    this.cfg = data.cfg;
    this.bus = data.bus;
    this.creatureDefs = data.creatures;
    this.quality = data.cfg.quality ?? 'high';
    for (const a of data.ammo) this.ammoColor[a.id] = hexNum(a.color);
    this.sim = new VoyageSim(data.cfg, { creatures: data.creatures, ammo: data.ammo });
    this.paused = false;
    this.ended = false;
    this.hitStop = 0;
    this.camY = 0;
    this.scroll = 0;
    this.lastPrompt = undefined;
    this.pv = [];
    this.rackBalls = [];
    this.itemV.clear(); this.leakV.clear(); this.fireV.clear(); this.crV.clear(); this.shotV.clear();
    this.boltV.clear(); this.flV.clear(); this.armBubbles.clear();
    this.parts = []; this.partPool = []; this.nums = []; this.fogImgs = []; this.rain = []; this.crests = [];
    this.highlights = [];
    this.head = null;
    this.bitV = null;
  }

  // ---------------------------------------------------------------------------------------
  create(): void {
    const mood = this.sim.sched.mood;
    this.makeAnims();
    this.sea = this.add.tileSprite(W / 2, H / 2, VW + 200, VH + 200, seaTile(this, mood)).setDepth(D.sea);
    this.cameras.main.setZoom(ZOOM);
    this.seaGlint = this.add.tileSprite(W / 2, H / 2, VW + 200, VH + 200, seaTile(this, mood)).setDepth(D.sea + 0.5)
      .setAlpha(0.22).setBlendMode(Phaser.BlendModes.ADD).setTileScale(1.6, 0.9);
    const nCrest = this.quality === 'low' ? 18 : this.quality === 'medium' ? 30 : 44;
    for (let i = 0; i < nCrest; i++) {
      const img = hasFrameIn(this, 'env', 'wave_0') ? this.add.image(0, 0, 'env', `wave_${i % 4}`) : this.add.image(0, 0, 'fx:crest');
      img.setDepth(D.crest).setAlpha(0);
      this.crests.push({ img, x: Phaser.Math.FloatBetween(-16, 18), y: Phaser.Math.FloatBetween(-16, 16), t: Math.random() * 4, p: 2.5 + Math.random() * 2.5 });
    }

    // the ship
    this.shipShadow = this.img(frameOf(this, 'ship', 'ship_shadow')).setDepth(D.shipShadow).setAlpha(0.55);
    this.shipC = this.add.container(CX, CY).setDepth(D.ship);
    this.hull = this.shipImg('hull', 0, 0, 0, -10000);
    this.waterGfx = this.add.graphics().setDepth(-9000);
    this.shipC.add(this.waterGfx);
    this.deckGfx = this.add.graphics().setDepth(-7000);
    this.shipC.add(this.deckGfx);
    this.hullFront = this.shipImg('hull_front', 0, 0, 0, 10000);
    const st = STATIONS;
    this.shipImg('plank_stack', st.planks.x, st.planks.y, 0);
    this.shipImg('barrel', st.barrel.x, st.barrel.y, 0);
    this.shipImg('hatch', st.hatch.x, st.hatch.y, 0, -6000);
    this.rack = this.shipImg('rack', st.rack.x, st.rack.y, 0);
    this.wheelBase = this.shipImg('wheel_base', st.wheel.x, st.wheel.y, 0);
    this.wheelDisc = this.shipImg(hasShipFrame(this, 'wheel_disc_0') ? 'wheel_disc_0' : 'wheel', st.wheel.x, st.wheel.y, 0, -st.wheel.y * 100 - 1);
    this.mast = this.shipImg('mast', st.mast.x, st.mast.y, 0);
    for (const id of CANNON_IDS) {
      const s = st[id];
      const top = id === 'cannon_near' ? 10001 : -s.y * 100;
      const base = this.shipImg('cannon_base', s.x, s.y, 0, top);
      const barrel = this.shipImg('cannon_barrel_00', s.x, s.y, 0, top + 0.5);
      const glow = this.add.image(0, 0, 'fx:dot').setBlendMode(Phaser.BlendModes.ADD).setDepth(top + 0.6).setTint(0xffd27a).setScale(2.2).setAlpha(0);
      const ball = this.add.image(0, 0, 'fx:dot').setDepth(top + 0.7).setScale(0.6).setVisible(false);
      this.shipC.add([glow, ball]);
      this.cannonV[id] = { base, barrel, glow, ball };
    }
    this.sail = this.shipImg('sail_0', st.mast.x, st.mast.y, 0, 20000);
    const ft = frameOf(this, 'ship', 'flag_0', () => shipPh(this, 'flag_0'));
    const top = this.mastTop();
    this.flag = this.add.sprite(this.mast.x + top.x, this.mast.y + top.y, ft.key, ft.frame).setDepth(20001);
    this.flag.setOriginFromFrame();
    this.shipC.add(this.flag);
    if (this.anims.exists('ship:flag')) this.flag.play('ship:flag');
    this.topGfx = this.add.graphics().setDepth(30000);
    this.shipC.add(this.topGfx);
    for (let i = 0; i < 2; i++) {
      const h = this.add.image(0, 0, 'fx:ring').setDepth(-6500).setVisible(false).setTint(i ? 0x6ff0e0 : 0xffd65a);
      this.shipC.add(h);
      this.highlights.push(h);
    }

    // players & Bit
    const look = this.cfg.look === 'boy' ? 'boy' : 'girl';
    const sheets: ('girl' | 'boy')[] = this.cfg.twoPlayers ? [look, look === 'girl' ? 'boy' : 'girl'] : [look];
    this.sim.w.players.forEach((_p, i) => {
      const lk = sheets[i] ?? 'girl';
      const sheet = this.pickSheet(lk);
      const spr = this.add.image(0, 0, sheet).setDepth(0);
      if (sheet.startsWith('ph:')) spr.setOrigin(0.5, 110 / 128);
      const held = this.add.image(0, 0, 'fx:dot').setVisible(false);
      let tag: Phaser.GameObjects.Text | null = null;
      if (this.cfg.twoPlayers) {
        tag = this.add.text(0, 0, i === 0 ? '1' : '2', { fontFamily: FONT, fontSize: '18px', fontStyle: 'bold', color: '#1a1a2a', backgroundColor: i === 0 ? '#ffd65a' : '#6ff0e0', padding: { x: 6, y: 1 } }).setOrigin(0.5, 1);
      }
      this.shipC.add(tag ? [spr, held, tag] : [spr, held]);
      this.pv.push({ spr, held, tag, sheet });
    });
    if (this.sim.w.bit) {
      const glow = this.add.image(0, 0, 'fx:dot').setBlendMode(Phaser.BlendModes.ADD).setTint(0xffd27a).setScale(3).setAlpha(0.5);
      const t = frameOf(this, 'bit', 'bit_0', bitPh(this, 0));
      const spr = this.add.image(0, 0, t.key, t.frame);
      this.shipC.add([glow, spr]);
      this.bitV = { spr, glow };
    }

    // world graphics
    this.armsFar = this.add.graphics().setDepth(D.armsFar);
    this.armsNear = this.add.graphics().setDepth(D.armsNear);
    this.trailGfx = this.add.graphics().setDepth(D.shots - 0.5).setBlendMode(Phaser.BlendModes.ADD);
    this.aimGfx = this.add.graphics().setDepth(D.aim);

    // weather & mood
    const [tint, alpha] = MOOD_TINT[mood];
    this.moodRect = this.add.rectangle(W / 2, H / 2, VW + 60, VH + 60, tint, alpha).setDepth(D.mood).setBlendMode(Phaser.BlendModes.MULTIPLY);
    this.vignette = this.add.image(W / 2, H / 2, 'fx:vignette').setDisplaySize(VW + 60, VH + 60).setDepth(D.mood + 1).setAlpha(mood === 'day' ? 0.18 : 0.32);
    this.flashRect = this.add.rectangle(W / 2, H / 2, VW + 60, VH + 60, 0xffffff, 0).setDepth(D.flash).setBlendMode(Phaser.BlendModes.ADD);
    for (let i = 0; i < 7; i++) {
      this.fogImgs.push((hasFrameIn(this, 'env', 'fog_0') ? this.add.image(Math.random() * W, Math.random() * H, 'env', `fog_${i % 4}`).setScale(4.4, 3.6) : this.add.image(Math.random() * W, Math.random() * H, 'fx:fog').setScale(5, 3.4)).setDepth(D.weather + 1).setAlpha(0));
    }
    const nRain = this.quality === 'low' ? 60 : this.quality === 'medium' ? 120 : 200;
    for (let i = 0; i < nRain; i++) {
      this.rain.push({ img: (hasFrameIn(this, 'env', 'rain') ? this.add.image(0, 0, 'env', 'rain') : this.add.image(0, 0, 'fx:rain')).setDepth(D.weather).setAlpha(0).setRotation(0.25), x: Math.random() * W, y: Math.random() * H, v: 900 + Math.random() * 500 });
    }

    // input
    this.setupInput();
    this.unsub.push(this.bus.on('ui:pause', (e) => { this.paused = e.paused; }));
    this.unsub.push(this.bus.on('ui:input', (v) => this.onVirtual(v)));
    this.events.once('shutdown', () => this.cleanup());
    this.events.once('destroy', () => this.cleanup());
    (window as unknown as { __voyage?: unknown }).__voyage = this;
  }

  private cleanup(): void {
    for (const u of this.unsub) u();
    this.unsub = [];
    this.bus.emit('voyage:prompt', null);
  }

  private makeAnims(): void {
    const mk = (key: string, atlas: string, frames: string[], rate: number): void => {
      if (this.anims.exists(key)) return;
      if (!frames.every((f) => hasFrameIn(this, atlas, f))) return;
      this.anims.create({ key, frames: frames.map((f) => ({ key: atlas, frame: f })), frameRate: rate, repeat: -1 });
    };
    mk('ship:flag', 'ship', ['flag_0', 'flag_1', 'flag_2', 'flag_3'], 7);
    mk('ship:flame', 'ship', [0, 1, 2, 3, 4, 5].map((i) => `flame_${i}`), 12);
    mk('ship:leak', 'ship', [0, 1, 2, 3].map((i) => `leak_${i}`), 8);
    mk('env:whirlpool', 'env', [0, 1, 2, 3].map((i) => `whirlpool_${i}`), 8);
    if (!this.anims.exists('cr:clean_burst') && hasFrameIn(this, 'creatures', 'clean_burst_5')) {
      this.anims.create({ key: 'cr:clean_burst', frames: [0, 1, 2, 3, 4, 5].map((i) => ({ key: 'creatures', frame: `clean_burst_${i}` })), frameRate: 16, repeat: 0 });
    }
  }

  private pickSheet(look: 'girl' | 'boy'): string {
    const order = look === 'girl' ? ['skin_girl_sea', 'apprentice_girl'] : ['skin_boy_navy', 'apprentice_boy'];
    for (const k of order) if (this.textures.exists(k) && this.textures.get(k).has('idle_S_0')) return k;
    const key = `ph:char_${look}`;
    charPh(this, key, look === 'girl' ? '#2c7fb8' : '#2a4a8a');
    return key;
  }

  private img(t: Tex): Phaser.GameObjects.Image {
    const i = this.add.image(0, 0, t.key, t.frame);
    i.setOriginFromFrame();
    return i;
  }

  /** An image attached to the ship at a ship-local point. */
  private shipImg(frame: string, x: number, y: number, z: number, depth = -y * 100): Phaser.GameObjects.Image {
    const t = frameOf(this, 'ship', frame, () => shipPh(this, frame));
    const p = project(x, y, z);
    const i = this.add.image(p.sx, p.sy, t.key, t.frame);
    i.setOriginFromFrame();
    i.setDepth(depth);
    this.shipC.add(i);
    return i;
  }

  private mastTop(): { x: number; y: number } {
    if (hasFrameIn(this, 'ship', 'mast')) {
      const cd = this.textures.get('ship').get('mast').customData as { topPx?: [number, number] };
      if (cd?.topPx) return { x: cd.topPx[0], y: cd.topPx[1] };
    }
    return { x: 0, y: -9.4 * PZ };
  }

  private rackSlotPx(cup: number): { x: number; y: number } {
    if (hasFrameIn(this, 'ship', 'rack')) {
      const cd = this.textures.get('ship').get('rack').customData as { slotsPx?: [number, number][] };
      const s = cd?.slotsPx?.[cup];
      if (s) return { x: s[0], y: s[1] };
    }
    return { x: (cup - (RACK_CUPS - 1) / 2) * RACK_CUP_DX * PX_PER_M, y: -0.8 * PZ };
  }

  // ---- input ------------------------------------------------------------------------------------
  private keys: Record<string, Phaser.Input.Keyboard.Key> = {};
  private virt: { mx: number; my: number; action: boolean; throwIt: boolean; t: number }[] = [
    { mx: 0, my: 0, action: false, throwIt: false, t: -9 }, { mx: 0, my: 0, action: false, throwIt: false, t: -9 },
  ];
  private kbWasActive = [false, false];
  private padPrev: { a: boolean; b: boolean }[] = [{ a: false, b: false }, { a: false, b: false }];

  private setupInput(): void {
    const kb = this.input.keyboard;
    if (!kb) return;
    const K = Phaser.Input.Keyboard.KeyCodes;
    this.keys = kb.addKeys({
      w: K.W, a: K.A, s: K.S, d: K.D, e: K.E, space: K.SPACE,
      up: K.UP, down: K.DOWN, left: K.LEFT, right: K.RIGHT, enter: K.ENTER, shift: K.SHIFT,
    }, false) as Record<string, Phaser.Input.Keyboard.Key>;
    kb.addCapture([K.SPACE, K.UP, K.DOWN, K.LEFT, K.RIGHT]);
    // buttons are latched from raw keydown events: a tap shorter than a frame still counts
    const onDown = (ev: KeyboardEvent): void => {
      if (ev.repeat) return;
      switch (ev.code) {
        case 'KeyE': this.pressed.a0 = true; break;
        case 'Space': this.pressed.t0 = true; break;
        case 'Enter': case 'NumpadEnter': this.pressed.a1 = true; break;
        case 'ShiftRight': this.pressed.t1 = true; break;
        case 'ShiftLeft': if (!this.cfg.twoPlayers) this.pressed.t0 = true; break;
        default: break;
      }
    };
    kb.on('keydown', onDown);
    this.unsub.push(() => kb.off('keydown', onDown));
  }

  private pressed = { a0: false, t0: false, a1: false, t1: false };

  private onVirtual(v: import('../voyage/contract').VirtualInput): void {
    const s = this.virt[v.p];
    if (!s) return;
    // REQUESTS.md: action/throwIt are held states -> rising edges become presses
    const press = v.action && !s.action, thr = v.throwIt && !s.throwIt;
    s.mx = v.moveX; s.my = v.moveY; s.action = v.action; s.throwIt = v.throwIt; s.t = this.time.now;
    this.sim.setInput({ p: v.p, moveX: v.moveX, moveY: v.moveY, action: press, throwIt: thr });
  }

  private readInput(): void {
    const k = this.keys;
    const dn = (n: string): number => (k[n]?.isDown ? 1 : 0);
    const pr = this.pressed;
    const two = this.cfg.twoPlayers;
    const inputs: { mx: number; my: number; a: boolean; t: boolean }[] = [
      { mx: dn('d') - dn('a'), my: dn('w') - dn('s'), a: pr.a0, t: pr.t0 },
      { mx: dn('right') - dn('left'), my: dn('up') - dn('down'), a: pr.a1, t: pr.t1 },
    ];
    pr.a0 = pr.t0 = pr.a1 = pr.t1 = false;
    if (!two) {
      const p2 = inputs[1]!, p1 = inputs[0]!;
      if (p1.mx === 0 && p1.my === 0) { p1.mx = p2.mx; p1.my = p2.my; }
      p1.a = p1.a || p2.a;
      p1.t = p1.t || p2.t;
      inputs.length = 1;
    }
    // gamepads (only if the game enabled the gamepad plugin)
    const gp = this.input.gamepad;
    if (gp && gp.total > 0) {
      gp.gamepads.forEach((pad, i) => {
        if (!pad || i > 1) return;
        const slot = two ? i : 0;
        const inp = inputs[slot];
        const prev = this.padPrev[i]!;
        if (!inp) return;
        const sx = pad.leftStick.x, sy = pad.leftStick.y;
        if (Math.hypot(sx, sy) > 0.25) { inp.mx = sx; inp.my = -sy; }
        if (pad.left) inp.mx = -1;
        if (pad.right) inp.mx = 1;
        if (pad.up) inp.my = 1;
        if (pad.down) inp.my = -1;
        const a = pad.A, b = pad.B || pad.X || pad.R2 > 0.5;
        if (a && !prev.a) inp.a = true;
        if (b && !prev.b) inp.t = true;
        prev.a = a; prev.b = b;
      });
    }
    inputs.forEach((inp, p) => {
      const v = this.virt[p]!;
      const virtActive = this.time.now - v.t < 400 && Math.abs(v.mx) + Math.abs(v.my) > 0.05;
      const local = inp.mx !== 0 || inp.my !== 0 || inp.a || inp.t;
      // only write when this device has something to say (or just let go), so the touch UI and
      // scripted inputs are not overwritten by an idle keyboard
      if (!local && !this.kbWasActive[p]) return;
      this.kbWasActive[p] = local;
      const mx = virtActive && inp.mx === 0 && inp.my === 0 ? v.mx : inp.mx;
      const my = virtActive && inp.mx === 0 && inp.my === 0 ? v.my : inp.my;
      this.sim.setInput({ p: p as 0 | 1, moveX: mx, moveY: my, action: inp.a, throwIt: inp.t });
    });
  }

  // ---- frame ----------------------------------------------------------------------------------------
  update(_time: number, deltaMs: number): void {
    const dt = Math.min(0.1, deltaMs / 1000);
    if (!this.paused && !this.ended) {
      this.readInput();
      if (this.hitStop > 0) this.hitStop -= dt;
      else this.sim.advance(dt);
      this.handleEvents(this.sim.drainEvents());
    }
    const rdt = this.paused ? 0 : dt;
    this.render(rdt);
    this.hudT -= dt;
    if (this.hudT <= 0 && !this.ended) {
      this.hudT = 0.1;
      this.bus.emit('voyage:hud', this.sim.hud());
      const pr = this.sim.prompt(0);
      if (pr !== this.lastPrompt) {
        this.lastPrompt = pr;
        const act = this.sim.w.players[0] ? decide(this.sim.w, this.sim.w.players[0]) : null;
        this.bus.emit('voyage:prompt', pr ? { text: pr, id: act?.a ?? 'act' } : null);
      }
    }
  }

  // ---- projection helpers -------------------------------------------------------------------------
  private ws(x: number, y: number, z = 0): { x: number; y: number } {
    return { x: CX + x * PX_PER_M, y: CY - (y - this.camY) * PY - z * PZ };
  }
  private bandDepth(relY: number): number {
    return relY > 0 ? D.far + Math.max(0, Math.min(9, 9 - relY * 0.4)) : D.near + Math.max(0, Math.min(8, -relY * 0.4));
  }

  // ---- render --------------------------------------------------------------------------------------
  private render(dt: number): void {
    const w = this.sim.w;
    const s = w.ship;
    const t = this.time.now / 1000;
    // camera follows the ship's lane position lazily, keeping it within a band
    this.camY += (s.y - this.camY) * Math.min(1, dt * 1.6);
    this.camY = Math.max(s.y - 2.2, Math.min(s.y + 2.2, this.camY));
    this.scroll += s.speed * dt;
    this.sea.tilePositionX = this.scroll * PX_PER_M * 0.5 * 2;
    this.sea.tilePositionY = -this.camY * PY;
    this.seaGlint.tilePositionX = this.scroll * PX_PER_M * 0.62 + t * 9;
    this.seaGlint.tilePositionY = -this.camY * PY * 0.9 + Math.sin(t * 0.4) * 20;

    // ship transform
    const sink = s.sinking >= 0 ? s.sinking : 0;
    const shipX = CX, shipY = CY - (s.y - this.camY) * PY - s.heave * PZ * 0.55 + sink * 40;
    this.shipC.setPosition(shipX, shipY);
    this.shipC.setRotation(-s.pitch * 0.9 + s.roll * 0.12 + sink * 0.05);
    this.shipC.setScale(1, 1 + s.roll * 0.35);
    this.shipC.setAlpha(1 - Math.max(0, sink - 1.8) * 1.1);
    this.shipShadow.setPosition(CX, CY - (s.y - this.camY) * PY + 8).setScale(1 + s.heave * 0.04);

    this.renderCrests(dt, t);
    this.renderShip(dt, t);
    this.renderPlayers(t);
    this.renderDeckThings(t);
    this.renderCreatures(t);
    this.renderBoss(t);
    this.renderFloaters(t);
    this.renderShots();
    this.renderAim(t);
    this.renderWeather(dt, t);
    this.renderWake(dt);
    this.updateParts(dt);
    this.shipC.sort('depth');
  }

  private renderCrests(dt: number, t: number): void {
    const s = this.sim.w.ship;
    const sea = Math.min(1.4, this.sim.sched.swell + this.sim.w.storm.level);
    for (const c of this.crests) {
      c.x -= s.speed * dt;
      c.t += dt;
      if (c.t > c.p || c.x < -16) {
        c.t = 0;
        c.p = 2.2 + Math.random() * 2.8;
        c.x = c.x < -16 ? Phaser.Math.FloatBetween(14, 18) : Phaser.Math.FloatBetween(-15, 17);
        c.y = this.camY + Phaser.Math.FloatBetween(-16, 15);
      }
      const p = this.ws(c.x, c.y);
      const u = c.t / c.p;
      c.img.setPosition(p.x, p.y + Math.sin(t * 1.4 + c.x) * 3).setAlpha(Math.sin(u * Math.PI) * (0.32 + sea * 0.3)).setScale(0.7 + sea * 0.5, 0.8);
    }
  }

  private renderShip(dt: number, t: number): void {
    const w = this.sim.w;
    const s = w.ship;
    // sail level & transparency when someone stands behind it
    const sailT = frameOf(this, 'ship', `sail_${s.sail}`, () => shipPh(this, `sail_${s.sail}`));
    setTex(this.sail, sailT);
    let behind = w.players.some((p) => p.y > -0.3 && p.x > -2.2 && p.x < 5.5) || (!!w.bit && w.bit.y > -0.3 && w.bit.x > -2 && w.bit.x < 5.5);
    if (!behind) {
      // anything hostile in the sea behind the sail (far side, within the sail's x span)
      const sb = this.sail.getBounds();
      const inSail = (x: number, y: number, z = 0): boolean => { const q = this.ws(x, y, z); return sb.contains(q.x, q.y - 20); };
      behind = w.creatures.some((c) => c.hostile && c.state !== 'cleaned' && c.state !== 'gone' && c.y > s.y && inSail(c.x, c.y, c.z))
        || w.bolts.some((b) => inSail(b.x, b.y, 0.9))
        || !!w.boss?.arms.some((a) => a.baseY > 0 && a.state !== 'calm' && inSail(a.x, a.y, 2));
    }
    this.sail.setAlpha(Phaser.Math.Linear(this.sail.alpha, behind ? 0.42 : 0.93, Math.min(1, dt * 6)));
    this.sail.setScale(1 + Math.sin(t * 1.1) * 0.006 * (1 + w.storm.level), 1);
    // the mast hides whoever stands right behind it (the far cannon's gunner): fade it then
    const mastBehind = w.players.some((p) => p.y > 0.3 && Math.abs(p.x - STATIONS.mast.x) < 0.75);
    this.mast.setAlpha(Phaser.Math.Linear(this.mast.alpha, mastBehind ? 0.4 : 1, Math.min(1, dt * 8)));
    // helm wheel
    this.wheelRot += s.wheel * dt * 9;
    if (hasFrameIn(this, 'ship', 'wheel_disc_0')) {
      const f = ((Math.floor(this.wheelRot) % 8) + 8) % 8;
      this.wheelDisc.setFrame(`wheel_disc_${f}`);
    }
    // cannons: barrel frame by aim angle (16 directions), loading glow, loaded ball
    const dark = this.sim.sched.mood !== 'day';
    for (const id of CANNON_IDS) {
      const c = w.cannons[id];
      const v = this.cannonV[id];
      const deg = ((c.aim * 180) / Math.PI + 360) % 360;
      const idx = Math.round(deg / 22.5) % 16;
      const fr = `cannon_barrel_${idx.toString().padStart(2, '0')}`;
      if (hasFrameIn(this, 'ship', fr)) v.barrel.setFrame(fr);
      else v.barrel.setRotation(Math.atan2(-Math.sin(c.aim) * PY, Math.cos(c.aim) * PX_PER_M));
      const st = STATIONS[id];
      const rc = c.recoil * 0.25;
      const p = project(st.x - Math.cos(c.aim) * rc, st.y - Math.sin(c.aim) * rc, 0);
      v.barrel.setPosition(p.sx, p.sy);
      const m = project(st.x + Math.cos(c.aim) * CANNONS[id].muzzle, st.y + Math.sin(c.aim) * CANNONS[id].muzzle, MUZZLE_Z);
      const ready = c.loaded && c.loadT <= 0;
      v.glow.setPosition(m.sx, m.sy).setAlpha((dark ? 0.35 : 0.12) + (ready ? 0.35 + Math.sin(t * 6) * 0.1 : 0));
      v.glow.setTint(c.loaded ? (this.ammoColor[c.loaded] ?? 0xffd27a) : 0xffd27a);
      v.barrel.setTint(c.jam ? 0x9a7ab0 : 0xffffff);
    }
    // rack balls
    const n = w.rack.length;
    while (this.rackBalls.length < RACK_CUPS) {
      const b = this.shipImgBall();
      this.rackBalls.push(b);
    }
    const rp = { x: this.rack.x, y: this.rack.y };
    this.rackBalls.forEach((b, cup) => {
      const i = cup - rackCup(0, n);
      const slot = i >= 0 && i < n ? w.rack[i] : undefined;
      if (!slot || !slot.has) { b.setVisible(false); return; }
      const off = this.rackSlotPx(cup);
      b.setVisible(true).setPosition(rp.x + off.x, rp.y + off.y + 4).setTint(this.ammoColor[slot.ammo] ?? 0xffffff);
    });
    // flood water on the deck
    this.waterGfx.clear();
    if (s.water > 0.01) {
      this.waterGfx.fillStyle(0x3a8fd0, Math.min(0.6, 0.15 + s.water * 0.5));
      this.waterGfx.beginPath();
      const slosh = s.roll * 3;
      const pts: { x: number; y: number }[] = [];
      for (let x = -7.8; x <= 7.6; x += 0.4) pts.push({ x, y: halfBeam(x) - 0.25 });
      for (let x = 7.6; x >= -7.8; x -= 0.4) pts.push({ x, y: -(halfBeam(x) - 0.25) });
      pts.forEach((q, i) => {
        const pp = project(q.x, q.y, 0.02 + s.water * 0.35 + slosh * (q.y / 3.5) * 0.1);
        if (i === 0) this.waterGfx.moveTo(pp.sx, pp.sy); else this.waterGfx.lineTo(pp.sx, pp.sy);
      });
      this.waterGfx.closePath();
      this.waterGfx.fillPath();
    }
  }

  private shipImgBall(): Phaser.GameObjects.Image {
    const t = frameOf(this, 'ship', 'ball', () => shipPh(this, 'ball'));
    const i = this.add.image(0, 0, t.key, t.frame).setOrigin(0.5, 0.5).setDepth(-STATIONS.rack.y * 100 + 1);
    this.shipC.add(i);
    return i;
  }

  private charFrame(sheet: string, face: number, moving: boolean, phase: number, t: number): string | undefined {
    if (sheet.startsWith('ph:')) return undefined;
    const sx = Math.cos(face) * PX_PER_M, sy = -Math.sin(face) * PY;
    const a = Math.atan2(sy, sx);
    const dir = DIRS[((Math.round(a / (Math.PI / 4)) % 8) + 8) % 8] ?? 'S';
    const tex = this.textures.get(sheet);
    if (moving) {
      const f = `walk_${dir}_${Math.floor(phase * 2.2) % 8}`;
      if (tex.has(f)) return f;
    }
    const f = `idle_${dir}_${Math.floor(t * 6) % 4}`;
    return tex.has(f) ? f : `idle_S_0`;
  }

  private renderPlayers(t: number): void {
    const w = this.sim.w;
    w.players.forEach((p, i) => {
      const v = this.pv[i];
      if (!v) return;
      const moving = Math.hypot(p.vx, p.vy) > 0.4;
      const pos = project(p.x, p.y, 0);
      const fr = this.charFrame(v.sheet, p.face, moving, p.walk, t + i * 0.37);
      if (fr && v.spr.frame.name !== fr) v.spr.setFrame(fr);
      v.spr.setPosition(pos.sx, pos.sy).setDepth(-p.y * 100);
      if (v.sheet.startsWith('ph:')) v.spr.setFlipX(Math.cos(p.face) < 0);
      // carried item above the head
      if (p.held) {
        const hp = project(p.x, p.y, 1.62);
        let tx: Tex;
        if (p.held.kind === 'ball') tx = frameOf(this, 'ship', 'ball', () => shipPh(this, 'ball'));
        else if (p.held.kind === 'plank') tx = frameOf(this, 'ship', 'plank', () => shipPh(this, 'plank'));
        else tx = frameOf(this, 'ship', p.held.full ? 'bucket' : 'bucket_empty', () => shipPh(this, 'bucket'));
        setTex(v.held, tx);
        v.held.setVisible(true).setPosition(hp.sx, hp.sy + Math.sin(t * 8 + i) * (moving ? 2 : 0.5)).setDepth(-p.y * 100 + 0.2);
        v.held.setScale(p.held.kind === 'ball' ? 1.15 : 1);
        if (p.held.kind === 'ball' && p.held.ammo) v.held.setTint(this.ammoColor[p.held.ammo] ?? 0xffffff); else v.held.clearTint();
      } else v.held.setVisible(false);
      if (v.tag) v.tag.setPosition(pos.sx, pos.sy - 98 - (p.held ? 22 : 0)).setDepth(25000 + i);
    });
    const b = w.bit;
    if (b && this.bitV) {
      const pos = project(b.x, b.y, b.z);
      const f = Math.floor(t * 4) % 8 === 7 ? 3 : Math.floor(t * 3) % 2;
      setTex(this.bitV.spr, frameOf(this, 'bit', `bit_${f}`, bitPh(this, f)));
      this.bitV.spr.setPosition(pos.sx, pos.sy).setDepth(-b.y * 100 + 0.5);
      this.bitV.glow.setPosition(pos.sx, pos.sy - 14).setDepth(-b.y * 100 + 0.4).setAlpha(0.35 + Math.sin(t * 3) * 0.08);
    }
  }

  private renderDeckThings(t: number): void {
    const w = this.sim.w;
    // loose items
    const seen = new Set<number>();
    for (const it of w.items) {
      seen.add(it.uid);
      let img = this.itemV.get(it.uid);
      const fr = it.kind === 'ball' ? 'ball' : it.kind === 'plank' ? 'plank' : it.full ? 'bucket' : 'bucket_empty';
      const tx = frameOf(this, 'ship', fr, () => shipPh(this, fr === 'bucket_empty' ? 'bucket' : fr));
      if (!img) {
        img = this.add.image(0, 0, tx.key, tx.frame);
        this.shipC.add(img);
        this.itemV.set(it.uid, img);
      }
      setTex(img, tx);
      const p = project(it.x, it.y, it.z);
      img.setPosition(p.sx, p.sy).setDepth(-it.y * 100 + 0.1);
      if (it.kind === 'ball' && it.ammo) img.setTint(this.ammoColor[it.ammo] ?? 0xffffff); else img.clearTint();
    }
    for (const [k, img] of this.itemV) if (!seen.has(k)) { img.destroy(); this.itemV.delete(k); }
    // leaks
    const lseen = new Set<number>();
    for (const l of w.leaks) {
      lseen.add(l.uid);
      let spr = this.leakV.get(l.uid);
      if (!spr) {
        const tx = frameOf(this, 'ship', 'leak_0', () => shipPh(this, 'leak_0'));
        spr = this.add.sprite(0, 0, tx.key, tx.frame);
        spr.setOriginFromFrame();
        if (this.anims.exists('ship:leak')) spr.play({ key: 'ship:leak', startFrame: l.uid % 4 });
        this.shipC.add(spr);
        this.leakV.set(l.uid, spr);
      }
      const p = project(l.x, l.y, 0);
      spr.setPosition(p.sx, p.sy).setDepth(-5000 - l.y).setScale(0.8 + l.size * 0.25);
    }
    for (const [k, s] of this.leakV) if (!lseen.has(k)) { s.destroy(); this.leakV.delete(k); }
    // fires
    const fseen = new Set<number>();
    for (const f of w.fires) {
      fseen.add(f.uid);
      let v = this.fireV.get(f.uid);
      if (!v) {
        const tx = frameOf(this, 'ship', 'flame_0', () => shipPh(this, 'flame_0'));
        const spr = this.add.sprite(0, 0, tx.key, tx.frame);
        spr.setOriginFromFrame();
        if (this.anims.exists('ship:flame')) spr.play({ key: 'ship:flame', startFrame: f.uid % 6 });
        const glow = this.add.image(0, 0, 'fx:dot').setBlendMode(Phaser.BlendModes.ADD).setTint(0xff8a2a);
        this.shipC.add([glow, spr]);
        v = { spr, glow };
        this.fireV.set(f.uid, v);
      }
      const p = project(f.x, f.y, 0);
      const sc = 0.55 + f.level * 0.7;
      v.spr.setPosition(p.sx, p.sy).setDepth(-f.y * 100 + 0.05).setScale(sc * (1 + Math.sin(t * 9 + f.uid) * 0.05), sc);
      if (!this.anims.exists('ship:flame')) v.spr.setScale(sc, sc * (1 + Math.sin(t * 14 + f.uid) * 0.12));
      v.glow.setPosition(p.sx, p.sy - 20).setDepth(-f.y * 100).setScale(2.5 + f.level * 2).setAlpha(0.35 + Math.sin(t * 11 + f.uid) * 0.1);
    }
    for (const [k, v] of this.fireV) if (!fseen.has(k)) { v.spr.destroy(); v.glow.destroy(); this.fireV.delete(k); }

    // highlights of what the action button would do + progress
    const g = this.deckGfx;
    g.clear();
    const tg = this.topGfx;
    tg.clear();
    w.players.forEach((p, i) => {
      const h = this.highlights[i];
      if (!h) return;
      const act = decide(w, p);
      let hx: number | null = null, hy = 0, r = 0.75;
      if (act) {
        switch (act.a) {
          case 'man': case 'load': hx = STATIONS[act.c].x; hy = STATIONS[act.c].y; break;
          case 'helm': hx = STATIONS.wheel.x; hy = STATIONS.wheel.y; break;
          case 'sail': hx = STATIONS.mast.x; hy = STATIONS.mast.y; break;
          case 'plank': hx = STATIONS.planks.x; hy = STATIONS.planks.y; break;
          case 'bucket': case 'fill': hx = STATIONS.barrel.x; hy = STATIONS.barrel.y; break;
          case 'take': { hx = STATIONS.rack.x + (rackCup(act.slot, w.rack.length) - (RACK_CUPS - 1) / 2) * RACK_CUP_DX; hy = 2.95; r = 0.3; break; }
          case 'return': hx = STATIONS.rack.x; hy = STATIONS.rack.y; break;
          case 'repair': { const l = w.leaks.find((q) => q.uid === act.uid); if (l) { hx = l.x; hy = l.y; } break; }
          case 'douse': { const f = w.fires.find((q) => q.uid === act.uid); if (f) { hx = f.x; hy = f.y; } break; }
          case 'pick': { const it = w.items.find((q) => q.uid === act.uid); if (it) { hx = it.x; hy = it.y; r = 0.4; } break; }
          case 'splash': case 'shoo': { const c = w.creatures.find((q) => q.uid === act.uid); if (c) { hx = c.dx; hy = c.dy; } break; }
          default: break;
        }
      }
      if (hx === null) { h.setVisible(false); }
      else {
        const pp = project(hx, hy, 0.02);
        const pulse = 1 + Math.sin(t * 6) * 0.06;
        h.setVisible(true).setPosition(pp.sx, pp.sy).setScale((r * 2 * PX_PER_M * pulse) / 96, (r * 2 * PY * pulse) / 96).setAlpha(0.75);
      }
      // hold-to-repair progress
      if (p.job) {
        const pp = project(p.x, p.y, 2.25);
        const u = Math.min(1, p.job.t / p.job.need);
        tg.fillStyle(0x10131f, 0.7).fillRoundedRect(pp.sx - 26, pp.sy - 6, 52, 12, 5);
        tg.fillStyle(p.job.kind === 'leak' ? 0xffd27a : 0x6fd3ff, 1).fillRoundedRect(pp.sx - 24, pp.sy - 4, 48 * u, 8, 4);
      }
    });
    // cannon charges (lights left from the loaded ball) and reload arcs
    for (const id of CANNON_IDS) {
      const c = w.cannons[id];
      if (c.loaded) {
        const st = STATIONS[id];
        // a small row of lights beside the cannon base (not over the gunner's head)
        const pp = project(st.x, st.y, 0);
        const col = this.ammoColor[c.loaded] ?? 0xffffff;
        const ox = id === 'cannon_stern' ? -34 : 34, oy = id === 'cannon_near' ? 10 : 2;
        for (let k = 0; k < c.charges; k++) {
          const x = pp.sx + ox + (id === 'cannon_stern' ? -k : k) * 12;
          tg.fillStyle(0x10131f, 0.8).fillCircle(x, pp.sy + oy, 6);
          tg.fillStyle(col, 1).fillCircle(x, pp.sy + oy, 4.5);
        }
      }
      if (!c.loaded || c.loadT <= 0) continue;
      const st = STATIONS[id];
      const pp = project(st.x, st.y, 1.75);
      const full = c.charges >= 3 ? Math.max(0.2, w.stats.reloadSec || 1.6) : Math.max(0.15, (w.stats.reloadSec || 1.6) * 0.45);
      const u = Math.max(0, 1 - c.loadT / full);
      tg.lineStyle(5, 0x10131f, 0.6).beginPath().arc(pp.sx, pp.sy, 13, 0, Math.PI * 2).strokePath();
      tg.lineStyle(4, this.ammoColor[c.loaded] ?? 0xffffff, 1).beginPath().arc(pp.sx, pp.sy, 13, -Math.PI / 2, -Math.PI / 2 + u * Math.PI * 2).strokePath();
    }
  }

  private creatureTex(c: Creature, t: number): Tex {
    const friend = c.friendly || c.state === 'cleaned' || c.state === 'flee' && !c.hostile;
    const f = Math.floor(t * 3 + c.uid) % 2;
    const name = `${c.def.id}_${friend ? 'friend' : 'noise'}_${f}`;
    return frameOf(this, 'creatures', name, () => creaturePh(this, 'ph:' + name, c.def, friend, f, this.colorOfAmmo(c.def.weakness)));
  }

  private colorOfAmmo(a: AmmoId): string {
    const n = this.ammoColor[a];
    return n === undefined ? '#8fd3ff' : '#' + n.toString(16).padStart(6, '0');
  }

  private renderCreatures(t: number): void {
    const w = this.sim.w;
    const seen = new Set<number>();
    const fog = w.fog.level;
    const lantern = (w.stats.lanternRadius || 260) / PX_PER_M;
    for (const c of w.creatures) {
      if (c.state === 'gone') continue;
      seen.add(c.uid);
      let v = this.crV.get(c.uid);
      const tx = this.creatureTex(c, t);
      if (!v) {
        const shadow = this.add.image(0, 0, 'fx:shadow');
        const ring = this.add.image(0, 0, 'fx:ring').setTint(0xff4a4a).setVisible(false);
        const spr = this.add.image(0, 0, tx.key, tx.frame);
        spr.setOriginFromFrame();
        const bubble = this.add.text(0, 0, c.def.symptom, {
          fontFamily: FONT, fontSize: '19px', fontStyle: 'bold', color: '#2a1838', backgroundColor: '#fff4dc',
          padding: { x: 8, y: 4 }, rtl: true,
        }).setOrigin(0.5, 1).setDepth(D.bubble);
        v = { spr, shadow, ring, bubble, onDeck: false, jx: 0 };
        this.crV.set(c.uid, v);
      }
      setTex(v.spr, tx);
      const deck = c.state === 'deck';
      if (deck !== v.onDeck) {
        v.onDeck = deck;
        if (deck) this.shipC.add([v.shadow, v.ring, v.spr]);
        else { this.shipC.remove([v.shadow, v.ring, v.spr]); this.add.existing(v.shadow); this.add.existing(v.ring); this.add.existing(v.spr); }
      }
      const tele = c.state === 'telegraph';
      if (!c.friendly && c.state !== 'cleaned' && Math.random() < 0.06) v.jx = (Math.random() - 0.5) * 6; else v.jx *= 0.7;
      const shake = tele ? Math.sin(t * 60) * 3 : 0;
      const bob = Math.sin(t * 2 + c.uid) * 4;
      let sx: number, sy: number, gy: number, depth: number;
      if (deck) {
        const p = project(c.dx, c.dy, 0);
        sx = p.sx; sy = p.sy; gy = p.sy; depth = -c.dy * 100;
        v.shadow.setDepth(depth - 0.2); v.ring.setDepth(depth - 0.1);
      } else {
        const p = this.ws(c.x, c.y, c.z);
        const g = this.ws(c.x, c.y, 0);
        sx = p.x; sy = p.y + bob; gy = g.y;
        depth = this.bandDepth(c.y - w.ship.y);
        v.shadow.setDepth(depth - 0.02); v.ring.setDepth(depth - 0.01);
      }
      v.spr.setPosition(sx + shake + v.jx, sy).setDepth(depth);
      v.spr.setFlipX(c.face > 0); // art faces screen-left
      const sc = tele ? 1 + Math.min(1, c.t / 0.8) * 0.12 : 1;
      v.spr.setScale(sc);
      v.shadow.setPosition(sx, gy + 4).setScale((c.r * 2.2 * PX_PER_M) / 64, (c.r * 1.4 * PY) / 28 * 0.9).setAlpha(c.z > 0.5 ? 0.25 : 0.45);
      if (c.hitFlash > 0.12) v.spr.setTintFill(0xffffff);
      else if (c.state === 'cleaned') v.spr.clearTint();
      else v.spr.clearTint();
      let alpha = 1;
      if (c.state === 'cleaned') alpha = Math.max(0, 1 - Math.max(0, c.t - 2.2));
      if (!deck && fog > 0.05) {
        const d = Math.hypot(c.x, c.y - w.ship.y);
        const vis = Math.max(0, 1 - fog * Math.max(0, (d - lantern - 3) / 4));
        alpha *= Math.max(0.12, vis);
      }
      v.spr.setAlpha(alpha);
      // telegraph ring
      if (tele) {
        const u = Math.min(1, c.t / 0.8);
        const rr = c.r * (1.6 - u * 0.5) * 2;
        v.ring.setVisible(true).setPosition(sx, gy).setScale((rr * PX_PER_M) / 96, (rr * PY) / 96).setAlpha(0.4 + u * 0.6);
      } else v.ring.setVisible(false);
      // symptom bubble (hostile, on screen)
      // one bubble per flock: only its first living member speaks
      const flockLead = c.def.behavior !== 'swarm' || !w.creatures.some((o) => o !== c && o.def.id === c.def.id && o.wave === c.wave && o.group === c.group && o.uid < c.uid && o.hostile && o.state !== 'cleaned' && o.state !== 'gone' && o.state !== 'flee');
      const showBubble = flockLead && c.hostile && c.state !== 'cleaned' && c.state !== 'flee' && Math.abs(c.x) < 14.5 && alpha > 0.3;
      v.bubble.setVisible(showBubble);
      if (showBubble) {
        let bx = sx, by = sy - (v.spr.displayHeight * (deck ? 0.75 : 0.62)) - 6;
        if (deck) { const m = this.shipC.getWorldTransformMatrix(); const q = m.transformPoint(sx, by); bx = q.x; by = q.y; }
        v.bubble.setPosition(Phaser.Math.Clamp(bx, VX0 + 90, VX1 - 90), Phaser.Math.Clamp(by, VY0 + 50, VY1 - 10)).setAlpha(alpha);
      }
    }
    for (const [k, v] of this.crV) if (!seen.has(k)) { v.spr.destroy(); v.shadow.destroy(); v.ring.destroy(); v.bubble.destroy(); this.crV.delete(k); }
  }

  private armSpr = new Map<number, Phaser.GameObjects.Image>();

  private renderBoss(t: number): void {
    const b = this.sim.w.boss;
    this.armsFar.clear();
    this.armsNear.clear();
    if (!b) return;
    const sy = this.sim.w.ship.y;
    const art = hasFrameIn(this, 'kraken', 'kraken_head_p1_0');
    const f2 = Math.floor(t * 2.5) % 2;
    let htx: Tex;
    if (art) htx = { key: 'kraken', frame: b.friendly ? `kraken_head_friend_${f2}` : `kraken_head_p${Math.max(1, b.phase)}_${f2}` };
    else htx = b.friendly ? frameOf(this, 'creatures', 'kraken_head_friend', envPh(this, 'kraken_head_friend')) : frameOf(this, 'creatures', 'kraken_head', envPh(this, 'kraken_head'));
    if (!this.head) this.head = this.add.image(0, 0, htx.key, htx.frame);
    setTex(this.head, htx);
    const rise = Math.min(1, b.phase === 0 ? b.t / 2.5 : 1);
    const hp = this.ws(b.x, b.y, 0);
    this.head.setPosition(hp.x, hp.y + (1 - rise) * 160 + Math.sin(t * 0.8) * 6).setDepth(this.bandDepth(b.y - sy) - 0.5);
    const hs = art ? 1.5 : 1;
    this.head.setScale(hs * (1 + b.roarT * 0.05 + Math.sin(t * 1.3) * 0.01));
    const seen = new Set<number>();
    for (const a of b.arms) {
      seen.add(a.uid);
      const calm = a.state === 'calm';
      const tele = a.state === 'telegraph';
      const depth = this.bandDepth(a.y - sy) + 0.1;
      if (art) {
        const ph = Math.max(1, b.phase);
        const fr = calm ? `kraken_arm_friend_${f2}` : ph === 1 ? `kraken_arm_p1_${a.weakness}_${f2}` : `kraken_arm_p${ph}_${f2}`;
        const tx: Tex = hasFrameIn(this, 'kraken', fr) ? { key: 'kraken', frame: fr } : { key: 'kraken', frame: `kraken_arm_p2_${f2}` };
        let spr = this.armSpr.get(a.uid);
        if (!spr) { spr = this.add.image(0, 0, tx.key, tx.frame); this.armSpr.set(a.uid, spr); }
        setTex(spr, tx);
        const p = this.ws(a.x, a.y, 0);
        const lean = tele ? Math.min(1, a.t / 0.8) : 0;
        spr.setPosition(p.x, p.y).setDepth(depth);
        spr.setFlipX(a.baseX > 1.5);
        spr.setScale(1.25 * (1 + lean * 0.15), 1.25 * Math.max(0.05, a.rise) * (1 + lean * 0.12));
        spr.setRotation((a.baseX > 1.5 ? -1 : 1) * (Math.sin(a.sway) * 0.06 - (a.state === 'slam' ? 0.25 * (1 - a.t / 0.5) : 0)));
        if (a.hitFlash > 0.1) spr.setTintFill(0xffffff);
        else if (tele) spr.setTint(Math.sin(t * 24) > 0 ? 0xff7a6a : 0xffffff);
        else spr.clearTint();
        const g = a.baseY > 0 ? this.armsFar : this.armsNear;
        g.lineStyle(3, 0xffffff, 0.55 * a.rise).strokeEllipse(p.x, p.y, 74, 24);
        if (tele) g.lineStyle(4, 0xff5a4a, 0.5 + Math.sin(t * 20) * 0.3).strokeEllipse(p.x, p.y, 96, 34);
      } else {
        this.drawArmProcedural(a, sy, t);
      }
      // symptom bubble above the arm
      let bub = this.armBubbles.get(a.uid);
      if (!bub) {
        bub = this.add.text(0, 0, a.symptom, { fontFamily: FONT, fontSize: '18px', fontStyle: 'bold', color: '#2a1838', backgroundColor: '#ffe3ef', padding: { x: 7, y: 3 }, rtl: true }).setOrigin(0.5, 1).setDepth(D.bubble);
        this.armBubbles.set(a.uid, bub);
      }
      const top = this.ws(a.x, a.y, a.rise * 4.2);
      bub.setVisible(!calm && a.rise > 0.6).setPosition(Phaser.Math.Clamp(top.x, VX0 + 90, VX1 - 90), Phaser.Math.Clamp(top.y - 6, VY0 + 50, VY1));
    }
    for (const [k, v] of this.armBubbles) if (!seen.has(k) || b.friendly) { v.destroy(); this.armBubbles.delete(k); }
    for (const [k, v] of this.armSpr) if (!seen.has(k)) { v.destroy(); this.armSpr.delete(k); }
  }

  private drawArmProcedural(a: import('../voyage/sim/types').BossArm, sy: number, t: number): void {
    const g = a.baseY > 0 ? this.armsFar : this.armsNear;
    const l = Math.hypot(a.baseX, a.baseY) || 1;
    const bx = a.baseX + (a.baseX / l) * 1.8, by = sy + a.baseY + (a.baseY / l) * 1.8;
    const base = this.ws(bx, by, 0);
    const zTip = a.rise * (2.3 + (a.state === 'telegraph' ? 0.8 : 0)) + Math.sin(a.sway) * 0.2;
    const tip = this.ws(a.x, a.y, zTip);
    const ctrl = this.ws((bx + a.x) / 2, (by + a.y) / 2, zTip + 1.6 * a.rise);
    const calm = a.state === 'calm';
    const col = a.hitFlash > 0.1 ? 0xffffff : calm ? 0xff9ac0 : 0x4a3378;
    const edge = calm ? 0x8a3a5a : a.state === 'telegraph' ? 0xff4a4a : 0x1a0f30;
    const N = 18;
    for (const pass of [0, 1]) {
      for (let i = 0; i <= N; i++) {
        const u = i / N;
        const x = (1 - u) * (1 - u) * base.x + 2 * (1 - u) * u * ctrl.x + u * u * tip.x;
        const y = (1 - u) * (1 - u) * base.y + 2 * (1 - u) * u * ctrl.y + u * u * tip.y;
        const r = (24 - u * 15) * Math.max(0.2, a.rise);
        if (pass === 0) g.fillStyle(edge, 1).fillCircle(x, y, r + 3);
        else {
          g.fillStyle(col, 1).fillCircle(x, y, r);
          if (i % 3 === 1 && !calm) g.fillStyle(0xc0a0ff, 0.7).fillCircle(x + r * 0.3, y + r * 0.35, r * 0.25);
        }
      }
    }
    g.lineStyle(3, 0xffffff, 0.6 * a.rise).strokeEllipse(base.x, base.y, 70, 22);
    if (a.state === 'telegraph') g.lineStyle(4, 0xff5a4a, 0.5 + Math.sin(t * 20) * 0.3).strokeCircle(tip.x, tip.y, 26);
  }

  private renderFloaters(t: number): void {
    const w = this.sim.w;
    const seen = new Set<number>();
    for (const f of w.floaters) {
      if (!f.alive) continue;
      seen.add(f.uid);
      let img = this.flV.get(f.uid);
      const tx = this.floaterTex(f);
      if (!img) {
        img = this.add.image(0, 0, tx.key, tx.frame);
        img.setOriginFromFrame();
        this.flV.set(f.uid, img);
      }
      setTex(img, tx);
      const bob = f.kind === 'coin' ? -Math.abs(Math.sin(f.t * 9)) * 10 : Math.sin(t * 1.8 + f.uid) * 3;
      const p = this.ws(f.x, f.y, f.kind === 'coin' ? 0.6 : 0);
      img.setPosition(p.x, p.y + bob);
      const big = f.kind === 'island' || f.kind === 'cove' || f.kind === 'lighthouse' || f.kind === 'pier';
      img.setDepth(big ? D.far - 1 : f.kind === 'whirlpool' ? D.crest + 0.5 : f.kind === 'coin' ? D.shots : this.bandDepth(f.y - w.ship.y));
      if (f.kind === 'whirlpool') img.setScale(2.2 * (1 + Math.sin(t * 2) * 0.03));
      if (f.kind === 'reef') img.setScale((2.3 * f.r * PX_PER_M) / Math.max(1, img.frame.width));
      if (f.kind === 'crate' && f.tag === 'treasure') img.setTint(0xffe08a); else if (f.kind !== 'coin') img.clearTint();
    }
    for (const [k, img] of this.flV) if (!seen.has(k)) { img.destroy(); this.flV.delete(k); }
  }

  private floaterTex(f: Floater): Tex {
    const ab = 'abcd';
    switch (f.kind) {
      case 'coin': return { key: 'fx:coin' };
      case 'crate': return frameOf(this, 'env', 'crate_float', envPh(this, 'crate_float'));
      case 'reef': { const n = `reef_${ab[f.variant % 3]}`; return frameOf(this, 'env', n, envPh(this, n)); }
      case 'island': { const n = `island_${ab[f.variant % 4]}`; return frameOf(this, 'env', n, envPh(this, n)); }
      case 'cove': { const n = `cove_${ab[f.variant % 2]}`; return frameOf(this, 'env', n, envPh(this, n)); }
      case 'lighthouse': { const n = this.sim.w.arrived ? 'lighthouse_lit' : 'lighthouse_unlit'; return frameOf(this, 'env', n, envPh(this, n)); }
      case 'whirlpool':
        if (hasFrameIn(this, 'env', 'whirlpool_0')) return { key: 'env', frame: `whirlpool_${Math.floor(f.t * 8) % 4}` };
        return frameOf(this, 'env', 'whirlpool', envPh(this, 'whirlpool'));
      default: return frameOf(this, 'env', f.kind, envPh(this, f.kind));
    }
  }

  private renderShots(): void {
    const w = this.sim.w;
    const seen = new Set<number>();
    const g = this.trailGfx;
    g.clear();
    for (const s of w.shots) {
      seen.add(s.uid);
      let v = this.shotV.get(s.uid);
      const color = this.ammoColor[s.ammo] ?? 0xffffff;
      if (!v) {
        const tx = frameOf(this, 'ship', 'ball', () => shipPh(this, 'ball'));
        const img = this.add.image(0, 0, tx.key, tx.frame).setOrigin(0.5).setDepth(D.shots).setTint(color).setScale(1.1);
        const glow = this.add.image(0, 0, 'fx:dot').setBlendMode(Phaser.BlendModes.ADD).setDepth(D.shots - 0.1).setTint(color).setScale(2.4);
        v = { img, glow, trail: [], color };
        this.shotV.set(s.uid, v);
      }
      const z = shotHeight(s.z0, s.t, s.T);
      const p = this.ws(s.x, s.y, z);
      v.img.setPosition(p.x, p.y);
      v.glow.setPosition(p.x, p.y);
      v.trail.push({ x: p.x, y: p.y });
      if (v.trail.length > 10) v.trail.shift();
      for (let i = 1; i < v.trail.length; i++) {
        const a = v.trail[i - 1]!, b = v.trail[i]!;
        g.lineStyle(2 + i * 0.9, color, (i / v.trail.length) * 0.7).lineBetween(a.x, a.y, b.x, b.y);
      }
    }
    for (const [k, v] of this.shotV) if (!seen.has(k)) { v.img.destroy(); v.glow.destroy(); this.shotV.delete(k); }
    // noise bolts
    const bseen = new Set<number>();
    for (const b of w.bolts) {
      bseen.add(b.uid);
      let v = this.boltV.get(b.uid);
      if (!v) {
        const tx = frameOf(this, 'creatures', 'bolt_noise', envPh(this, 'bolt_noise'));
        const img = this.add.image(0, 0, tx.key, tx.frame).setDepth(D.shots - 1);
        const sh = this.add.image(0, 0, 'fx:shadow').setDepth(D.crest + 1).setScale(0.6, 0.6);
        v = { img, sh };
        this.boltV.set(b.uid, v);
      }
      const p = this.ws(b.x, b.y, 0.9 + Math.sin(b.t * 5) * 0.1);
      const gp = this.ws(b.x, b.y, 0);
      v.img.setPosition(p.x, p.y).setRotation(b.t * 6).setScale(1 + Math.sin(b.t * 12) * 0.08);
      v.sh.setPosition(gp.x, gp.y);
      if (Math.random() < 0.4) this.spawnPart('fx:glyph', b.x, b.y, 0.9, 0, 0, 0.6, 0.4, 0.6, 0.2, 0.8, 0, 'world');
    }
    for (const [k, v] of this.boltV) if (!bseen.has(k)) { v.img.destroy(); v.sh.destroy(); this.boltV.delete(k); }
  }

  private renderAim(t: number): void {
    const w = this.sim.w;
    const g = this.aimGfx;
    g.clear();
    for (const p of w.players) {
      if (!p.at || p.at === 'wheel') continue;
      const id = p.at;
      const c = w.cannons[id];
      const pr = predictShot(w, id);
      const def = CANNONS[id];
      const st = STATIONS[id];
      // arc limits
      const o = this.ws(st.x, w.ship.y + st.y, 0.05);
      for (const s of [-1, 1]) {
        const a = def.base + s * def.arc;
        const e = this.ws(st.x + Math.cos(a) * 3, w.ship.y + st.y + Math.sin(a) * 3, 0.05);
        g.lineStyle(2, 0xffffff, 0.18).lineBetween(o.x, o.y, e.x, e.y);
      }
      const ready = !!c.loaded && c.loadT <= 0 && !c.jam;
      const col = c.loaded ? (this.ammoColor[c.loaded] ?? 0xffffff) : 0xffffff;
      // ballistic path: a soft white guide with bright dots in the ammo colour
      const N = 24;
      const pts: { x: number; y: number }[] = [];
      for (let i = 0; i <= N; i++) {
        const u = i / N;
        const x = pr.x0 + (pr.x1 - pr.x0) * u, y = pr.y0 + (pr.y1 - pr.y0) * u;
        pts.push(this.ws(x, y, shotHeight(0.85, pr.t * u, pr.T)));
      }
      g.lineStyle(7, 0x0b1830, ready ? 0.28 : 0.15).strokePoints(pts);
      g.lineStyle(3, 0xffffff, ready ? 0.55 : 0.25).strokePoints(pts);
      const phase = (t * 3) % 1;
      for (let i = 1; i < N; i += 2) {
        const a = pts[i]!, b = pts[i + 1] ?? a;
        const q = { x: a.x + (b.x - a.x) * phase, y: a.y + (b.y - a.y) * phase };
        g.fillStyle(0x0b1830, ready ? 0.7 : 0.3).fillCircle(q.x, q.y, ready ? 5 : 3.5);
        g.fillStyle(col, ready ? 1 : 0.5).fillCircle(q.x, q.y, ready ? 3.5 : 2.5);
      }
      // predicted impact
      const hit = pr.hit;
      const end = this.ws(pr.x1, pr.y1, hit ? 0.3 : 0);
      const pulse = 1 + Math.sin(t * 8) * 0.08;
      if (hit) {
        g.lineStyle(7, 0x0b1830, 0.5).strokeEllipse(end.x, end.y, 54 * pulse, 34 * pulse);
        g.lineStyle(4, 0xffe066, 1).strokeEllipse(end.x, end.y, 54 * pulse, 34 * pulse);
        g.lineStyle(3, 0xffffff, 1).lineBetween(end.x - 12, end.y, end.x + 12, end.y).lineBetween(end.x, end.y - 8, end.x, end.y + 8);
      } else {
        g.lineStyle(6, 0x0b1830, 0.35).strokeEllipse(end.x, end.y, 36, 22);
        g.lineStyle(3, 0xffffff, 0.8).strokeEllipse(end.x, end.y, 36, 22);
      }
      // lead marker: where to aim for the nearest target (aim assist pulls toward it)
      if (pr.lead && !hit) {
        const L = this.ws(pr.lead.x, pr.lead.y, 0.3);
        g.lineStyle(3, 0x6ff0e0, 0.9);
        g.strokePoints([{ x: L.x, y: L.y - 12 }, { x: L.x + 12, y: L.y }, { x: L.x, y: L.y + 12 }, { x: L.x - 12, y: L.y }], true);
      }
    }
  }

  private renderWeather(dt: number, t: number): void {
    const w = this.sim.w;
    const st = w.storm.level;
    // mood darkens with the storm
    const base = MOOD_TINT[this.sim.sched.mood];
    const a = Math.min(0.62, base[1] + st * 0.3);
    this.moodRect.setFillStyle(st > 0.05 ? 0x5a6a90 : base[0], a);
    // rain
    const want = st > 0.05 ? st : 0;
    for (const r of this.rain) {
      r.y += r.v * dt;
      r.x -= r.v * 0.25 * dt + w.ship.speed * 20 * dt;
      if (r.y > VY1 + 20) { r.y = VY0 - 30; r.x = VX0 + Math.random() * (VW + 300); }
      if (r.x < VX0 - 20) r.x += VW + 300;
      r.img.setPosition(r.x, r.y).setAlpha(want * 0.6);
    }
    // fog
    const fog = w.fog.level;
    this.fogImgs.forEach((f, i) => {
      f.x -= (w.ship.speed * 30 + 10 + i * 3) * dt;
      if (f.x < VX0 - 700) f.x = VX1 + 700;
      f.y = 120 + i * 120 + Math.sin(t * 0.2 + i) * 30;
      f.setAlpha(fog * (0.55 + 0.2 * Math.sin(t * 0.3 + i)));
    });
    // flash (lightning, phase changes)
    this.flashA = Math.max(0, this.flashA - dt * 3.2);
    this.flashRect.setAlpha(this.flashA);
    const L = w.storm.lightning;
    if (L) this.flashRect.setAlpha(Math.max(this.flashA, Math.random() < 0.15 ? 0.12 : 0));
    // lightning bolt line
    const g = this.aimGfx;
    if (this.lightningLine) {
      this.lightningLine.t -= dt;
      const ll = this.lightningLine;
      const p = this.ws(ll.x, ll.y, 0);
      g.lineStyle(5, 0xffffff, Math.max(0, ll.t * 5));
      let x = p.x + 60, y = -10;
      g.beginPath().moveTo(x, y);
      for (let i = 1; i <= 8; i++) { x = p.x + 60 * (1 - i / 8) + (Math.random() - 0.5) * 40; y = (p.y * i) / 8; g.lineTo(x, y); }
      g.strokePath();
      if (ll.t <= 0) this.lightningLine = null;
    }
    if (L) {
      // warn mark where it will strike
      const loc = L.onDeck ? this.shipLocalToScreen(L.x, L.y) : this.ws(L.x, L.y);
      g.lineStyle(3, 0xfff2a0, 0.5 + Math.sin(t * 30) * 0.4).strokeEllipse(loc.x, loc.y, 60, 34);
    }
    // incoming wave slam: a white crest line on that side
    if (this.slamWarn) {
      this.slamWarn.t += dt;
      const side = this.slamWarn.side;
      const yy = this.ws(0, w.ship.y + side * (9 - this.slamWarn.t * 5)).y;
      g.lineStyle(6, 0xffffff, 0.7).beginPath();
      for (let x = 200; x <= 1400; x += 40) { const q = yy + Math.sin(x * 0.03 + t * 4) * 6; if (x === 200) g.moveTo(x, q); else g.lineTo(x, q); }
      g.strokePath();
      if (this.slamWarn.t > 1.2) this.slamWarn = null;
    }
  }

  private wakeT = 0;
  private renderWake(dt: number): void {
    const w = this.sim.w;
    const s = w.ship;
    if (s.sinking >= 0) return;
    const rate = (this.quality === 'low' ? 10 : this.quality === 'medium' ? 22 : 36) * Math.min(1.4, s.speed / 3 + 0.2);
    this.wakeT += dt * rate;
    while (this.wakeT >= 1) {
      this.wakeT -= 1;
      const r = Math.random();
      let x: number, y: number;
      if (r < 0.3) { x = 7.9 + Math.random() * 0.4; y = (Math.random() - 0.5) * 1.2; }
      else if (r < 0.75) { x = -8 + Math.random() * 14; y = -3.6 - Math.random() * 0.3; }
      else { x = -8 + Math.random() * 13; y = 3.6 + Math.random() * 0.3; }
      this.spawnPart('fx:foam', x, s.y + y, 0, -s.speed * 0.15 + (Math.random() - 0.5) * 0.4, Math.sign(y) * (0.3 + Math.random() * 0.5), 1.3 + Math.random(), 0.55, 1.1, 0.75, 0, 0, 'world', true);
    }
  }

  // ---- particles ------------------------------------------------------------------------------------
  private spawnPart(key: string, x: number, y: number, z: number, vx: number, vy: number, life: number, s0: number, s1: number, a0: number, vz = 0, g = 0, mode: 'world' | 'screen' = 'world', flow = false, tint?: number, add = false): void {
    const cap = this.quality === 'low' ? 160 : this.quality === 'medium' ? 320 : 520;
    if (this.parts.length >= cap) return;
    const img = this.partPool.pop() ?? this.add.image(0, 0, key);
    if (key === 'fx:foam' && hasFrameIn(this, 'env', 'foam_0')) { img.setTexture('env', `foam_${(Math.random() * 4) | 0}`); s0 *= 0.6; s1 *= 0.6; }
    else img.setTexture(key);
    img.setVisible(true).setActive(true).setOrigin(0.5);
    img.setBlendMode(add ? Phaser.BlendModes.ADD : Phaser.BlendModes.NORMAL);
    if (tint !== undefined) img.setTint(tint); else img.clearTint();
    img.setDepth(key === 'fx:foam' ? D.crest + 1 : D.fx);
    this.parts.push({ img, x, y, z, vx: flow ? vx - this.sim.w.ship.speed : vx, vy, vz, life, max: life, s0, s1, a0, g, mode, spin: (Math.random() - 0.5) * 4 });
  }

  private updateParts(dt: number): void {
    const out: Part[] = [];
    for (const p of this.parts) {
      p.life -= dt;
      if (p.life <= 0) { p.img.setVisible(false).setActive(false); this.partPool.push(p.img); continue; }
      p.x += p.vx * dt;
      p.y += p.vy * dt;
      p.vz -= p.g * dt;
      p.z = Math.max(0, p.z + p.vz * dt);
      const u = 1 - p.life / p.max;
      if (p.mode === 'world') { const q = this.ws(p.x, p.y, p.z); p.img.setPosition(q.x, q.y); }
      else p.img.setPosition(p.x, p.y);
      p.img.setScale(p.s0 + (p.s1 - p.s0) * u).setAlpha(p.a0 * (1 - u)).setRotation(p.img.rotation + p.spin * dt);
      out.push(p);
    }
    this.parts = out;
    const keep: Num[] = [];
    for (const n of this.nums) {
      n.life -= dt;
      if (n.life <= 0) { n.t.destroy(); continue; }
      n.y -= dt * 40;
      n.t.setPosition(n.x, n.y).setAlpha(Math.min(1, n.life * 2));
      keep.push(n);
    }
    this.nums = keep;
  }

  private burst(x: number, y: number, z: number, n: number, color: number, speed = 3, key = 'fx:star', life = 0.7): void {
    const k = this.quality === 'low' ? 0.5 : this.quality === 'medium' ? 0.75 : 1;
    for (let i = 0; i < Math.round(n * k); i++) {
      const a = Math.random() * Math.PI * 2, sp = speed * (0.4 + Math.random() * 0.8);
      this.spawnPart(key, x, y, z, Math.cos(a) * sp, Math.sin(a) * sp * 0.8, life * (0.6 + Math.random() * 0.6), 0.9, 0.2, 1, 2 + Math.random() * 3, 6, 'world', false, color, true);
    }
  }

  private ringFx(x: number, y: number, color: number, size = 2.5): void {
    this.spawnPart('fx:ring', x, y, 0.4, 0, 0, 0.45, 0.2, size, 0.9, 0, 0, 'world', false, color, true);
  }

  private number(x: number, y: number, z: number, text: string, color: string): void {
    const p = this.ws(x, y, z);
    const t = this.add.text(p.x, p.y, text, { fontFamily: FONT, fontSize: '20px', fontStyle: 'bold', color, stroke: '#1a1030', strokeThickness: 4 }).setOrigin(0.5).setDepth(D.bubble + 1);
    this.nums.push({ t, x: p.x, y: p.y, life: 0.8 });
  }

  private shipLocalToScreen(x: number, y: number, z = 0): { x: number; y: number } {
    const p = project(x, y, z);
    const m = this.shipC.getWorldTransformMatrix();
    const q = m.transformPoint(p.sx, p.sy);
    return { x: q.x, y: q.y };
  }

  private shake(amount: number): void {
    if (amount <= 0) return;
    this.cameras.main.shake(140 + amount * 200, 0.002 + amount * 0.006);
  }

  // ---- events -----------------------------------------------------------------------------------------
  private handleEvents(evs: SimEvent[]): void {
    const w = this.sim.w;
    const bus = this.bus;
    const nodeId = this.cfg.nodeId;
    for (const e of evs) {
      switch (e.e) {
        case 'sfx': bus.emit('audio:sfx', e.x === undefined ? { name: e.name } : { name: e.name, pan: Math.max(-1, Math.min(1, e.x / 12)) }); break;
        case 'toast': bus.emit('voyage:toast', { text: e.text, kind: e.kind ?? 'info' }); break;
        case 'hint': bus.emit('voyage:hint', { text: e.text }); break;
        case 'pickup':
          bus.emit('voyage:pickup', { kind: e.kind, amount: e.amount });
          if (e.kind === 'coins') this.burst(e.x, e.y, 0.5, 4, 0xffd65a, 1.5, 'fx:star', 0.4);
          else this.ringFx(e.x, e.y, 0x8fe0ff, 3);
          break;
        case 'shot': {
          const st = STATIONS[e.cannon];
          const c = w.cannons[e.cannon];
          const m = { x: st.x + Math.cos(c.aim) * 0.9, y: w.ship.y + st.y + Math.sin(c.aim) * 0.9 };
          const col = this.ammoColor[e.ammo] ?? 0xffffff;
          this.spawnPart('fx:dot', m.x, m.y, MUZZLE_Z, 0, 0, 0.18, 1.5, 3.5, 1, 0, 0, 'world', false, col, true);
          for (let i = 0; i < 4; i++) this.spawnPart('fx:foam', m.x, m.y, MUZZLE_Z, Math.cos(c.aim) * 1.5 + (Math.random() - 0.5), Math.sin(c.aim) * 1.5 + (Math.random() - 0.5), 0.6, 0.4, 1.0, 0.6, 0.5, 0);
          this.shake(0.12);
          break;
        }
        case 'hit': {
          const col = this.ammoColor[e.ammo] ?? 0xffffff;
          if (e.right) {
            this.burst(e.x, e.y, 0.6, 10, col, 3.2);
            this.ringFx(e.x, e.y, col, 2.2);
            this.number(e.x, e.y, 1.6, `+${Math.round(e.dmg * 10) / 10}`, '#ffe066');
            this.hitStop = 0.045;
          } else {
            this.burst(e.x, e.y, 0.6, 5, 0x9a9ab0, 1.6, 'fx:dot', 0.5);
            this.number(e.x, e.y, 1.6, '½', '#c8c8d8');
          }
          break;
        }
        case 'miss':
          for (let i = 0; i < 6; i++) this.spawnPart('fx:foam', e.x, e.y, 0, (Math.random() - 0.5) * 1.5, (Math.random() - 0.5) * 1.5, 0.7, 0.4, 0.9, 0.9, 2.5 + Math.random() * 2, 9, 'world', true);
          break;
        case 'clean': {
          const col = e.boss ? 0xff9ac0 : 0xfff2b0;
          this.burst(e.x, e.y, 0.8, e.boss ? 40 : 18, col, e.boss ? 6 : 4, 'fx:star', 1);
          this.burst(e.x, e.y, 0.8, 8, 0xff6a4a, 2.5, 'fx:glyph', 0.9);
          this.ringFx(e.x, e.y, 0xffffff, e.boss ? 8 : 3.5);
          if (this.anims.exists('cr:clean_burst')) {
            const q = this.ws(e.x, e.y, 0.8);
            const cb = this.add.sprite(q.x, q.y, 'creatures', 'clean_burst_0').setDepth(D.fx + 1).setBlendMode(Phaser.BlendModes.ADD).setScale(e.boss ? 3 : 1.3);
            cb.play('cr:clean_burst');
            cb.once(Phaser.Animations.Events.ANIMATION_COMPLETE, () => cb.destroy());
          }
          this.hitStop = 0.08;
          this.shake(e.boss ? 0.8 : 0.15);
          if (e.uid > 0 && !e.id.startsWith('arm_')) bus.emit('voyage:creature-cleaned', { creatureId: e.id });
          if (e.boss) { bus.emit('voyage:creature-cleaned', { creatureId: e.id }); this.flashA = 0.5; }
          break;
        }
        case 'hullhit': {
          const p = { x: e.x, y: w.ship.y + e.y };
          if (e.shield) this.ringFx(p.x, p.y, 0x7fd0ff, 4);
          else {
            this.burst(p.x, p.y, 0.5, 8, 0x9a6a3a, 3, 'fx:dot', 0.6);
            this.shake(Math.min(0.6, e.dmg / 14));
          }
          break;
        }
        case 'boltpop': this.burst(e.x, e.y, 0.9, 8, 0xff5a8a, 2.5, 'fx:dot', 0.5); break;
        case 'fixed': this.burst(e.x, w.ship.y + e.y, 0.4, 8, e.kind === 'leak' ? 0xffd27a : 0x8fe0ff, 2, 'fx:star', 0.6); break;
        case 'leak': case 'fire': this.burst(e.x, w.ship.y + e.y, 0.3, 6, e.e === 'fire' ? 0xff8a2a : 0x8fd0ff, 2, 'fx:dot', 0.5); break;
        case 'lightning':
          if (!e.warn) {
            this.flashA = 0.75;
            this.lightningLine = { x: e.x, y: e.onDeck ? w.ship.y + e.y : e.y, t: 0.2 };
          }
          break;
        case 'slam':
          if (e.warn) this.slamWarn = { side: e.side, t: 0 };
          else for (let i = 0; i < 26; i++) this.spawnPart('fx:foam', -7 + Math.random() * 14, w.ship.y + e.side * (2 + Math.random() * 2), 0.5, 0, -e.side * 2, 0.9, 0.6, 1.4, 0.9, 2 + Math.random() * 2, 7, 'world');
          break;
        case 'splash':
          for (let i = 0; i < 10; i++) this.spawnPart('fx:foam', e.x, e.local ? w.ship.y + e.y : e.y, 0, (Math.random() - 0.5) * 2, (Math.random() - 0.5) * 2, 0.8, 0.4, 1.1, 0.9, 3 + Math.random() * 2, 9, 'world', true);
          break;
        case 'phase':
          bus.emit('voyage:boss-phase', { phase: e.phase });
          this.flashA = 0.45;
          this.shake(0.6);
          break;
        case 'shake': this.shake(e.amount); break;
        case 'arrive': bus.emit('voyage:arrive', { nodeId }); break;
        case 'sunk':
          this.ended = true;
          bus.emit('voyage:prompt', null);
          bus.emit('voyage:sunk', { nodeId });
          break;
        case 'done':
          this.ended = true;
          bus.emit('voyage:prompt', null);
          bus.emit('voyage:hud', this.sim.hud());
          bus.emit('voyage:node-done', { nodeId, stats: this.sim.stats() });
          break;
        default: break;
      }
    }
  }
}

// ---- helpers ---------------------------------------------------------------------------------------------
function hasFrameIn(scene: Phaser.Scene, atlas: string, frame: string): boolean {
  return scene.textures.exists(atlas) && scene.textures.get(atlas).has(frame);
}
function hasShipFrame(scene: Phaser.Scene, f: string): boolean {
  return hasFrameIn(scene, 'ship', f);
}

/** Minimal ship-part placeholders (the ship atlas exists; these only cover a missing file). */
function shipPh(scene: Phaser.Scene, frame: string): void {
  const key = 'ph:' + frame;
  if (scene.textures.exists(key)) return;
  const tex = (w: number, h: number, ox: number, oy: number, draw: (c: CanvasRenderingContext2D, w: number, h: number) => void): void => {
    const t = scene.textures.createCanvas(key, w, h);
    if (!t) return;
    draw(t.getContext(), w, h);
    t.refresh();
    const f = t.get();
    f.customPivot = true; f.pivotX = ox; f.pivotY = oy;
  };
  if (frame === 'hull') {
    tex(980, 300, 490 / 980, 150 / 300, (c) => {
      c.translate(490, 150);
      const pt = (x: number, y: number, z: number): [number, number] => [x * PX_PER_M, -y * PY - z * PZ];
      c.fillStyle = '#6a4024'; c.beginPath();
      for (let x = -8; x <= 8; x += 0.25) { const [a, b] = pt(x, -halfBeam(x), -1.2); c.lineTo(a, b); }
      for (let x = 8; x >= -8; x -= 0.25) { const [a, b] = pt(x, -halfBeam(x), 0); c.lineTo(a, b); }
      c.fill();
      c.fillStyle = '#c99a5e'; c.strokeStyle = '#4a2a14'; c.lineWidth = 3; c.beginPath();
      for (let x = -8; x <= 8; x += 0.25) { const [a, b] = pt(x, halfBeam(x), 0); c.lineTo(a, b); }
      for (let x = 8; x >= -8; x -= 0.25) { const [a, b] = pt(x, -halfBeam(x), 0); c.lineTo(a, b); }
      c.closePath(); c.fill(); c.stroke();
    });
  } else if (frame === 'ball') {
    tex(28, 28, 0.5, 0.5, (c) => { c.fillStyle = '#f4f4f4'; c.strokeStyle = '#333'; c.lineWidth = 2; c.beginPath(); c.arc(14, 14, 11, 0, 7); c.fill(); c.stroke(); });
  } else if (frame.startsWith('sail')) {
    tex(400, 300, 0.4, 1.1, (c) => { c.fillStyle = 'rgba(245,240,225,.95)'; c.beginPath(); c.moveTo(160, 20); c.lineTo(380, 280); c.lineTo(40, 280); c.closePath(); c.fill(); });
  } else {
    tex(40, 40, 0.5, 0.8, (c) => { c.fillStyle = '#9a6a3a'; c.strokeStyle = '#3a2210'; c.lineWidth = 2; c.fillRect(6, 10, 28, 26); c.strokeRect(6, 10, 28, 26); });
  }
}
