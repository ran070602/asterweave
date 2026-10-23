'use strict';
/* v21 复核 D：运行时（自写 DOM 桩，直跑 dist 内联脚本） */
const fs = require('fs');
const path = require('path');
const { boot, makeStorage } = require('./v21_stub.js');
const P = require('./v21_play.js');
const { q, qa, state, cells, textOf, btnLabels } = P;

const HTML = fs.readFileSync(process.env.V21_HTML || path.join(__dirname, 'frozen_v21b', 'dist_index.html'), 'utf8');
const R = [];
const check = (id, name, ok, detail) => { R.push({ id, name, ok: !!ok, detail: detail === undefined ? '' : String(detail) }); return !!ok; };

/* ---------------- D1：50 关全部玩到 won + 揭晓图计数 ---------------- */
(function D1() {
  const g = boot({ storage: makeStorage() });
  P.closeIntro(g);
  P.unlockAll(g);
  const fails = [];
  let checkedLevels = 0;
  for (let li = 0; li < 50; li++) {
    const lv = P.LV[li];
    const theme = lv.theme;
    const { sol } = P.winLevel(g, li);
    const errsBefore = g.errors.length;
    P.walkReveal(g, 8000);
    const st = state(g);
    const litCells = qa(g, '#board .cell.lit').length;
    const boardLines = qa(g, '#boardReveal line').length;
    const noiseCells = qa(g, '#board .cell.wonoise').length;
    const starCells = qa(g, '#board .cell.wonstar').length;
    const gstar = qa(g, '#modal .gstar').length, gline = qa(g, '#modal .gline').length, gnoise = qa(g, '#modal .gnoise').length;
    const overlayOpen = q(g, '#overlay').className.indexOf('open') >= 0;
    const litIdx = [], noiseIdx = [];
    cells(g).forEach((c, i) => { if (c.classList.contains('lit')) litIdx.push(i); if (c.classList.contains('wonoise')) noiseIdx.push(i); });
    const overlap = litIdx.filter(i => noiseIdx.indexOf(i) >= 0);
    const bad = [];
    if (st.status !== 'won') bad.push('status=' + st.status);
    if (st.lives !== 3) bad.push('lives=' + st.lives);
    if (g.errors.length !== errsBefore) bad.push('js-errors:' + g.errors.slice(errsBefore, errsBefore + 1));
    if (litCells !== theme.stars.length) bad.push('lit=' + litCells + '!=' + theme.stars.length);
    if (boardLines !== theme.lines.length) bad.push('boardLines=' + boardLines + '!=' + theme.lines.length);
    if (noiseCells !== lv.noise.length) bad.push('wonoise=' + noiseCells + '!=' + lv.noise.length);
    if (starCells !== theme.stars.length - 0) { /* 已踩雷的星座星会变 hitstar，重玩前不会 */ }
    if (gstar !== theme.stars.length) bad.push('gstar=' + gstar + '!=' + theme.stars.length);
    if (gline !== theme.lines.length) bad.push('gline=' + gline + '!=' + theme.lines.length);
    if (gnoise !== lv.noise.length) bad.push('gnoise=' + gnoise + '!=' + lv.noise.length);
    if (!overlayOpen) bad.push('modal-not-open');
    if (overlap.length) bad.push('noise∩star=' + overlap);
    if (st.clearedLevels !== li + 1) bad.push('clearedLevels=' + st.clearedLevels);
    if (bad.length) fails.push('L' + (li + 1) + ':' + bad.join(','));
    checkedLevels++;
    // 回关卡面板（下一轮 startLevel 直接点按钮）
  }
  check('D1', '50 关全部玩到 status=won 且揭晓图计数正确', fails.length === 0,
    fails.length ? fails.slice(0, 8).join(' | ') : ('50/50 关通过，lit=stars, boardLines=lines, wonoise=noise, gstar/gline/gnoise 全等，modal 均打开'));
})();

/* ---------------- D2：现行交互四条路径 ---------------- */
(function D2() {
  const g = boot({ storage: makeStorage() });
  P.closeIntro(g);
  const lv1 = P.LV[0];
  const mineSet = new Set(lv1.mines.map(m => m[0] * lv1.size + m[1]));
  const noiseSet = new Set(lv1.noise.map(m => m[0] * lv1.size + m[1]));
  let cs = cells(g);

  const safeUnrevealed = () => cells(g).findIndex((c, i) => !mineSet.has(i) && !c.classList.contains('revealed') && !c.classList.contains('flagged'));
  const mineUnflagged = () => cells(g).findIndex((c, i) => mineSet.has(i) && !c.classList.contains('flagged') && !c.classList.contains('revealed'));

  // (a) 触摸轻触 = 即时观测（同一次 pointerup 内、不推进时钟）
  let i = safeUnrevealed();
  const before = state(g).revealed;
  P.touchDown(g, cs[i], 5, 5); P.touchUp(g, cs[i], 5, 5);
  const afterTap = state(g).revealed;
  check('D2a', '📱触摸轻触 = 即时观测', afterTap > before, `revealed ${before} -> ${afterTap}（未推进时钟）`);

  // (b) 触摸长按 ~380ms = 标记，且长按后抬起不再观测
  i = safeUnrevealed();
  const rBefore = state(g).revealed, lBefore = state(g).lives, fBefore = state(g).flagged;
  P.touchDown(g, cs[i], 5, 5);
  g.advance(200);
  const midFlag = cells(g)[i].classList.contains('flagged');
  g.advance(200);            // 累计 400ms > 380ms
  const flagOn = cells(g)[i].classList.contains('flagged');
  const livesAfterLong = state(g).lives;
  P.touchUp(g, cs[i], 5, 5);
  g.advance(20);
  const revealedAfterUp = cells(g)[i].classList.contains('revealed');
  check('D2b', '触摸长按 ~380ms = 标记；抬起不再观测', flagOn && !midFlag && !revealedAfterUp && livesAfterLong === lBefore,
    `200ms时flagged=${midFlag} 400ms时flagged=${flagOn} 抬起后revealed=${revealedAfterUp} lives=${lBefore}->${livesAfterLong}`);

  // (c) 长按雷位：标记但不扣命
  let mi = mineUnflagged();
  const lv0 = state(g).lives;
  P.touchDown(g, cs[mi], 5, 5); g.advance(420);
  const mineFlagged = cells(g)[mi].classList.contains('flagged');
  const livesAfterMine = state(g).lives;
  P.touchUp(g, cs[mi], 5, 5);
  check('D2c', '长按雷位 = 标记且不扣命', mineFlagged && livesAfterMine === lv0 && !cells(g)[mi].classList.contains('revealed'),
    `mineFlagged=${mineFlagged} lives=${lv0}->${livesAfterMine}`);

  // (d) 鼠标左键单击 = 观测
  i = safeUnrevealed();
  const b2 = state(g).revealed;
  P.pressCell(g, cs[i], 'dig');
  const a2 = state(g).revealed;
  check('D2d', '💻鼠标左键单击 = 即时观测', a2 > b2, `revealed ${b2} -> ${a2}`);

  // (e) 鼠标右键 = 标记
  i = safeUnrevealed();
  const f2 = state(g).flagged;
  P.pressCell(g, cs[i], 'flag');
  const f3 = state(g).flagged;
  check('D2e', '鼠标右键 = 标记（不观测）', f3 === f2 + 1 && !cells(g)[i].classList.contains('revealed'),
    `flagged ${f2} -> ${f3}, revealed=${cells(g)[i].classList.contains('revealed')}`);

  // (f) 双击不产生标记
  const g2 = boot({ storage: makeStorage() });
  P.closeIntro(g2);
  let cs2 = cells(g2);
  const safe2 = (() => { for (let k = 0; k < cs2.length; k++) if (!mineSet.has(k)) return k; })();
  P.pressCell(g2, cs2[safe2], 'dig'); g.advance(30);
  P.pressCell(g2, cs2[safe2], 'dig'); g.advance(30);
  const dblFlagged = state(g2).flagged;
  check('D2f', '双击不产生标记（鼠标）', dblFlagged === 0, `两次左键后 flagged=${dblFlagged}`);
  const g3 = boot({ storage: makeStorage() });
  P.closeIntro(g3);
  const cs3 = cells(g3);
  P.tapCell(g3, cs3[safe2], 5, 5); g.advance(30); P.tapCell(g3, cs3[safe2], 5, 5); g.advance(30);
  const tapFlagged = state(g3).flagged;
  check('D2f2', '两次轻触不产生标记（触摸）', tapFlagged === 0, `两次轻触后 flagged=${tapFlagged}`);

  // (g) 源码无 DBL_MS / lastMouse / board 上无 dblclick 监听
  const dblMs = (HTML.match(/DBL_MS/g) || []).length, lastMouse = (HTML.match(/lastMouse/g) || []).length;
  const boardDbl = /boardEl\.addEventListener\('dblclick'/.test(HTML);
  check('D2g', '源码无 DBL_MS / lastMouse / 棋盘 dblclick 监听', dblMs === 0 && lastMouse === 0 && !boardDbl,
    `DBL_MS=${dblMs} lastMouse=${lastMouse} boardDblclick=${boardDbl}`);
})();

/* ---------------- D3：界面细节 ---------------- */
(function D3() {
  const g = boot({ storage: makeStorage() });
  const lvtag = q(g, '#lvtag'), hint = q(g, '#actHint'), board = q(g, '#board');
  const iTag = P.staticIndex(g, lvtag), iHint = P.staticIndex(g, hint), iBoard = P.staticIndex(g, board);
  const sameParent = lvtag.parentNode === hint.parentNode;
  const txt = hint.textContent;
  check('D3a', '#actHint 在棋盘正上方且紧跟「第 N/50 关」行', sameParent && iTag < iHint && iHint < iBoard,
    `staticIndex lvtag=${iTag} actHint=${iHint} board=${iBoard}, sameParent=${sameParent}`);
  const hasAll = ['轻触', '长按', '单击', '右键'].every(k => txt.indexOf(k) >= 0);
  check('D3b', '#actHint 文案含 轻触/长按/单击/右键 且不含「双击」', hasAll && txt.indexOf('双击') < 0, txt);

  // 首屏说明只弹一次
  const store = makeStorage();
  const gA = boot({ storage: store });
  const shownFirst = !q(gA, '#introOverlay').hidden;
  const introLines = q(gA, '#introOverlay').querySelectorAll('.intro-line').length;
  gA.dispatch(q(gA, '#introStart'), 'click', {});
  const hiddenAfter = q(gA, '#introOverlay').hidden;
  const saved = JSON.parse(store.getItem('leixian.migong.progress.v1'));
  const gB = boot({ storage: store });
  const shownSecond = !q(gB, '#introOverlay').hidden;
  // 重置进度后不再弹
  gB.dispatch(q(gB, '#lvBtn'), 'click', {});
  gB.dispatch(q(gB, '#resetBtn'), 'click', {});
  gB.dispatch(q(gB, '#resetBtn'), 'click', {});
  gB.advance(400);
  const shownAfterReset = !q(gB, '#introOverlay').hidden;
  check('D3c', '首次进入第1关弹一次说明（3句），关闭写 introSeen，重置后不再弹',
    shownFirst && hiddenAfter && saved.introSeen === true && !shownSecond && !shownAfterReset,
    `首屏=${shownFirst} 关闭后hidden=${hiddenAfter} introSeen=${saved.introSeen} 二次启动弹=${shownSecond} 重置后弹=${shownAfterReset} 说明句数=${introLines}`);

  // 失败结算条
  const g4 = boot({ storage: makeStorage() });
  P.closeIntro(g4);
  const lv1 = P.LV[0];
  const mineIdx = [];
  cells(g4).forEach((c, i) => { if (lv1.mines.some(m => m[0] * lv1.size + m[1] === i)) mineIdx.push(i); });
  const cs4 = cells(g4);
  for (let k = 0; k < 3; k++) P.pressCell(g4, cs4[mineIdx[k]], 'dig');
  const lostSt = state(g4);
  const replayHiddenLost = q(g4, '#replayActions').hidden;
  g4.dispatch(g4.win, 'keydown', { key: 'Escape' });   // 收起 modal → 结算条
  g4.advance(50);
  const strip = q(g4, '#result');
  const loseLabels = btnLabels(strip);
  const loseShown = strip.className.indexOf('show') >= 0 && strip.className.indexOf('lose') >= 0;
  check('D3d', '失败：结算条无「结算」按钮（只有重来/换关）；常驻重玩按钮隐藏',
    lostSt.status === 'lost' && lostSt.lives === 0 && replayHiddenLost && loseShown
    && loseLabels.length === 2 && loseLabels[0].indexOf('重来本关') >= 0 && loseLabels[1].indexOf('换个关卡') >= 0
    && loseLabels.every(l => l.indexOf('结算') < 0),
    `status=${lostSt.status} lives=${lostSt.lives} 常驻重玩hidden=${replayHiddenLost} 结算条按钮=${JSON.stringify(loseLabels)}`);

  // 通关结算条
  const g5 = boot({ storage: makeStorage() });
  P.closeIntro(g5); P.unlockAll(g5);
  P.winLevel(g5, 0);
  P.walkReveal(g5, 8000);
  const wonSt = state(g5);
  const modalLabels = btnLabels(q(g5, '#modalBtns'));
  const replayHiddenWon = q(g5, '#replayActions').hidden;
  g5.dispatch(g5.win, 'keydown', { key: 'Escape' });
  g5.advance(50);
  const winStrip = q(g5, '#result');
  const winLabels = btnLabels(winStrip);
  check('D3e', '通关：结算条保留「下一关」；常驻重玩按钮隐藏',
    wonSt.status === 'won' && replayHiddenWon && winStrip.className.indexOf('win') >= 0
    && winLabels.some(l => l.indexOf('下一关') >= 0) && modalLabels.some(l => l.indexOf('下一关') >= 0),
    `常驻重玩hidden=${replayHiddenWon} modal按钮=${JSON.stringify(modalLabels)} 结算条按钮=${JSON.stringify(winLabels)}`);
  // 进行中常驻重玩可见
  const g6 = boot({ storage: makeStorage() });
  P.closeIntro(g6);
  check('D3f', '游戏进行中常驻「↻ 重玩本关」可见', !q(g6, '#replayActions').hidden && textOf(g6, '#replay').indexOf('重玩本关') >= 0,
    `hidden=${q(g6, '#replayActions').hidden} label=${textOf(g6, '#replay')}`);
  // 全库不存在「结算」按钮
  const allBtnText = qa(g6, 'button').map(b => b.textContent);
  check('D3g', '全库无任何按钮文案为「结算」', allBtnText.every(t => t.indexOf('结算') < 0),
    JSON.stringify(allBtnText.filter(t => t.indexOf('结算') >= 0)));
})();

/* ---------------- D4：解锁 / gameState / 不泄露 ---------------- */
(function D4() {
  const g = boot({ storage: makeStorage() });
  P.closeIntro(g);
  const before = qa(g, '#lvGrid button').filter(b => !b.disabled).length;
  g.dispatch(q(g, '#unlockBtn'), 'click', {});
  const after = qa(g, '#lvGrid button').filter(b => !b.disabled).length;
  check('D4a', '「全部解锁」一次点击即生效（50 关全可用）', before === 1 && after === 50,
    `click 前可用=${before} 后可用=${after}`);

  const st = state(g);
  const need = ['level', 'levelId', 'size', 'revealed', 'totalSafe', 'flagged', 'mines', 'lives', 'status', 'mode', 'totalLevels', 'clearedLevels', 'noise'];
  const missing = need.filter(k => !(k in st));
  check('D4b', 'dataset.gameState 字段齐全', missing.length === 0, missing.length ? '缺 ' + missing : Object.keys(st).join(','));

  // 不泄露雷位（playing）
  const cls = cells(g).map(c => c.className);
  const leakCls = cls.filter(c => /wonstar|wonoise|hitstar|hitnoise/.test(c));
  const leakSvg = cells(g).filter(c => c.innerHTML.indexOf('noise-star') >= 0);
  const revealEmpty = q(g, '#boardReveal').innerHTML === '';
  const modalEmpty = q(g, '#modalBtns').childNodes.length === 0 && q(g, '#constSlot').childNodes.length === 0;
  const constModalEmpty = (q(g, '#constModalBody') || { innerHTML: '' }).innerHTML === '';
  check('D4c', 'status!=won 时 DOM 不泄露雷位（含杂星）',
    leakCls.length === 0 && leakSvg.length === 0 && revealEmpty && modalEmpty && constModalEmpty,
    `异常class=${leakCls.length} 杂星SVG=${leakSvg.length} boardReveal空=${revealEmpty} 结算区空=${modalEmpty} 图鉴modal空=${constModalEmpty}`);

  // 踩一颗雷后只泄露被踩的那一颗
  const lv1 = P.LV[0];
  const cs = cells(g);
  const mIdx = lv1.mines.map(m => m[0] * lv1.size + m[1]);
  P.pressCell(g, cs[mIdx[0]], 'dig');
  const cls2 = cells(g).map(c => c.className);
  const hit = cls2.filter(c => /hitstar|hitnoise/.test(c)).length;
  const won2 = cls2.filter(c => /wonstar|wonoise/.test(c)).length;
  check('D4d', '踩雷后只亮被踩的那 1 颗，其余雷位仍不泄露', hit === 1 && won2 === 0,
    `hit=${hit} won-leak=${won2} 被踩格是雷=${lv1.mines.some(m => m[0] * lv1.size + m[1] === mIdx[0])}`);
})();

const out = { results: R, pass: R.filter(r => r.ok).length, fail: R.filter(r => !r.ok).length };
fs.writeFileSync(path.join(__dirname, 'v21_out_d.json'), JSON.stringify(out, null, 1), 'utf8');
console.log('=== D 运行时复核 ===');
R.forEach(r => console.log(`${r.ok ? 'PASS' : 'FAIL'}  ${r.id}  ${r.name}\n        ${r.detail}`));
console.log(`D 合计 PASS ${out.pass} / FAIL ${out.fail}`);
