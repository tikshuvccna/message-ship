/**
 * All the sound of the game, made in the browser (no files to download): a generative sea score that changes with
 * the place (calm sea, battle, storm, lighthouse, lesson, boss), and small synthesized effects. Music and effects have their own volume and their own off switch.
 */
export type Mood =
  | 'menu' | 'chart' | 'harbour' | 'lighthouse' | 'lesson' | 'game' | 'calm' | 'battle' | 'storm' | 'island' | 'boss' | 'ending';

export interface SoundSettings { musicOn: boolean; sfxOn: boolean; musicVol: number; sfxVol: number }

interface MoodDef {
  /** Semitone steps above the root that the tune walks on. */
  scale: number[];
  root: number;
  bpm: number;
  /** Chord roots (semitones) the pad cycles through, each as a triad of the scale. */
  chords: number[][];
  /** Chance that a beat plays a note. */
  density: number;
  voice: 'pluck' | 'bell' | 'soft' | 'box';
  /** Octave shift of the tune. */
  octave: number;
  pad: number;
  /** 0 none; low rumble/pulse for tension. */
  pulse?: number;
  noise?: { kind: 'wind' | 'waves'; level: number };
  /** Music that must not pull attention (lessons, tasks) is played at this share of the music volume. */
  share: number;
}

const MAJ_PENT = [0, 2, 4, 7, 9];
const MIN_PENT = [0, 3, 5, 7, 10];

export const MOODS: Record<Mood, MoodDef> = {
  menu: { scale: MAJ_PENT, root: 196, bpm: 64, chords: [[0, 4, 7], [-3, 0, 4], [5, 9, 12], [-5, -1, 2]], density: 0.4, voice: 'bell', octave: 1, pad: 0.6, noise: { kind: 'waves', level: 0.02 }, share: 1 },
  chart: { scale: MAJ_PENT, root: 220, bpm: 72, chords: [[0, 4, 7], [-3, 0, 4], [-5, -1, 2], [0, 4, 7]], density: 0.45, voice: 'pluck', octave: 0, pad: 0.5, noise: { kind: 'waves', level: 0.015 }, share: 0.9 },
  harbour: { scale: [0, 2, 4, 5, 7, 9, 10], root: 261.6, bpm: 88, chords: [[0, 4, 7], [5, 9, 12], [10, 14, 17], [0, 4, 7]], density: 0.55, voice: 'box', octave: 0, pad: 0.3, noise: { kind: 'waves', level: 0.025 }, share: 0.9 },
  lighthouse: { scale: MAJ_PENT, root: 174.6, bpm: 56, chords: [[0, 7, 12], [-3, 4, 9], [-5, 2, 7], [0, 7, 12]], density: 0.25, voice: 'bell', octave: 1, pad: 0.7, noise: { kind: 'wind', level: 0.015 }, share: 0.85 },
  lesson: { scale: MAJ_PENT, root: 220, bpm: 56, chords: [[0, 7, 12], [-3, 4, 9], [-5, 2, 7], [0, 7, 12]], density: 0.07, voice: 'soft', octave: 1, pad: 0.45, share: 0.4 },
  game: { scale: MAJ_PENT, root: 261.6, bpm: 108, chords: [[0, 4, 7], [-3, 0, 4], [5, 9, 12], [-5, -1, 2]], density: 0.55, voice: 'pluck', octave: 1, pad: 0.25, share: 0.6 },
  calm: { scale: MAJ_PENT, root: 246.9, bpm: 76, chords: [[0, 4, 7], [-3, 0, 4], [5, 9, 12], [-5, -1, 2]], density: 0.5, voice: 'pluck', octave: 0, pad: 0.55, noise: { kind: 'waves', level: 0.035 }, share: 1 },
  island: { scale: [0, 2, 4, 6, 7, 9, 11], root: 293.7, bpm: 66, chords: [[0, 4, 7], [2, 6, 9], [4, 7, 11], [0, 4, 7]], density: 0.45, voice: 'soft', octave: 0, pad: 0.5, noise: { kind: 'waves', level: 0.03 }, share: 1 },
  battle: { scale: MIN_PENT, root: 164.8, bpm: 112, chords: [[0, 7, 12], [-2, 5, 10], [-4, 3, 8], [-2, 5, 10]], density: 0.55, voice: 'pluck', octave: 1, pad: 0.4, pulse: 0.35, noise: { kind: 'waves', level: 0.03 }, share: 0.9 },
  storm: { scale: [0, 1, 3, 5, 6, 8], root: 146.8, bpm: 96, chords: [[0, 6, 11], [1, 6, 10], [0, 6, 11], [-1, 5, 10]], density: 0.3, voice: 'bell', octave: 1, pad: 0.8, pulse: 0.45, noise: { kind: 'wind', level: 0.05 }, share: 0.9 },
  boss: { scale: MIN_PENT, root: 130.8, bpm: 120, chords: [[0, 7, 12], [-2, 5, 10], [-4, 3, 8], [-2, 5, 10]], density: 0.6, voice: 'pluck', octave: 1, pad: 0.55, pulse: 0.55, noise: { kind: 'wind', level: 0.03 }, share: 0.95 },
  ending: { scale: MAJ_PENT, root: 261.6, bpm: 70, chords: [[0, 4, 7], [5, 9, 12], [-3, 0, 4], [0, 4, 7]], density: 0.45, voice: 'bell', octave: 0, pad: 0.65, noise: { kind: 'waves', level: 0.02 }, share: 1 },
};

export type Sfx =
  | 'click' | 'good' | 'bad' | 'win' | 'talk' | 'coin' | 'prize'
  | 'shot' | 'hit_right' | 'hit_wrong' | 'clean' | 'pickup' | 'drop' | 'load' | 'splash' | 'wave_slam' | 'thunder'
  | 'fire' | 'extinguish' | 'plank' | 'creak' | 'step' | 'kraken_roar' | 'reef_hit' | 'bolt' | 'alarm' | 'fanfare';

const DEFAULTS: SoundSettings = { musicOn: true, sfxOn: true, musicVol: 0.5, sfxVol: 0.8 };

const mtof = (root: number, semis: number): number => root * Math.pow(2, semis / 12);

export class AudioHub {
  private ctx: AudioContext | null = null;
  private master!: GainNode;
  private musicBus!: GainNode;
  private sfxBus!: GainNode;
  private delay!: DelayNode;
  private noiseBuf: AudioBuffer | null = null;
  settings: SoundSettings = { ...DEFAULTS };
  private moodNow: Mood | null = null;
  private layer: { stop(): void; gain: GainNode } | null = null;
  // what decides the mood, strongest first
  private base: Mood = 'menu';
  private overlays: Mood[] = [];
  private boss = false;
  private held = false;
  private ducked = false;
  /** Moods that have a recorded track in assets/music (listed in index.json); the rest use the generated score. */
  private recorded = new Set<string>();

  configure(s: Partial<SoundSettings>): void {
    this.settings = { ...this.settings, ...s };
    this.applyVolumes();
  }

  /** Browsers only allow sound after a tap: call this from the first click. */
  unlock(): void {
    if (!this.ctx) this.build();
    void this.ctx?.resume();
    this.resolve();
  }

  private build(): void {
    const AC = (window.AudioContext ?? (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext);
    if (!AC) return;
    const ctx = new AC();
    this.ctx = ctx;
    this.master = ctx.createGain();
    // a gentle limiter, so layered notes and effects can never clip
    const limiter = ctx.createDynamicsCompressor();
    limiter.threshold.value = -14;
    limiter.ratio.value = 6;
    this.master.connect(limiter).connect(ctx.destination);
    this.musicBus = ctx.createGain();
    this.sfxBus = ctx.createGain();
    this.musicBus.connect(this.master);
    this.sfxBus.connect(this.master);
    // a soft echo for the music, so a few notes feel like a place
    this.delay = ctx.createDelay(1.5);
    this.delay.delayTime.value = 0.42;
    const fb = ctx.createGain();
    fb.gain.value = 0.32;
    const wet = ctx.createGain();
    wet.gain.value = 0.35;
    this.delay.connect(fb).connect(this.delay);
    this.delay.connect(wet).connect(this.musicBus);
    const len = ctx.sampleRate * 2;
    this.noiseBuf = ctx.createBuffer(1, len, ctx.sampleRate);
    const d = this.noiseBuf.getChannelData(0);
    for (let i = 0; i < len; i++) d[i] = Math.random() * 2 - 1;
    this.applyVolumes();
    this.loadRecorded();
  }

  private applyVolumes(): void {
    if (!this.ctx) return;
    const t = this.ctx.currentTime;
    this.musicBus.gain.setTargetAtTime(this.settings.musicOn && !this.held ? this.settings.musicVol * (this.ducked ? 0.3 : 1) : 0, t, 0.15);
    this.sfxBus.gain.setTargetAtTime(this.settings.sfxOn ? this.settings.sfxVol : 0, t, 0.05);
  }

  // ----- mood: who decides -----
  setBase(m: Mood): void { this.base = m; this.resolve(); }
  pushOverlay(m: Mood): () => void {
    this.overlays.push(m);
    this.resolve();
    return () => { const i = this.overlays.lastIndexOf(m); if (i >= 0) this.overlays.splice(i, 1); this.resolve(); };
  }
  setBoss(on: boolean): void { this.boss = on; this.resolve(); }
  /** Lower the music while a recorded voice line is playing. */
  duck(on: boolean): void { this.ducked = on; this.applyVolumes(); }
  /** Silence the music while a video plays. */
  hold(on: boolean): void { this.held = on; this.applyVolumes(); }

  private resolve(): void {
    const top = this.overlays[this.overlays.length - 1];
    this.playMood(this.boss ? 'boss' : top ?? this.base);
  }

  /** Simple API for the UI: the base mood of the current screen. */
  mood(m: Mood | string): void { if (m in MOODS) this.setBase(m as Mood); }
  setVolumes(): void { this.applyVolumes(); }

  get currentMood(): Mood | null { return this.moodNow; }

  // ----- the score -----
  private wanted: Mood = 'menu';

  private playMood(m: Mood): void {
    this.wanted = m;
    const ctx = this.ctx;
    if (!ctx || m === this.moodNow) return;
    const old = this.layer;
    if (old) {
      old.gain.gain.setTargetAtTime(0, ctx.currentTime, 0.8);
      window.setTimeout(() => old.stop(), 3500);
    }
    this.moodNow = m;
    this.layer = this.recorded.has(m) ? this.startRecorded(m, MOODS[m].share) : this.startLayer(MOODS[m]);
  }

  /** A recorded track for the mood, looped and streamed (not decoded), through the same music bus. */
  private startRecorded(m: Mood, share: number): { stop(): void; gain: GainNode } {
    const ctx = this.ctx as AudioContext;
    const a = new Audio(`${import.meta.env.BASE_URL}assets/music/${m}.mp3`);
    a.loop = true;
    const src = ctx.createMediaElementSource(a);
    const gain = ctx.createGain();
    gain.gain.value = 0;
    gain.gain.setTargetAtTime(share * 0.7, ctx.currentTime, 1.2);
    src.connect(gain).connect(this.musicBus);
    void a.play().catch(() => { /* the generated score is not restarted: the next mood change tries again */ });
    return {
      gain,
      stop: () => { a.pause(); src.disconnect(); gain.disconnect(); },
    };
  }

  /** A short recorded jingle (assets/music/win.mp3) for a finished lesson or game; false when there is none. */
  private jingle(name: string): boolean {
    const ctx = this.ctx;
    if (!ctx || !this.recorded.has(name)) return false;
    const a = new Audio(`${import.meta.env.BASE_URL}assets/music/${name}.mp3`);
    const src = ctx.createMediaElementSource(a);
    src.connect(this.sfxBus);
    void a.play().catch(() => undefined);
    a.addEventListener('ended', () => src.disconnect());
    return true;
  }

  private loadRecorded(): void {
    void fetch(`${import.meta.env.BASE_URL}assets/music/index.json`)
      .then((r) => (r.ok ? (r.json() as Promise<{ ids?: string[] }>) : { ids: [] }))
      .then((j) => {
        this.recorded = new Set(j.ids ?? []);
        // a track that arrived late replaces the generated score that already started
        if (this.moodNow && this.recorded.has(this.moodNow)) { this.moodNow = null; this.resolve(); }
      })
      .catch(() => undefined);
  }

  private startLayer(def: MoodDef): { stop(): void; gain: GainNode } {
    const ctx = this.ctx as AudioContext;
    const gain = ctx.createGain();
    gain.gain.value = 0;
    gain.gain.setTargetAtTime(def.share, ctx.currentTime, 1.2);
    gain.connect(this.musicBus);
    const send = ctx.createGain();
    send.gain.value = 0.55;
    gain.connect(send).connect(this.delay);
    const nodes: AudioNode[] = [gain, send];
    const stops: Array<() => void> = [];
    const beat = 60 / def.bpm;
    let step = 0;
    let chordIdx = 0;
    let next = ctx.currentTime + 0.2;
    let pos = Math.floor(Math.random() * def.scale.length);

    const padChord = (when: number, chord: number[]): void => {
      const len = beat * 8;
      for (const semi of chord) {
        for (const detune of [-6, 6]) {
          const o = ctx.createOscillator();
          o.type = def.voice === 'bell' ? 'sine' : 'triangle';
          o.frequency.value = mtof(def.root / 2, semi);
          o.detune.value = detune;
          const g = ctx.createGain();
          const lp = ctx.createBiquadFilter();
          lp.type = 'lowpass';
          lp.frequency.value = 900;
          g.gain.setValueAtTime(0, when);
          g.gain.linearRampToValueAtTime(0.05 * def.pad, when + len * 0.35);
          g.gain.linearRampToValueAtTime(0, when + len + 1.5);
          o.connect(lp).connect(g).connect(gain);
          o.start(when);
          o.stop(when + len + 1.8);
        }
      }
    };

    const note = (when: number, freq: number, vel: number): void => {
      const o = ctx.createOscillator();
      const g = ctx.createGain();
      const dur = def.voice === 'soft' ? beat * 2.2 : def.voice === 'bell' ? beat * 3 : def.voice === 'box' ? beat * 1.4 : beat * 1.1;
      o.type = def.voice === 'bell' || def.voice === 'box' ? 'sine' : def.voice === 'soft' ? 'triangle' : 'triangle';
      o.frequency.value = freq;
      const peak = 0.11 * vel;
      g.gain.setValueAtTime(0, when);
      g.gain.linearRampToValueAtTime(peak, when + (def.voice === 'soft' ? 0.18 : 0.012));
      g.gain.exponentialRampToValueAtTime(0.0008, when + dur);
      o.connect(g).connect(gain);
      o.start(when);
      o.stop(when + dur + 0.1);
      if (def.voice === 'bell' || def.voice === 'box') {
        const o2 = ctx.createOscillator();
        const g2 = ctx.createGain();
        o2.type = 'sine';
        o2.frequency.value = freq * 2.01;
        g2.gain.setValueAtTime(0, when);
        g2.gain.linearRampToValueAtTime(peak * 0.35, when + 0.01);
        g2.gain.exponentialRampToValueAtTime(0.0005, when + dur * 0.5);
        o2.connect(g2).connect(gain);
        o2.start(when);
        o2.stop(when + dur);
      }
    };

    const pulse = (when: number): void => {
      const o = ctx.createOscillator();
      const g = ctx.createGain();
      o.type = 'sine';
      o.frequency.setValueAtTime(110, when);
      o.frequency.exponentialRampToValueAtTime(48, when + 0.18);
      g.gain.setValueAtTime(0.16 * (def.pulse ?? 0), when);
      g.gain.exponentialRampToValueAtTime(0.001, when + 0.28);
      o.connect(g).connect(gain);
      o.start(when);
      o.stop(when + 0.3);
    };

    if (def.noise && this.noiseBuf) {
      const src = ctx.createBufferSource();
      src.buffer = this.noiseBuf;
      src.loop = true;
      const bp = ctx.createBiquadFilter();
      bp.type = 'lowpass';
      bp.frequency.value = def.noise.kind === 'wind' ? 520 : 900;
      const ng = ctx.createGain();
      ng.gain.value = def.noise.level;
      const lfo = ctx.createOscillator();
      lfo.frequency.value = def.noise.kind === 'wind' ? 0.11 : 0.09;
      const lg = ctx.createGain();
      lg.gain.value = def.noise.level * 0.7;
      lfo.connect(lg).connect(ng.gain);
      src.connect(bp).connect(ng).connect(gain);
      src.start();
      lfo.start();
      stops.push(() => { try { src.stop(); lfo.stop(); } catch { /* already stopped */ } });
    }

    const tick = (): void => {
      // schedule everything that falls in the next second
      while (next < ctx.currentTime + 1.0) {
        if (step % 8 === 0) {
          padChord(next, (def.chords[chordIdx % def.chords.length] as number[]).map((s) => s));
          chordIdx++;
        }
        if (def.pulse && step % 2 === 0) pulse(next);
        if (Math.random() < def.density) {
          // walk gently on the scale: mostly small steps, sometimes a leap
          pos = Math.max(0, Math.min(def.scale.length * 2 - 1, pos + (Math.random() < 0.7 ? (Math.random() < 0.5 ? -1 : 1) : (Math.random() < 0.5 ? -3 : 3))));
          const semis = (def.scale[pos % def.scale.length] as number) + 12 * Math.floor(pos / def.scale.length) + 12 * def.octave;
          note(next, mtof(def.root, semis), 0.55 + Math.random() * 0.45);
        }
        next += beat;
        step++;
      }
    };
    tick();
    const timer = window.setInterval(tick, 400);
    return {
      gain,
      stop: () => {
        window.clearInterval(timer);
        stops.forEach((s) => s());
        for (const n of nodes) { try { n.disconnect(); } catch { /* gone */ } }
      },
    };
  }

  // ----- effects -----
  private tone(freq: number, dur: number, type: OscillatorType, vol: number, when = 0, slideTo?: number): void {
    const ctx = this.ctx;
    if (!ctx || !this.settings.sfxOn) return;
    const t = ctx.currentTime + when;
    const o = ctx.createOscillator();
    const g = ctx.createGain();
    o.type = type;
    o.frequency.setValueAtTime(freq, t);
    if (slideTo) o.frequency.exponentialRampToValueAtTime(slideTo, t + dur);
    g.gain.setValueAtTime(0, t);
    g.gain.linearRampToValueAtTime(vol, t + 0.01);
    g.gain.exponentialRampToValueAtTime(0.0008, t + dur);
    o.connect(g).connect(this.sfxBus);
    o.start(t);
    o.stop(t + dur + 0.05);
  }

  private burst(dur: number, vol: number, from: number, to: number, when = 0): void {
    const ctx = this.ctx;
    if (!ctx || !this.noiseBuf || !this.settings.sfxOn) return;
    const t = ctx.currentTime + when;
    const src = ctx.createBufferSource();
    src.buffer = this.noiseBuf;
    const f = ctx.createBiquadFilter();
    f.type = 'bandpass';
    f.frequency.setValueAtTime(from, t);
    f.frequency.exponentialRampToValueAtTime(to, t + dur);
    const g = ctx.createGain();
    g.gain.setValueAtTime(vol, t);
    g.gain.exponentialRampToValueAtTime(0.001, t + dur);
    src.connect(f).connect(g).connect(this.sfxBus);
    src.start(t);
    src.stop(t + dur + 0.05);
  }

  sfx(name: Sfx | string): void {
    if (!this.ctx || !this.settings.sfxOn) return;
    if (name === 'fanfare' && this.jingle('win')) return;
    switch (name) {
      case 'click': this.tone(660, 0.07, 'triangle', 0.12); break;
      case 'good': [523, 784].forEach((f, i) => this.tone(f, 0.14, 'triangle', 0.15, i * 0.08)); break;
      case 'bad': this.tone(220, 0.25, 'triangle', 0.16, 0, 150); break;
      case 'win': case 'fanfare': [392, 523, 659, 784, 1047].forEach((f, i) => this.tone(f, 0.4, 'triangle', 0.16, i * 0.12)); this.tone(1319, 0.8, 'sine', 0.13, 0.6); break;
      case 'prize': [523, 659, 784, 1047, 1319].forEach((f, i) => this.tone(f, 0.28, 'triangle', 0.17, i * 0.1)); break;
      case 'talk': this.tone(420 + Math.random() * 120, 0.05, 'square', 0.04); break;
      case 'coin': this.tone(1318, 0.09, 'square', 0.07); this.tone(1760, 0.18, 'square', 0.06, 0.07); break;
      case 'shot': this.burst(0.18, 0.22, 1500, 300); this.tone(220, 0.2, 'sine', 0.2, 0, 90); this.tone(1200, 0.25, 'sine', 0.06, 0.02, 1800); break;
      case 'hit_right': this.tone(660, 0.1, 'triangle', 0.18); this.tone(990, 0.16, 'triangle', 0.16, 0.07); this.burst(0.15, 0.08, 4000, 8000); break;
      case 'hit_wrong': this.tone(180, 0.18, 'sawtooth', 0.1, 0, 120); this.burst(0.12, 0.1, 800, 300); break;
      case 'clean': [660, 880, 1100, 1320].forEach((f, i) => this.tone(f, 0.2, 'sine', 0.14, i * 0.06, f * 1.05)); this.burst(0.4, 0.06, 3000, 7000); break;
      case 'pickup': this.tone(784, 0.1, 'sine', 0.18); this.tone(1175, 0.16, 'sine', 0.15, 0.07); break;
      case 'drop': this.tone(300, 0.09, 'triangle', 0.14, 0, 200); break;
      case 'load': this.burst(0.1, 0.14, 600, 300); this.tone(440, 0.08, 'square', 0.06, 0.05); break;
      case 'splash': this.burst(0.35, 0.16, 1200, 400); break;
      case 'wave_slam': this.burst(0.5, 0.28, 600, 120); this.tone(70, 0.45, 'sine', 0.3, 0, 40); break;
      case 'thunder': this.burst(1.2, 0.3, 300, 60); this.tone(55, 1.0, 'sine', 0.3, 0.05, 35); break;
      case 'fire': this.burst(0.3, 0.08, 1500, 700); break;
      case 'extinguish': this.burst(0.5, 0.14, 4000, 900); break;
      case 'plank': this.burst(0.08, 0.14, 700, 400); this.burst(0.08, 0.14, 800, 450, 0.12); this.burst(0.08, 0.14, 700, 400, 0.24); break;
      case 'creak': this.tone(140, 0.5, 'sawtooth', 0.04, 0, 100); break;
      case 'step': this.burst(0.05, 0.05, 500, 300); break;
      case 'kraken_roar': this.tone(80, 1.1, 'sawtooth', 0.22, 0, 45); this.burst(1.0, 0.18, 500, 90); break;
      case 'reef_hit': this.burst(0.4, 0.3, 500, 100); this.tone(95, 0.35, 'triangle', 0.25, 0, 55); break;
      case 'bolt': this.tone(900, 0.18, 'square', 0.05, 0, 300); break;
      case 'alarm': this.tone(300, 0.14, 'square', 0.06); this.tone(300, 0.14, 'square', 0.06, 0.2); break;
    }
  }
}

export const audio = new AudioHub();

