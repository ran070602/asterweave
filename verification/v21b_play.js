'use strict';
/* v21 复核：DOM 驱动辅助（只通过公开 DOM + 事件驱动，不触碰脚本内部变量） */
const fs = require('fs');
const path = require('path');

const SOL = JSON.parse(fs.readFileSync(path.join(__dirname, 'v21b_solution.json'), 'utf8'));
const LV = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'tools', 'levels.json'), 'utf8'));
const SKY = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'tools', 'sky.json'), 'utf8'));

function q(g, s) { return g.doc.querySelector(s); }
function qa(g, s) { return g.doc.querySelectorAll(s); }
function state(g) { return JSON.parse(g.doc.body.dataset.gameState); }
function cells(g) { return g.doc.querySelectorAll('#board .cell'); }
function cellClasses(g) { return cells(g).map(c => c.className); }
function textOf(g, s) { const e = q(g, s); return e ? e.textContent : null; }
function btnLabels(el) { return (el.querySelectorAll ? el.querySelectorAll('button') : el.childNodes.filter(n => n.nodeType === 1 && n.tagName === 'BUTTON')).map(b => b.textContent); }

function closeIntro(g) { const o = q(g, '#introOverlay'); if (o && !o.hidden) g.dispatch(q(g, '#introStart'), 'click', {}); }
function unlockAll(g) { g.dispatch(q(g, '#unlockBtn'), 'click', {}); }
function startLevel(g, li) {
  const btn = g.doc.querySelector('#lvGrid button[data-index="' + li + '"]');
  g.dispatch(btn, 'click', {});
  g.advance(20);
  return cells(g);
}
/* 鼠标左键 = 观测；鼠标右键 = 标记 */
function pressCell(g, el, kind, extra) {
  g.dispatch(el, 'pointerdown', Object.assign({
    pointerType: 'mouse', button: kind === 'flag' ? 2 : 0, clientX: 5, clientY: 5, pointerId: 1
  }, extra || {}));
}
function tapCell(g, el, x, y) {
  const p = { pointerType: 'touch', button: 0, clientX: x === undefined ? 5 : x, clientY: y === undefined ? 5 : y, pointerId: 2 };
  g.dispatch(el, 'pointerdown', p);
  g.dispatch(el, 'pointerup', p);
}
function touchDown(g, el, x, y) {
  g.dispatch(el, 'pointerdown', { pointerType: 'touch', button: 0, clientX: x === undefined ? 5 : x, clientY: y === undefined ? 5 : y, pointerId: 3 });
}
function touchUp(g, el, x, y) {
  g.dispatch(el, 'pointerup', { pointerType: 'touch', button: 0, clientX: x === undefined ? 5 : x, clientY: y === undefined ? 5 : y, pointerId: 3 });
}
function cellByIdx(g, i) { return g.doc.querySelector('#board .cell[data-i="' + i + '"]'); }

/* 按独立求解器的推理顺序走完整关（先翻开所有安全格，再标记所有雷） */
function winLevel(g, li, opts) {
  opts = opts || {};
  const sol = SOL[li];
  const n = sol.n;
  const cs = startLevel(g, li);
  for (const i of sol.safe_order) pressCell(g, cs[i], 'dig');
  const mineCells = [];
  for (const i of sol.mine_order) { pressCell(g, cs[i], 'flag'); mineCells.push(i); }
  return { cs, sol, n, mineCells };
}
function walkReveal(g, ms) { g.advance(ms === undefined ? 6000 : ms); }

function staticIndex(g, el) {
  let k = 0, found = -1;
  const walk = n => { if (found >= 0 || !n) return; if (n === el) { found = k; return; } k++; for (const c of n.childNodes) { walk(c); if (found >= 0) return; } };
  walk(g.doc.documentElement);
  return found;
}

module.exports = { SOL, LV, SKY, q, qa, state, cells, cellClasses, textOf, btnLabels, closeIntro, unlockAll,
  startLevel, pressCell, tapCell, touchDown, touchUp, cellByIdx, winLevel, walkReveal, staticIndex };
