/** Tiny typed event bus between the Phaser voyage scene and the DOM UI. */
export interface GameEvents {
  /** Voyage -> UI */
  'voyage:hud': import('../voyage/contract').HudState;
  'voyage:prompt': { text: string; id: string } | null;       // contextual action label ("לטעון", "להחזיק הגה")
  'voyage:toast': { text: string; kind?: 'info' | 'good' | 'bad' };
  'voyage:hint': { text: string };                             // short rule hint after a wrong ammo hit
  'voyage:node-done': { nodeId: string; stats: import('../voyage/contract').NodeStats };
  'voyage:sunk': { nodeId: string };
  'voyage:arrive': { nodeId: string };                         // reached a lighthouse/harbour node
  'voyage:creature-cleaned': { creatureId: string };
  'voyage:pickup': { kind: string; amount: number };
  'voyage:fog-warning': { secondsLeft: number };
  'voyage:boss-phase': { phase: number };
  /** UI -> Voyage */
  'ui:pause': { paused: boolean };
  'ui:input': import('../voyage/contract').VirtualInput;     // touch joystick/buttons
  'voyage:start': import('../voyage/contract').VoyageConfig;
  'voyage:quit': undefined;
  'audio:sfx': { name: string; pan?: number };
}

type Handler<T> = (payload: T) => void;

export class Bus {
  private map = new Map<keyof GameEvents, Set<Handler<never>>>();

  on<K extends keyof GameEvents>(k: K, h: Handler<GameEvents[K]>): () => void {
    let s = this.map.get(k);
    if (!s) this.map.set(k, (s = new Set()));
    s.add(h as Handler<never>);
    return () => s?.delete(h as Handler<never>);
  }

  emit<K extends keyof GameEvents>(k: K, payload: GameEvents[K]): void {
    this.map.get(k)?.forEach((h) => (h as Handler<GameEvents[K]>)(payload));
  }
}
