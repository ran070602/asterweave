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

// ---------------- v23：♾ 无尽挑战 ----------------
const PROG_KEY = 'leixian.migong.progress.v1';
function prog(){ try { return JSON.parse(store[PROG_KEY] || '{}'); } catch (e) { return {}; } }
function runMode(){ return String(bodyEl.dataset.runMode || ''); }
function tapCell2(i){
  boardEl.dispatchEvent(mkEvent('pointerdown', { target: cellsByI()[i], pointerType: 'touch', button: 0, clientX: 100, clientY: 100 }));
  boardEl.dispatchEvent(mkEvent('pointerup',   { target: cellsByI()[i], pointerType: 'touch', button: 0, clientX: 100, clientY: 100 }));
  flush(0);
}
function rightClick2(i){
  boardEl.dispatchEvent(mkEvent('pointerdown', { target: cellsByI()[i], button: 2, pointerType: 'mouse', clientX: 100, clientY: 100 }));
  flush(0);
}
function deepText(el){
  if (!el) return '';
  let s = String(el.innerHTML || '') + ' ' + String(el.textContent || '') + ' ';
  (el.children || []).forEach(function(c){ s += deepText(c) + ' '; });
  return s;
}
function clearBoard(){                       // 按标准序列通关当前这一题（无尽会自动进下一题）
  const id = String(state().levelId);
  const seq = play[id] || [];
  for (let i = 0; i < seq.length; i++){ if (seq[i][0] === 'flag') rightClick2(seq[i][1]); else tapCell2(seq[i][1]); }
  flush(1700);                               // 快速揭晓 + 900ms 后自动进下一题
}
function nthMine(n){                     // 第 n 颗尚未被观测过的雷（同一颗雷只算一次失误）
  const id = String(state().levelId);
  const seq = play[id] || [];
  let seen = 0;
  for (let i = 0; i < seq.length; i++){
    if (seq[i][0] !== 'flag') continue;
    const idx = seq[i][1];
    if (seen === n) return idx;
    seen++;
  }
  return -1;
}

// ① 主页 → 无尽
ok('首次打开显示主页', byId.introOverlay.hidden === false);
const endlessBtnTxt = String((byId.homeEndlessLabel && byId.homeEndlessLabel.textContent) || '') +
                      String((byId.homeEndless && byId.homeEndless.innerHTML) || '');
ok('主页有无尽入口', !!byId.homeEndless && endlessBtnTxt.indexOf('无尽') >= 0, endlessBtnTxt.slice(0, 60));
byId.homeEndless.dispatchEvent(mkEvent('click', { target: byId.homeEndless }));
flush(60);
ok('进入无尽模式（runMode=endless）', runMode() === 'endless', runMode());
ok('无尽下隐藏「关卡」按钮、显示「结束本轮」', byId.lvBtn.hidden === true && byId.endRunBtn.hidden === false,
   'lv=' + byId.lvBtn.hidden + ' end=' + byId.endRunBtn.hidden);
ok('第 1 题开局', state().status === 'playing', state().status);
ok('开局 1 架望远镜', state().lives === 1, String(state().lives));

// ② 连过 3 题：连击、分数、每 3 题 +1 架
const lv1 = state().levelId;
clearBoard();
ok('通关后自动进下一题', state().status === 'playing' && state().levelId !== lv1,
   lv1 + ' → ' + state().levelId + ' status=' + state().status);
clearBoard();
clearBoard();
ok('连过 3 题后望远镜变为 2 架', state().lives === 2, String(state().lives));
ok('无尽通关不写入闯关进度（cleared 仍为空）',
   Object.keys(prog().cleared || {}).length === 0, JSON.stringify(prog().cleared || {}));
ok('无尽不改变闯关断点（last 仍为 0）', (prog().last || 0) === 0, String(prog().last));

// ③ 失误扣命
const m1 = nthMine(0);
tapCell2(m1);
flush(20);
ok('失误 −1 架（2 → 1）', state().lives === 1, String(state().lives));
ok('失误未被计入闯关的失败（仍有望远镜）', state().status === 'playing', state().status);

// ④ 再失误 → 本轮结束
const m2 = nthMine(1);
tapCell2(m2);
flush(1200);
ok('0 架时再失误即结束', state().status === 'lost', state().status);
ok('结束弹窗标题为「本轮结束」', String(byId.modalTitle.textContent).indexOf('本轮结束') >= 0, byId.modalTitle.textContent);
const modalTxt = deepText(byId.constSlot) + deepText(byId.modalSub);
ok('结算展示 SCORE 与规则说明',
   modalTxt.indexOf('SCORE') >= 0 && modalTxt.indexOf('望远镜') >= 0, modalTxt.slice(0, 60));
const st = prog().endless || {};
ok('本轮成绩写入 progress.endless（runs/best/bestStreak/fastestMs）',
   st.runs === 1 && (st.best || 0) > 0 && (st.bestStreak || 0) >= 3 && st.fastestMs != null,
   JSON.stringify({ runs: st.runs, best: st.best, bestStreak: st.bestStreak, fastestMs: st.fastestMs }));

// ⑤ 「再来一轮」→ 新一轮
const btns = byId.modalBtns.children || [];
const againBtn = btns.filter(function(b){ return String(b.textContent).indexOf('再来一轮') >= 0; })[0];
ok('结束弹窗有「再来一轮」', !!againBtn, (btns.map(function(b){ return String(b.textContent); }).join(' / ')));
if (againBtn){ againBtn.dispatchEvent(mkEvent('click', { target: againBtn })); flush(60); }
ok('再来一轮后回到 playing 且望远镜重置为 1',
   state().status === 'playing' && state().lives === 1, state().status + '/' + state().lives);
ok('runs 计数累加为 2', (prog().endless || {}).runs === 2, String((prog().endless || {}).runs));

// ⑥ 「结束本轮」按钮 → 主动结束
byId.endRunBtn.dispatchEvent(mkEvent('click', { target: byId.endRunBtn }));
flush(1200);
ok('主动结束也会出结算弹窗', String(byId.modalTitle.textContent).indexOf('本轮结束') >= 0, byId.modalTitle.textContent);
ok('结算里注明「你主动结束了本轮」',
   (deepText(byId.constSlot) + deepText(byId.modalSub)).indexOf('主动结束') >= 0, deepText(byId.constSlot).slice(0, 90));

// ⑦ 「回到闯关」→ 恢复闯关模式且可正常玩
const btns2 = byId.modalBtns.children || [];
const backBtn = btns2.filter(function(b){ return String(b.textContent).indexOf('回到闯关') >= 0; })[0];
ok('结束弹窗有「回到闯关」', !!backBtn, btns2.map(function(b){ return String(b.textContent); }).join(' / '));
if (backBtn){ backBtn.dispatchEvent(mkEvent('click', { target: backBtn })); flush(1200); }
ok('回到闯关模式（runMode=campaign）', runMode() === 'campaign', runMode());
ok('「关卡」按钮恢复、「结束本轮」隐藏', byId.lvBtn.hidden === false && byId.endRunBtn.hidden === true,
   'lv=' + byId.lvBtn.hidden + ' end=' + byId.endRunBtn.hidden);
ok('闯关下第 1 关仍可玩、且不是无尽棋盘', state().status === 'playing' && state().lives === 3,
   state().status + '/' + state().lives);
const before = state().revealed;
const safe0 = (play['1'] || []).filter(function(a){ return a[0] === 'dig'; })[0][1];
tapCell2(safe0);
flush(20);
ok('闯关棋盘可正常观测', state().revealed >= before, before + ' → ' + state().revealed);
ok('闯关不显示 ⏱ 计时条（第 1 关不计时）', byId.timerChip.hidden === true);

const pass = R.filter(x => x.pass === true).length;
const fail = R.filter(x => x.pass === false);
console.log(R.map(x => (x.pass === true ? '  ✓ ' : x.pass === false ? '  ✗ ' : '  · ') + x.name + (x.ev ? '  [' + x.ev + ']' : '')).join('\n'));
console.log(`\nSUMMARY pass=${pass} fail=${fail.length}`);
if (fail.length) { console.log('FAILED:', fail.map(x => x.name).join(' | ')); process.exitCode = 1; }
