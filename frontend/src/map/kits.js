// Model scale tables for the Kenney kits. Pure data + lookups.

export const KIT = { town: 1.5, chars: 1.4, pirate: 0.45, td: 3, grave: 1.4, survival: 3.5 };
export const MSCALE = {
  'town/fountain-round-detail': 2.6, 'pirate/ship-large': 1.6, 'pirate/ship-pirate-medium': 1.6, 'pirate/ship-ghost': 1.8, 'pirate/ship-wreck': 1.6,
  'pirate/tower-complete-large': 2, 'pirate/castle-wall': 1.6, 'pirate/castle-gate': 1.6, 'pirate/structure-platform-dock': 2,
  'pirate/structure': 2, 'pirate/structure-roof': 2, 'pirate/boat-row-large': 1.3, 'pirate/boat-row-small': 1.3,
  'pirate/palm-straight': 2, 'pirate/palm-bend': 2, 'grave/crypt-large': 1.9, 'grave/column-large': 2.4,
  'grave/altar-stone': 1.6, 'grave/pillar-obelisk': 1.8, 'pirate/grass-plant': 2, 'pirate/grass-patch': 1.8, 'pirate/grass': 2.4,
  'pirate/patch-grass-foliage': 1.4, 'pirate/patch-sand-foliage': 1.2, 'pirate/flag-pennant': 1.6, 'pirate/mast': 1.3,
};
export const NO_SHADOW = new Set(['proc/wheat', 'proc/veg', 'grave/candle-multiple', 'grave/grave', 'grave/grave-border', 'town/road', 'grave/road',
  'survival/grass', 'survival/grass-large', 'pirate/grass', 'pirate/grass-plant', 'pirate/grass-patch', 'pirate/patch-grass-foliage', 'pirate/patch-sand-foliage']);

/** 'td/detail-crystal#glow' -> 'td/detail-crystal' */
export const baseKey = (k) => k.split('#')[0];
export const kitScale = (k) => (KIT[baseKey(k).split('/')[0]] ?? 1) * (MSCALE[baseKey(k)] ?? 1);
