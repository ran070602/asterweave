'use strict';
/* v21 复核 F：通关动画（静态 + 运行时） */
const fs = require('fs');
const path = require('path');
const { boot, makeStorage } = require('./v21_stub.js');
const P = require('./v21_play.js');
const { q, qa } = P;

const HTML = fs.readFileSync(process.env.V21_HTML || path.join(__dirname, 'frozen_v21b', 'dist_index.html'), 'utf8');
const LINES = HTML.split('\n');
const R = [];
const check = (id, name, ok, detail) => { R.push({ id, name, ok: !!ok, detail: String(detail === undefined ? '' : detail) }); };
const srcLine = re => { const i = LINES.findIndex(l => re.test(l)); return i < 0 ? null : i + 1; };

/* ---- 静态 ---- */
const guard = /if \(winFlashPending \|\| winRevealPending\)\{ closeModal\(false\); return; \}/.test(HTML);
const reduceShort = /prefersReduced\(\)\)\{\s*\n\s*finishBoardReveal\(\);/.test(HTML) || /winRevealPending = false;\s*\n\s*winRevealDone = true;/.test(HTML);
const winFlashAssignTrue = /winFlashPending\s*=\s*true/.test(HTML);
const revealFlashApplied = /classList\.add\([^)]*reveal-flash/.test(HTML);
const starGlow = /\.board\.reveal-stage \.cell\.wonstar\.lit\{[^}]*animation:starGlow/.test(HTML);
const cwStart = HTML.indexOf('function checkWin');
const cwBody = HTML.slice(cwStart, HTML.indexOf('function act(', cwStart));
const order = ['S.status = \'won\';', 'markCleared(S.index);', 'winRevealDone = false;', 'winRevealPending = true;', 'render();', 'startBoardReveal(alreadyCleared);'];
let last = -1, ordered = true;
for (const s of order) { const i = cwBody.indexOf(s); if (i < last || i < 0) ordered = false; last = i; }
check('F1', '静态：renderModal 在 winFlashPending/winRevealPending 期间提前返回；checkWin 顺序为 置 won → 挂起揭晓 → render → 播放',
  guard && ordered && reduceShort,
  `guard@L${srcLine(/winFlashPending \|\| winRevealPending/)} ordered=${ordered} reduced-motion 直落终态=${reduceShort}`);
check('F2', '静态：点亮星座用 .reveal-stage + wonstar.lit{animation:starGlow}（「闪一下」由 starGlow 实现）',
  starGlow, `starGlow=${starGlow}`);
check('F3', '静态：winFlashPending 从未被赋 true；.reveal-flash 类从未被 JS 添加（两处死代码）',
  !winFlashAssignTrue && !revealFlashApplied,
  `winFlashPending=true 赋值=${winFlashAssignTrue} reveal-flash 被添加=${revealFlashApplied}（CSS 里定义了 winStarFlash 但不可达）`);

/* ---- 运行时：首通（慢速路径） ---- */
function winAndMeasure(reduce, li) {
  const g = boot({ storage: makeStorage(), reduce: !!reduce });
  P.closeIntro(g); P.unlockAll(g);
  const sol = P.SOL[li];
  const cs = P.startLevel(g, li);
  for (const i of sol.safe_order) P.pressCell(g, cs[i], 'dig');
  for (let k = 0; k < sol.mine_order.length - 1; k++) P.pressCell(g, cs[sol.mine_order[k]], 'flag');
  const overlay = q(g, '#overlay');
  const beforeWin = { open: overlay.className.indexOf('open') >= 0 };
  P.pressCell(g, cs[sol.mine_order[sol.mine_order.length - 1]], 'flag');   // 制胜一击
  const t0 = g.clock.now;
  const rightAfter = {
    status: JSON.parse(g.doc.body.dataset.gameState).status,
    open: overlay.className.indexOf('open') >= 0,
    btns: q(g, '#modalBtns').childNodes.length,
    stage: q(g, '#board').classList.contains('reveal-stage'),
    lit: qa(g, '#board .cell.lit').length
  };
  let tLit = null, tLines = null, tModal = null;
  const total = P.LV[li].theme.lines.length, stars = P.LV[li].theme.stars.length;
  for (let k = 0; k < 1400; k++) {
    g.advance(5);
    const dt = g.clock.now - t0;
    if (tLit === null && qa(g, '#board .cell.lit').length >= stars) tLit = dt;
    if (tLines === null && qa(g, '#boardReveal line').length >= total) tLines = dt;
    if (overlay.className.indexOf('open') >= 0) { tModal = dt; break; }
  }
  return { g, rightAfter, tLit, tLines, tModal, beforeWin, stars, total };
}
const slow = winAndMeasure(false, 0);
check('F4', '运行时：制胜瞬间不弹 modal（先点亮星座闪一下），星座点亮后延迟约 2s 才弹窗',
  slow.rightAfter.status === 'won' && !slow.rightAfter.open && slow.rightAfter.btns === 0
  && slow.rightAfter.stage === true && slow.rightAfter.lit === 0
  && slow.tLit !== null && slow.tLines !== null && slow.tModal !== null
  && slow.tLit < slow.tModal && slow.tLines <= slow.tModal && slow.tModal >= 800,
  `制胜瞬间 status=${slow.rightAfter.status} modalOpen=${slow.rightAfter.open} stage=${slow.rightAfter.stage} lit=${slow.rightAfter.lit} | 首次点亮=${slow.tLit}ms 连线注入=${slow.tLines}ms（CSS animation-delay 生效）弹窗=${slow.tModal}ms`);

/* ---- 运行时：重玩已通关（fast 路径） ---- */
(function () {
  const g = boot({ storage: makeStorage() });
  P.closeIntro(g); P.unlockAll(g);
  const sol = P.SOL[0], cs = P.startLevel(g, 0);
  for (const i of sol.safe_order) P.pressCell(g, cs[i], 'dig');
  for (const i of sol.mine_order) P.pressCell(g, cs[i], 'flag');
  P.walkReveal(g, 8000);
  // 再走一遍（此时该关已 cleared → fast=true）
  const cs2 = P.startLevel(g, 0);
  for (const i of sol.safe_order) P.pressCell(g, cs2[i], 'dig');
  for (let k = 0; k < sol.mine_order.length - 1; k++) P.pressCell(g, cs2[sol.mine_order[k]], 'flag');
  P.pressCell(g, cs2[sol.mine_order[sol.mine_order.length - 1]], 'flag');
  const t0 = g.clock.now;
  let tModal = null;
  for (let k = 0; k < 1400; k++) { g.advance(5); if (q(g, '#overlay').className.indexOf('open') >= 0) { tModal = g.clock.now - t0; break; } }
  check('F5', '运行时：重玩已通关关走快速版（弹窗明显早于首通）', tModal !== null && tModal < slow.tModal,
    `重玩弹窗=${tModal}ms vs 首通=${slow.tModal}ms`);
})();

/* ---- 运行时：reduced-motion 缩短 ---- */
(function () {
  const red = winAndMeasure(true, 0);
  check('F6', '运行时：prefers-reduced-motion 下直接落终态（弹窗 0ms，连线立即齐全）',
    red.rightAfter.status === 'won' && red.rightAfter.open === true && red.tModal !== null && red.tModal <= 5
    && red.tLines !== null && red.tLines <= 5 && red.tModal < slow.tModal,
    `reduced: 制胜瞬间 modalOpen=${red.rightAfter.open} 弹窗=${red.tModal}ms 连线齐=${red.tLines}ms vs 首通=${slow.tModal}ms`);
})();

/* ---- 运行时：揭晓可跳过 ---- */
(function () {
  const g = boot({ storage: makeStorage() });
  P.closeIntro(g); P.unlockAll(g);
  const sol = P.SOL[0], cs = P.startLevel(g, 0);
  for (const i of sol.safe_order) P.pressCell(g, cs[i], 'dig');
  for (const i of sol.mine_order) P.pressCell(g, cs[i], 'flag');
  g.advance(100);
  const openBefore = q(g, '#overlay').className.indexOf('open') >= 0;
  g.dispatch(g.win, 'keydown', { key: 'Enter' });   // 揭晓期间按键 → 跳过
  const openAfter = q(g, '#overlay').className.indexOf('open') >= 0;
  check('F7', '运行时：揭晓播放中按键/点击可立即跳过到结算', !openBefore && openAfter,
    `跳过前 modalOpen=${openBefore} 跳过后=${openAfter}`);
})();

const out = { results: R, pass: R.filter(r => r.ok).length, fail: R.filter(r => !r.ok).length };
fs.writeFileSync(path.join(__dirname, 'v21_out_f.json'), JSON.stringify(out, null, 1), 'utf8');
console.log('=== F 通关动画 ===');
R.forEach(r => console.log(`${r.ok ? 'PASS' : 'FAIL'}  ${r.id}  ${r.name}\n        ${r.detail}`));
console.log(`F 合计 PASS ${out.pass} / FAIL ${out.fail}`);
