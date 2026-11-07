import type { Bus } from '../core/bus';
import type { HudState, VirtualInput } from '../voyage/contract';
import { btn, h } from './dom';

/** In-voyage overlay: status bars, prompt, toasts, touch joystick and buttons (physical left/right so RTL never swaps them). */
export class Hud {
  readonly root: HTMLElement;
  private hullFill: HTMLElement;
  private waterFill: HTMLElement;
  private progFill: HTMLElement;
  private coinText: HTMLElement;
  private heldChip: HTMLElement;
  private promptEl: HTMLElement;
  private comboEl: HTMLElement;
  private toasts: HTMLElement;
  private bossBar: HTMLElement;
  private bossFill: HTMLElement;
  private joy: HTMLElement;
  private knob: HTMLElement;
  private actionBtn: HTMLButtonElement;
  private throwBtn: HTMLButtonElement;
  private input: VirtualInput = { p: 0, moveX: 0, moveY: 0, action: false, throwIt: false };
  private offs: (() => void)[] = [];
  private lastSend = 0;

  constructor(private bus: Bus, onPause: () => void) {
    const r = (this.root = h('div', 'hud'));
    const top = h('div', 'hud-top');
    const hull = h('div', 'bar hull');
    hull.append(h('span', 'bar-label', 'גוף'));
    const hb = h('div', 'bar-track'); this.hullFill = h('div', 'bar-fill'); hb.appendChild(this.hullFill); hull.appendChild(hb);
    const water = h('div', 'bar water');
    water.append(h('span', 'bar-label', 'מים'));
    const wb = h('div', 'bar-track'); this.waterFill = h('div', 'bar-fill'); wb.appendChild(this.waterFill); water.appendChild(wb);
    const stats = h('div', 'hud-left'); stats.append(hull, water);
    const prog = h('div', 'bar prog');
    const pb = h('div', 'bar-track'); this.progFill = h('div', 'bar-fill'); pb.appendChild(this.progFill); prog.appendChild(pb);
    const right = h('div', 'hud-right');
    const coin = h('div', 'coinpill');
    this.coinText = h('b', null, '0');
    coin.append(h('span', 'coin'), this.coinText);
    right.append(coin, btn('הפסקה', onPause, 'btn small ghost'));
    top.append(stats, prog, right);

    this.bossBar = h('div', 'bossbar hidden');
    this.bossBar.append(h('span', null, 'הקראקן'));
    const bt = h('div', 'bar-track'); this.bossFill = h('div', 'bar-fill'); bt.appendChild(this.bossFill); this.bossBar.appendChild(bt);

    this.heldChip = h('div', 'held hidden');
    this.comboEl = h('div', 'combo hidden');
    this.promptEl = h('div', 'prompt hidden');
    this.toasts = h('div', 'toasts');

    this.joy = h('div', 'joy');
    this.knob = h('div', 'joy-knob');
    this.joy.appendChild(this.knob);
    this.actionBtn = h('button', 'abtn action', 'פעולה', { type: 'button' });
    this.throwBtn = h('button', 'abtn throwit', 'זריקה', { type: 'button' });
    const pad = h('div', 'actions');
    pad.append(this.throwBtn, this.actionBtn);

    r.append(top, this.bossBar, this.heldChip, this.comboEl, this.promptEl, this.toasts, this.joy, pad);
    this.wireJoystick();
    this.wireButton(this.actionBtn, 'action');
    this.wireButton(this.throwBtn, 'throwIt');

    this.offs.push(
      bus.on('voyage:hud', (s) => this.update(s)),
      bus.on('voyage:prompt', (p) => { this.promptEl.textContent = p?.text ?? ''; this.promptEl.classList.toggle('hidden', !p); }),
      bus.on('voyage:toast', (t) => this.toast(t.text, t.kind)),
      bus.on('voyage:hint', (t) => this.toast(t.text, 'info', 3800)),
    );
  }

  mount(parent: HTMLElement): void { parent.appendChild(this.root); }
  destroy(): void { this.offs.forEach((o) => o()); this.root.remove(); }

  update(s: HudState): void {
    this.hullFill.style.width = `${Math.max(0, Math.min(1, s.hull / s.hullMax)) * 100}%`;
    this.hullFill.classList.toggle('low', s.hull / s.hullMax < 0.3);
    this.waterFill.style.width = `${Math.max(0, Math.min(1, s.water)) * 100}%`;
    this.progFill.style.width = `${Math.max(0, Math.min(1, s.progress)) * 100}%`;
    this.coinText.textContent = String(Math.round(s.coins));
    this.heldChip.textContent = s.held ?? '';
    this.heldChip.classList.toggle('hidden', !s.held);
    this.comboEl.textContent = s.combo > 1 ? `קומבו ${s.combo}` : '';
    this.comboEl.classList.toggle('hidden', s.combo <= 1);
    if (s.bossHp !== undefined) { this.bossBar.classList.remove('hidden'); this.bossFill.style.width = `${Math.max(0, s.bossHp) * 100}%`; }
    else this.bossBar.classList.add('hidden');
  }

  toast(text: string, kind: 'info' | 'good' | 'bad' = 'info', ms = 2600): void {
    const t = h('div', `toast ${kind}`, text);
    this.toasts.appendChild(t);
    while (this.toasts.children.length > 3) this.toasts.firstChild?.remove();
    setTimeout(() => t.remove(), ms);
  }

  private send(force = false): void {
    const now = performance.now();
    if (!force && now - this.lastSend < 33) return;
    this.lastSend = now;
    this.bus.emit('ui:input', { ...this.input });
  }

  private wireButton(b: HTMLButtonElement, key: 'action' | 'throwIt'): void {
    const set = (v: boolean) => (e: Event): void => { e.preventDefault(); this.input[key] = v; b.classList.toggle('down', v); this.send(true); };
    b.addEventListener('pointerdown', set(true));
    b.addEventListener('pointerup', set(false));
    b.addEventListener('pointercancel', set(false));
    b.addEventListener('pointerleave', set(false));
  }

  private wireJoystick(): void {
    const j = this.joy;
    let id = -1;
    const R = 46;
    const move = (e: PointerEvent): void => {
      const rect = j.getBoundingClientRect();
      const cx = rect.left + rect.width / 2, cy = rect.top + rect.height / 2;
      let dx = e.clientX - cx, dy = e.clientY - cy;
      const len = Math.hypot(dx, dy);
      if (len > R) { dx = (dx / len) * R; dy = (dy / len) * R; }
      this.knob.style.transform = `translate(${dx}px, ${dy}px)`;
      this.input.moveX = dx / R;
      this.input.moveY = dy / R;
      this.send();
    };
    j.addEventListener('pointerdown', (e) => { id = e.pointerId; j.setPointerCapture(id); move(e); e.preventDefault(); });
    j.addEventListener('pointermove', (e) => { if (e.pointerId === id) move(e); });
    const end = (e: PointerEvent): void => {
      if (e.pointerId !== id) return;
      id = -1;
      this.knob.style.transform = 'translate(0,0)';
      this.input.moveX = 0; this.input.moveY = 0;
      this.send(true);
    };
    j.addEventListener('pointerup', end);
    j.addEventListener('pointercancel', end);
  }
}
