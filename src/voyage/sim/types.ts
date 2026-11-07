import type { AmmoId, CreatureDef } from '../contract';
import type { CannonId, StationId } from './layout';

export type ItemKind = 'ball' | 'plank' | 'bucket';

export interface Held { kind: ItemKind; ammo?: AmmoId; full?: boolean }

/** A loose item on the deck or flying through the air (ship-local coordinates). */
export interface LooseItem extends Held {
  uid: number;
  x: number; y: number; z: number;
  vx: number; vy: number; vz: number;
  /** player index that threw it (-1 none) */
  from: number;
  /** seconds since it came to rest */
  rest: number;
  /** carried by Bit */
  bit?: boolean;
}

export type Facing = 'S' | 'SW' | 'W' | 'NW' | 'N' | 'NE' | 'E' | 'SE';

export interface Player {
  idx: number;
  x: number; y: number;
  vx: number; vy: number;
  face: number;              // facing angle (rad, ship-local)
  held: Held | null;
  /** station the player is operating (helm or a cannon) */
  at: 'wheel' | CannonId | null;
  /** current hold-to-repair job */
  job: { kind: 'leak' | 'fire'; uid: number; t: number; need: number } | null;
  walk: number;              // walk animation phase
  stepT: number;
}

export interface Cannon {
  id: CannonId;
  aim: number;               // absolute angle (ship-local == world, ship never yaws)
  loaded: AmmoId | null;
  loadT: number;             // seconds left until ready (0 = ready if loaded)
  jam: number;               // uid of a boarded creature jamming it (0 = none)
  recoil: number;            // 0..1 display
  fireCd: number;
}

export interface RackSlot { ammo: AmmoId; has: boolean; refill: number }

export interface Leak { uid: number; x: number; y: number; size: number; age: number }
export interface Fire { uid: number; x: number; y: number; level: number; spreadT: number }

export type CreatureState = 'enter' | 'act' | 'telegraph' | 'attack' | 'recover' | 'board' | 'deck' | 'cleaned' | 'flee' | 'gone';

export interface Creature {
  uid: number;
  def: CreatureDef;
  /** world-relative position (x along the travel axis with the ship at x = 0; y world lateral) */
  x: number; y: number; z: number;
  vx: number; vy: number;
  hp: number; maxHp: number;
  r: number;                 // hit radius (m)
  rx: number; ry: number;    // ellipse semi-axes (m)
  maxSpeed: number;
  state: CreatureState;
  t: number;                 // time in state
  cd: number;                // attack cooldown
  ang: number;               // orbit phase etc.
  side: number;              // +1 far side, -1 near side
  attack: 'bolt' | 'charge' | 'shock' | 'peck' | 'board' | null;
  tx: number; ty: number;    // attack target
  group: number;
  /** ship-local deck position while boarded */
  dx: number; dy: number;
  jamming: CannonId | null;
  stun: number;
  hitFlash: number;
  face: number;              // -1 left, +1 right
  wave: number;              // spawned in wave n
  friendly: boolean;         // already friendly (island visitor)
  hostile: boolean;          // counts for clearing
}

export interface Projectile {
  uid: number;
  ammo: AmmoId;
  x: number; y: number;      // world-relative
  vx: number; vy: number;
  t: number; T: number;      // age, total flight time
  z0: number;
  cannon: CannonId;
  power: number;
  prevX: number; prevY: number;
}

export interface Bolt { uid: number; x: number; y: number; vx: number; vy: number; t: number; life: number; from: number }

export type FloatKind = 'crate' | 'bottle' | 'reef' | 'coin' | 'island' | 'cove' | 'lighthouse' | 'pier' | 'buoy' | 'whirlpool';
export interface Floater {
  uid: number;
  kind: FloatKind;
  x: number; y: number;
  vx: number; vy: number;
  r: number;
  variant: number;
  /** crate contents / coin value / bottle id */
  value: number;
  tag: string;
  t: number;
  alive: boolean;
  /** static in the water (scrolls past) vs. moving with the ship (coins) */
  anchored: boolean;
}

export interface Lightning { warn: number; x: number; y: number; onDeck: boolean; uid: number }
export interface WaveSlam { warn: number; side: number; uid: number }

export interface BossArm {
  uid: number;
  slot: number;
  weakness: AmmoId;
  symptom: string;
  hint: string;
  hp: number; maxHp: number;
  /** position of the hittable tip (world-relative) */
  x: number; y: number;
  baseX: number; baseY: number; // relative to the ship center
  state: 'under' | 'rise' | 'idle' | 'telegraph' | 'slam' | 'hurt' | 'calm';
  t: number;
  cd: number;
  rise: number;              // 0..1 out of the water
  sway: number;
  hitFlash: number;
}

export interface Boss {
  phase: 0 | 1 | 2 | 3;      // 0 = intro, 3 = last; after the last phase: friendly
  arms: BossArm[];
  queue: { weakness: AmmoId; symptom: string; hint: string }[];
  x: number; y: number;      // head position (relative X, world Y)
  t: number;
  calm: number;              // seconds of calm between phases
  friendly: boolean;
  hp: number; maxHp: number;
  roarT: number;
  spitT: number;
}

export type SimEvent =
  | { e: 'sfx'; name: string; x?: number }
  | { e: 'shot'; uid: number; cannon: CannonId; ammo: AmmoId }
  | { e: 'hit'; x: number; y: number; right: boolean; dmg: number; target: number; ammo: AmmoId }
  | { e: 'miss'; x: number; y: number }
  | { e: 'clean'; uid: number; id: string; x: number; y: number; boss?: boolean }
  | { e: 'hint'; text: string }
  | { e: 'toast'; text: string; kind?: 'info' | 'good' | 'bad' }
  | { e: 'pickup'; kind: string; amount: number; x: number; y: number }
  | { e: 'hullhit'; dmg: number; x: number; y: number; shield?: boolean }
  | { e: 'telegraph'; uid: number; attack: string }
  | { e: 'bolt'; uid: number }
  | { e: 'boltpop'; x: number; y: number }
  | { e: 'leak'; x: number; y: number }
  | { e: 'fire'; x: number; y: number }
  | { e: 'fixed'; kind: 'leak' | 'fire'; x: number; y: number }
  | { e: 'lightning'; x: number; y: number; onDeck: boolean; warn: boolean }
  | { e: 'slam'; side: number; warn: boolean }
  | { e: 'board'; uid: number }
  | { e: 'splashOff'; uid: number }
  | { e: 'phase'; phase: number }
  | { e: 'bossFriend' }
  | { e: 'splash'; x: number; y: number; local: boolean }
  | { e: 'arrive' }
  | { e: 'done' }
  | { e: 'sunk' }
  | { e: 'sinking' }
  | { e: 'bottle'; id: string }
  | { e: 'rackSwap' }
  | { e: 'shake'; amount: number };

export type StationUse = StationId | 'item' | 'leak' | 'fire' | 'creature' | 'leave' | 'drop' | null;
