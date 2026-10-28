// v24：命数评价（🔭 历史最佳剩余望远镜数 / ✦ 完美观测）—— 自写 DOM 桩（无 npm、无外部依赖），驱动 dist/index.html 真实脚本。
//
// 覆盖：
//   ① 默认与向后兼容：全新存档 / 老存档缺 bestLives → 面板「完美 0/88」、无任何格子带 perfect
//   ② 零失误通关 → 满分：bestLives=3、格子 perfect、aria-label「，完美观测」、#perfectCount=1、
//      #lvtag「最佳 🔭×3」、结算「本次 🔭 3/3」+ .modal-perfect
//   ③ 失误一次通关 → 有评价但非满分：bestLives=2、无 perfect、#perfectCount=0、#lvtag「最佳 🔭×2」、
//      结算「本次 🔭 2/3」且没有 .modal-perfect
//   ④ 只增不减（历史最佳）：先满分（3）再故意失误通关（本次 2）→ 仍为 3 且格子仍带 perfect
//   ⑤ 重玩也能刷新：先失误通关（2）再从干净状态零失误通关 → 升到 3
//   ⑥ 无尽模式不记录：进无尽、通关一题 → progress.bestLives 不变
//   ⑦ CSS 契约：页面有 .lvl.perfect（左下金点 radial-gradient），注释点出「左上 ⏱、右上 ✓/🔒 已占用」
//      （并用实际 CSS 反证：.lvl.timed::before 占 left、.lvl.cleared/.locked::after 占 right）
//
// 盘面序列全部「现场解码」自页面内联数据（LEVELS_PACKED 锚点 + expandLevelsPacked 展开结果），
// 不使用 verification/v13_play.json（那份是 50 关时代的旧录像，按键取值已对不上当前盘面）。
// 雷集口径与 startBoard 一致：mines ∪ noise。
//
// 两个沙箱（同一份 dist 产物、各造一套元素）：
//   · FRESH = 全新存档（localStorage 里连存档键都没有）→ 跑【1】的「全新存档」与【2】的首通满分
//   · MAIN  = 老存档（有 cleared/best/timeOk，唯独没有 bestLives）→ 跑【1】的兜底、【6】【3】【5】【4】【7】
// 用 useSandbox() 在两者间切换；两者状态互不影响，断言各归各的。
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const crypto = require('crypto');

const ROOT = 'D:\\AI-Native casual game';
const DIST = path.join(ROOT, 'dist', '星织-游戏本体', 'index.html');
const html = fs.readFileSync(DIST, 'utf8');

// ---------- 数据导出补丁：只改测试手里那份 HTML 字符串副本，把解码结果挂到 globalThis ----------
// 注入块在 IIFE 里，外部读不到常量；打完补丁再交给 vm，跑完从 ctx 取 LEVELS / BANK。
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

// ---------------- 计时器（可手动 flush，用于验证通关揭晓动画） ----------------
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
let doc = null;                     // 当前沙箱的 document（mkEl.focus 会写它）
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
    focus() { if (doc) doc.activeElement = this; }, blur() {}, scrollIntoView() {}, click() { this.dispatchEvent(mkEvent('click', { target: this })); },
    get firstChild() { return this.children[0] || null; },
    remove() { if (this.parentNode) this.parentNode.children = this.parentNode.children.filter(x => x !== this); },
    _textOf() { if (this.textContent) return this.textContent; return this.children.map(c => c._textOf()).join(''); },
    _allText() { return this._textOf() + this.children.map(c => c._allText()).join(''); }
  };
  // innerHTML 是真实 DOM 语义：赋值会清空子节点（本桩必须如此，否则 constSlot/modalSub 会累积旧内容）
  let _html = '';
  Object.defineProperty(el, 'innerHTML', {
    get() { return _html; },
    set(v) { _html = String(v); if (_html === '') { this.children = []; this.childNodes = this.children; } },
    enumerable: true, configurable: true
  });
  // textContent 也是真实 DOM 语义：赋值会替换掉所有子节点。
  // 本套件必须如此——结算弹窗「通关」分支是 appendChild(span…)，而「失败」分支是 modalSubEl.textContent = '…'；
  // 若桩不清子节点，失败弹窗会残留上一轮通关的「本次 🔭 N/3」与 .modal-perfect，造成假红/假绿。
  let _text = '';
  Object.defineProperty(el, 'textContent', {
    get() { return _text; },
    set(v) { _text = String(v); this.children = []; this.childNodes = this.children; },
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

const PROG_KEY = 'leixian.migong.progress.v1';

// ---------------- 沙箱：同一份 dist 产物里跑两次（全新存档 / 老存档） ----------------
// 每次 parseStatic() 都从同一份 html 造一套全新元素，两套互不干扰；
// 计时器桩是共享的（flush 会同时推进两边），但两边状态各自独立，互不影响断言。
function mkSandbox(seedRaw) {
  const byIdS = parseStatic();
  const bodyS = mkEl('body', null);
  const docS = {
    body: bodyS, documentElement: mkEl('html', null), activeElement: null,
    getElementById: id => byIdS[id] || null,
    createElement: t => mkEl(t),
    createDocumentFragment: () => { const f = mkEl('fragment'); f._frag = true; return f; },
    querySelector: () => null, addEventListener() {}, removeEventListener() {}
  };
  const storeS = {};
  if (seedRaw != null) storeS[PROG_KEY] = seedRaw;
  const winS = {
    localStorage: { getItem: k => (k in storeS ? storeS[k] : null), setItem: (k, v) => { storeS[k] = String(v); }, removeItem: k => { delete storeS[k]; } },
    matchMedia: () => ({ matches: false, addEventListener() {}, addListener() {} }),
    setTimeout: setTimeoutStub, clearTimeout: clearTimeoutStub, requestAnimationFrame: rafStub,
    setInterval: setIntervalStub, clearInterval: clearIntervalStub,
    addEventListener(t, fn) { (winS._h[t] = winS._h[t] || []).push(fn); },
    _h: {}, innerWidth: 390, innerHeight: 844, devicePixelRatio: 2,
    document: docS, Math, JSON, console, Set, Map, Array, Object, String, Number, Boolean, Date,
    Int16Array, Uint8Array, parseInt, parseFloat, isNaN, isFinite, Error, encodeURIComponent
  };
  winS.window = winS;
  // base64 垫片：关卡/题库数据用 atob 解压，Node 沙箱没有该浏览器全局
  winS.atob = function(b){ return Buffer.from(String(b), 'base64').toString('binary'); };
  winS.btoa = function(s){ return Buffer.from(String(s), 'binary').toString('base64'); };
  doc = docS;                                     // mkEl.focus 指向本沙箱
  const scriptsS = [...dataHtml.matchAll(/<script[^>]*>([\s\S]*?)<\/script>/g)].map(x => x[1]);
  if (scriptsS.length !== 1) throw new Error('页面内联 script 数量不为 1：' + scriptsS.length);
  const ctxS = vm.createContext(Object.assign(winS, { globalThis: winS }));
  vm.runInContext(scriptsS[0], ctxS, { filename: 'dist-index-inline.js' });
  return { byId: byIdS, body: bodyS, board: byIdS.board, doc: docS, ctx: ctxS, store: storeS, win: winS, scripts: scriptsS };
}

// —— 沙箱 A：全新存档（localStorage 里连存档键都没有）
const FRESH = mkSandbox(null);
flush(0);
// —— 沙箱 B：老存档（有 cleared/best/timeOk，唯独没有 bestLives）——主测试对象
const LEGACY_SAVE = {
  v: 1, cleared: { '0': 1 }, last: 0, introSeen: true, sound: true, volume: 0.85,
  sky3d: true, strictTime: false, best: { '0': 12 }, timeOk: { '0': 1 }
};
const LEGACY_RAW = JSON.stringify(LEGACY_SAVE);
const MAIN = mkSandbox(LEGACY_RAW);
flush(0);

// 「当前沙箱」别名：下面的读取/驱动辅助都作用于它。
// 主测试跑在 MAIN（老存档）上；单独一段跑在 FRESH（全新存档）上，用 useSandbox 切过去再切回来。
const MAIN_CTX = MAIN.ctx;
let byId = MAIN.byId, boardEl = MAIN.board, bodyEl = MAIN.body, store = MAIN.store;
function useSandbox(sb){ byId = sb.byId; boardEl = sb.board; bodyEl = sb.body; store = sb.store; }

ok('页面内联 script 数量==1（两个沙箱同一份产物）', FRESH.scripts.length === 1 && MAIN.scripts.length === 1,
   'fresh=' + FRESH.scripts.length + ' main=' + MAIN.scripts.length);
ok('脚本执行无致命异常（关卡数据缺失提示未出现）', String(boardEl.innerHTML).indexOf('关卡数据缺失') < 0);
note('被测产物', 'dist/星织-游戏本体/index.html ' + Buffer.byteLength(html, 'utf8') + ' 字节 sha256=' +
   crypto.createHash('sha256').update(html, 'utf8').digest('hex').slice(0, 16) + '…');

// 现场解码出来的两套盘面池：闯关 88 关 / 无尽 176 题题库
const POOLS = { campaign: MAIN_CTX.__LEVELS || [], endless: MAIN_CTX.__BANK || [] };
const L1 = POOLS.campaign[0] || null;
ok('测试内可现场解码盘面（LEVELS / BANK）', POOLS.campaign.length > 0 && POOLS.endless.length > 0,
   'LEVELS=' + POOLS.campaign.length + ' BANK=' + POOLS.endless.length);

// ---------------- 夹具自检（v16 锚点写法）：直接解页面内联的 LEVELS_PACKED ----------------
// 注意锚点必须打在未补丁的 html 上（补丁副本里这行被改写了）。
const PACKED_M = /const LEVELS_PACKED = (\[[\s\S]*?\]);\s*\/\* LEVELS_INJECT_END \*\//.exec(html);
const PACKED_L1 = PACKED_M ? JSON.parse(PACKED_M[1])[0] : null;   // [id, ?, n, minesB64, noiseB64, ...]
function packedCells(b64, n){
  const raw = Buffer.from(String(b64), 'base64').toString('binary'), out = [];
  for (let i = 0; i < n * n; i++) if (raw.charCodeAt(i >> 3) & (1 << (7 - (i & 7)))) out.push(i);
  return out;
}
function mineCells(lv){
  const n = lv.size, set = new Set();
  (lv.mines || []).forEach(function(c){ set.add(c[0] * n + c[1]); });
  (lv.noise || []).forEach(function(c){ set.add(c[0] * n + c[1]); });   // startBoard 把 noise 并进雷集
  return Array.from(set).sort(function(a, b){ return a - b; });
}
const packedMines = PACKED_L1
  ? Array.from(new Set(packedCells(PACKED_L1[3], PACKED_L1[2]).concat(packedCells(PACKED_L1[4], PACKED_L1[2])))).sort((a, b) => a - b)
  : [];
const L1_MINES = L1 ? mineCells(L1) : [];
const L1_MAX = L1 ? ((typeof L1.lives === 'number' && L1.lives > 0) ? Math.floor(L1.lives) : 3) : 0;
ok('夹具自检：LEVELS_INJECT_END 锚点在，现场解码的第 1 关与 expandLevelsPacked 一致（雷集 = mines ∪ noise）',
   !!PACKED_M && !!L1 && PACKED_L1[0] === L1.id && PACKED_L1[2] === L1.size &&
   packedMines.length === L1_MINES.length && packedMines.join(',') === L1_MINES.join(','),
   '锚点=' + !!PACKED_M + ' id=' + (PACKED_L1 && PACKED_L1[0]) + ' size=' + (L1 && L1.size) +
   ' packed雷=' + packedMines.length + ' expanded雷=' + L1_MINES.length);
{
  const notThree = POOLS.campaign.filter(function(l){
    return ((typeof l.lives === 'number' && l.lives > 0) ? Math.floor(l.lives) : 3) !== 3;
  }).length;
  ok('夹具自检：88 关的命数上限（level.lives）都是 3（所以「满分」恒为 3/3）',
     POOLS.campaign.length === 88 && notThree === 0, '关数=' + POOLS.campaign.length + ' 上限非 3 的关数=' + notThree);
}
note('第 1 关现场参数', 'size=' + (L1 && L1.size) + ' 雷数=' + L1_MINES.length +
   ' 开局=' + JSON.stringify(L1 && L1.opening) + ' 命数上限=' + L1_MAX +
   ' 星座星数=' + (((L1 && L1.theme && L1.theme.stars) || []).length));

// ============================================================================
// ① 默认与向后兼容
// ============================================================================
{
  const total88 = String(POOLS.campaign.length);
  const gr = FRESH.byId.lvGrid.children || [];
  const perfectCells = gr.filter(function(b){ return String(b.className || '').split(/\s+/).indexOf('perfect') >= 0; });
  ok('【1】全新存档（localStorage 里连存档键都没有 → 自然也没有 bestLives）：面板「完美」计数 0/88',
     FRESH.byId.perfectCount.textContent === '0' && FRESH.byId.perfectTotal.textContent === total88,
     '完美=' + FRESH.byId.perfectCount.textContent + '/' + FRESH.byId.perfectTotal.textContent);
  ok('【1】全新存档：「已通关」计数 0/88',
     FRESH.byId.clearedCount.textContent === '0' && FRESH.byId.totalCount.textContent === total88,
     FRESH.byId.clearedCount.textContent + '/' + FRESH.byId.totalCount.textContent);
  ok('【1】全新存档：88 个关卡格子中没有任何一个带 perfect',
     gr.length === 88 && perfectCells.length === 0, '格子=' + gr.length + ' 带 perfect=' + perfectCells.length);
  let fp = null;
  try { fp = JSON.parse(FRESH.store[PROG_KEY] || '{}'); } catch (e) {}
  ok('【1】全新存档：bestLives 初始化为空对象（启动落盘后也没有任何评价）',
     !!fp && fp.bestLives && typeof fp.bestLives === 'object' && Object.keys(fp.bestLives).length === 0,
     JSON.stringify(fp && fp.bestLives));
  ok('【1】全新存档：主页弹出、棋盘开局 playing（新增字段没有把启动搞崩）',
     FRESH.byId.introOverlay.hidden === false &&
     JSON.parse(FRESH.body.dataset.gameState || '{}').status === 'playing',
     '主页hidden=' + FRESH.byId.introOverlay.hidden + ' status=' + JSON.parse(FRESH.body.dataset.gameState || '{}').status);
}

// 主沙箱（老存档）的读取辅助
const state = () => JSON.parse(bodyEl.dataset.gameState || '{}');
const cells = () => (boardEl.children || []).filter(c => (c.className || '').split(/\s+/).includes('cell'));
const cellsByI = () => { const a = []; cells().forEach(c => { a[+c.getAttribute('data-i')] = c; }); return a; };
function runMode(){ return String(bodyEl.dataset.runMode || ''); }
function prog(){ try { return JSON.parse(store[PROG_KEY] || '{}'); } catch (e) { return {}; } }
function bestLives(){ const p = prog(); return (p.bestLives && typeof p.bestLives === 'object') ? p.bestLives : {}; }
function deepText(el){
  if (!el) return '';
  let s = String(el.innerHTML || '') + ' ' + String(el.textContent || '') + ' ';
  (el.children || []).forEach(function(c){ s += deepText(c) + ' '; });
  return s;
}
function gridBtn(i){ return (byId.lvGrid.children || [])[i]; }
function gridCls(i){ const b = gridBtn(i); return b ? String(b.className || '') : ''; }
function hasCls(i, c){ return gridCls(i).split(/\s+/).indexOf(c) >= 0; }
function perfectGridIdx(){
  const out = [];
  (byId.lvGrid.children || []).forEach(function(b, i){
    if (String(b.className || '').split(/\s+/).indexOf('perfect') >= 0) out.push(i);
  });
  return out;
}
function modalOpen(){ return String(byId.overlay.className || '').split(/\s+/).indexOf('open') >= 0; }
function modalBtn(sub){
  return (byId.modalBtns.children || []).filter(function(b){ return String(b.textContent || '').indexOf(sub) >= 0; })[0] || null;
}
function tapCell2(i){
  const c = cellsByI()[i];
  if (!c) throw new Error('cell ' + i + ' 不存在');
  boardEl.dispatchEvent(mkEvent('pointerdown', { target: c, pointerType: 'touch', button: 0, clientX: 100, clientY: 100 }));
  boardEl.dispatchEvent(mkEvent('pointerup',   { target: c, pointerType: 'touch', button: 0, clientX: 100, clientY: 100 }));
  flush(0);
}
function rightClick2(i){
  const c = cellsByI()[i];
  if (!c) throw new Error('cell ' + i + ' 不存在');
  boardEl.dispatchEvent(mkEvent('pointerdown', { target: c, button: 2, pointerType: 'mouse', clientX: 100, clientY: 100 }));
  flush(0);
}
function openPanel2(){ byId.lvBtn.dispatchEvent(mkEvent('click', { target: byId.lvBtn })); flush(20); }
function closePanel2(){ if (byId.drawerMask) byId.drawerMask.dispatchEvent(mkEvent('click', { target: byId.drawerMask })); flush(260); }
function goLevel(n){ openPanel2(); gridBtn(n - 1).dispatchEvent(mkEvent('click', { target: gridBtn(n - 1) })); flush(80); closePanel2(); }
// 按现场解码的序列通关：先标记所有雷，再翻开所有安全格（不踩雷）
function winSeq(lv){
  const mines = new Set(mineCells(lv)), total = lv.size * lv.size;
  for (let i = 0; i < total; i++) if (mines.has(i)) rightClick2(i);
  for (let i = 0; i < total; i++) if (!mines.has(i)) tapCell2(i);
  return state().status === 'won';
}
function poolForMode(){ return runMode() === 'endless' ? POOLS.endless : POOLS.campaign; }
function currentLevel(){
  const st = state(), pool = poolForMode();
  for (let i = 0; i < pool.length; i++) if (pool[i].id === st.levelId && pool[i].size === st.size) return pool[i];
  return pool[st.level - 1] || null;
}

// ---- 主沙箱：老存档缺 bestLives 的兜底（对应页面加载分支的 bestLives 兜底） ----
{
  const mp = prog();
  ok('【1】老存档（有 cleared/best/timeOk，唯独没有 bestLives）加载不崩，兜底为 {}',
     !!mp.bestLives && typeof mp.bestLives === 'object' && Object.keys(mp.bestLives).length === 0,
     JSON.stringify(mp.bestLives));
  ok('【1】兜底不误伤其它字段（cleared / best / timeOk 原样保留）',
     mp.cleared && mp.cleared['0'] === 1 && mp.best && mp.best['0'] === 12 && mp.timeOk && mp.timeOk['0'] === 1,
     JSON.stringify({ cleared: mp.cleared, best: mp.best, timeOk: mp.timeOk }));
  ok('【1】老存档的面板「完美」计数仍是 0/88',
     byId.perfectCount.textContent === '0' && byId.perfectTotal.textContent === '88',
     byId.perfectCount.textContent + '/' + byId.perfectTotal.textContent);
  ok('【1】老存档的「已通关」计数沿用存档（1/88）',
     byId.clearedCount.textContent === '1' && byId.totalCount.textContent === '88',
     byId.clearedCount.textContent + '/' + byId.totalCount.textContent);
  ok('【1】老存档：没有任何格子带 perfect（虽然第 1 关带 cleared/timeok）',
     perfectGridIdx().length === 0 && hasCls(0, 'cleared') && hasCls(0, 'timeok'),
     '第1关class=' + gridCls(0));
  const headM = /已通关 <b id="clearedCount">[\s\S]{0,60}?完美 <b id="perfectCount">[\s\S]{0,40}?<b id="perfectTotal">/.exec(html);
  ok('【1】关卡面板标题行形态为「已通关 n/88　·　完美 x/88」', !!headM,
     headM ? headM[0].replace(/\s+/g, ' ') : '(未匹配)');
  const legendAt = html.indexOf('左下金点 = 完美观测');
  const hintAt = legendAt < 0 ? -1 : html.lastIndexOf('class="panel-hint"', legendAt);
  ok('【1】【7】面板底部图例写明「✦ 左下金点 = 完美观测（零失误通关，三架望远镜全留）」',
     legendAt > 0 && hintAt >= 0 && (legendAt - hintAt) < 500 &&
     html.slice(legendAt, legendAt + 90).indexOf('三架望远镜全留') >= 0,
     html.slice(Math.max(0, legendAt - 12), legendAt + 60));
}

// ============================================================================
// ② 零失误通关 → 满分（在「真正全新、第 1 关从未通关」的存档上跑首通，最贴近原始场景）
// ============================================================================
useSandbox(FRESH);
goLevel(1);
ok('【2】全新存档：第 1 关开局（playing、3 架望远镜、盘面与现场解码一致）',
   state().level === 1 && state().status === 'playing' && state().lives === L1_MAX &&
   state().size === L1.size && state().mines === L1_MINES.length,
   '第' + state().level + '关 ' + state().status + ' lives=' + state().lives + ' 雷=' + state().mines);
ok('【2】全新存档：通关前 #lvtag 无「最佳 🔭」、格子不带 perfect、#perfectCount 为 0',
   String(byId.lvtag.textContent).indexOf('最佳') < 0 && !hasCls(0, 'perfect') &&
   byId.perfectCount.textContent === '0',
   byId.lvtag.textContent + ' | ' + gridCls(0));
{
  const won2 = winSeq(L1);                     // 全程不踩雷
  ok('【2】零失误通关（首通、一颗雷都没踩）', won2 === true, 'status=' + state().status);
  flush(3000);
  const d2 = deepText(byId.modalSub);
  ok('【2】bestLives["0"] === 3（3 架望远镜全留 = 满分）', bestLives()['0'] === 3, JSON.stringify(bestLives()));
  ok('【2】第 1 关格子 className 含 perfect', hasCls(0, 'perfect'), gridCls(0));
  ok('【2】第 1 关格子 aria-label 追加「，完美观测」',
     String(gridBtn(0).getAttribute('aria-label')).indexOf('完美观测') >= 0,
     String(gridBtn(0).getAttribute('aria-label')));
  ok('【2】#perfectCount === 1、#perfectTotal === 88',
     byId.perfectCount.textContent === '1' && byId.perfectTotal.textContent === '88',
     byId.perfectCount.textContent + '/' + byId.perfectTotal.textContent);
  ok('【2】恰好 1 个格子带 perfect，且就是第 1 关', perfectGridIdx().join(',') === '0', perfectGridIdx().join(','));
  ok('【2】#lvtag 追加「最佳 🔭×3」', String(byId.lvtag.textContent).indexOf('最佳 🔭×3') >= 0, byId.lvtag.textContent);
  ok('【2】首通同时计入「已通关」（1/88）', byId.clearedCount.textContent === '1', byId.clearedCount.textContent);
  ok('【2】结算弹窗已打开', modalOpen(), String(byId.overlay.className));
  ok('【2】结算 meta 含「本次 🔭 3/3」', d2.indexOf('本次 🔭 3/3') >= 0, d2.replace(/\s+/g, ' ').slice(0, 140));
  const pf = byId.modalSub.querySelectorAll('.modal-perfect');
  ok('【2】结算挂出恰好 1 个 .modal-perfect，文本 = 「✦ 完美观测（零失误，望远镜全留）」',
     pf.length === 1 && String(pf[0].textContent) === '✦ 完美观测（零失误，望远镜全留）',
     pf.length + ' | ' + (pf[0] ? String(pf[0].textContent) : '(缺失)'));
}
useSandbox(MAIN);

// ============================================================================
// ⑥ 无尽模式不记录命数评价（趁 bestLives 还空着，能直接证明「压根没写」）
// ============================================================================
{
  ok('【6】进无尽前：bestLives 为空、第 1 关没有任何评价',
     Object.keys(bestLives()).length === 0, JSON.stringify(bestLives()));
  byId.homeEndless.dispatchEvent(mkEvent('click', { target: byId.homeEndless }));
  flush(80);
  ok('【6】从主页进入无尽模式（runMode=endless）', runMode() === 'endless', runMode());
  ok('【6】无尽第 1 题开局 playing', state().status === 'playing', state().status);
  const lvE = currentLevel();
  ok('【6】夹具自检：现场解码的无尽盘面雷数与 state().mines 一致',
     !!lvE && mineCells(lvE).length === state().mines,
     (lvE ? (lvE.id + '/' + lvE.size + '×' + lvE.size) : '?') + ' 解码雷=' + (lvE ? mineCells(lvE).length : '?') + ' 盘面雷=' + state().mines);
  const before = JSON.stringify(bestLives());
  const wonE = !!lvE && winSeq(lvE);
  ok('【6】按现场序列通关该无尽题', wonE === true, 'status=' + state().status);
  flush(1700);
  ok('【6】无尽通关不写入闯关命数评价（progress.bestLives 与通关前完全一致，仍为空）',
     JSON.stringify(bestLives()) === before && Object.keys(bestLives()).length === 0,
     before + ' → ' + JSON.stringify(bestLives()));
  ok('【6】无尽通关不会凭空造出第 1 关的评价', bestLives()['0'] === undefined, String(bestLives()['0']));
  ok('【6】无尽通关后面板「完美」计数仍为 0/88', byId.perfectCount.textContent === '0', byId.perfectCount.textContent);
  byId.endRunBtn.dispatchEvent(mkEvent('click', { target: byId.endRunBtn }));
  flush(1300);
  const backBtn = modalBtn('回到闯关');
  ok('【6】结束本轮弹窗有「回到闯关」', !!backBtn,
     (byId.modalBtns.children || []).map(function(b){ return String(b.textContent); }).join(' / '));
  if (backBtn) { backBtn.dispatchEvent(mkEvent('click', { target: backBtn })); flush(1300); }
  ok('【6】回到闯关模式（runMode=campaign）', runMode() === 'campaign', runMode());
}

// ============================================================================
// ③ 失误一次通关 → 有评价但非满分（这一关此前没有任何评价）
// ============================================================================
goLevel(1);
ok('夹具自检：已进入第 1 关且盘面与现场解码一致',
   state().level === 1 && state().size === L1.size && state().mines === L1_MINES.length &&
   state().status === 'playing',
   '第' + state().level + '关 size=' + state().size + ' 雷=' + state().mines + '/' + L1_MINES.length + ' ' + state().status);
ok('【3】开局望远镜 = levelMaxLives(第 1 关)（= level.lives = 3）', state().lives === 3 && state().lives === L1_MAX,
   'lives=' + state().lives + ' 上限=' + L1_MAX);
ok('【3】通关前：没有历史最佳（#lvtag 不含「最佳 🔭」）',
   String(byId.lvtag.textContent).indexOf('最佳') < 0, byId.lvtag.textContent);
ok('【3】通关前：第 1 关格子不带 perfect（只有 cleared/timeok）',
   !hasCls(0, 'perfect'), gridCls(0));
tapCell2(L1_MINES[0]);                       // 故意踩 1 颗雷
ok('【3】踩 1 颗雷后仍 playing、望远镜 3→2（第 1 关有 3 条命）',
   state().status === 'playing' && state().lives === 2, state().status + '/' + state().lives);
ok('【3】进行中不写评价（bestLives 无 "0"，#lvtag 也没有「最佳」）',
   bestLives()['0'] === undefined && String(byId.lvtag.textContent).indexOf('最佳') < 0,
   JSON.stringify(bestLives()) + ' | ' + byId.lvtag.textContent);
{
  const won3 = winSeq(L1);
  ok('【3】踩雷后按现场序列仍能通关（won）', won3 === true, 'status=' + state().status);
  flush(3000);                               // 播完揭晓 → 弹结算小弹窗
  const d3 = deepText(byId.modalSub);
  ok('【3】bestLives["0"] === 2（失误一次 = 有评价，但不满分）', bestLives()['0'] === 2,
     JSON.stringify(bestLives()));
  ok('【3】该格 className 不含 perfect', !hasCls(0, 'perfect'), gridCls(0));
  ok('【3】该格 aria-label 不含「完美观测」',
     String(gridBtn(0).getAttribute('aria-label')).indexOf('完美观测') < 0,
     String(gridBtn(0).getAttribute('aria-label')));
  ok('【3】#perfectCount === 0（88 关里 0 个满分）', byId.perfectCount.textContent === '0', byId.perfectCount.textContent);
  ok('【3】恰好 0 个格子带 perfect', perfectGridIdx().length === 0, perfectGridIdx().join(','));
  ok('【3】#lvtag 追加「最佳 🔭×2」', String(byId.lvtag.textContent).indexOf('最佳 🔭×2') >= 0, byId.lvtag.textContent);
  ok('【3】结算弹窗已打开（文本不是上一轮残留）', modalOpen(), String(byId.overlay.className));
  ok('【3】结算 meta 含「本次 🔭 2/3」', d3.indexOf('本次 🔭 2/3') >= 0, d3.replace(/\s+/g, ' ').slice(0, 150));
  ok('【3】结算里没有 .modal-perfect（非满分不挂满分区）',
     byId.modalSub.querySelectorAll('.modal-perfect').length === 0);
  ok('【3】结算文案整体不含「完美观测」', d3.indexOf('完美观测') < 0, d3.replace(/\s+/g, ' ').slice(0, 150));
}

// ============================================================================
// ⑤ 重玩也能刷新（2 → 3）；顺带在「重玩路径」上复核 ② 的满分判定（标记为【2·重玩】）
// ============================================================================
{
  const rb = modalBtn('重来本关');
  ok('【5】结算弹窗有「↻ 重来本关」', !!rb, (byId.modalBtns.children || []).map(function(b){ return String(b.textContent); }).join(' / '));
  if (rb) { rb.dispatchEvent(mkEvent('click', { target: rb })); flush(120); }
  ok('【5】重玩后回到「干净状态」：playing 且望远镜恢复满（3 架）',
     state().status === 'playing' && state().lives === 3, state().status + '/' + state().lives);
  ok('【5】重玩不会清掉已有评价（bestLives["0"] 仍为 2）', bestLives()['0'] === 2, JSON.stringify(bestLives()));
  ok('【5】重玩后 #lvtag 仍显示历史最佳「最佳 🔭×2」',
     String(byId.lvtag.textContent).indexOf('最佳 🔭×2') >= 0, byId.lvtag.textContent);
  ok('【5】重玩后格子仍不带 perfect（历史最佳 2 < 上限 3）', !hasCls(0, 'perfect'), gridCls(0));

  const won5 = winSeq(L1);                    // 这一次零失误
  ok('【5】零失误通关成功', won5 === true, 'status=' + state().status);
  flush(3000);
  const d2t = deepText(byId.modalSub);
  ok('【5】bestLives["0"] 由 2 升到 3（重玩通关也参与刷新，不是只认首通）',
     bestLives()['0'] === 3, '2 → ' + bestLives()['0']);
  ok('【2·重玩】bestLives["0"] === 3（零失误 = 望远镜全留 = 满分 3/3）', bestLives()['0'] === 3, JSON.stringify(bestLives()));
  ok('【2·重玩】第 1 关格子 className 含 perfect', hasCls(0, 'perfect'), gridCls(0));
  ok('【2·重玩】第 1 关格子 aria-label 追加「，完美观测」',
     String(gridBtn(0).getAttribute('aria-label')).indexOf('完美观测') >= 0,
     String(gridBtn(0).getAttribute('aria-label')));
  ok('【2·重玩】#perfectCount === 1（88 关中恰好 1 关满分）', byId.perfectCount.textContent === '1', byId.perfectCount.textContent);
  ok('【2·重玩】#perfectTotal === 88', byId.perfectTotal.textContent === '88', byId.perfectTotal.textContent);
  ok('【2·重玩】恰好 1 个格子带 perfect，且就是第 1 关', perfectGridIdx().join(',') === '0', perfectGridIdx().join(','));
  ok('【2·重玩】#lvtag 追加「最佳 🔭×3」', String(byId.lvtag.textContent).indexOf('最佳 🔭×3') >= 0, byId.lvtag.textContent);
  ok('【2·重玩】结算弹窗已打开', modalOpen(), String(byId.overlay.className));
  ok('【2·重玩】结算 meta 含「本次 🔭 3/3」', d2t.indexOf('本次 🔭 3/3') >= 0, d2t.replace(/\s+/g, ' ').slice(0, 150));
  {
    const pf = byId.modalSub.querySelectorAll('.modal-perfect');
    ok('【2·重玩】结算挂出恰好 1 个 .modal-perfect', pf.length === 1, 'count=' + pf.length);
    ok('【2·重玩】.modal-perfect 文本 = 「✦ 完美观测（零失误，望远镜全留）」',
       !!pf[0] && String(pf[0].textContent) === '✦ 完美观测（零失误，望远镜全留）',
       pf[0] ? String(pf[0].textContent) : '(缺失)');
  }
}

// ============================================================================
// ④ 只增不减（历史最佳）：先满分 3，再故意失误通关（本次 2）→ 仍为 3
// ============================================================================
{
  const rb = modalBtn('重来本关');
  if (rb) { rb.dispatchEvent(mkEvent('click', { target: rb })); flush(120); }
  tapCell2(L1_MINES[0]);                     // 故意再失误一次
  ok('【4】重玩后再失误一次：望远镜 3→2、仍 playing', state().lives === 2 && state().status === 'playing',
     state().status + '/' + state().lives);
  const won4 = winSeq(L1);
  ok('【4】失误后仍能通关', won4 === true, 'status=' + state().status);
  flush(3000);
  const d4 = deepText(byId.modalSub);
  ok('【4】历史最佳只增不减：本次只有 2，但 bestLives["0"] 仍为 3', bestLives()['0'] === 3,
     '本次=2 · 记录=' + bestLives()['0']);
  ok('【4】该格仍带 perfect（历史最佳 3 未被更差的一轮抹掉）', hasCls(0, 'perfect'), gridCls(0));
  ok('【4】#perfectCount 仍为 1', byId.perfectCount.textContent === '1', byId.perfectCount.textContent);
  ok('【4】#lvtag 仍为「最佳 🔭×3」', String(byId.lvtag.textContent).indexOf('最佳 🔭×3') >= 0, byId.lvtag.textContent);
  ok('【4】本次结算如实显示「本次 🔭 2/3」（历史最佳不冒充本次成绩）',
     d4.indexOf('本次 🔭 2/3') >= 0, d4.replace(/\s+/g, ' ').slice(0, 150));
  ok('【4】本次结算不挂 .modal-perfect（满分标记不会被历史最佳误触发）',
     byId.modalSub.querySelectorAll('.modal-perfect').length === 0);
  // 反面补充：失败（望远镜用尽）同样不写评价
  const rb2 = modalBtn('重来本关');
  if (rb2) { rb2.dispatchEvent(mkEvent('click', { target: rb2 })); flush(120); }
  tapCell2(L1_MINES[0]); flush(20);
  tapCell2(L1_MINES[1]); flush(20);
  tapCell2(L1_MINES[2]); flush(20);
  ok('【4+】连踩 3 颗雷 → lost、望远镜 0（3 条命耗尽）',
     state().status === 'lost' && state().lives === 0, state().status + '/' + state().lives);
  flush(1200);
  ok('【4+】失败不写命数评价（bestLives["0"] 仍为 3）', bestLives()['0'] === 3, JSON.stringify(bestLives()));
  ok('【4+】失败后格子仍带 perfect、#perfectCount 仍为 1',
     hasCls(0, 'perfect') && byId.perfectCount.textContent === '1', gridCls(0));
  ok('【4+】失败结算里不出现「本次 🔭」（失败没有命数评价行）',
     deepText(byId.modalSub).indexOf('本次 🔭') < 0,
     deepText(byId.modalSub).replace(/\s+/g, ' ').slice(0, 120));
  ok('【4+】失败结算里也没有 .modal-perfect（满分区不会残留）',
     byId.modalSub.querySelectorAll('.modal-perfect').length === 0);
}

// ============================================================================
// ⑦ CSS 契约
// ============================================================================
{
  function cssRule(sel){ const i = html.indexOf(sel); return i < 0 ? '' : html.slice(i, html.indexOf('}', i) + 1); }
  // 取「紧贴在该规则之前的那段说明注释」：从规则前的最后一个 /* 到它自己的 */，
  // 且两者之间到规则为止只允许空白（否则说明注释和规则不是一对）。
  function cssCommentBefore(sel){
    const i = html.indexOf(sel);
    if (i < 0) return '';
    const j = html.lastIndexOf('/*', i);
    if (j < 0) return '';
    const k = html.indexOf('*/', j);
    if (k < 0 || html.slice(k + 2, i).trim() !== '') return '';
    return html.slice(j, k + 2);
  }
  const perfectRule = cssRule('.lvl.perfect');
  ok('【7】存在 .lvl.perfect 规则，用 radial-gradient 画「左下角金点」',
     perfectRule.indexOf('.lvl.perfect') >= 0 && perfectRule.indexOf('radial-gradient') >= 0 &&
     perfectRule.indexOf('calc(100% - 6px)') >= 0 && perfectRule.indexOf('#ffd166') >= 0,
     perfectRule);
  const cmt = cssCommentBefore('.lvl.perfect').replace(/\s+/g, ' ');
  ok('【7】规则上方注释点明「左上 ⏱、右上 ✓/🔒 已占用」（故用背景圆点而非伪元素）',
     ['左上', '⏱', '右上', '✓/🔒', '占用'].every(function(t){ return cmt.indexOf(t) >= 0; }) &&
     (cmt.indexOf('背景圆点') >= 0 || cmt.indexOf('非伪元素') >= 0),
     cmt.slice(0, 120));
  ok('【7】反证契约：⏱ 确实占左上（.lvl.timed::before 用 left:5px）',
     cssRule('.lvl.timed::before').indexOf('⏱') >= 0 && cssRule('.lvl.timed::before').indexOf('left:5px') >= 0,
     cssRule('.lvl.timed::before'));
  ok('【7】反证契约：✓ / 🔒 确实占右上（.lvl.cleared/.locked 的 ::after 用 right 定位）',
     cssRule('.lvl.cleared::after').indexOf('"✓"') >= 0 && cssRule('.lvl.cleared::after').indexOf('right:') >= 0 &&
     cssRule('.lvl.locked::after').indexOf('🔒') >= 0 && cssRule('.lvl.locked::after').indexOf('right:') >= 0,
     cssRule('.lvl.cleared::after') + ' | ' + cssRule('.lvl.locked::after'));
  ok('【7】金点规则排在 .lvl.cleared / .lvl.locked 之后，并用 .lvl.cleared.perfect 提高权重（不被 background 简写清掉）',
     html.indexOf('.lvl.perfect') > html.indexOf('.lvl.cleared{') &&
     html.indexOf('.lvl.perfect') > html.indexOf('.lvl.locked{') &&
     /\.lvl\.cleared\.perfect\{/.test(html));
  ok('【7】.modal-perfect 有独立样式（金色加粗）',
     cssRule('.modal-perfect').indexOf('#ffd166') >= 0 && cssRule('.modal-perfect').indexOf('font-weight') >= 0,
     cssRule('.modal-perfect'));
}

const pass = R.filter(x => x.pass === true).length;
const fail = R.filter(x => x.pass === false);
console.log(R.map(x => (x.pass === true ? '  ✓ ' : x.pass === false ? '  ✗ ' : '  · ') + x.name + (x.ev ? '  [' + x.ev + ']' : '')).join('\n'));
console.log(`\nSUMMARY pass=${pass} fail=${fail.length}`);
if (fail.length) { console.log('FAILED:', fail.map(x => x.name).join(' | ')); process.exitCode = 1; }
