// Transcribed from the labels on the retained public PNGs, not unrounded rates.
// Row-major order: y=0 at the top, x=0 at the defending team's own goal.
// Original mapping: origin/arpit-dev src/metrics/zones.py and src/viz/zone_heatmap.py.
export const SPATIAL_DOMINANCE = {
  psg: { matches: 57, percentages: [58, 44, 31, 75, 56, 33, 58, 44, 29], source: '/team/spatial_Paris_Saint-Germain.png' },
  barca: { matches: 35, percentages: [62, 44, 29, 74, 55, 31, 61, 46, 33], source: '/team/spatial_Barcelona.png' },
  leverkusen: { matches: 31, percentages: [59, 42, 25, 71, 52, 30, 58, 44, 30], source: '/team/spatial_Bayer_Leverkusen.png' },
};

// Use upper/lower channels rather than inventing camera-dependent left/right names.
export const SPATIAL_ZONES = Array.from({ length: 9 }, (_, index) => ({
  id: index + 1,
  row: Math.floor(index / 3),
  column: index % 3,
  name: `${['Defensive', 'Middle', 'Attacking'][index % 3]} ${['upper channel', 'center', 'lower channel'][Math.floor(index / 3)]}`,
}));

// Shared absolute 0–100 scale, including the legend; no per-team rescaling.
export function spatialColor(percentage) {
  const low = [16, 35, 29], high = [57, 255, 136];
  return `rgb(${low.map((value, index) => Math.round(value + (high[index] - value) * percentage / 100)).join(', ')})`;
}

export function spatialLabelColor(percentage) {
  const channels = spatialColor(percentage).match(/\d+/g).map(Number).map((value) => {
    const channel = value / 255;
    return channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4;
  });
  const luminance = channels[0] * 0.2126 + channels[1] * 0.7152 + channels[2] * 0.0722;
  return luminance > 0.179 ? '#000000' : '#ffffff';
}
