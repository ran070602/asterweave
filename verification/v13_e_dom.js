// v13-e 专项：星座图鉴 level 映射 —— 运行时断言（自写 DOM 桩，无 npm）。
// 目标：
//   R1 六种进度状态下 #skyCount 文本 == 该状态实际通关数 == SKY.filter(level 已通关) 条数
//   R2 cleared={1,21} 下点选未通关的蛇夫/船底/长蛇座：不泄露 gstar/gline/gnoise、
//      不出现别的星座中文名或 fact 文案、文案表明"未观测/通关后点亮"，且关卡号正确
//   R3 通关第 26/29/30 关后：对应星座恰好点亮一次，天球图上亮起的节点集合 == 期望集合
//   R4 负向对照：把 SKY 里 ophiuchus.level 改回 21（复现旧 bug），断言本 harness 能报错
//      —— 证明 R1/R2 不是空洞断言
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = 'D:\\AI-Native casual game';
const DIST = path.join(ROOT, 'dist', '星织-游戏本体', 'index.html');
const HTML = fs.readFileSync(DIST, 'utf8');

// ---------- 独立取出注入块（自写括号配平扫描，不依赖 build_sky.py） ----------
function extractBlock(src, marker) {
  const s = src.indexOf('/* ' + marker + '_START */');
  const e = src.indexOf('/* ' + marker + '_END */');
  if (s < 0 || e < 0) throw new Error('marker not found: ' + marker);
  let b = src.slice(s, e);
  b = b.slice(b.indexOf('*/') + 2);
  b = b.slice(b.indexOf('['));
  let depth = 0, inStr = false, esc = false;
  for (let i = 0; i < b.length; i++) {
    const ch = b[i];
    if (inStr) { if (esc) esc = false; else if (ch === '\\') esc = true; else if (ch === '"') inStr = false; continue; }
    if (ch === '"') inStr = true;
    else if (ch === '[' || ch === '{') depth++;
    else if (ch === ']' || ch === '}') { depth--; if (depth === 0) return JSON.parse(b.slice(0, i + 1)); }
  }
  throw new Error('unbalanced ' + marker);
}
const SKY = extractBlock(HTML, 'SKY_INJECT');
const LEVELS = extractBlock(HTML, 'LEVELS_INJECT');
const SCRIPTS = [...HTML.matchAll(/<script[^>]*>([\s\S]*?)<\/script>/g)].map(x => x[1]);
const SRC = () => SCRIPTS[0];

const R = [];
function ok(name, cond, ev) { R.push({ name, pass: !!cond, ev: ev === undefined ? '' : String(ev) }); }
function note(name, ev) { R.push({ name, pass: null, ev: String(ev) }); }

// 真实 level -> 星座 id（从 LEVELS 反查，纯独立于 SKY 的 level 字段）
const idByLevel = {};
LEVELS.forEach(L => { idByLevel[L.id] = (L.theme || {}).id; });
const allFacts = LEVELS.map(L => (L.theme && L.theme.fact) || '');
const ZH = SKY.map(s => s.zh);
const colliding = [];
for (const a of ZH) for (const b of ZH) if (a !== b && b.includes(a)) colliding.push(a + '<>' + b);
note('SKY 中文名互为子串的情况（影响"别的星座名"判定）', colliding.length ? colliding.join(',') : '无');

// ---------- 计时器 ----------
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

// ---------- 元素桩 ----------
function mkEl(tag, id) {
  const el = {
    tagName: String(tag || 'div').toUpperCase(), _id: id || null,
    className: '', textContent: '', hidden: false, disabled: false,
    attrs: {}, children: [], parentNode: null, dataset: {}, _h: {},
    style: { setProperty() {} }, offsetWidth: 100,
    classList: {
      add(c) { const s = new Set((el.className || '').split(/\s+/).filter(Boolean)); s.add(c); el.className = [...s].join(' '); },
      remove(c) { const s = new Set((el.className || '').split(/\s+/).filter(Boolean)); s.delete(c); el.className = [...s].join(' '); },
      contains(c) { return (el.className || '').split(/\s+/).includes(c); },
      toggle(c) { el.classList.contains(c) ? el.classList.remove(c) : el.classList.add(c); }
    },
    setAttribute(k, v) { this.attrs[k] = String(v); if (k === 'class') this.className = String(v); if (k === 'id') this._id = String(v); if (k === 'hidden') this.hidden = true; },
    getAttribute(k) { return Object.prototype.hasOwnProperty.call(this.attrs, k) ? this.attrs[k] : null; },
    removeAttribute(k) { delete this.attrs[k]; },
    addEventListener(t, fn) { (this._h[t] = this._h[t] || []).push(fn); },
    removeEventListener(t, fn) { this._h[t] = (this._h[t] || []).filter(f => f !== fn); },
    dispatchEvent(e) { (this._h[e.type] || []).slice().forEach(fn => fn(e)); return true; },
    appendChild(c) {
      if (c && c._frag) { c.children.slice().forEach(x => this.appendChild(x)); return c; }
      this.children.push(c); if (c) c.parentNode = this; return c;
    },
    removeChild(c) { this.children = this.children.filter(x => x !== c); return c; },
    querySelector(sel) { const cls = sel.replace(/^\./, ''); const w = n => { for (const k of n.children) { if ((k.className || '').split(/\s+/).includes(cls)) return k; const r = w(k); if (r) return r; } return null; }; return w(this); },
    querySelectorAll(sel) { const cls = sel.replace(/^\./, ''); const out = []; const w = n => { for (const k of n.children) { if ((k.className || '').split(/\s+/).includes(cls)) out.push(k); w(k); } }; w(this); return out; },
    closest(sel) { const cls = sel.replace(/^\./, ''); let n = this; while (n) { if ((n.className || '').split(/\s+/).includes(cls)) return n; n = n.parentNode; } return null; },
    getBoundingClientRect() { return { width: 300, height: 300, left: 0, top: 0, right: 300, bottom: 300 }; },
    setPointerCapture() {}, releasePointerCapture() {},
    focus() {}, blur() {}, scrollIntoView() {}, get firstChild() { return this.children[0] || null; },
    get childNodes() { return this.children; },
    get lastChild() { return this.children[this.children.length - 1] || null; },
    remove() { if (this.parentNode) this.parentNode.children = this.parentNode.children.filter(x => x !== this); },
    click() { this.dispatchEvent(mkEvent('click', { target: this })); }
  };
  let _html = '';
  Object.defineProperty(el, 'innerHTML', {
    get() { return _html; },
    set(v) { _html = String(v); if (_html === '') { this.children = []; } },
    enumerable: true, configurable: true
  });
  return el;
}
function mkEvent(type, extra) { return Object.assign({ type, preventDefault() {}, stopPropagation() {}, cancelable: true, button: 0, key: '' }, extra || {}); }

// ---------- 静态元素（按 id 索引；每次会话重建一套，避免串味） ----------
function parseStatic() {
  const map = {};
  const re = /<(\w+)([^>]*?\bid="([^"]+)"[^>]*?)>/g;
  let m;
  while ((m = re.exec(HTML))) {
    const [, tag, attrStr, id] = m;
    const el = mkEl(tag, id);
    const cls = /class="([^"]*)"/.exec(attrStr);
    if (cls) el.className = cls[1];
    const rest = HTML.slice(m.index + m[0].length);
    const txt = rest.match(/^([^<]*)/);
    el.textContent = (txt ? txt[1] : '').trim();
    for (const a of attrStr.matchAll(/([\w-]+)="([^"]*)"/g)) el.attrs[a[1]] = a[2];
    for (const a of attrStr.matchAll(/(?:^|\s)(hidden|disabled)(?=[\s/>]|$)/g)) el.attrs[a[1]] = '';
    if (el.attrs.hidden !== undefined) el.hidden = true;
    if (el.attrs.disabled !== undefined) el.disabled = true;
    map[id] = el;
  }
  return map;
}

const SRC_KEYS = ['Math', 'JSON', 'console', 'Set', 'Map', 'Array', 'Object', 'String', 'Number', 'Boolean',
  'Date', 'Int16Array', 'Uint8Array', 'parseInt', 'parseFloat', 'isNaN', 'isFinite', 'Error', 'encodeURIComponent'];

// 起一个会话：srcHtml 可替换（负向对照用），clearedLevels = 已通关关卡号数组（1 基）
function startSession(src, clearedLevels) {
  const S = parseStatic();
  const body = mkEl('body');
  const doc = {
    body, documentElement: mkEl('html'), activeElement: null,
    getElementById: id => S[id] || null,
    createElement: t => mkEl(t),
    createDocumentFragment: () => { const f = mkEl('fragment'); f._frag = true; return f; },
    querySelector: () => null, addEventListener() {}, removeEventListener() {}
  };
  const store = {};
  const cleared = {};
  clearedLevels.forEach(l => { cleared[String(l - 1)] = 1; });   // 应用自身约定：键 = 关卡 index（关卡号-1）
  store['leixian.migong.progress.v1'] = JSON.stringify({ v: 1, cleared, last: 0, devUnlock: false, devSkyLit: false });
  const w = {
    localStorage: { getItem: k => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = String(v); }, removeItem: k => { delete store[k]; } },
    matchMedia: () => ({ matches: false, addEventListener() {}, addListener() {} }),
    setTimeout: setTimeoutStub, clearTimeout: clearTimeoutStub, requestAnimationFrame: rafStub,
  setInterval: setIntervalStub, clearInterval: clearIntervalStub,
    addEventListener() {}, _h: {}, innerWidth: 390, innerHeight: 844, devicePixelRatio: 2, document: doc
  };
  SRC_KEYS.forEach(k => { w[k] = global[k]; });
  w.window = w;
  timers = []; clock = 0;
  const ctx = vm.createContext(Object.assign(w, { globalThis: w }));
  let err = null;
  try { vm.runInContext(src, ctx, { filename: 'dist-inline.js' }); } catch (e) { err = e; }
  flush(0);
  return { S, body, store, err, doc };
}

function state(sess) { return JSON.parse(sess.body.dataset.gameState || '{}'); }
// 点选星座：从真实渲染出的天球图里取出该节点的 class，再模拟点击（比凭空造节点更贴近真实）
function clickSky(sess, id) {
  const mapHtml = sess.S.skyMap.innerHTML;
  const m = mapHtml.match(new RegExp('<g class="([^"]*)" data-sky="' + id + '"'));
  if (!m) return { found: false, html: '' };
  const node = { className: m[1], getAttribute: k => (k === 'data-sky' ? id : null), closest: () => node };
  sess.S.skyMap.dispatchEvent(mkEvent('click', { target: node }));
  flush(20);
  return { found: true, cls: m[1], html: sess.S.constModalBody.innerHTML };
}
function litSet(sess) {
  const out = [];
  const re = /<g class="([^"]*)" data-sky="([^"]+)"/g;
  let m;
  while ((m = re.exec(sess.S.skyMap.innerHTML))) if (m[1].split(/\s+/).includes('on')) out.push(m[2]);
  return out.sort();
}
const SKY_LEVEL = {}; SKY.forEach(s => { SKY_LEVEL[s.id] = s.level; });

// ================= R1：六种进度状态下的 skyCount =================
const STATES = [
  { name: 'cleared={}', lv: [] },
  { name: 'cleared={1}', lv: [1] },
  { name: 'cleared={1,21}', lv: [1, 21] },
  { name: '前 21 关', lv: Array.from({ length: 21 }, (_, i) => i + 1) },
  { name: '前 49 关', lv: Array.from({ length: 49 }, (_, i) => i + 1) },
  { name: '全部 50 关', lv: Array.from({ length: 50 }, (_, i) => i + 1) }
];
const rows = [];
for (const st of STATES) {
  const sess = startSession(SRC(), st.lv);
  if (sess.err) { ok('R1 ' + st.name + ' 脚本无异常', false, sess.err.message); console.log('INIT_ERR_STACK\n' + sess.err.stack); break; }
  const g = state(sess);
  sess.S.skyBtn.dispatchEvent(mkEvent('click', { target: sess.S.skyBtn }));
  flush(20);
  const count = String(sess.S.skyCount.textContent);
  const setLv = new Set(st.lv);
  const expectFromSky = SKY.filter(s => setLv.has(s.level)).length;   // 任务指定公式
  const trueCleared = st.lv.filter(l => idByLevel[l]).length;         // 独立公式：有星座的已通关关卡数
  const pass = count === String(trueCleared) && count === String(expectFromSky) && g.clearedLevels === st.lv.length;
  rows.push({ state: st.name, skyCount: count, expectFromSky, trueCleared, clearedLevels: g.clearedLevels, pass });
  ok('R1 ' + st.name + ' → skyCount=' + count + ' 实际通关=' + g.clearedLevels + ' SKY命中=' + expectFromSky, pass,
    'skyCount=' + count + ' clearedLevels=' + g.clearedLevels + ' 期望=' + trueCleared);
  const lit = litSet(sess);
  const wantLit = st.lv.map(l => idByLevel[l]).filter(Boolean).sort();
  ok('R1 ' + st.name + ' → 天球图亮起的节点恰好 = 已通关关卡对应星座（不点亮别的关）',
    JSON.stringify(lit) === JSON.stringify(wantLit), 'lit=' + JSON.stringify(lit) + ' 期望=' + JSON.stringify(wantLit));
  sess._lit = lit;
}

// ================= R2：cleared={1,21} 下未通关星座不泄露 =================
const s2 = startSession(SRC(), [1, 21]);
if (s2.err) ok('R2 会话建立', false, s2.err.message);
s2.S.skyBtn.dispatchEvent(mkEvent('click', { target: s2.S.skyBtn }));
flush(20);
const LEAK_IDS = ['ophiuchus', 'carina', 'hydra'];
const expectedLv = { ophiuchus: 29, carina: 26, hydra: 30 };
const oldLv = { ophiuchus: 21, carina: 22, hydra: 23 };
for (const id of LEAK_IDS) {
  const r = clickSky(s2, id);
  const h = r.html || '';
  const zh = SKY.find(s => s.id === id).zh;
  const others = ZH.filter(z => z !== zh && h.includes(z));
  const facts = allFacts.filter(f => f && f.length >= 8 && h.includes(f));
  const noSvg = !h.includes('gstar') && !h.includes('gline') && !h.includes('gnoise') && !h.includes('const-svg') && !h.includes('sky-map-slot');
  const lvOk = h.includes('第 ' + expectedLv[id] + ' 关');
  const wording = h.includes('未观测') && h.includes('通关后点亮');
  ok('R2 未通关 ' + zh + '(' + id + ', 真实第 ' + expectedLv[id] + ' 关) 不泄露星图', noSvg,
    'gstar=' + h.includes('gstar') + ' gline=' + h.includes('gline') + ' gnoise=' + h.includes('gnoise') + ' len=' + h.length);
  ok('R2 ' + zh + ' 卡片不含别的星座中文名 / 别的关卡 fact', others.length === 0 && facts.length === 0,
    'others=[' + others.slice(0, 3) + '] facts=[' + facts.slice(0, 1).map(x => x.slice(0, 12)) + ']');
  ok('R2 ' + zh + ' 文案表明未观测 + 关卡号已改为 ' + expectedLv[id] + '（旧值 ' + oldLv[id] + '）', wording && lvOk,
    h.replace(/\s+/g, ' ').replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 100));
}

// R2b：已通关的第 21 关（摩羯座）必须渲染"自己的"星图与 fact —— 张冠李戴的另一半
const cap = clickSky(s2, 'capricornus');
const lv21 = LEVELS[20];
function expCoords(theme, n) { return theme.stars.map(s => (8 + (s.rc[1] + 0.5) / n * 84).toFixed(1) + ',' + (8 + (s.rc[0] + 0.5) / n * 84).toFixed(1)).sort(); }
const drawn = [...(cap.html || '').matchAll(/class="gstar" cx="([\d.]+)" cy="([\d.]+)"/g)].map(x => x[1] + ',' + x[2]).sort();
const capFact = ((cap.html || '').match(/class="sky-fact">([^<]*)/) || [, ''])[1];
ok('R2b 已通关的摩羯座（第 21 关）星图坐标属于自己 / fact 属于自己 / 不冒充蛇夫座',
  JSON.stringify(drawn) === JSON.stringify(expCoords(lv21.theme, lv21.size)) && capFact === lv21.theme.fact && !(cap.html || '').includes('蛇夫座'),
  'stars=' + drawn.length + ' 坐标命中=' + (JSON.stringify(drawn) === JSON.stringify(expCoords(lv21.theme, lv21.size))) + ' fact命中=' + (capFact === lv21.theme.fact) +
  ' drawn=' + JSON.stringify(drawn.slice(0, 4)) + ' exp=' + JSON.stringify(expCoords(lv21.theme, lv21.size).slice(0, 4)) + ' n=' + lv21.size + ' stars0=' + JSON.stringify(lv21.theme.stars[0]));

// ================= R3：通关第 26/29/30 关后恰好点亮对应星座 =================
for (const lv of [26, 29, 30]) {
  const sess = startSession(SRC(), [lv]);
  sess.S.skyBtn.dispatchEvent(mkEvent('click', { target: sess.S.skyBtn }));
  flush(20);
  const g = state(sess);
  const want = idByLevel[lv];
  const lit = litSet(sess);
  ok('R3 只通关第 ' + lv + ' 关 → 亮起 == [' + want + ']，skyCount=1',
    lit.length === 1 && lit[0] === want && sess.S.skyCount.textContent === '1' && g.clearedLevels === 1,
    'lit=' + JSON.stringify(lit) + ' skyCount=' + sess.S.skyCount.textContent);
  const on = clickSky(sess, want);
  const off = clickSky(sess, idByLevel[29] === want ? 'carina' : 'ophiuchus');
  ok('R3 第 ' + lv + ' 关星座（' + want + '）详情含星图，且其未通关邻居无星图',
    on.html.includes('gstar') && !off.html.includes('gstar'),
    'on.gstar=' + (on.html.match(/gstar/g) || []).length + ' off.gstar=' + off.html.includes('gstar'));
}
// 26+29+30 一起：恰好 3 个节点亮
const s3 = startSession(SRC(), [26, 29, 30]);
s3.S.skyBtn.dispatchEvent(mkEvent('click', { target: s3.S.skyBtn }));
flush(20);
ok('R3 通关 26+29+30 → 恰好亮 3 个且为 carina/hydra/ophiuchus', JSON.stringify(litSet(s3)) === JSON.stringify(['carina', 'hydra', 'ophiuchus']) && s3.S.skyCount.textContent === '3',
  'lit=' + JSON.stringify(litSet(s3)) + ' skyCount=' + s3.S.skyCount.textContent);

// ================= R4：负向对照（复现旧 bug，验证 harness 有检出能力） =================
const buggy = SRC().replace(/("abbr": "Oph",\s*\n\s*"level": )29/, '$121');
if (buggy === SRC()) { ok('R4 负向对照构造成功（ophiuchus.level 29→21）', false, '替换未命中'); }
else {
  const sb = startSession(buggy, [1, 21]);
  sb.S.skyBtn.dispatchEvent(mkEvent('click', { target: sb.S.skyBtn }));
  flush(20);
  const oph = clickSky(sb, 'ophiuchus').html;
  const leaked = oph.includes('gstar');
  const fact = allFacts.find(f => f && f.length >= 8 && oph.includes(f)) || '';
  ok('R4[对照] 旧 bug 复现：skyCount 与真实通关数不一致', sb.S.skyCount.textContent !== String(state(sb).clearedLevels),
    'skyCount=' + sb.S.skyCount.textContent + ' 真实通关=' + state(sb).clearedLevels);
  ok('R4[对照] 旧 bug 复现：未通关蛇夫座泄露星图 + 张冠李戴', leaked && !!fact,
    'gstar=' + leaked + ' 渲染出的 fact=' + fact.slice(0, 16));
}

// ---------- 输出 ----------
const fails = R.filter(r => r.pass === false);
console.log(JSON.stringify({ states: rows, results: R }, null, 1));
R.forEach(r => console.log((r.pass === true ? 'PASS ' : r.pass === false ? 'FAIL ' : 'NOTE ') + r.name + (r.ev ? ' :: ' + r.ev : '')));
console.log('SUMMARY pass=' + R.filter(r => r.pass === true).length + ' fail=' + fails.length + ' note=' + R.filter(r => r.pass === null).length);
process.exitCode = fails.length ? 1 : 0;
