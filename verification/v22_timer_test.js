// v22：⏱ 限时关卡（第 11 关起强制）+ 关卡面板 ⏱ 图标 + 无尽每题倒计时。
// 自写 DOM 桩（无 npm、无外部依赖），驱动 dist/index.html 真实脚本。
//
// 2026-10-28 新口径（重玩也要计时，推翻旧的「重玩不限时」）：
//   timeIsTimed() = 无尽 false；关卡序号 < 11 false；>= 11 一律 true（含重玩已通关的关卡）。
//   所以重玩第 11 关（及以后）同样显示「限时 m:ss」/倒计时，超时同样判负。
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

// 仓库根 = 本文件所在目录的上一级（不再硬编码检出目录名，避免仓库改名/搬家后 ENOENT）
const ROOT = path.resolve(__dirname, '..');
const DIST = path.join(ROOT, 'dist', '星织-游戏本体', 'index.html');
const html = fs.readFileSync(DIST, 'utf8');

// ---------- 序列来源：从 dist 注入的紧凑数据「现场解码」 ----------
// 旧写法读 verification/v13_play.json —— 那是 50 关时代按旧关卡 id 生成的映射，
// 现在是 88 关，按键取值不保证对得上当前盘面。这里只改测试手里那份 HTML 字符串副本：
// 把 LEVELS_PACKED / BANK_PACKED 以及展开后的 LEVELS / BANK 额外挂到 globalThis，跑完再取。
const DATA_PATCH = [
  [/const\s+LEVELS_PACKED\s*=/, 'const LEVELS_PACKED = globalThis.__LEVELS_PACKED ='],
  [/const\s+BANK_PACKED\s*=/, 'const BANK_PACKED = globalThis.__BANK_PACKED ='],
  [/const\s+LEVELS\s*=\s*expandLevelsPacked\(LEVELS_PACKED\)\s*;/,
   'const LEVELS = globalThis.__LEVELS = expandLevelsPacked(LEVELS_PACKED);'],
  [/const\s+BANK\s*=\s*\(ENDLESS_BANK\s*&&\s*ENDLESS_BANK\.length\)\s*\?\s*ENDLESS_BANK\s*:\s*LEVELS\s*;/,
   'const BANK = globalThis.__BANK = ((ENDLESS_BANK && ENDLESS_BANK.length) ? ENDLESS_BANK : LEVELS);']
];
let dataHtml = html;
DATA_PATCH.forEach(function(pair){
  if (!pair[0].test(dataHtml)) throw new Error('注入点缺失：' + pair[0]);
  dataHtml = dataHtml.replace(pair[0], pair[1]);
});

const R = [];                       // 结果
function ok(name, cond, ev) { R.push({ name, pass: !!cond, ev: ev === undefined ? '' : String(ev) }); }
function note(name, ev) { R.push({ name, pass: null, ev: String(ev) }); }

// ---------------- 计时器（可手动 flush，用于验证 900ms 通关动画） ----------------
let clock = 0, timers = [], tid = 1;
function setTimeoutStub(fn, ms) { const id = tid++; timers.push({ id, t: clock + (ms || 0), fn, seq: id }); return id; }
function clearTimeoutStub(id) { timers = timers.filter(x => x.id !== id); }
function rafStub(fn) { return setTimeoutStub(fn, 16); }
// setInterval 桩：周期性重排定时器（游戏里用于 500ms 计时器）
function setIntervalStub(fn, ms) {
  const id = tid++;
  const arm = function () { timers.push({ id: id, t: clock + (ms || 16), fn: function () { arm(); fn(); }, seq: id }); };
  arm();
  return id;
}
function clearIntervalStub(id) { timers = timers.filter(x => x.id !== id); }
function flush(ms) {
  const target = clock + ms;
  for (;;) {
    timers.sort((a, b) => a.t - b.t || a.seq - b.seq);
    const nx = timers.find(x => x.t <= target);
    if (!nx) break;
    timers = timers.filter(x => x !== nx);
    clock = Math.max(clock, nx.t);
    try { nx.fn(); } catch (e) { note('timer 抛错', e.message); }
  }
  clock = target;
}

// ---------------- 元素桩 ----------------
let created = 0;
function mkEl(tag, id) {
  const el = {
    tagName: String(tag || 'div').toUpperCase(), _id: id || null,
    className: '', innerHTML: '', textContent: '', hidden: false, disabled: false,
    attrs: {}, children: [], childNodes: [], parentNode: null, style: { _p: {}, setProperty(k, v) { this._p[k] = v; } },
    dataset: {}, _h: {}, offsetWidth: 100, _created: ++created,
    classList: {
      _o: null,
      add(c) { const s = new Set((el.className || '').split(/\s+/).filter(Boolean)); s.add(c); el.className = [...s].join(' '); },
      remove(c) { const s = new Set((el.className || '').split(/\s+/).filter(Boolean)); s.delete(c); el.className = [...s].join(' '); },
      contains(c) { return (el.className || '').split(/\s+/).includes(c); }
    },
    setAttribute(k, v) { this.attrs[k] = String(v); if (k === 'class') this.className = String(v); if (k === 'id') this._id = String(v); if (k === 'hidden') this.hidden = true; },
    getAttribute(k) { return Object.prototype.hasOwnProperty.call(this.attrs, k) ? this.attrs[k] : null; },
    removeAttribute(k) { delete this.attrs[k]; },
    addEventListener(t, fn) { (this._h[t] = this._h[t] || []).push(fn); },
    removeEventListener(t, fn) { this._h[t] = (this._h[t] || []).filter(f => f !== fn); },
    dispatchEvent(e) { (this._h[e.type] || []).slice().forEach(fn => fn(e)); return true; },
    appendChild(c) {
      if (c && c._frag) { c.children.slice().forEach(x => this.appendChild(x)); return c; }
      this.children.push(c); this.childNodes = this.children; if (c) c.parentNode = this;
      return c;
    },
    querySelector(sel) {
      const cls = sel.replace(/^\./, '');
      const walk = n => { for (const k of n.children) { if ((k.className || '').split(/\s+/).includes(cls)) return k; const r = walk(k); if (r) return r; } return null; };
      return walk(this);
    },
    querySelectorAll(sel) {
      const cls = sel.replace(/^\./, ''); const out = [];
      const walk = n => { for (const k of n.children) { if ((k.className || '').split(/\s+/).includes(cls)) out.push(k); walk(k); } };
      walk(this); return out;
    },
    closest(sel) {
      const cls = sel.replace(/^\./, '');
      let n = this;
      while (n) { if ((n.className || '').split(/\s+/).includes(cls)) return n; n = n.parentNode; }
      return null;
    },
    getBoundingClientRect() { return { width: 300, height: 300, left: 0, top: 0, right: 300, bottom: 300 }; },
    setPointerCapture() {}, releasePointerCapture() {},
    focus() { doc.activeElement = this; }, blur() {}, scrollIntoView() {}, click() { this.dispatchEvent(mkEvent('click', { target: this })); },
    get firstChild() { return this.children[0] || null; },
    remove() { if (this.parentNode) this.parentNode.children = this.parentNode.children.filter(x => x !== this); },
    _textOf() { if (this.textContent) return this.textContent; return this.children.map(c => c._textOf()).join(''); },
    _allText() { return this._textOf() + this.children.map(c => c._allText()).join(''); }
  };
  // innerHTML 是真实 DOM 语义：赋值会清空子节点（本桩必须如此，否则 constSlot 会累积旧关卡面板）
  let _html = '';
  Object.defineProperty(el, 'innerHTML', {
    get() { return _html; },
    set(v) { _html = String(v); if (_html === '') { this.children = []; this.childNodes = this.children; } },
    enumerable: true, configurable: true
  });
  return el;
}
function mkEvent(type, extra) { const e = Object.assign({ type, preventDefault() {}, stopPropagation() {}, cancelable: true, button: 0, shiftKey: false, key: '' }, extra || {}); return e; }

// ---------------- 静态 HTML 元素索引 ----------------
function parseStatic() {
  const map = {};
  const tagRe = /<(\w+)([^>]*?\bid="([^"]+)"[^>]*?)>/g;
  let mm;
  while ((mm = tagRe.exec(html))) {
    const [, tag, attrStr, id] = mm;
    const el = mkEl(tag, id);
    if (id === 'skyMap') el.tagName = 'svg';
    const cls = /class="([^"]*)"/.exec(attrStr);
    if (cls) el.className = cls[1];
    // 只取紧邻标签之后的纯文本（够用：这些按钮都是纯文本）
    const rest = html.slice(mm.index + mm[0].length);
    const txt = rest.match(/^([^<]*)/);
    el.textContent = (txt ? txt[1] : '').trim();
    el.innerHTML = el.textContent;
    for (const a of attrStr.matchAll(/([\w-]+)="([^"]*)"/g)) el.attrs[a[1]] = a[2];
    for (const a of attrStr.matchAll(/(?:^|\s)(hidden|disabled)(?=[\s/>]|$)/g)) el.attrs[a[1]] = '';
    if (el.attrs.hidden !== undefined) el.hidden = true;     // 无值布尔属性
    if (el.attrs.disabled !== undefined) el.disabled = true;
    map[id] = el;
  }
  return map;
}
const byId = parseStatic();
const titleText = (html.match(/<title>([\s\S]*?)<\/title>/) || [, ''])[1];
const boardEl = byId.board, bodyEl = mkEl('body', null);
const docEl = mkEl('html', null);
const doc = {
  body: bodyEl, documentElement: docEl, activeElement: null,
  getElementById: id => byId[id] || null,
  createElement: t => mkEl(t),
  createDocumentFragment: () => { const f = mkEl('fragment'); f._frag = true; return f; },
  querySelector: s => (s === 'title' ? null : null), addEventListener() {}, removeEventListener() {},
  _byId: byId
};
const store = {};
const win = {
  localStorage: { getItem: k => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = String(v); }, removeItem: k => { delete store[k]; } },
  matchMedia: () => ({ matches: false, addEventListener() {}, addListener() {} }),
  setTimeout: setTimeoutStub, clearTimeout: clearTimeoutStub, requestAnimationFrame: rafStub,
  setInterval: setIntervalStub, clearInterval: clearIntervalStub,
  addEventListener(t, fn) { (win._h[t] = win._h[t] || []).push(fn); },
  _h: {}, innerWidth: 390, innerHeight: 844, devicePixelRatio: 2,
  document: doc, Math, JSON, console, Set, Map, Array, Object, String, Number, Boolean, Date, Int16Array, Uint8Array, parseInt, parseFloat, isNaN, isFinite, Error, encodeURIComponent
};
win.window = win;

// ---------------- 取出页面脚本并执行（用打了数据导出补丁的副本） ----------------
const scripts = [...dataHtml.matchAll(/<script[^>]*>([\s\S]*?)<\/script>/g)].map(x => x[1]);
ok('页面内联 script 数量==1', scripts.length === 1, 'count=' + scripts.length);
win.Date = { now: function(){ return 1700000000000 + clock; }, UTC: Date.UTC, parse: Date.parse };
// base64 垫片：关卡/题库数据用 atob 解压，Node 沙箱没有该浏览器全局
if (typeof win.atob !== 'function'){ win.atob = function(b){ return Buffer.from(String(b), 'base64').toString('binary'); }; }
if (typeof win.btoa !== 'function'){ win.btoa = function(s){ return Buffer.from(String(s), 'binary').toString('base64'); }; }
const ctx = vm.createContext(Object.assign(win, { globalThis: win }));
vm.runInContext(scripts[0], ctx, { filename: 'dist-index-inline.js' });
flush(0);
ok('脚本执行无致命异常（关卡数据缺失提示未出现）', !String(boardEl.innerHTML).includes('关卡数据缺失'));

// 现场解码出来的两套盘面池：闯关 88 关 / 无尽 176 题题库
const POOLS = { campaign: ctx.__LEVELS || [], endless: ctx.__BANK || [] };
ok('测试内可现场解码盘面（LEVELS / BANK）', POOLS.campaign.length > 0 && POOLS.endless.length > 0,
   'LEVELS=' + POOLS.campaign.length + ' BANK=' + POOLS.endless.length);

// ---------------- 辅助：读状态 ----------------
const state = () => JSON.parse(bodyEl.dataset.gameState || '{}');
const cells = () => (boardEl.children || []).filter(c => (c.className || '').split(/\s+/).includes('cell'));
const cellsByI = () => { const a = []; cells().forEach(c => { a[+c.getAttribute('data-i')] = c; }); return a; };
function clickEl(el, ev) { el.dispatchEvent(mkEvent('click', Object.assign({ target: el }, ev || {}))); flush(50); }
function actCell(i, mode) {
  const cell = cellsByI()[i];
  if (!cell) throw new Error('cell ' + i + ' 不存在');
  boardEl.dispatchEvent(mkEvent('pointerdown', { target: cell, button: mode === 'flag' ? 2 : 0 }));
  flush(0);
}

// ---------------- v22：⏱ 限时关卡（强制） + 关卡面板 ⏱ 图标 ----------------
const PROG_KEY = 'leixian.migong.progress.v1';
if (byId.introStart) { byId.introStart.dispatchEvent(mkEvent('click', { target: byId.introStart })); flush(0); }
const anyClose = byId.homeClose || byId.homeBack || byId.homeStart;
if (anyClose && byId.homeOverlay && !byId.homeOverlay.hidden) { anyClose.dispatchEvent(mkEvent('click', { target: anyClose })); flush(60); }

function openPanel(){ byId.lvBtn.dispatchEvent(mkEvent('click', { target: byId.lvBtn })); flush(20); }
function closePanel2(){ if (byId.drawerMask) byId.drawerMask.dispatchEvent(mkEvent('click', { target: byId.drawerMask })); flush(260); }
function goLevel(n){ openPanel(); byId.lvGrid.children[n - 1].dispatchEvent(mkEvent('click', { target: byId.lvGrid.children[n - 1] })); flush(40); }

// ---------- 盘面序列：按「当前真实盘面」现场生成（先右键标记所有雷，再点开所有安全格） ----------
function campaignLevelAt(i){ return POOLS.campaign[i] || null; }
function campaignLevelById(id){
  for (let i = 0; i < POOLS.campaign.length; i++) if (POOLS.campaign[i].id === id) return POOLS.campaign[i];
  return null;
}
function currentLevel(){
  const st = state();
  return campaignLevelById(st.levelId) || campaignLevelAt(st.level - 1);
}
function mineCells(lv){                      // mines 已含杂星；startBoard 再把 noise 并进雷集
  const n = lv.size, set = new Set();
  (lv.mines || []).forEach(function(c){ set.add(c[0] * n + c[1]); });
  (lv.noise || []).forEach(function(c){ set.add(c[0] * n + c[1]); });
  return Array.from(set).sort(function(a, b){ return a - b; });
}
function firstSafe(lv){ const mines = new Set(mineCells(lv)); for (let i = 0; i < lv.size * lv.size; i++) if (!mines.has(i)) return i; return -1; }
function clearSeq(lv){
  const mines = new Set(mineCells(lv)), ops = [], total = lv.size * lv.size;
  for (let i = 0; i < total; i++) if (mines.has(i)) ops.push(['flag', i]);
  for (let i = 0; i < total; i++) if (!mines.has(i)) ops.push(['dig', i]);
  return ops;
}
function tapCell(i){
  boardEl.dispatchEvent(mkEvent('pointerdown', { target: cellsByI()[i], pointerType: 'touch', button: 0, clientX: 100, clientY: 100 }));
  boardEl.dispatchEvent(mkEvent('pointerup',   { target: cellsByI()[i], pointerType: 'touch', button: 0, clientX: 100, clientY: 100 }));
  flush(0);
}
function rightClick(i){ boardEl.dispatchEvent(mkEvent('pointerdown', { target: cellsByI()[i], button: 2, pointerType: 'mouse', clientX: 100, clientY: 100 })); flush(0); }
function enterLevel(n){
  goLevel(n); closePanel2();
  const lv = campaignLevelAt(n - 1);
  const d = lv ? firstSafe(lv) : -1;
  if (d >= 0) tapCell(d);
  flush(20);
}
function runClearSeq(){                      // 用当前盘面的现场序列通关（不 flush 揭晓动画）
  const lv = currentLevel();
  if (!lv) throw new Error('无法定位当前盘面：levelId=' + state().levelId + ' level=' + state().level);
  const seq = clearSeq(lv);
  for (let i = 0; i < seq.length; i++){ if (seq[i][0] === 'flag') rightClick(seq[i][1]); else tapCell(seq[i][1]); }
}
function chipMins(){                       // 返回 {el: 已用秒, limit: 限时秒}
  const t = String(byId.timerChip.textContent || '');
  const m = t.match(/(\d+):(\d\d)/);
  return m ? (+m[1] * 60 + +m[2]) : null;
}
function gridCls(n){ return String(byId.lvGrid.children[n - 1].className); }
function hasCls(n, c){ return gridCls(n).split(/\s+/).indexOf(c) >= 0; }   // 按空格分词，避免 untimed 命中 timed
function cssRule(sel){
  const i = html.indexOf(sel);
  return i < 0 ? '' : html.slice(i, html.indexOf('}', i) + 1);
}

// ① 只有第 11 关起是限时关卡
ok('第 1 关不显示计时条', byId.timerChip.hidden === true, String(byId.timerChip.hidden));
byId.unlockBtn.dispatchEvent(mkEvent('click', { target: byId.unlockBtn })); flush(20);
enterLevel(11);
ok('第 11 关显示计时条', byId.timerChip.hidden === false, byId.timerChip.textContent);
ok('第 11 关已开始计时（不是 idle）', String(byId.timerChip.className).indexOf('idle') < 0, byId.timerChip.className);
const limit11 = chipMins();
ok('倒计时是「剩余时间」而不是已用时间（剩余 ≈ 限时）', limit11 !== null, byId.timerChip.textContent);

// ② 未操作时只显示「限时 m:ss」，不倒计时
goLevel(11); closePanel2();
ok('刚进关未操作时显示「限时 …」且不倒计时',
   String(byId.timerChip.textContent).indexOf('限时') >= 0 && String(byId.timerChip.className).indexOf('idle') >= 0,
   byId.timerChip.textContent + ' / ' + byId.timerChip.className);
const idleShown = chipMins();
tapCell(firstSafe(currentLevel())); flush(0);
ok('第一次操作后开始倒计时', chipMins() !== null && Math.abs(chipMins() - idleShown) <= 1,
   idleShown + ' → ' + chipMins());

// ③ 倒计时随虚拟时间走
const beforeLeft = chipMins();
flush(3000);
const afterLeft = chipMins();
ok('剩余时间随时间减少（约 3 秒）', afterLeft <= beforeLeft - 2, beforeLeft + ' → ' + afterLeft);

// ④ 危险配色（≤10s 红、≤20% 黄）
ok('CSS 定义了 warn/danger/over 三档配色',
   cssRule('.timer.warn').length > 0 && cssRule('.timer.danger').length > 0 && cssRule('.timer.over').length > 0);
flush((beforeLeft - 5) * 1000);
ok('剩余 ≤10 秒时进入 danger 档', String(byId.timerChip.className).indexOf('danger') >= 0,
   byId.timerChip.className + ' ' + byId.timerChip.textContent);

// ⑤ 超时即失败（强制，没有开关）
ok('不再有「严格限时」开关', byId.strictBtn === undefined || byId.strictBtn === null, String(byId.strictBtn));
flush(20000);
ok('超过硬限时即判负', state().status === 'lost', state().status);
ok('失败原因是「⏱ 超时」', String(byId.modalTitle.textContent).indexOf('超时') >= 0, byId.modalTitle.textContent);
ok('超时不扣命（仍是 3 架望远镜）', state().lives === 3, String(state().lives));

// ⑥ 达标通关：金色 ⏱ + 最快用时
byId.replay.dispatchEvent(mkEvent('click', { target: byId.replay })); flush(20);
tapCell(firstSafe(currentLevel())); flush(20);
runClearSeq();
flush(1400);
ok('第 11 关已通关', state().status === 'won', state().status);
const prog = JSON.parse(store[PROG_KEY] || '{}');
ok('记录最快用时 progress.best["10"]', typeof (prog.best || {})['10'] === 'number', JSON.stringify(prog.best));
ok('在目标时间内完成 → progress.timeOk["10"]', (prog.timeOk || {})['10'] === 1, JSON.stringify(prog.timeOk));
flush(1400);
openPanel();
ok('达标关卡带金色 ⏱（timeok + timed）',
   hasCls(11, 'timeok') && hasCls(11, 'timed'), gridCls(11));
closePanel2();

// ⑥b 新口径（2026-10-28 用户决定，推翻旧的「重玩不限时」）：重玩已通关的关卡同样限时。
// timeIsTimed()：无尽 false；关卡序号 < 11 false；>= 11 一律 true（含重玩已通关的关卡）。
byId.replay.dispatchEvent(mkEvent('click', { target: byId.replay })); flush(20);
ok('重玩已通关的第 11 关：计时条仍然可见（不再隐藏）', byId.timerChip.hidden === false,
   'hidden=' + byId.timerChip.hidden + ' text=' + JSON.stringify(byId.timerChip.textContent));
ok('重玩时计时条是「限时 m:ss」形态（未操作 → idle，不倒计时）',
   /^限时\s+\d+:\d\d$/.test(String(byId.timerChip.textContent)) &&
   String(byId.timerChip.className).indexOf('idle') >= 0,
   byId.timerChip.textContent + ' / ' + byId.timerChip.className);
const replayLimit = chipMins();                 // 重玩时的本关限时（= 首次挑战同一口径）
tapCell(firstSafe(currentLevel())); flush(20);
ok('重玩时第一次操作后进入倒计时（「⏱ m:ss」，不再是 idle/隐藏）',
   byId.timerChip.hidden === false && /^⏱\s+\d+:\d\d$/.test(String(byId.timerChip.textContent)) &&
   String(byId.timerChip.className).indexOf('idle') < 0,
   byId.timerChip.textContent + ' / ' + byId.timerChip.className);
ok('重玩时的倒计时读数 ≈ 本关限时（与首次挑战同一个 levelLimitSec）',
   replayLimit !== null && chipMins() !== null && Math.abs(replayLimit - chipMins()) <= 1,
   replayLimit + ' → ' + chipMins());
ok('但关卡面板仍标出它是限时关卡（timed）', hasCls(11, 'timed'), gridCls(11));
// 新口径的后果：重玩不再豁免限时——到点同样判负
flush((replayLimit + 5) * 1000);
ok('重玩时限时到点同样判负（不再有「重玩免罚」）', state().status === 'lost', state().status);
ok('重玩的失败原因同样是「⏱ 超时」', String(byId.modalTitle.textContent).indexOf('超时') >= 0,
   byId.modalTitle.textContent);
ok('重玩超时不扣命（仍是 3 架望远镜）', state().lives === 3, String(state().lives));

// ⑥c 反面：第 10 关（序号 < 11）无论首玩还是重玩都不限时——对照组，证明「>= 11 一律限时」不是按通关状态判的
goLevel(10); closePanel2(); flush(20);
ok('第 10 关进入时不显示计时条', byId.timerChip.hidden === true,
   'hidden=' + byId.timerChip.hidden + ' text=' + JSON.stringify(byId.timerChip.textContent));
tapCell(firstSafe(currentLevel())); flush(20);
ok('第 10 关操作后仍不显示计时条（确实没有开始计时）', byId.timerChip.hidden === true,
   'hidden=' + byId.timerChip.hidden + ' text=' + JSON.stringify(byId.timerChip.textContent));
flush(60000);
ok('第 10 关停留远超任何限时也不判负（第 1–10 关确实不受限时约束）',
   state().status === 'playing', state().status);

// ⑦ 新需求：第 11 关起「所有」关卡都带 ⏱，包括未解锁的（按现场解码出的关卡数扫完，摆脱 50 关时代的硬编码）
byId.unlockBtn.dispatchEvent(mkEvent('click', { target: byId.unlockBtn })); flush(20);   // 先收回解锁（恢复锁）
const N = POOLS.campaign.length;
let untimedBad = [], lockedTimedBad = [];
for (let i = 1; i <= 10; i++){ if (hasCls(i, 'timed')) untimedBad.push(i); }
for (let i = 11; i <= N; i++){
  if (!hasCls(i, 'timed')) untimedBad.push(i);
  if (hasCls(i, 'locked') && !hasCls(i, 'timed')) lockedTimedBad.push(i);
}
ok('第 1–10 关不带 ⏱（非限时）', untimedBad.filter(function(n){ return n <= 10; }).length === 0,
   '误标: ' + untimedBad.filter(function(n){ return n <= 10; }).join(','));
ok('第 11–' + N + ' 关全部带 ⏱（含未达标的）', untimedBad.filter(function(n){ return n >= 11; }).length === 0,
   '缺失: ' + untimedBad.filter(function(n){ return n >= 11; }).slice(0, 8).join(',') + (untimedBad.length > 8 ? '…' : ''));
const lockedTimed = [];
for (let i = 11; i <= N; i++) if (hasCls(i, 'locked')) lockedTimed.push(i);
ok('锁定中的限时关卡也带 ⏱（与已解锁一致）',
   lockedTimed.length > 0 && lockedTimed.every(function(n){ return hasCls(n, 'timed'); }),
   '锁定 ' + lockedTimed.length + ' 关，例如 ' + lockedTimed.slice(0, 5).join(','));
ok('锁定关卡同时保留 🔒（locked 类）', lockedTimed.length > 0 && hasCls(lockedTimed[0], 'locked'),
   gridCls(lockedTimed[0] || 11));
ok('全部解锁后仍带 ⏱',
   (function(){ byId.unlockBtn.dispatchEvent(mkEvent('click', { target: byId.unlockBtn })); flush(20);
     let bad = 0; for (let i = 11; i <= N; i++) if (!hasCls(i, 'timed')) bad++; return bad === 0; })(),
   '缺失数 ' + (function(){ let bad = 0; for (let i = 11; i <= N; i++) if (!hasCls(i, 'timed')) bad++; return bad; })());
ok('CSS：.lvl.timed::before 画 ⏱', cssRule('.lvl.timed::before').indexOf('⏱') >= 0, cssRule('.lvl.timed::before'));
ok('CSS：金色 timeok 规则在 timed 之后（覆盖生效）',
   html.indexOf('.lvl.timeok::before') > html.indexOf('.lvl.timed::before'));
closePanel2();

// ⑧ 无尽模式：每题有独立倒计时；闯关的 timeIsTimed() 在无尽恒为 false
if (byId.homeBtn) { byId.homeBtn.dispatchEvent(mkEvent('click', { target: byId.homeBtn })); flush(200); }
if (byId.homeEndless) { byId.homeEndless.dispatchEvent(mkEvent('click', { target: byId.homeEndless })); flush(60); }
else if (byId.introEndless) { byId.introEndless.dispatchEvent(mkEvent('click', { target: byId.introEndless })); flush(60); }
const inEndless = String(bodyEl.dataset.runMode || '') === 'endless';
ok('进入无尽模式用于对照', inEndless === true, 'runMode=' + bodyEl.dataset.runMode);
if (inEndless){
  function chipSecs(){                     // 无尽快照是「⏱ 剩 m:ss」，闯关是「限时 m:ss / ⏱ m:ss」
    const m = String(byId.timerChip.textContent || '').match(/剩\s*(\d+):(\d\d)/);
    return m ? (+m[1] * 60 + +m[2]) : null;
  }
  function toastLimitSec(){                // 开局 toast：「第 N 题 · 随机抽到 n×n（档）· 限时 Xs」
    const kids = (bodyEl.children || []).filter(function(c){ return String(c.className).indexOf('runtoast') >= 0; });
    const m = kids.length ? String(kids[kids.length - 1].textContent).match(/限时\s*(\d+)s/) : null;
    return m ? +m[1] : null;
  }
  const left0 = chipSecs(), lim0 = toastLimitSec();
  ok('现行：无尽每题有倒计时（不再是「不显示限时条」）', byId.timerChip.hidden === false && left0 !== null,
     'hidden=' + byId.timerChip.hidden + ' text=' + JSON.stringify(byId.timerChip.textContent));
  ok('每题倒计时落在 [25, 210] 秒（ENDLESS_TIME_MIN / ENDLESS_TIME_MAX）',
     left0 !== null && left0 >= 25 && left0 <= 210 && lim0 !== null && lim0 >= 25 && lim0 <= 210,
     '读数 ' + left0 + 's · 本题限时 ' + lim0 + 's');
  ok('倒计时起点 = 本题限时（toast 与读数一致）', left0 !== null && lim0 !== null && Math.abs(lim0 - left0) <= 1,
     lim0 + ' vs ' + left0);
  ok('无尽走「每题倒计时」分支、不是闯关限时（未操作就已在倒数、没有 idle 的「限时 …」）',
     String(byId.timerChip.className).indexOf('idle') < 0 && String(byId.timerChip.textContent).indexOf('限时') < 0,
     byId.timerChip.className + ' / ' + byId.timerChip.textContent);

  const lives0 = state().lives, lvId0 = state().levelId, progBefore = store[PROG_KEY] || '';
  flush((left0 + 2) * 1000 + 900);         // 越过本题 deadline + 700ms 换题
  ok('无尽超时扣 1 架望远镜（相对超时前）', state().lives === lives0 - 1, lives0 + ' → ' + state().lives);
  ok('无尽超时后自动换下一题、本轮继续（不判负）',
     state().status === 'playing' && state().levelId !== lvId0,
     lvId0 + ' → ' + state().levelId + ' status=' + state().status);
  ok('无尽倒计时不写闯关最快用时（timeIsTimed() 在无尽为 false）',
     String(store[PROG_KEY] || '') === progBefore, String(store[PROG_KEY] || '').slice(0, 80));
}

const pass = R.filter(x => x.pass === true).length;
const fail = R.filter(x => x.pass === false);
console.log(R.map(x => (x.pass === true ? '  ✓ ' : x.pass === false ? '  ✗ ' : '  · ') + x.name + (x.ev ? '  [' + x.ev + ']' : '')).join('\n'));
console.log(`\nSUMMARY pass=${pass} fail=${fail.length}`);
if (fail.length) { console.log('FAILED:', fail.map(x => x.name).join(' | ')); process.exitCode = 1; }
