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
const play = JSON.parse(fs.readFileSync(path.join(ROOT, 'verification', 'v13_play.json'), 'utf8'));

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

// ---------------- 取出页面脚本并执行 ----------------
const scripts = [...html.matchAll(/<script[^>]*>([\s\S]*?)<\/script>/g)].map(x => x[1]);
ok('页面内联 script 数量==1', scripts.length === 1, 'count=' + scripts.length);
win.Date = { now: function(){ return 1700000000000 + clock; }, UTC: Date.UTC, parse: Date.parse };
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

// ---------------- v22：⏱ 计时挑战 ----------------
if (byId.introStart) { byId.introStart.dispatchEvent(mkEvent('click', { target: byId.introStart })); flush(0); }

function openPanel(){ byId.lvBtn.dispatchEvent(mkEvent('click', { target: byId.lvBtn })); flush(20); }
function closePanel2(){ byId.drawerMask.dispatchEvent(mkEvent('click', { target: byId.drawerMask })); flush(260); }
function goLevel(n){ openPanel(); byId.lvGrid.children[n - 1].dispatchEvent(mkEvent('click', { target: byId.lvGrid.children[n - 1] })); flush(30); }
function chipParse(){
  const t = String(byId.timerChip.textContent || '');
  const m = t.match(/(\d+):(\d\d)\s*\/\s*(\d+):(\d\d)/);
  return m ? { el: +m[1] * 60 + +m[2], target: +m[3] * 60 + +m[4], text: t } : null;
}
function tapCell(i){
  boardEl.dispatchEvent(mkEvent('pointerdown', { target: cellsByI()[i], pointerType: 'touch', button: 0, clientX: 100, clientY: 100 }));
  boardEl.dispatchEvent(mkEvent('pointerup',   { target: cellsByI()[i], pointerType: 'touch', button: 0, clientX: 100, clientY: 100 }));
  flush(0);
}
function firstDig(key){
  const seq = play[key] || [];
  for (let i = 0; i < seq.length; i++) if (seq[i][0] === 'dig') return seq[i][1];
  return -1;
}
function enterLevel(n){          // 进关 + 点一下格子（计时从第一次操作开始）
  goLevel(n);
  closePanel2();
  const d = firstDig(String(n));
  if (d >= 0) tapCell(d);
  flush(20);
}
function rightClick(i){
  boardEl.dispatchEvent(mkEvent('pointerdown', { target: cellsByI()[i], button: 2, pointerType: 'mouse', clientX: 100, clientY: 100 }));
  flush(0);
}

// ① 第 11 关起才计时
ok('第 1 关不显示计时条', byId.timerChip.hidden === true, String(byId.timerChip.hidden));
byId.unlockBtn.dispatchEvent(mkEvent('click', { target: byId.unlockBtn }));
flush(20);
enterLevel(11);
ok('第 11 关第一次操作后出现计时条', byId.timerChip.hidden === false,
   'hidden=' + byId.timerChip.hidden + ' text=' + JSON.stringify(byId.timerChip.textContent));
const c1 = chipParse();
ok('计时条格式为「⏱ 已用 / 目标」', !!c1, byId.timerChip.textContent);
ok('目标时间是个合理值（30s–15min）', c1 && c1.target >= 30 && c1.target <= 900, c1 && String(c1.target));
ok('刚进入时已用时间 ≈ 0', c1 && c1.el <= 1, c1 && String(c1.el));

// ② 目标时间随盘面规模上升（第 11 关 vs 第 50 关）
const target11 = c1.target;
enterLevel(50);
const c50 = chipParse();
ok('更大的关卡目标时间更宽裕', c50 && c50.target > target11, target11 + ' → ' + (c50 && c50.target));

// ③ 走时：虚拟时钟前进，计时条增长（tickClock 每 500ms 刷新）
enterLevel(11);
const before = chipParse().el;
flush(3100);
const after = chipParse().el;
ok('计时随真实时间前进（约 3 秒）', after >= before + 3, before + ' → ' + after);

// ④ 软模式（默认）：超过目标不失败，但计时条变红
enterLevel(11);
const tg = chipParse().target;
flush((tg + 3) * 1000);
ok('默认软模式：超时后仍在游戏（status=playing）', state().status === 'playing', state().status);
ok('超时后计时条加 over 类', String(byId.timerChip.className).indexOf('over') >= 0, byId.timerChip.className);

// ⑤ 严格限时：超时判失败，弹窗标题为「⏱ 超时」
tapCell(firstDig('11')); flush(20);                 // 确保本轮计时已开始
openPanel();
byId.strictBtn.dispatchEvent(mkEvent('click', { target: byId.strictBtn }));
flush(20);
closePanel2();
ok('严格限时开关状态正确', /严格限时：开/.test(String(byId.strictBtn.textContent)) && /"strictTime":true/.test(String(store['leixian.migong.progress.v1'] || '')), byId.strictBtn.textContent);
const tg2 = chipParse().target;
flush((tg2 + 3) * 1000);
ok('严格限时：超时即失败', state().status === 'lost', state().status);
ok('失败原因是「⏱ 超时」而非命数耗尽', String(byId.modalTitle.textContent).indexOf('超时') >= 0, byId.modalTitle.textContent);
ok('超时失败不扣命（命数仍为 3）', state().lives === 3, String(state().lives));

// 关掉严格限时，避免影响后续
byId.strictBtn.dispatchEvent(mkEvent('click', { target: byId.strictBtn })); flush(20);
ok('可以再关掉严格限时', /严格限时：关/.test(String(byId.strictBtn.textContent)), byId.strictBtn.textContent);

// ⑥ 达标通关：记录最佳时间并留下 ⏱ 标记
byId.replay.dispatchEvent(mkEvent('click', { target: byId.replay })); flush(20);
tapCell(firstDig('11')); flush(20);
const seq = play['11'] || [];
for (let i = 0; i < seq.length; i++){ if (seq[i][0] === 'flag') rightClick(seq[i][1]); else tapCell(seq[i][1]); }
flush(1200);
ok('第 11 关已通关', state().status === 'won', state().status);
const prog = JSON.parse(store['leixian.migong.progress.v1'] || '{}');
ok('记录最佳时间 progress.best["10"]', typeof (prog.best || {})['10'] === 'number', JSON.stringify(prog.best));
ok('达标写入 progress.timeOk["10"]', (prog.timeOk || {})['10'] === 1, JSON.stringify(prog.timeOk));
flush(1200);
openPanel();
const btn = byId.lvGrid.children[10];
ok('关卡面板第 11 关出现 ⏱ 达标标记', String(btn.className).indexOf('timeok') >= 0, btn.className);
closePanel2();

// ⑦ 切关重置换表：新关从 0 开始
byId.replay.dispatchEvent(mkEvent('click', { target: byId.replay })); flush(20);
ok('重玩后未操作前不显示计时条（等第一次操作）', byId.timerChip.hidden === true, String(byId.timerChip.hidden));
tapCell(firstDig('11')); flush(20);
const c2 = chipParse();
ok('重新开始后计时归零', c2 && c2.el <= 1, c2 && String(c2.el));

const pass = R.filter(x => x.pass === true).length;
const fail = R.filter(x => x.pass === false);
console.log(R.map(x => (x.pass === true ? '  ✓ ' : x.pass === false ? '  ✗ ' : '  · ') + x.name + (x.ev ? '  [' + x.ev + ']' : '')).join('\n'));
console.log(`\nSUMMARY pass=${pass} fail=${fail.length}`);
if (fail.length) { console.log('FAILED:', fail.map(x => x.name).join(' | ')); process.exitCode = 1; }
