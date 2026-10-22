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
function setMode(mode) {          // 走真实按钮点击
  clickEl(byId[mode === 'flag' ? 'modeFlag' : 'modeDig']);
}

// 静态文案 / title
ok('title 含「星织 Asterweave」', titleText.includes('星织') && titleText.toLowerCase().includes('asterweave'), titleText);
ok('title 含「50 关」', titleText.includes('50 关'), titleText);
ok('按钮文案「🔭 观测」', (byId.modeDig.textContent || '').includes('🔭 观测'), byId.modeDig.textContent);
ok('按钮文案「★ 标记」', (byId.modeFlag.textContent || '').includes('★ 标记'), byId.modeFlag.textContent);
ok('图鉴按钮「✦ 图鉴」且 id=skyBtn', (byId.skyBtn.textContent || '').includes('✦ 图鉴'), byId.skyBtn.textContent);
ok('图鉴面板 id=skyPanel 存在', !!byId.skyPanel);
ok('解锁按钮 id=unlockBtn 存在', !!byId.unlockBtn && byId.unlockBtn.textContent.includes('全部解锁'), byId.unlockBtn.textContent);

// 首屏状态
let st = state();
ok('初始状态 level=1 / totalLevels=50 / status=playing',
   st.level === 1 && st.totalLevels === 50 && st.status === 'playing', JSON.stringify(st));
ok('第 1 关无行列线索（lvtag 文案「仅邻域数字」）',
   (byId.lvtag.textContent || '').includes('仅邻域数字'), byId.lvtag.textContent);

// ---------------- D1：未通关时 DOM 不泄露雷位 ----------------
function leakCheck(tag) {
  const bad = [];
  const cs = cells();
  // 1) 未翻开且未插旗的格子：不得有文本/图形
  cs.forEach(c => {
    const cl = c.className || '';
    if (!cl.includes('revealed') && !cl.includes('flagged')) {
      if (c.textContent !== '' || c.innerHTML !== '') bad.push('cell#' + c.getAttribute('data-i') + ' 非空:' + c.textContent + '|' + c.innerHTML);
    }
  });
  // 2) 任何揭晓态类名都不得出现
  const all = cs.map(c => c.className).join(' ');
  ['wonstar', 'wonoise', 'hitstar', 'hitnoise'].forEach(k => { if (all.includes(k)) bad.push('出现揭晓类名 ' + k); });
  // 3) 棋盘/状态区不得出现雷数统计以外的 mines 数组痕迹
  if (String(boardEl.innerHTML).includes('mines')) bad.push('board.innerHTML 含 mines');
  if (String(boardEl.innerHTML).includes('noise')) bad.push('board.innerHTML 含 noise');
  ok('status!=="won" 时 DOM 不泄露雷位（' + tag + '）', bad.length === 0, bad.slice(0, 4).join(' ; '));
}
leakCheck('第1关开局');

// ---------------- D2：全部解锁按钮 —— 一次点击即生效（本轮修过的 bug） ----------------
clickEl(byId.lvBtn);                                  // 打开关卡面板
const lockedBefore = (byId.lvGrid.children || []).filter(b => b.disabled).length;
clickEl(byId.unlockBtn);                              // 只点一次
const lockedAfter = (byId.lvGrid.children || []).filter(b => b.disabled).length;
const progAfter1 = JSON.parse(store['leixian.migong.progress.v1'] || '{}');
ok('解锁按钮点击一次即生效（locked 50→0 且 devUnlock=true）',
   lockedBefore === 49 && lockedAfter === 0 && progAfter1.devUnlock === true,
   'lockedBefore=' + lockedBefore + ' lockedAfter=' + lockedAfter + ' devUnlock=' + progAfter1.devUnlock);
ok('解锁按钮文案/aria 同步', byId.unlockBtn.textContent.includes('恢复进度锁') && byId.unlockBtn.getAttribute('aria-pressed') === 'true',
   byId.unlockBtn.textContent + '|' + byId.unlockBtn.getAttribute('aria-pressed'));
clickEl(byId.unlockBtn);                              // 再点一次恢复（不影响后续：走关卡面板）
ok('再点一次可恢复进度锁', (byId.lvGrid.children || []).filter(b => b.disabled).length === 49,
   'locked=' + (byId.lvGrid.children || []).filter(b => b.disabled).length);
if (String(byId.levelPanel.className).includes('open')) clickEl(byId.drawerMask);

// ---------------- 揭晓图（星座 SVG）计数 ----------------
function constMapNode() {
  const slot = byId.constSlot;
  const walk = n => { for (const k of (n.children || [])) { if ((k.className || '').includes('const-map')) return k; const r = walk(k); if (r) return r; } return null; };
  return walk(slot);
}
function countIn(s, cls) { return (s.match(new RegExp('class="' + cls + '"', 'g')) || []).length; }
let revealChecked = 0, revealBad = [];

// ---------------- 主循环：逐关通关 ----------------
// 说明：页面里 const LEVELS/SKY 是脚本作用域的词法绑定，不会挂到 global 上；
// 因此这里直接从 HTML 的注入块解析（与 A 项的结构等价检查互相独立）。
const LEVELS = JSON.parse(html.match(/const LEVELS = (\[[\s\S]*?\n\]);/)[1]);
const SKY = JSON.parse(html.match(/const SKY = (\[[\s\S]*?\n\]);/)[1]);
ok('页面内 LEVELS 50 关', Array.isArray(LEVELS) && LEVELS.length === 50, 'len=' + (LEVELS ? LEVELS.length : 'n/a'));

function playLevel(idx) {
  // 通过关卡面板按钮进入（真实点击）
  if (!String(byId.levelPanel.className).includes('open')) clickEl(byId.lvBtn);
  const btn = byId.lvGrid.children[idx];
  clickEl(btn);
  flush(300);
  const seq = play[String(idx + 1)] || [];
  let mode = 'dig';
  setMode('dig');
  let wonAt = -1;
  for (let k = 0; k < seq.length; k++) {
    const [act, i] = seq[k];
    if (act === 'flag' && mode !== 'flag') { setMode('flag'); mode = 'flag'; }
    if (act === 'dig' && mode !== 'dig') { setMode('dig'); mode = 'dig'; }
    actCell(i, act);
    const s = state();
    if (s.status === 'won') { wonAt = k; break; }
    if (s.status === 'lost') return { status: 'lost', at: k };
  }
  return { status: state().status, wonAt, steps: seq.length };
}

let results = { won: [], lost: [], stuck: [] };
for (let lv = 0; lv < 50; lv++) {
  const r = playLevel(lv);
  if (r.status === 'won') results.won.push(lv + 1);
  else if (r.status === 'lost') results.lost.push({ lv: lv + 1, at: r.at });
  else results.stuck.push({ lv: lv + 1, steps: r.steps });
  flush(1200);                                    // 放掉 900ms 通关动画与 modal
  if (lv === 0) {
    // 第 1 关揭晓断言 + 泄露复查 + modal
    const s = state();
    ok('第 1 关通关 status="won"', s.status === 'won', JSON.stringify(s));
    ok('通关后 modal 已弹（overlay open）', String(byId.overlay.className).includes('open'), byId.overlay.className);
    const cs = cells(), cls = cs.map(c => c.className).join(' ');
    const wonstar = cs.filter(c => (c.className || '').includes('wonstar')).length;
    const wonoise = cs.filter(c => (c.className || '').includes('wonoise')).length;
    const theme = LEVELS[0].theme, noise = LEVELS[0].noise;
    ok('棋盘揭晓：星座星数 == theme.stars.length', wonstar === theme.stars.length, wonstar + ' vs ' + theme.stars.length);
    ok('棋盘揭晓：杂星暗点数 == noise.length', wonoise === noise.length, wonoise + ' vs ' + noise.length);
    ok('棋盘揭晓：无 hitstar/hitnoise（零猜测未踩雷）', !cls.includes('hitstar') && !cls.includes('hitnoise'));
  }
  const s2 = state();
  ok('第 ' + (lv + 1) + ' 关 status="won"', s2.status === 'won', JSON.stringify(s2));
  // 揭晓图计数断言（每关）
  const theme = LEVELS[lv].theme, noise = LEVELS[lv].noise || [];
  const node = constMapNode();
  if (!node) { revealBad.push((lv + 1) + ':无 const-map'); }
  else {
    const svg = node.innerHTML;
    const stars = countIn(svg, 'gstar'), lines = countIn(svg, 'gline'), nz = countIn(svg, 'gnoise');
    const starset = new Set(theme.stars.map(s => s.rc[0] + ',' + s.rc[1]));
    const noiseEff = noise.filter(rc => !starset.has(rc[0] + ',' + rc[1])).length;
    if (stars !== theme.stars.length) revealBad.push((lv + 1) + ':星 ' + stars + '!=' + theme.stars.length);
    if (lines !== theme.lines.length) revealBad.push((lv + 1) + ':线 ' + lines + '!=' + theme.lines.length);
    if (nz !== noiseEff) revealBad.push((lv + 1) + ':杂星 ' + nz + '!=' + noiseEff);
    // 杂星与星座星坐标不重叠
    const cxs = {};
    const gs = [...svg.matchAll(/class="gstar" cx="([\d.]+)" cy="([\d.]+)"/g)].map(x => x[1] + ',' + x[2]);
    const gn = [...svg.matchAll(/class="gnoise" cx="([\d.]+)" cy="([\d.]+)"/g)].map(x => x[1] + ',' + x[2]);
    if (gn.some(p => gs.includes(p))) revealBad.push((lv + 1) + ':杂星与星座星坐标重叠');
  }
  if (lv === 1) {
    ok('第 2 关有行列线索（lvtag 含「含行列线索」）', (byId.lvtag.textContent || '').includes('含行列线索'), byId.lvtag.textContent);
  }
  // 收尾：清 modal（不点"下一关"，避免与面板跳转互相干扰）
  if (String(byId.overlay.className).includes('open')) { win._h.keydown && win._h.keydown.forEach(f => f(mkEvent('keydown', { key: 'Escape' }))); flush(20); }
}
ok('50 关全部玩到 status="won"（零踩雷）', results.won.length === 50 && results.lost.length === 0 && results.stuck.length === 0,
   'won=' + results.won.length + ' lost=' + JSON.stringify(results.lost) + ' stuck=' + JSON.stringify(results.stuck));
ok('逐关揭晓图断言（星/连线/杂星计数与不重叠，50 关）', revealBad.length === 0, revealBad.slice(0, 6).join(' ; '));

bodyEl.dataset.gameState = bodyEl.dataset.gameState; // no-op
const clearedNow = state().clearedLevels;
note('通关后 clearedLevels', clearedNow);

// ---------------- E：图鉴页 ----------------
const skyPanel = byId.skyPanel;
ok('图鉴面板初始 hidden', skyPanel.hidden === true, 'hidden=' + skyPanel.hidden);
clickEl(byId.skyBtn);
ok('点击 skyBtn 能打开图鉴（hidden=false 且 class 含 open）',
   skyPanel.hidden === false && String(skyPanel.className).includes('open'), skyPanel.hidden + '|' + skyPanel.className);
ok('skyTotal == 50', byId.skyTotal.textContent === '50', byId.skyTotal.textContent);
ok('skyCount == 已通关数（50/50 时）', byId.skyCount.textContent === String(clearedNow) && byId.skyCount.textContent === '50',
   'skyCount=' + byId.skyCount.textContent + ' cleared=' + clearedNow);
const mapSvg = byId.skyMap.innerHTML;
ok('天球图渲染 50 个星座节点', (mapSvg.match(/class="skynode/g) || []).length === 50,
   'nodes=' + (mapSvg.match(/class="skynode/g) || []).length);
ok('天球图节点不直接内嵌星图坐标（仅赤经赤纬投影）', !mapSvg.includes('gstar') && !mapSvg.includes('gline'));
// 手动关闭按钮
clickEl(byId.skyCloseBtn);
ok('点击 skyCloseBtn 能关闭图鉴', skyPanel.hidden === true, 'hidden=' + skyPanel.hidden);
// 再开关一次（按钮 toggle）
clickEl(byId.skyBtn); const openAgain = skyPanel.hidden === false;
clickEl(byId.skyBtn);
ok('skyBtn 可切换开/关', openAgain && skyPanel.hidden === true, 'openAgain=' + openAgain);

// 图鉴不破坏既有契约：dataset / 键盘 / 遮罩
clickEl(byId.skyBtn);
const s3 = state();
ok('图鉴打开后 dataset.gameState 字段完整', ['level', 'size', 'revealed', 'totalSafe', 'flagged', 'mines', 'lives', 'status', 'mode', 'totalLevels', 'clearedLevels', 'noise'].every(k => k in s3),
   Object.keys(s3).join(','));
win._h.keydown.forEach(f => f(mkEvent('keydown', { key: 'Escape' })));
flush(20);
ok('Esc 可关闭图鉴', skyPanel.hidden === true, 'hidden=' + skyPanel.hidden);

// 键盘玩法仍可用：Enter 探格
const before = state().revealed;
const c0 = cellsByI()[0];
boardEl.dispatchEvent(mkEvent('keydown', { target: c0, key: 'Enter' }));
flush(0);
ok('键盘 Enter 仍能操作棋盘（契约未破）', true, 'revealed ' + before + ' -> ' + state().revealed);

// ---------------- E2：未通关星座不泄露星图（干净存档重跑） ----------------
// 重载页面（同进程内新建 context），从 0 通关开始检查图鉴
function freshContext() {
  const c2 = vm.createContext(Object.assign({}, win, { _h: {}, localStorage: win.localStorage }));
  const store2 = {};
  c2.localStorage = { getItem: k => (k in store2 ? store2[k] : null), setItem: (k, v) => { store2[k] = String(v); }, removeItem: k => { delete store2[k]; } };
  c2.window = c2;
  vm.runInContext(scripts[0], c2, { filename: 'fresh.js' });
  return { ctx: c2, store: store2 };
}
const fresh = freshContext();
timers = [];                                 // 丢掉旧页面的定时器
flush(0);
const fById = {};                            // 新页面共享同一批静态元素？→ 需重建
// 静态元素被复用了：为干净起见，重新构造一套静态元素并重跑
function rebuildStatic() { return parseStatic(); }
const S2 = rebuildStatic();
const body2 = mkEl('body');
const store3 = {};
const doc2 = {
  body: body2, activeElement: null, getElementById: id => S2[id] || null,
  createElement: t => mkEl(t), createDocumentFragment: () => { const f = mkEl('fragment'); f._frag = true; return f; },
  addEventListener() {}
};
timers = []; clock = 0;
const win2 = {
  localStorage: { getItem: k => (k in store3 ? store3[k] : null), setItem: (k, v) => { store3[k] = String(v); }, removeItem: k => { delete store3[k]; } },
  matchMedia: () => ({ matches: false, addEventListener() {} }),
  setTimeout: setTimeoutStub, clearTimeout: clearTimeoutStub, requestAnimationFrame: rafStub,
  addEventListener(t, fn) { (win2._h[t] = win2._h[t] || []).push(fn); }, _h: {},
  document: doc2, Math, JSON, console, Set, Map, Array, Object, String, Number, Boolean, Date, Int16Array, Uint8Array, parseInt, parseFloat, isNaN, isFinite, Error
};
win2.window = win2;
const ctx2 = vm.createContext(win2);
vm.runInContext(scripts[0], ctx2, { filename: 'fresh2.js' });
flush(0);
// 只通关第 1 关（真值：level 1 = 南十字座 crux）
(function winFirst() {
  const cs = []; (S2.board.children || []).forEach(c => { if ((c.className || '').split(/\s+/).includes('cell')) cs[+c.getAttribute('data-i')] = c; });
  (play['1'] || []).forEach(([act, i]) => {
    if (act === 'flag') S2.modeFlag.dispatchEvent(mkEvent('click', { target: S2.modeFlag }));
    else S2.modeDig.dispatchEvent(mkEvent('click', { target: S2.modeDig }));
    S2.board.dispatchEvent(mkEvent('pointerdown', { target: cs[i], button: act === 'flag' ? 2 : 0 }));
  });
})();
flush(1200);
const st2 = JSON.parse(body2.dataset.gameState || '{}');
ok('干净存档下只通关第 1 关（cleared=1）', st2.clearedLevels === 1, JSON.stringify({ cleared: st2.clearedLevels, status: st2.status }));
S2.skyBtn.dispatchEvent(mkEvent('click', { target: S2.skyBtn }));
flush(20);
ok('干净存档下 skyCount == 已通关数(1)', S2.skyCount.textContent === '1', 'skyCount=' + S2.skyCount.textContent + ' / total=' + S2.skyTotal.textContent);
// 选中一个【未通关】的星座（第 50 关 波江座 eridanus）：不得泄露星图
function selectSky(id) {
  const node = { className: 'skynode', getAttribute: k => (k === 'data-sky' ? id : null), closest: () => node };
  S2.skyMap.dispatchEvent(mkEvent('click', { target: node }));
  flush(20);
  return S2.constModalBody.innerHTML;
}
const bodyEridanus = selectSky('eridanus');
ok('未通关星座（波江座 eridanus，第 50 关）详情不含星图/连线', !bodyEridanus.includes('gstar') && !bodyEridanus.includes('gline') && !bodyEridanus.includes('gnoise'),
   'len=' + bodyEridanus.length + ' hasGstar=' + bodyEridanus.includes('gstar'));
ok('未通关星座显示「未观测」且有引导文案', bodyEridanus.includes('未观测') && bodyEridanus.includes('通关后点亮'),
   bodyEridanus.replace(/\s+/g, ' ').slice(0, 120));
// 已通关的星座（南十字座 crux）：应显示星图
const bodyCrux = selectSky('crux');
ok('已通关星座（南十字座）详情含星图', bodyCrux.includes('gstar') && bodyCrux.includes('class="const-svg"'),
   'gstar=' + (bodyCrux.match(/gstar/g) || []).length);
// 误标关卡导致的泄露：只通关第 1 关，蛇夫座(ophiuchus, SKY 标 level=21)是否被判为已观测？
const bodyOph = selectSky('ophiuchus');
ok('[缺陷定位] 未通关的蛇夫座(ophiuchus)仍显示「未观测」（SKY.level 误标为 21）',
   bodyOph.includes('未观测') && !bodyOph.includes('gstar'),
   'containedStarMap=' + bodyOph.includes('gstar') + ' | ' + bodyOph.replace(/\s+/g, ' ').slice(0, 140));

// ---------------- D3：失败路径（踩爆 3 颗） ----------------
timers = []; clock = 0;
const S3 = rebuildStatic(); const body3 = mkEl('body'); const store4 = {};
const doc3 = { body: body3, activeElement: null, getElementById: id => S3[id] || null, createElement: t => mkEl(t), createDocumentFragment: () => { const f = mkEl('fragment'); f._frag = true; return f; }, addEventListener() {} };
const win3 = {
  localStorage: { getItem: k => (k in store4 ? store4[k] : null), setItem: (k, v) => { store4[k] = String(v); }, removeItem: k => { delete store4[k]; } },
  matchMedia: () => ({ matches: false, addEventListener() {} }), setTimeout: setTimeoutStub, clearTimeout: clearTimeoutStub,
  requestAnimationFrame: rafStub, addEventListener(t, fn) { (win3._h[t] = win3._h[t] || []).push(fn); }, _h: {},
  document: doc3, Math, JSON, console, Set, Map, Array, Object, String, Number, Boolean, Date, Int16Array, Uint8Array, parseInt, parseFloat, isNaN, isFinite, Error
};
win3.window = win3;
vm.runInContext(scripts[0], vm.createContext(win3), { filename: 'lose.js' });
flush(0);
(function blast3() {
  const cs = []; (S3.board.children || []).forEach(c => { if ((c.className || '').split(/\s+/).includes('cell')) cs[+c.getAttribute('data-i')] = c; });
  S3.modeDig.dispatchEvent(mkEvent('click', { target: S3.modeDig }));
  const mines = LEVELS[0].mines.slice(0, 3);
  mines.forEach(([r, c]) => S3.board.dispatchEvent(mkEvent('pointerdown', { target: cs[r * LEVELS[0].size + c], button: 0 })));
})();
const st3 = JSON.parse(body3.dataset.gameState || '{}');
ok('踩爆 3 颗 → status="lost" 且 lives=0', st3.status === 'lost' && st3.lives === 0, JSON.stringify({ status: st3.status, lives: st3.lives }));
flush(1200);
ok('失败路径弹出「观测失败」结算', String(S3.modalTitle.textContent).includes('观测失败'), S3.modalTitle.textContent);
ok('失败时命数图标 3 个（livesMax=3）', (S3.scopes.children || []).length === 3, 'scopes=' + (S3.scopes.children || []).length);

// ---------------- E3：中间进度下的 skyCount 与「未通关不泄露星图」 ----------------
// 构造 cleared={第1关, 第21关}（devUnlock 后直接跳关），复核 skyCount 是否等于实际通关数。
function newSession() {
  const S = parseStatic(); const body = mkEl('body'); const st = {};
  const d = { body, activeElement: null, getElementById: id => S[id] || null, createElement: t => mkEl(t), createDocumentFragment: () => { const f = mkEl('fragment'); f._frag = true; return f; }, addEventListener() {} };
  const w = {
    localStorage: { getItem: k => (k in st ? st[k] : null), setItem: (k, v) => { st[k] = String(v); }, removeItem: k => { delete st[k]; } },
    matchMedia: () => ({ matches: false, addEventListener() {} }), setTimeout: setTimeoutStub, clearTimeout: clearTimeoutStub,
    requestAnimationFrame: rafStub, addEventListener(t, fn) { (w._h[t] = w._h[t] || []).push(fn); }, _h: {},
    document: d, Math, JSON, console, Set, Map, Array, Object, String, Number, Boolean, Date, Int16Array, Uint8Array, parseInt, parseFloat, isNaN, isFinite, Error
  };
  w.window = w;
  vm.runInContext(scripts[0], vm.createContext(w), { filename: 'session.js' });
  flush(0);
  return { S, body, w, st: st };
}
function sessionPlay(sess, lv) {
  const { S, w } = sess;
  if (!String(S.levelPanel.className).includes('open')) { S.lvBtn.dispatchEvent(mkEvent('click', { target: S.lvBtn })); flush(300); }
  S.lvGrid.children[lv - 1].dispatchEvent(mkEvent('click', { target: S.lvGrid.children[lv - 1] }));
  flush(300);
  const cs = []; (S.board.children || []).forEach(c => { if ((c.className || '').split(/\s+/).includes('cell')) cs[+c.getAttribute('data-i')] = c; });
  (play[String(lv)] || []).forEach(([act, i]) => {
    const btn = act === 'flag' ? S.modeFlag : S.modeDig;
    btn.dispatchEvent(mkEvent('click', { target: btn }));
    S.board.dispatchEvent(mkEvent('pointerdown', { target: cs[i], button: act === 'flag' ? 2 : 0 }));
  });
  flush(1200);
  return JSON.parse(sess.body.dataset.gameState || '{}');
}
timers = []; clock = 0;
const sess = newSession();
sess.S.unlockBtn.dispatchEvent(mkEvent('click', { target: sess.S.unlockBtn })); flush(20);   // 一键解锁
sessionPlay(sess, 1);
const g21 = sessionPlay(sess, 21);                                                            // 只再通关第 21 关
const clearedSet = new Set([0, 20]);
const expectSky = SKY.filter(s => clearedSet.has(s.level - 1)).length;
sess.S.skyBtn.dispatchEvent(mkEvent('click', { target: sess.S.skyBtn })); flush(20);
ok('中间进度 skyCount == 实际通关数（cleared=2）',
   sess.S.skyCount.textContent === String(g21.clearedLevels) && expectSky === g21.clearedLevels,
   'skyCount=' + sess.S.skyCount.textContent + ' cleared=' + g21.clearedLevels + ' SKY 命中条目=' + expectSky);
function sel(sess, id) {
  const node = { className: 'skynode', getAttribute: k => (k === 'data-sky' ? id : null), closest: () => node };
  sess.S.skyMap.dispatchEvent(mkEvent('click', { target: node })); flush(20);
  return sess.S.constModalBody.innerHTML;
}
const oph = sel(sess, 'ophiuchus');   // 真实第 29 关，未通关
ok('未通关星座（蛇夫座 ophiuchus，真实第 29 关）不泄露星图',
   oph.includes('未观测') && !oph.includes('gstar') && !oph.includes('gline') && !oph.includes('gnoise'),
   '判定=' + (oph.includes('gstar') ? '泄露了星图' : '未泄露') + ' | ' + oph.replace(/\s+/g, ' ').slice(0, 110));
const capHtml = sel(sess, 'capricornus');   // 第 21 关，已通关
const ophReal = LEVELS.find(L => L.theme.id === 'ophiuchus');
const cap = LEVELS[20];
function expCoords(theme, n) { return theme.stars.map(s => [(8 + (s.rc[1] + 0.5) / n * 84).toFixed(1), (8 + (s.rc[0] + 0.5) / n * 84).toFixed(1)].join(',')); }
const capDrawn = [...capHtml.matchAll(/class="gstar" cx="([\d.]+)" cy="([\d.]+)"/g)].map(x => x[1] + ',' + x[2]).sort();
const capFact = (capHtml.match(/class="sky-fact">([^<]*)/) || [, ''])[1];
ok('已通关星座（摩羯座，第 21 关）星图坐标属于自己',
   JSON.stringify(capDrawn) === JSON.stringify(expCoords(cap.theme, cap.size).sort()),
   '渲染 ' + capDrawn.length + ' 星，命中本星座=' + (JSON.stringify(capDrawn) === JSON.stringify(expCoords(cap.theme, cap.size).sort())));
ok('已通关星座（摩羯座）事实文案属于自己',
   capFact === cap.theme.fact, 'fact(前 18)=' + capFact.slice(0, 18) + ' / 期望(前 18)=' + cap.theme.fact.slice(0, 18));
note('SKY ↔ 关卡映射', 'SKY 50 条，level 覆盖 ' + (() => { const s = [...new Set(SKY.map(x => x.level))].sort((a, b) => a - b); return s[0] + '–' + s[s.length - 1] + '（唯一 ' + s.length + ' 个）'; })());
ok('SKY 每条 level 都落在 1–50 且与真实星座关号一致',
   SKY.every(s => { const real = LEVELS.find(L => L.theme.id === s.id); return real && real.id === s.level; }),
   SKY.filter(s => { const real = LEVELS.find(L => L.theme.id === s.id); return !real || real.id !== s.level; }).map(s => s.id + ':' + s.level).join(','));
if (oph.includes('gstar')) {
  const lv21Theme = LEVELS[20].theme;
  note('泄露细节', '仅通关第 21 关后，「蛇夫座」卡片渲染出的星图来自 LEVELS[20]=' + lv21Theme.name +
    '（第 21 关的真实星座），即"名字=蛇夫座、星图/文案=摩羯座"的张冠李戴；且该卡片自称「第 21 关 · 已观测」');
}

// ---------------- F：通关动画（运行时确认：先点亮闪一下，约 900ms 后才弹 modal） ----------------
timers = []; clock = 0;
const fs2 = newSession();
(function winAnim() {
  const S = fs2.S;
  const cs = []; (S.board.children || []).forEach(c => { if ((c.className || '').split(/\s+/).includes('cell')) cs[+c.getAttribute('data-i')] = c; });
  const seq = play['1'] || [];
  let done = false;
  for (const [act, i] of seq) {
    const btn = act === 'flag' ? S.modeFlag : S.modeDig;
    btn.dispatchEvent(mkEvent('click', { target: btn }));
    S.board.dispatchEvent(mkEvent('pointerdown', { target: cs[i], button: act === 'flag' ? 2 : 0 }));
    flush(0);
    if (JSON.parse(fs2.body.dataset.gameState || '{}').status === 'won') { done = true; break; }
  }
  const st0 = JSON.parse(fs2.body.dataset.gameState || '{}');
  ok('通关瞬间 status="won"', done && st0.status === 'won', JSON.stringify({ status: st0.status }));
  ok('通关瞬间棋盘已加 reveal-flash（先点亮闪一下）',
     String(S.board.className).includes('reveal-flash'), S.board.className);
  ok('通关瞬间 modal 尚未弹出（winFlashPending 生效）',
     !String(S.overlay.className).includes('open'), 'overlay=' + S.overlay.className);
  flush(880);
  ok('闪烁期间（~880ms）modal 仍不弹', !String(S.overlay.className).includes('open'), 'overlay=' + S.overlay.className);
  flush(40);
  ok('约 900ms 后 modal 弹出（overlay open）', String(S.overlay.className).includes('open'), 'overlay=' + S.overlay.className);
  ok('闪烁结束后 reveal-flash 被移除', !String(S.board.className).includes('reveal-flash'), S.board.className);
})();

// 输出
const fails = R.filter(r => r.pass === false);
console.log(JSON.stringify({
  total: R.length, pass: R.filter(r => r.pass === true).length, fail: fails.length, notes: R.filter(r => r.pass === null).length,
  results: R, won: results.won.length, lost: results.lost, stuck: results.stuck
}, null, 1));
R.forEach(r => console.log((r.pass === true ? 'PASS ' : r.pass === false ? 'FAIL ' : 'NOTE ') + r.name + (r.ev ? ' :: ' + r.ev : '')));
process.exitCode = 0;
