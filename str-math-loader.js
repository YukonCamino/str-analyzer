/* Loads the shared deal maths (str-math.js + settings.json, the same two
   files the Chrome plugin and Zero use) and hands it to the page's own
   script, which does no arithmetic of its own. */
import { analyze, DEFAULT_SETTINGS } from './str-math.js';

let fromFile = {};
try {
  const res = await fetch('./settings.json', { cache: 'no-cache' });
  if (res.ok) fromFile = await res.json();
} catch (e) { /* the copy built into str-math.js is used instead */ }

window.STRMath = { analyze, settings: { ...DEFAULT_SETTINGS, ...fromFile } };
window.dispatchEvent(new Event('strmath-ready'));
