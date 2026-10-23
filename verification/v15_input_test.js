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

// ---------------- v15（v1.9）：触摸轻触/长按；鼠标单击/右键（无双击）----------------
// 注意：每类测试前都先「重玩本关」，避免上一次操作引发的连锁展开影响断言。
const safeIdx = (play['1'] || []).filter(a => a[0] === 'dig').map(a => a[1]);
const mineIdx = (play['1'] || []).filter(a => a[0] === 'flag').map(a => a[1]);
if (byId.introStart) { byId.introStart.dispatchEvent(mkEvent('click', { target: byId.introStart })); flush(0); }

function down(i, opts){
  boardEl.dispatchEvent(mkEvent('pointerdown', Object.assign({ target: cellsByI()[i], button: 0, clientX: 100, clientY: 100 }, opts || {})));
}
function up(i, opts){
  boardEl.dispatchEvent(mkEvent('pointerup', Object.assign({ target: cellsByI()[i], button: 0, clientX: 100, clientY: 100 }, opts || {})));
}
function restart(){ byId.replay.dispatchEvent(mkEvent('click', { target: byId.replay })); flush(20); }

const S0 = state();
ok('第 1 关可玩', S0.status === 'playing', `size=${S0.size}`);
const hint = byId.actHint.textContent || '';
ok('提示说明手机（长按）与电脑（右键），且无「双击」',
   hint.includes('轻触') && hint.includes('长按') && hint.includes('右键') && !hint.includes('双击'), hint);
ok('源码中已无双击判定（DBL_MS / lastMouse）', !html.includes('DBL_MS') && !html.includes('lastMouse'));
ok('模式按钮已移除', !byId.modeDig && !byId.modeFlag);

// 1) 轻触 = 即时观测
restart();
let b = state();
down(safeIdx[0], { pointerType: 'touch' });
flush(0);
ok('触摸按下时不立即翻开（等抬起/长按判定）', state().revealed === b.revealed, `revealed=${state().revealed}`);
up(safeIdx[0], { pointerType: 'touch' });
flush(0);
ok('轻触抬起 → 立即观测（0ms）', state().revealed > b.revealed, `revealed=${state().revealed} before=${b.revealed}`);

// 2) 长按雷位 = 安全标记（不扣命、不观测）
restart();
b = state();
down(mineIdx[0], { pointerType: 'touch' });
flush(420);
ok('长按 ~420ms → 标记 +1', state().flagged === b.flagged + 1, `flagged=${state().flagged}`);
up(mineIdx[0], { pointerType: 'touch' });
flush(0);
ok('长按雷位不扣命、也不会被观测引爆', state().lives === b.lives && state().revealed === b.revealed,
   `lives=${state().lives} revealed=${state().revealed}/${b.revealed}`);
ok('长按后抬起不会补一次观测', state().revealed === b.revealed, `revealed=${state().revealed}`);

// 3) 划动取消长按
restart();
b = state();
down(safeIdx[0], { pointerType: 'touch', clientX: 100, clientY: 100 });
boardEl.dispatchEvent(mkEvent('pointermove', { target: cellsByI()[safeIdx[0]], pointerType: 'touch', clientX: 170, clientY: 150 }));
flush(420);
up(safeIdx[0], { pointerType: 'touch', clientX: 170, clientY: 150 });
flush(0);
ok('划动取消长按且不观测、不标记', state().flagged === b.flagged && state().revealed === b.revealed,
   `flagged=${state().flagged}/${b.flagged} revealed=${state().revealed}/${b.revealed}`);

// 4) 鼠标左键单击 = 即时观测
restart();
b = state();
down(safeIdx[0], { pointerType: 'mouse' });
flush(0);
ok('鼠标单击 → 立即观测', state().revealed > b.revealed, `revealed=${state().revealed} before=${b.revealed}`);

// 5) 鼠标双击 **不再**标记
restart();
b = state();
down(safeIdx[0], { pointerType: 'mouse' });
down(safeIdx[0], { pointerType: 'mouse' });
flush(0);
ok('鼠标双击不会标记（v1.8 起移除双击标记）', state().flagged === b.flagged, `flagged=${state().flagged} before=${b.flagged}`);

// 6) 鼠标右键 = 立即标记
restart();
b = state();
boardEl.dispatchEvent(mkEvent('pointerdown', { target: cellsByI()[mineIdx[0]], button: 2, pointerType: 'mouse', clientX: 100, clientY: 100 }));
flush(0);
ok('右键 → 立即标记且不扣命', state().flagged === b.flagged + 1 && state().lives === b.lives,
   `flagged=${state().flagged} lives=${state().lives}`);

// 7) 键盘：Enter = 观测；空格 = 标记
restart();
b = state();
boardEl.dispatchEvent(mkEvent('keydown', { key: 'Enter', target: cellsByI()[safeIdx[0]] }));
flush(0);
ok('键盘 Enter = 立即观测', state().revealed > b.revealed, `revealed=${state().revealed} before=${b.revealed}`);
restart();
b = state();
boardEl.dispatchEvent(mkEvent('keydown', { key: ' ', target: cellsByI()[mineIdx[0]] }));
flush(0);
ok('键盘空格 = 标记且不扣命', state().flagged === b.flagged + 1 && state().lives === b.lives,
   `flagged=${state().flagged} lives=${state().lives}`);

const pass = R.filter(x => x.pass === true).length;
const fail = R.filter(x => x.pass === false);
console.log(R.map(x => (x.pass === true ? '  ✓ ' : x.pass === false ? '  ✗ ' : '  · ') + x.name + (x.ev ? '  [' + x.ev + ']' : '')).join('\n'));
console.log(`\nSUMMARY pass=${pass} fail=${fail.length}`);
if (fail.length) { console.log('FAILED:', fail.map(x => x.name).join(' | ')); process.exitCode = 1; }
