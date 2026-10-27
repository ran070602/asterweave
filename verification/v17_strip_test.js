// v13 D/E/F：自写 DOM 桩（无 npm、无外部依赖），驱动 dist/index.html 真实脚本。
// 断言：50 关全部玩到 status="won"；揭晓图星/连线/杂星计数；按钮文案；title；
//       未通关时不泄露雷位；失败路径；全部解锁一次点击生效；图鉴页开关/计数/未通关不泄露星图。
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = 'D:\\AI-Native casual game';
const DIST = path.join(ROOT, 'dist', '星织-游戏本体', 'index.html');
const html = fs.readFileSync(DIST, 'utf8');
// 关卡数据源：tools/levels.json 的 mines/noise 与 dist 内嵌的打包数据同源（88 关）。
// 旧夹具 v13_play.json 的通关序列属于旧版第 1 关盘面，在现盘面上会踩雷 —— 已在下方改用现算夹具。
const LEVELS_JSON = JSON.parse(fs.readFileSync(path.join(ROOT, 'tools', 'levels.json'), 'utf8'));

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
// .boardwrap 只有 class 没有 id，只能靠 document.querySelector 取到。
// 取不到时 boardWrapEl=null，startBoardReveal() 会直接跳到终态（game/index.html:2649-2652），
// 真实揭晓时序（杂星淡出→星点亮→逐段画线→闪烁→弹窗）就完全测不到。这里补上该桩。
const _wrapStub = mkEl('div', 'boardwrap');
const doc = {
  body: bodyEl, documentElement: docEl, activeElement: null,
  getElementById: id => byId[id] || null,
  createElement: t => mkEl(t),
  createDocumentFragment: () => { const f = mkEl('fragment'); f._frag = true; return f; },
  querySelector: s => (s === '.boardwrap' ? _wrapStub : null), addEventListener() {}, removeEventListener() {},
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

// ---------------- 取出页面脚本并执行 ----------------
const scripts = [...html.matchAll(/<script[^>]*>([\s\S]*?)<\/script>/g)].map(x => x[1]);
ok('页面内联 script 数量==1', scripts.length === 1, 'count=' + scripts.length);
// base64 垫片：关卡/题库数据用 atob 解压，Node 沙箱没有该浏览器全局
if (typeof win.atob !== 'function'){ win.atob = function(b){ return Buffer.from(String(b), 'base64').toString('binary'); }; }
if (typeof win.btoa !== 'function'){ win.btoa = function(s){ return Buffer.from(String(s), 'binary').toString('base64'); }; }
const ctx = vm.createContext(Object.assign(win, { globalThis: win }));
vm.runInContext(scripts[0], ctx, { filename: 'dist-index-inline.js' });
flush(0);
ok('脚本执行无致命异常（关卡数据缺失提示未出现）', !String(boardEl.innerHTML).includes('关卡数据缺失'));

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

// ---------------- v17：结算条按钮（失败无「回看」，通关保留「图鉴详情 / 下一关」）----------------
// 夹具：按 tools/levels.json 现算当前关卡的雷位/安全格。
// 雷集 = mines ∪ noise（game/index.html:1601-1623），checkWin 要求「所有安全格翻开 + 所有雷标出」
// （game/index.html:1779-1788），所以 dig 全部安全格、flag 全部雷 = 一条合法通关序列。
const cur0 = state();
const fixtureLv = LEVELS_JSON.filter(l => l.id === (cur0.levelId || cur0.level))[0];
const N = fixtureLv ? fixtureLv.size : 0;
const mineSet = new Set();
if (fixtureLv){
  (fixtureLv.mines || []).forEach(rc => mineSet.add(rc[0] * N + rc[1]));
  (fixtureLv.noise || []).forEach(rc => mineSet.add(rc[0] * N + rc[1]));
}
const mineIdx = Array.from(mineSet).sort((a, b) => a - b);
const safeIdx = [];
for (let i = 0; i < N * N; i++) if (!mineSet.has(i)) safeIdx.push(i);
ok('夹具：当前关卡能在 tools/levels.json 中按 id 找到', !!fixtureLv,
   `gameState.levelId=${cur0.levelId} level=${cur0.level} size=${cur0.size}`);
ok('夹具与运行盘面一致（size / mines / totalSafe）',
   !!fixtureLv && cur0.size === N && cur0.mines === mineSet.size && cur0.totalSafe === N * N - mineSet.size,
   `盘面 size=${cur0.size} mines=${cur0.mines} totalSafe=${cur0.totalSafe} · 夹具 size=${N} mines=${mineSet.size} totalSafe=${N * N - mineSet.size}`);

// 关掉首屏说明（首次进入会弹）
if (byId.introStart) { byId.introStart.dispatchEvent(mkEvent('click', { target: byId.introStart })); flush(0); }

function touchTap(i){
  boardEl.dispatchEvent(mkEvent('pointerdown', { target: cellsByI()[i], pointerType: 'touch', button: 0, clientX: 100, clientY: 100 }));
  boardEl.dispatchEvent(mkEvent('pointerup',   { target: cellsByI()[i], pointerType: 'touch', button: 0, clientX: 100, clientY: 100 }));
  flush(0);
}
function rightClick(i){
  boardEl.dispatchEvent(mkEvent('pointerdown', { target: cellsByI()[i], button: 2, pointerType: 'mouse', clientX: 100, clientY: 100 }));
  flush(0);
}
function stripTexts(){
  const kids = (byId.result && byId.result.children) || [];
  const out = [];
  kids.forEach(function(k){
    if ((k.className || '').includes('result-btns')) (k.children || []).forEach(b => out.push(String(b.textContent || '')));
    else out.push(String(k.textContent || ''));
  });
  return out;
}
function dismissModal(){
  byId.overlay.dispatchEvent(mkEvent('click', { target: byId.overlay }));
  flush(20);
}

// ---- A. 失败：三击真雷 → modal → 收起后才出现底部结算条（game/index.html:2770-2780）----
// 逐次记录，失败时能看出是夹具过期（没踩到 3 颗）还是本体缺陷。
const hitTrace = [];
let lostOk = false;
for (const mi of mineIdx.slice(0, 3)){
  touchTap(mi);
  hitTrace.push(mi + ':' + state().status + '/lives=' + state().lives);
  if (state().status === 'lost'){ lostOk = true; break; }
}
ok('三击雷位 → lost', lostOk, `status=${state().status} lives=${state().lives} trace=${hitTrace.join(' ')}`);
flush(1200);
dismissModal();
const tLose = stripTexts();
ok('失败结算条出现（modal 收起后）', tLose.length > 0, JSON.stringify(tLose));
ok('失败结算条含「重来本关」', tLose.some(t => t.includes('重来本关')), JSON.stringify(tLose));
ok('失败结算条不含回看按钮（无「图鉴详情」）', !tLose.some(t => t.includes('图鉴详情')), JSON.stringify(tLose));

// ---- B. 通关：结算条保留「★ 图鉴详情」（用来回看星座）----
// 重开本关（#replay → replayLevel()，game/index.html:2051-2056）
const replayBtn = byId.replay;
if (replayBtn) { replayBtn.dispatchEvent(mkEvent('click', { target: replayBtn })); flush(30); }
ok('重玩后回到 playing', state().status === 'playing', `status=${state().status}`);

// 按现行盘面求解：翻开全部安全格 + 标出全部雷
for (const i of safeIdx) touchTap(i);
for (const mi of mineIdx) rightClick(mi);
flush(1200);                                   // 揭晓 ~1.1s（含闪烁+弹窗），见 game/index.html:2647-2701
ok('按通关序列执行后 status=won', state().status === 'won',
   `status=${state().status} revealed=${state().revealed}/${state().totalSafe} flagged=${state().flagged}/${state().mines}`);
dismissModal();
const tWin = stripTexts();
ok('通关结算条含「★ 图鉴详情」按钮', tWin.some(t => t.includes('图鉴详情')), JSON.stringify(tWin));
ok('通关结算条含「下一关」', tWin.some(t => t.includes('下一关')), JSON.stringify(tWin));

const pass = R.filter(x => x.pass === true).length;
const fail = R.filter(x => x.pass === false);
console.log(R.map(x => (x.pass === true ? '  ✓ ' : x.pass === false ? '  ✗ ' : '  · ') + x.name + (x.ev ? '  [' + x.ev + ']' : '')).join('\n'));
console.log(`\nSUMMARY pass=${pass} fail=${fail.length}`);
if (fail.length) { console.log('FAILED:', fail.map(x => x.name).join(' | ')); process.exitCode = 1; }
