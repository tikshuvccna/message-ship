/**
 * Texture resolution with code-drawn placeholders. The renderer always asks `frameOf(scene, atlas, frame)`:
 * if the art atlas is loaded and has that frame, it is used; otherwise a placeholder is drawn once (canvas)
 * under the key `ph:<frame>` with a sensible origin. Real atlases replace placeholders automatically.
 */
import Phaser from 'phaser';
import type { CreatureDef } from '../voyage/contract';

type Draw = (c: CanvasRenderingContext2D, w: number, h: number) => void;

export interface Tex { key: string; frame?: string }

const cache = new Map<string, Tex>();

export function clearTexCache(): void {
  cache.clear();
}

/** Make a canvas texture once; origin (ox, oy) normalised is stored as a custom pivot. */
export function makeTex(scene: Phaser.Scene, key: string, w: number, h: number, draw: Draw, ox = 0.5, oy = 0.5): void {
  if (scene.textures.exists(key)) return;
  const t = scene.textures.createCanvas(key, Math.max(1, Math.ceil(w)), Math.max(1, Math.ceil(h)));
  if (!t) return;
  draw(t.getContext(), t.width, t.height);
  t.refresh();
  const f = t.get();
  f.customPivot = true;
  f.pivotX = ox;
  f.pivotY = oy;
}

export function hasFrame(scene: Phaser.Scene, atlas: string, frame: string): boolean {
  return scene.textures.exists(atlas) && scene.textures.get(atlas).has(frame);
}

/** Resolve a frame from an atlas, falling back to a placeholder generator. */
export function frameOf(scene: Phaser.Scene, atlas: string, frame: string, ph?: () => void): Tex {
  const ck = atlas + '/' + frame;
  const hit = cache.get(ck);
  if (hit) return hit;
  let t: Tex;
  if (hasFrame(scene, atlas, frame)) t = { key: atlas, frame };
  else {
    const key = 'ph:' + frame;
    if (!scene.textures.exists(key)) (ph ?? (() => genericPh(scene, key, frame)))();
    t = { key };
  }
  cache.set(ck, t);
  return t;
}

export function setTex(img: Phaser.GameObjects.Image, t: Tex): void {
  if (img.texture.key !== t.key || (t.frame !== undefined && img.frame.name !== t.frame)) {
    img.setTexture(t.key, t.frame);
    img.setOriginFromFrame();
  }
}

function genericPh(scene: Phaser.Scene, key: string, frame: string): void {
  makeTex(scene, key, 40, 40, (c, w, h) => {
    c.fillStyle = '#c98bff';
    c.strokeStyle = '#2a1a40';
    c.lineWidth = 2;
    c.beginPath();
    c.arc(w / 2, h / 2, w / 2 - 3, 0, 7);
    c.fill();
    c.stroke();
    c.fillStyle = '#2a1a40';
    c.font = 'bold 10px Arial';
    c.textAlign = 'center';
    c.fillText(frame.slice(0, 6), w / 2, h / 2 + 4);
  });
}

// ---- small FX textures (always generated; not part of the art list) --------------------------

const rnd = (s: { v: number }): number => (s.v = (s.v * 16807) % 2147483647) / 2147483647;

export function makeFxTextures(scene: Phaser.Scene): void {
  makeTex(scene, 'fx:dot', 32, 32, (c, w) => {
    const g = c.createRadialGradient(w / 2, w / 2, 0, w / 2, w / 2, w / 2);
    g.addColorStop(0, 'rgba(255,255,255,1)');
    g.addColorStop(0.45, 'rgba(255,255,255,.55)');
    g.addColorStop(1, 'rgba(255,255,255,0)');
    c.fillStyle = g;
    c.fillRect(0, 0, w, w);
  });
  makeTex(scene, 'fx:foam', 48, 30, (c, w, h) => {
    const s = { v: 11 };
    for (let i = 0; i < 9; i++) {
      const x = 8 + rnd(s) * (w - 16), y = 7 + rnd(s) * (h - 14), r = 4 + rnd(s) * 7;
      const g = c.createRadialGradient(x, y, 0, x, y, r);
      g.addColorStop(0, 'rgba(255,255,255,.9)');
      g.addColorStop(1, 'rgba(255,255,255,0)');
      c.fillStyle = g;
      c.beginPath();
      c.ellipse(x, y, r, r * 0.6, 0, 0, 7);
      c.fill();
    }
  });
  makeTex(scene, 'fx:crest', 64, 18, (c, w, h) => {
    c.strokeStyle = 'rgba(255,255,255,.85)';
    c.lineCap = 'round';
    c.lineWidth = 3;
    c.beginPath();
    c.moveTo(4, h - 5);
    c.quadraticCurveTo(w * 0.35, 2, w * 0.6, h - 8);
    c.quadraticCurveTo(w * 0.8, h - 3, w - 4, h - 6);
    c.stroke();
    c.strokeStyle = 'rgba(255,255,255,.35)';
    c.lineWidth = 2;
    c.beginPath();
    c.moveTo(12, h - 2);
    c.quadraticCurveTo(w * 0.4, h - 9, w * 0.7, h - 2);
    c.stroke();
  });
  makeTex(scene, 'fx:ring', 96, 96, (c, w) => {
    c.strokeStyle = '#fff';
    c.lineWidth = 6;
    c.beginPath();
    c.arc(w / 2, w / 2, w / 2 - 5, 0, 7);
    c.stroke();
  });
  makeTex(scene, 'fx:star', 32, 32, (c, w) => {
    c.fillStyle = '#fff';
    c.beginPath();
    for (let i = 0; i < 8; i++) {
      const a = (i * Math.PI) / 4, r = i % 2 ? 4 : 15;
      c.lineTo(w / 2 + Math.cos(a) * r, w / 2 + Math.sin(a) * r);
    }
    c.fill();
  });
  makeTex(scene, 'fx:shadow', 64, 28, (c, w, h) => {
    const g = c.createRadialGradient(w / 2, h / 2, 1, w / 2, h / 2, w / 2);
    g.addColorStop(0, 'rgba(0,10,30,.5)');
    g.addColorStop(1, 'rgba(0,10,30,0)');
    c.fillStyle = g;
    c.save();
    c.scale(1, h / w);
    c.fillRect(0, 0, w, w);
    c.restore();
  });
  makeTex(scene, 'fx:rain', 4, 26, (c, w, h) => {
    const g = c.createLinearGradient(0, 0, 0, h);
    g.addColorStop(0, 'rgba(200,220,255,0)');
    g.addColorStop(1, 'rgba(220,235,255,.8)');
    c.fillStyle = g;
    c.fillRect(1, 0, 2, h);
  });
  makeTex(scene, 'fx:glyph', 20, 24, (c) => {
    c.fillStyle = '#ff6a4a';
    c.font = 'bold 20px Arial';
    c.fillText('#', 2, 19);
  });
  makeTex(scene, 'fx:coin', 22, 22, (c, w) => {
    c.fillStyle = '#ffcf4a';
    c.strokeStyle = '#8a5a12';
    c.lineWidth = 2;
    c.beginPath();
    c.arc(w / 2, w / 2, w / 2 - 2, 0, 7);
    c.fill();
    c.stroke();
    c.fillStyle = '#fff3b0';
    c.beginPath();
    c.arc(w / 2 - 3, w / 2 - 3, 3, 0, 7);
    c.fill();
  }, 0.5, 0.5);
  makeTex(scene, 'fx:fog', 256, 128, (c, w, h) => {
    const s = { v: 5 };
    for (let i = 0; i < 14; i++) {
      const x = 30 + rnd(s) * (w - 60), y = 30 + rnd(s) * (h - 60), r = 30 + rnd(s) * 40;
      const g = c.createRadialGradient(x, y, 0, x, y, r);
      g.addColorStop(0, 'rgba(230,236,245,.35)');
      g.addColorStop(1, 'rgba(230,236,245,0)');
      c.fillStyle = g;
      c.fillRect(0, 0, w, h);
    }
  });
  makeTex(scene, 'fx:vignette', 400, 225, (c, w, h) => {
    const g = c.createRadialGradient(w / 2, h / 2, h * 0.35, w / 2, h / 2, w * 0.62);
    g.addColorStop(0, 'rgba(0,0,0,0)');
    g.addColorStop(1, 'rgba(0,0,0,1)');
    c.fillStyle = g;
    c.fillRect(0, 0, w, h);
  });
}

// ---- sea tiles ------------------------------------------------------------------------------

const SEA_COLORS: Record<string, [string, string, string]> = {
  day: ['#1f7fa8', '#2a93bb', '#7fd3e6'],
  sunset: ['#2a5f8f', '#3a74a0', '#ffc59a'],
  storm: ['#1d3a4f', '#24485f', '#8aa6b8'],
  noise: ['#2a2350', '#352c62', '#c78bff'],
  night: ['#173253', '#1e3f66', '#8fb6e8'],
};

export function seaTile(scene: Phaser.Scene, mood: string): string {
  // art names: day, dusk, storm, noise (sunset -> dusk, night -> dusk/storm)
  const alias: Record<string, string[]> = { sunset: ['sunset', 'dusk'], night: ['night', 'dusk', 'storm'] };
  for (const m of alias[mood] ?? [mood]) if (scene.textures.exists(`sea_tile_${m}`)) return `sea_tile_${m}`;
  const key = `ph:sea_${mood}`;
  const [base, mid, hi] = SEA_COLORS[mood] ?? SEA_COLORS.day!;
  makeTex(scene, key, 256, 256, (c, w, h) => {
    c.fillStyle = base;
    c.fillRect(0, 0, w, h);
    const s = { v: 77 };
    // soft colour blotches (wrapped so the tile is seamless)
    for (let i = 0; i < 26; i++) {
      const x = rnd(s) * w, y = rnd(s) * h, r = 20 + rnd(s) * 46;
      for (const ox of [-w, 0, w]) for (const oy of [-h, 0, h]) {
        const g = c.createRadialGradient(x + ox, y + oy, 0, x + ox, y + oy, r);
        g.addColorStop(0, mid);
        g.addColorStop(1, 'rgba(0,0,0,0)');
        c.globalAlpha = 0.22;
        c.fillStyle = g;
        c.fillRect(x + ox - r, y + oy - r, r * 2, r * 2);
      }
    }
    // little highlight ripples
    c.globalAlpha = 0.28;
    c.strokeStyle = hi;
    c.lineCap = 'round';
    for (let i = 0; i < 34; i++) {
      const x = rnd(s) * w, y = rnd(s) * h, l = 8 + rnd(s) * 18;
      c.lineWidth = 1.5 + rnd(s) * 1.5;
      for (const ox of [-w, 0, w]) for (const oy of [-h, 0, h]) {
        c.beginPath();
        c.moveTo(x + ox, y + oy);
        c.quadraticCurveTo(x + ox + l / 2, y + oy - 3, x + ox + l, y + oy);
        c.stroke();
      }
    }
    c.globalAlpha = 1;
  });
  return key;
}

// ---- creatures --------------------------------------------------------------------------------

function family(id: string): string {
  for (const f of ['squid', 'jelly', 'whale', 'gull', 'bottle', 'crab', 'eel', 'hermit', 'urchin', 'snail', 'pearl', 'barnacle', 'ray', 'turtle', 'swarm', 'kraken']) {
    if (id.includes(f)) return f;
  }
  return 'jelly';
}

function glitch(c: CanvasRenderingContext2D, w: number, h: number, seed: number): void {
  const s = { v: seed };
  const letters = 'אבגדהו#%&?@ABCXZ01';
  c.font = `bold ${Math.max(9, Math.round(w / 9))}px Arial`;
  for (let i = 0; i < 5; i++) {
    c.fillStyle = rnd(s) < 0.5 ? 'rgba(255,90,70,.85)' : 'rgba(90,240,220,.7)';
    c.fillText(letters[Math.floor(rnd(s) * letters.length)] ?? '#', rnd(s) * w * 0.8 + w * 0.05, rnd(s) * h * 0.7 + h * 0.2);
  }
  // slice offsets
  for (let i = 0; i < 3; i++) {
    const y = Math.floor(rnd(s) * h), hh = 2 + Math.floor(rnd(s) * 4);
    const img = c.getImageData(0, y, w, hh);
    c.putImageData(img, Math.round((rnd(s) - 0.5) * 10), y);
  }
}

function eyes(c: CanvasRenderingContext2D, x: number, y: number, r: number, gap: number, friend: boolean): void {
  for (const dx of [-gap, gap]) {
    if (friend) {
      c.fillStyle = '#fff';
      c.beginPath(); c.arc(x + dx, y, r, 0, 7); c.fill();
      c.fillStyle = '#1b1b2e';
      c.beginPath(); c.arc(x + dx, y + r * 0.15, r * 0.62, 0, 7); c.fill();
      c.fillStyle = '#fff';
      c.beginPath(); c.arc(x + dx - r * 0.25, y - r * 0.2, r * 0.25, 0, 7); c.fill();
    } else {
      c.fillStyle = '#ff7a2e';
      c.shadowColor = '#ff4a1a';
      c.shadowBlur = r * 2;
      c.beginPath(); c.ellipse(x + dx, y, r * 0.9, r * 0.55, dx > 0 ? -0.35 : 0.35, 0, 7); c.fill();
      c.shadowBlur = 0;
      c.fillStyle = '#ffe2a0';
      c.beginPath(); c.arc(x + dx, y, r * 0.25, 0, 7); c.fill();
    }
  }
  if (friend) {
    c.fillStyle = 'rgba(255,120,150,.5)';
    for (const dx of [-gap * 1.7, gap * 1.7]) { c.beginPath(); c.ellipse(x + dx, y + r * 1.2, r * 0.6, r * 0.35, 0, 0, 7); c.fill(); }
  }
}

function shade(hex: string, k: number): string {
  const n = parseInt(hex.replace('#', ''), 16);
  const f = (v: number): number => Math.max(0, Math.min(255, Math.round(k < 0 ? v * (1 + k) : v + (255 - v) * k)));
  return `rgb(${f((n >> 16) & 255)},${f((n >> 8) & 255)},${f(n & 255)})`;
}

/** Draw a creature placeholder: noise (dark, glitchy) or friend (bright, cute). */
export function creaturePh(scene: Phaser.Scene, key: string, def: CreatureDef, friend: boolean, frame: number, color: string): void {
  const R = Math.max(22, def.radius);
  const W = R * 2.7, H = R * 2.5;
  makeTex(scene, key, W, H, (c, w, h) => {
    const fam = family(def.id);
    const body = friend ? color : '#2c2346';
    const edge = friend ? shade(color, -0.45) : '#120c22';
    const belly = friend ? shade(color, 0.45) : '#4a3a6e';
    const cx = w / 2, cy = h * 0.5;
    const r = R;
    const bob = frame ? 1 : 0;
    c.lineWidth = Math.max(2, r / 14);
    c.strokeStyle = edge;
    c.fillStyle = body;
    c.lineJoin = 'round';
    const fillStroke = (): void => { c.fill(); c.stroke(); };
    switch (fam) {
      case 'squid': case 'kraken': {
        for (let i = 0; i < 5; i++) {
          const x0 = cx - r * 0.5 + (i * r) / 4;
          c.beginPath();
          c.moveTo(x0 - r * 0.08, cy + r * 0.2);
          c.quadraticCurveTo(x0 + (bob ? 8 : -8), cy + r * 0.9, x0 + (i - 2) * 4, cy + r * 1.15);
          c.lineTo(x0 + r * 0.1, cy + r * 0.2);
          fillStroke();
        }
        c.beginPath(); c.ellipse(cx, cy - r * 0.2, r * 0.6, r * 0.75, 0, 0, 7); fillStroke();
        c.fillStyle = belly; c.beginPath(); c.ellipse(cx - r * 0.15, cy - r * 0.45, r * 0.18, r * 0.3, -0.3, 0, 7); c.fill();
        eyes(c, cx, cy - r * 0.1, r * 0.17, r * 0.24, friend);
        break;
      }
      case 'jelly': {
        c.strokeStyle = friend ? shade(color, 0.3) : '#6a4a9e';
        c.lineWidth = Math.max(2, r / 10);
        for (let i = 0; i < 5; i++) {
          const x0 = cx - r * 0.5 + (i * r) / 4;
          c.beginPath(); c.moveTo(x0, cy);
          c.bezierCurveTo(x0 + 8, cy + r * 0.4, x0 - 8, cy + r * 0.7, x0 + (bob ? 6 : -6), cy + r);
          c.stroke();
        }
        c.strokeStyle = edge; c.lineWidth = Math.max(2, r / 14);
        c.globalAlpha = friend ? 0.92 : 1;
        c.beginPath(); c.ellipse(cx, cy, r * 0.75, r * 0.6, 0, Math.PI, 0); c.closePath(); fillStroke();
        c.globalAlpha = 1;
        eyes(c, cx, cy - r * 0.2, r * 0.15, r * 0.25, friend);
        break;
      }
      case 'whale': {
        c.beginPath(); c.moveTo(cx - r * 0.95, cy - r * 0.1);
        c.lineTo(cx - r * 1.25, cy - r * (0.55 + bob * 0.08)); c.lineTo(cx - r * 1.15, cy + r * 0.05); c.lineTo(cx - r * 1.25, cy + r * 0.45); c.closePath(); fillStroke();
        c.beginPath(); c.ellipse(cx, cy, r * 1.0, r * 0.62, 0, 0, 7); fillStroke();
        c.fillStyle = belly; c.beginPath(); c.ellipse(cx + r * 0.1, cy + r * 0.25, r * 0.75, r * 0.3, 0, 0, 7); c.fill();
        eyes(c, cx + r * 0.55, cy - r * 0.1, r * 0.11, r * 0.12, friend);
        break;
      }
      case 'gull': {
        const up = bob ? -r * 0.5 : r * 0.1;
        c.beginPath(); c.moveTo(cx, cy); c.quadraticCurveTo(cx - r * 0.6, cy + up - r * 0.2, cx - r * 1.1, cy + up); c.quadraticCurveTo(cx - r * 0.5, cy + r * 0.1, cx, cy + r * 0.15); fillStroke();
        c.beginPath(); c.moveTo(cx, cy); c.quadraticCurveTo(cx + r * 0.6, cy + up - r * 0.2, cx + r * 1.1, cy + up); c.quadraticCurveTo(cx + r * 0.5, cy + r * 0.1, cx, cy + r * 0.15); fillStroke();
        c.fillStyle = friend ? '#fff' : body; c.beginPath(); c.ellipse(cx, cy, r * 0.42, r * 0.32, 0, 0, 7); fillStroke();
        c.fillStyle = '#ffb03a'; c.beginPath(); c.moveTo(cx + r * 0.35, cy); c.lineTo(cx + r * 0.7, cy + r * 0.08); c.lineTo(cx + r * 0.35, cy + r * 0.15); c.fill();
        eyes(c, cx + r * 0.12, cy - r * 0.08, r * 0.12, r * 0.12, friend);
        break;
      }
      case 'bottle': {
        c.save(); c.translate(cx, cy); c.rotate(-0.5 + bob * 0.06);
        c.globalAlpha = 0.95;
        c.beginPath(); c.roundRect(-r * 0.4, -r * 0.55, r * 0.8, r * 1.2, r * 0.25); fillStroke();
        c.beginPath(); c.rect(-r * 0.15, -r * 0.95, r * 0.3, r * 0.42); fillStroke();
        c.fillStyle = '#c8a46a'; c.fillRect(-r * 0.17, -r * 1.05, r * 0.34, r * 0.16);
        c.fillStyle = friend ? '#fff7d8' : '#8a7a5a'; c.fillRect(-r * 0.22, -r * 0.2, r * 0.44, r * 0.5);
        c.restore();
        eyes(c, cx, cy + r * 0.05, r * 0.11, r * 0.15, friend);
        break;
      }
      case 'crab': case 'hermit': {
        c.lineWidth = Math.max(2, r / 10);
        for (let i = 0; i < 3; i++) for (const s2 of [-1, 1]) {
          c.beginPath(); c.moveTo(cx + s2 * r * 0.4, cy + r * 0.1 + i * 6);
          c.lineTo(cx + s2 * r * (0.85 + (bob ? 0.05 : 0)), cy + r * 0.45 + i * 6); c.stroke();
        }
        for (const s2 of [-1, 1]) {
          c.beginPath(); c.ellipse(cx + s2 * r * 0.75, cy - r * 0.35 - bob * 3, r * 0.25, r * 0.2, s2 * 0.5, 0, 7); fillStroke();
        }
        if (fam === 'hermit') {
          c.fillStyle = friend ? shade(color, -0.2) : '#3a2d55';
          c.beginPath(); c.arc(cx - r * 0.1, cy - r * 0.15, r * 0.55, 0, 7); fillStroke();
          c.beginPath(); c.arc(cx - r * 0.1, cy - r * 0.15, r * 0.3, 0, 5); c.stroke();
          c.fillStyle = body;
          c.beginPath(); c.ellipse(cx + r * 0.3, cy + r * 0.1, r * 0.35, r * 0.25, 0, 0, 7); fillStroke();
          eyes(c, cx + r * 0.32, cy + r * 0.02, r * 0.1, r * 0.12, friend);
        } else {
          c.beginPath(); c.ellipse(cx, cy, r * 0.6, r * 0.42, 0, 0, 7); fillStroke();
          if (def.id.includes('paper')) { c.fillStyle = friend ? '#fff' : '#9a8fb0'; c.fillRect(cx - r * 0.3, cy - r * 0.05, r * 0.6, r * 0.25); }
          eyes(c, cx, cy - r * 0.2, r * 0.13, r * 0.2, friend);
        }
        break;
      }
      case 'eel': {
        c.lineWidth = r * 0.42; c.lineCap = 'round'; c.strokeStyle = edge;
        const path = (): void => { c.beginPath(); c.moveTo(cx - r * 1.0, cy + r * 0.3); c.bezierCurveTo(cx - r * 0.4, cy - r * (0.6 + bob * 0.1), cx + r * 0.1, cy + r * 0.7, cx + r * 0.75, cy - r * 0.1); c.stroke(); };
        path(); c.lineWidth = r * 0.32; c.strokeStyle = body; path();
        c.lineWidth = 2; c.strokeStyle = edge; c.fillStyle = body;
        c.beginPath(); c.ellipse(cx + r * 0.8, cy - r * 0.12, r * 0.28, r * 0.22, 0, 0, 7); fillStroke();
        eyes(c, cx + r * 0.85, cy - r * 0.18, r * 0.09, r * 0.1, friend);
        break;
      }
      case 'urchin': {
        c.lineWidth = Math.max(2, r / 12);
        for (let i = 0; i < 18; i++) {
          const a = (i / 18) * Math.PI * 2 + bob * 0.1;
          c.beginPath(); c.moveTo(cx + Math.cos(a) * r * 0.4, cy + Math.sin(a) * r * 0.4); c.lineTo(cx + Math.cos(a) * r * 0.9, cy + Math.sin(a) * r * 0.8); c.stroke();
        }
        c.beginPath(); c.arc(cx, cy, r * 0.5, 0, 7); fillStroke();
        eyes(c, cx, cy - r * 0.05, r * 0.13, r * 0.18, friend);
        break;
      }
      case 'snail': {
        c.beginPath(); c.ellipse(cx + r * 0.1, cy + r * 0.35, r * 0.85, r * 0.22, 0, 0, 7); fillStroke();
        c.fillStyle = friend ? shade(color, -0.2) : '#3a2d55';
        c.beginPath(); c.arc(cx - r * 0.15, cy - r * 0.05, r * 0.5, 0, 7); fillStroke();
        c.beginPath(); c.arc(cx - r * 0.15, cy - r * 0.05, r * 0.25, 0, 5); c.stroke();
        c.strokeStyle = edge; c.beginPath(); c.moveTo(cx + r * 0.65, cy + r * 0.2); c.lineTo(cx + r * 0.8, cy - r * (0.35 + bob * 0.05)); c.stroke();
        eyes(c, cx + r * 0.6, cy + r * 0.2, r * 0.1, r * 0.12, friend);
        break;
      }
      case 'pearl': {
        c.fillStyle = friend ? shade(color, -0.25) : '#3a2d55';
        c.beginPath(); c.ellipse(cx, cy + r * 0.25, r * 0.9, r * 0.35, 0, 0, Math.PI); c.closePath(); fillStroke();
        c.beginPath(); c.ellipse(cx, cy - r * 0.05, r * 0.9, r * 0.5, 0, Math.PI, 0); c.closePath(); fillStroke();
        c.fillStyle = friend ? '#fff8e0' : '#c9b8ff';
        c.beginPath(); c.arc(cx, cy + r * 0.1, r * 0.3, 0, 7); fillStroke();
        eyes(c, cx, cy + r * 0.08, r * 0.08, r * 0.12, friend);
        break;
      }
      case 'barnacle': {
        for (const [dx, s2] of [[-0.45, 0.7], [0.45, 0.75], [0, 1]] as const) {
          c.beginPath(); c.moveTo(cx + (dx - 0.32 * s2) * r, cy + r * 0.45); c.lineTo(cx + (dx - 0.12 * s2) * r, cy + r * (0.45 - 0.9 * s2)); c.lineTo(cx + (dx + 0.12 * s2) * r, cy + r * (0.45 - 0.9 * s2)); c.lineTo(cx + (dx + 0.32 * s2) * r, cy + r * 0.45); c.closePath(); fillStroke();
        }
        eyes(c, cx, cy - r * 0.05, r * 0.11, r * 0.13, friend);
        break;
      }
      case 'ray': {
        c.beginPath(); c.moveTo(cx - r * 0.2, cy); c.quadraticCurveTo(cx - r * 0.9, cy + r * 0.2, cx - r * 1.2, cy + r * 0.05); c.stroke();
        c.beginPath(); c.moveTo(cx + r * 0.6, cy); c.quadraticCurveTo(cx, cy - r * (0.75 + bob * 0.1), cx - r * 0.5, cy); c.quadraticCurveTo(cx, cy + r * (0.75 + bob * 0.1), cx + r * 0.6, cy); fillStroke();
        eyes(c, cx + r * 0.15, cy - r * 0.08, r * 0.1, r * 0.13, friend);
        break;
      }
      case 'turtle': {
        c.fillStyle = friend ? shade(color, -0.1) : '#3c3058';
        for (const [dx, dy] of [[-0.6, -0.45], [0.5, -0.45], [-0.6, 0.45], [0.5, 0.45]] as const) { c.beginPath(); c.ellipse(cx + dx * r, cy + dy * r + (bob ? 2 : -2), r * 0.25, r * 0.13, dx * dy, 0, 7); fillStroke(); }
        c.beginPath(); c.ellipse(cx + r * 0.85, cy - r * 0.05, r * 0.24, r * 0.2, 0, 0, 7); fillStroke();
        c.fillStyle = body; c.beginPath(); c.ellipse(cx, cy, r * 0.7, r * 0.5, 0, 0, 7); fillStroke();
        c.strokeStyle = belly; c.beginPath(); c.moveTo(cx - r * 0.4, cy); c.lineTo(cx + r * 0.4, cy); c.moveTo(cx, cy - r * 0.4); c.lineTo(cx, cy + r * 0.4); c.stroke();
        eyes(c, cx + r * 0.9, cy - r * 0.1, r * 0.07, r * 0.08, friend);
        break;
      }
      case 'swarm': {
        c.font = `bold ${Math.round(r * 0.75)}px Consolas, monospace`;
        c.textAlign = 'center';
        const pts = [[-0.45, -0.2], [0.35, -0.35], [0, 0.25], [-0.35, 0.45], [0.5, 0.3]] as const;
        pts.forEach(([dx, dy], i) => {
          c.fillStyle = friend ? color : i % 2 ? '#ff6a4a' : '#5fe8d0';
          c.fillText(((i + frame) % 2).toString(), cx + dx * r, cy + dy * r + r * 0.25);
        });
        break;
      }
    }
    if (!friend) glitch(c, w, h, 31 + def.id.length * 7 + frame * 13);
    else {
      c.fillStyle = 'rgba(255,255,255,.8)';
      c.beginPath(); c.arc(cx + r * 0.6, cy - r * 0.7, 3, 0, 7); c.arc(cx - r * 0.7, cy - r * 0.4, 2, 0, 7); c.fill();
    }
  }, 0.5, 0.62);
}

// ---- environment ---------------------------------------------------------------------------------

export function envPh(scene: Phaser.Scene, frame: string): () => void {
  const key = 'ph:' + frame;
  return () => {
    const base = frame.replace(/_[a-d0-9]$/, '');
    switch (base) {
      case 'crate_float':
      case 'crate':
        makeTex(scene, key, 64, 60, (c) => {
          c.fillStyle = '#b07a3e'; c.strokeStyle = '#4a2a10'; c.lineWidth = 2.5;
          c.beginPath(); c.moveTo(12, 22); c.lineTo(44, 14); c.lineTo(58, 22); c.lineTo(26, 31); c.closePath(); c.fillStyle = '#d29a55'; c.fill(); c.stroke();
          c.beginPath(); c.moveTo(12, 22); c.lineTo(26, 31); c.lineTo(26, 54); c.lineTo(12, 45); c.closePath(); c.fillStyle = '#9a6430'; c.fill(); c.stroke();
          c.beginPath(); c.moveTo(26, 31); c.lineTo(58, 22); c.lineTo(58, 45); c.lineTo(26, 54); c.closePath(); c.fillStyle = '#b77a3c'; c.fill(); c.stroke();
          c.strokeStyle = '#ffd36a'; c.lineWidth = 3; c.beginPath(); c.moveTo(42, 26); c.lineTo(42, 49); c.stroke();
        }, 0.55, 0.85);
        break;
      case 'bottle':
        makeTex(scene, key, 40, 40, (c) => {
          c.save(); c.translate(20, 24); c.rotate(-1.1);
          c.fillStyle = 'rgba(120,220,170,.85)'; c.strokeStyle = '#1e5a44'; c.lineWidth = 2;
          c.beginPath(); c.roundRect(-7, -11, 14, 22, 5); c.fill(); c.stroke();
          c.fillRect(-3, -18, 6, 8); c.strokeRect(-3, -18, 6, 8);
          c.fillStyle = '#fff4d0'; c.fillRect(-4, -6, 8, 12);
          c.restore();
        }, 0.5, 0.75);
        break;
      case 'reef':
        makeTex(scene, key, 150, 90, (c, w, h) => {
          const s = { v: 3 + frame.length };
          c.fillStyle = 'rgba(255,255,255,.55)';
          c.beginPath(); c.ellipse(w / 2, h * 0.72, w * 0.46, h * 0.2, 0, 0, 7); c.fill();
          for (let i = 0; i < 6; i++) {
            const x = w * 0.2 + rnd(s) * w * 0.6, y = h * 0.62, rw = 14 + rnd(s) * 22, rh = 16 + rnd(s) * 28;
            c.fillStyle = i % 2 ? '#6d6a74' : '#87828c'; c.strokeStyle = '#2c2a33'; c.lineWidth = 2;
            c.beginPath(); c.moveTo(x - rw, y); c.lineTo(x - rw * 0.4, y - rh); c.lineTo(x + rw * 0.3, y - rh * 0.8); c.lineTo(x + rw, y); c.closePath(); c.fill(); c.stroke();
          }
          c.fillStyle = '#e46a8e'; for (let i = 0; i < 5; i++) { c.beginPath(); c.arc(w * 0.25 + rnd(s) * w * 0.5, h * 0.58 + rnd(s) * 6, 3, 0, 7); c.fill(); }
        }, 0.5, 0.72);
        break;
      case 'island':
      case 'cove':
        makeTex(scene, key, 420, 240, (c, w, h) => {
          c.fillStyle = 'rgba(255,255,255,.6)'; c.beginPath(); c.ellipse(w / 2, h * 0.75, w * 0.48, h * 0.17, 0, 0, 7); c.fill();
          c.fillStyle = '#f1d9a0'; c.beginPath(); c.ellipse(w / 2, h * 0.72, w * 0.45, h * 0.15, 0, 0, 7); c.fill();
          c.fillStyle = '#4fa35a'; c.strokeStyle = '#24502c'; c.lineWidth = 3;
          c.beginPath(); c.ellipse(w / 2, h * 0.6, w * 0.36, h * 0.22, 0, Math.PI, 0); c.closePath(); c.fill(); c.stroke();
          for (const px of [0.38, 0.55, 0.66]) {
            c.strokeStyle = '#7a4f2a'; c.lineWidth = 7; c.beginPath(); c.moveTo(w * px, h * 0.6); c.quadraticCurveTo(w * px + 10, h * 0.35, w * px + 4, h * 0.2); c.stroke();
            c.fillStyle = '#3d8f4a'; for (let k = 0; k < 5; k++) { c.beginPath(); c.ellipse(w * px + 4 + Math.cos(k * 1.3) * 20, h * 0.2 + Math.sin(k * 1.3) * 8, 26, 8, k * 1.3, 0, 7); c.fill(); }
          }
        }, 0.5, 0.75);
        break;
      case 'lighthouse_lit':
      case 'lighthouse_unlit':
      case 'lighthouse':
        makeTex(scene, key, 200, 420, (c, w, h) => {
          c.fillStyle = '#8c8a8f'; c.beginPath(); c.ellipse(w / 2, h - 30, 90, 26, 0, 0, 7); c.fill();
          for (let i = 0; i < 6; i++) {
            c.fillStyle = i % 2 ? '#d94f4f' : '#f4efe4';
            const y0 = h - 40 - i * 50, t0 = 40 - i * 3;
            c.beginPath(); c.moveTo(w / 2 - t0, y0); c.lineTo(w / 2 - t0 + 3, y0 - 50); c.lineTo(w / 2 + t0 - 3, y0 - 50); c.lineTo(w / 2 + t0, y0); c.fill();
          }
          c.fillStyle = '#333'; c.fillRect(w / 2 - 28, h - 360, 56, 12);
          c.fillStyle = '#ffe38a'; c.shadowColor = '#ffd04a'; c.shadowBlur = 30; c.fillRect(w / 2 - 20, h - 392, 40, 32); c.shadowBlur = 0;
          c.fillStyle = '#d94f4f'; c.beginPath(); c.moveTo(w / 2 - 28, h - 392); c.lineTo(w / 2, h - 418); c.lineTo(w / 2 + 28, h - 392); c.fill();
        }, 0.5, 0.93);
        break;
      case 'pier':
        makeTex(scene, key, 360, 120, (c, w, h) => {
          c.fillStyle = '#7a5532'; for (let i = 0; i < 8; i++) c.fillRect(20 + i * 44, 40, 10, 70);
          c.fillStyle = '#b48552'; c.strokeStyle = '#4a2f18'; c.lineWidth = 2; c.fillRect(10, 30, w - 20, 22); c.strokeRect(10, 30, w - 20, 22);
        }, 0.5, 0.8);
        break;
      case 'buoy':
        makeTex(scene, key, 40, 64, (c) => {
          c.fillStyle = '#e04a3a'; c.strokeStyle = '#4a1a10'; c.lineWidth = 2;
          c.beginPath(); c.moveTo(8, 50); c.lineTo(14, 16); c.lineTo(26, 16); c.lineTo(32, 50); c.closePath(); c.fill(); c.stroke();
          c.fillStyle = '#fff'; c.fillRect(11, 30, 18, 7);
          c.fillStyle = '#ffe680'; c.beginPath(); c.arc(20, 11, 6, 0, 7); c.fill();
        }, 0.5, 0.8);
        break;
      case 'whirlpool':
        makeTex(scene, key, 360, 210, (c, w, h) => {
          c.translate(w / 2, h / 2); c.scale(1, 0.57);
          for (let i = 0; i < 26; i++) {
            const r = 12 + i * 6.5; c.strokeStyle = `rgba(220,245,255,${0.55 - i * 0.018})`; c.lineWidth = 3;
            c.beginPath(); c.arc(0, 0, r, i * 0.7, i * 0.7 + 3.4); c.stroke();
          }
          c.fillStyle = 'rgba(10,30,60,.55)'; c.beginPath(); c.arc(0, 0, 22, 0, 7); c.fill();
        }, 0.5, 0.5);
        break;
      case 'bolt_noise':
        makeTex(scene, key, 44, 44, (c, w) => {
          const g = c.createRadialGradient(w / 2, w / 2, 2, w / 2, w / 2, w / 2);
          g.addColorStop(0, '#ffd2a0'); g.addColorStop(0.35, '#ff4a6a'); g.addColorStop(0.7, 'rgba(90,30,140,.8)'); g.addColorStop(1, 'rgba(60,20,100,0)');
          c.fillStyle = g; c.fillRect(0, 0, w, w);
          c.fillStyle = '#fff'; c.font = 'bold 13px Arial'; c.fillText('?#', 12, 27);
        });
        break;
      case 'kraken_head':
        makeTex(scene, key, 340, 300, (c, w, h) => {
          c.fillStyle = '#3a2a5c'; c.strokeStyle = '#140b28'; c.lineWidth = 5;
          c.beginPath(); c.ellipse(w / 2, h * 0.48, 130, 120, 0, Math.PI, 0); c.lineTo(w / 2 + 130, h * 0.8); c.lineTo(w / 2 - 130, h * 0.8); c.closePath(); c.fill(); c.stroke();
          c.fillStyle = '#5a4488'; for (let i = 0; i < 6; i++) { c.beginPath(); c.arc(w / 2 - 80 + i * 32, h * 0.3 + (i % 2) * 20, 12, 0, 7); c.fill(); }
          eyes(c, w / 2, h * 0.55, 26, 60, false);
          glitch(c, w, h, 99);
        }, 0.5, 0.8);
        break;
      case 'kraken_head_friend':
        makeTex(scene, key, 340, 300, (c, w, h) => {
          c.fillStyle = '#ff9ac0'; c.strokeStyle = '#8a3a5a'; c.lineWidth = 5;
          c.beginPath(); c.ellipse(w / 2, h * 0.48, 130, 120, 0, Math.PI, 0); c.lineTo(w / 2 + 130, h * 0.8); c.lineTo(w / 2 - 130, h * 0.8); c.closePath(); c.fill(); c.stroke();
          eyes(c, w / 2, h * 0.55, 26, 60, true);
        }, 0.5, 0.8);
        break;
      default:
        genericPh(scene, key, frame);
    }
  };
}

// ---- Bit the lantern and a fallback character --------------------------------------------------------

export function bitPh(scene: Phaser.Scene, frame: number): () => void {
  return () => makeTex(scene, 'ph:bit_' + frame, 52, 60, (c) => {
    const g = c.createRadialGradient(26, 30, 2, 26, 30, 26);
    g.addColorStop(0, 'rgba(255,230,140,.9)'); g.addColorStop(1, 'rgba(255,200,80,0)');
    c.fillStyle = g; c.fillRect(0, 0, 52, 60);
    c.fillStyle = '#c98a2e'; c.strokeStyle = '#5a3610'; c.lineWidth = 2;
    c.fillRect(16, 12, 20, 5); c.strokeRect(16, 12, 20, 5);
    c.beginPath(); c.arc(26, 9, 4, Math.PI, 0); c.stroke();
    c.fillStyle = '#fff2b0'; c.beginPath(); c.roundRect(15, 17, 22, 24, 6); c.fill(); c.stroke();
    c.fillStyle = '#c98a2e'; c.fillRect(17, 41, 18, 5); c.strokeRect(17, 41, 18, 5);
    c.fillStyle = '#2a1a10';
    const blink = frame === 3;
    if (blink) { c.fillRect(20, 27, 4, 1.5); c.fillRect(28, 27, 4, 1.5); }
    else { c.beginPath(); c.arc(22, 27, 2.2, 0, 7); c.arc(30, 27, 2.2, 0, 7); c.fill(); }
    c.beginPath(); c.arc(26, 32 + (frame === 1 ? 1 : 0), 3, 0.2, Math.PI - 0.2); c.stroke();
  }, 0.5, 0.75);
}

export function charPh(scene: Phaser.Scene, key: string, color: string): void {
  makeTex(scene, key, 128, 128, (c) => {
    c.fillStyle = 'rgba(0,0,0,.25)'; c.beginPath(); c.ellipse(64, 110, 18, 6, 0, 0, 7); c.fill();
    c.fillStyle = color; c.strokeStyle = '#1a1a2a'; c.lineWidth = 2.5;
    c.beginPath(); c.moveTo(48, 108); c.lineTo(52, 66); c.lineTo(76, 66); c.lineTo(80, 108); c.closePath(); c.fill(); c.stroke();
    c.fillStyle = '#f2c9a0'; c.beginPath(); c.arc(64, 54, 13, 0, 7); c.fill(); c.stroke();
    c.fillStyle = '#2a4a8a'; c.beginPath(); c.ellipse(64, 44, 20, 6, 0, 0, 7); c.fill(); c.stroke();
    c.beginPath(); c.arc(64, 44, 11, Math.PI, 0); c.fill();
  }, 0.5, 110 / 128);
}
