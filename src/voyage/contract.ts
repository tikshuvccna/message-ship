/**
 * Shared contract between the voyage engine (src/voyage, src/scenes/VoyageScene.ts, Opus engine agent),
 * the DOM UI (src/ui, the main session) and the data in content/he/*.json.
 * Keep this file small and stable: both sides import it.
 */

/** Ammo ids. Leg 1 = the five rules, leg 2 = OSI layers, leg 3 = PDU names. */
export type AmmoId =
  | 'addr' | 'code' | 'fmt' | 'size' | 'time'
  | 'l1' | 'l2' | 'l3' | 'l4' | 'l5' | 'l6' | 'l7'
  | 'data' | 'segment' | 'packet' | 'frame' | 'bits';

export type CreatureBehavior =
  | 'orbit'    // circles the ship at a radius and spits noise
  | 'charge'   // slow big charge at the hull
  | 'drift'    // drifts by, shocks when close
  | 'swarm'    // many small ones, fast, weak hits
  | 'skitter'  // crawls on the surface toward the hull and boards it (can be knocked off by a cleaning shot)
  | 'shooter'  // keeps distance, fires noise bolts
  | 'boss';

export interface AmmoDef { id: AmmoId; he: string; color: string; short: string }

export interface CreatureDef {
  id: string;
  he: string;
  leg: 1 | 2 | 3 | 4;           // 4 = boss
  symptom: string;              // short Hebrew line shown above the creature ("ג'יבריש!")
  weakness: AmmoId;             // the correct ammo
  hint: string;                 // shown after a wrong hit (one short Hebrew sentence)
  hp: number;                   // base health (1 correct hit = 2 damage, wrong = 0.5)
  speed: number;                // world px/s
  radius: number;               // hit radius in world px
  behavior: CreatureBehavior;
  coins: number;                // dropped when cleaned
  friend: string;               // Hebrew name of the friendly form shown in the codex
}

export interface VoyageStats {          // computed from upgrades, passed in VoyageConfig
  hullMax: number;                     // base 100
  reloadSec: number;                   // cannon reload, base 1.6
  shotPower: number;                   // multiplier, base 1
  sailSpeed: number;                   // multiplier, base 1
  repairSpeed: number;                 // multiplier, base 1
  lanternRadius: number;               // secret reveal radius px, base 260
  doubleShot: boolean;                 // relic
  shield: boolean;                     // relic: absorbs the next 3 hits
}

export type NodeKind = 'battle' | 'island' | 'event' | 'storm' | 'harbour' | 'lighthouse' | 'boss' | 'start';

export interface VoyageConfig {
  seed: number;
  leg: 1 | 2 | 3 | 4;
  nodeId: string;
  nodeKind: NodeKind;
  look: 'girl' | 'boy';
  playerName: string;
  twoPlayers: boolean;
  stats: VoyageStats;
  ammo: AmmoId[];                      // ammo available on the shelf in this leg
  /** seconds of sailing before the node ends (battle ~75-110, island ~50) */
  duration: number;
  checkpointHull: number;              // hull to start with (0..1 of max)
  quality: 'low' | 'medium' | 'high';
}

export interface HudState {
  hull: number; hullMax: number;       // hull
  water: number;                       // 0..1 flooding
  coins: number;
  progress: number;                    // 0..1 of the node
  held: string | null;                 // carried item label (cannonball name, plank, bucket)
  fires: number; leaks: number;
  wind: number;                        // sail 0..1
  combo: number;
  bossHp?: number;                     // 0..1
}

export interface NodeStats {
  shots: number; hits: number; rightAmmo: number; wrongAmmo: number;
  cleaned: string[];                   // creature ids cleaned
  coins: number; hullLeft: number;
  secondsPlayed: number;
  bottles: string[];                   // message bottle ids picked up
}

export interface VirtualInput {
  p: 0 | 1;                            // player index (0 or 1 in two-player)
  moveX: number; moveY: number;        // -1..1 (deck walk, aim at a cannon, steer at the helm)
  action: boolean;                     // pressed this frame
  throwIt: boolean;
}
