'use strict';
/*
 * T13 独立复核 · D 部分：v0.3 UI 运行时（Node + 自写最小 DOM stub，零依赖、不 npm install）
 *
 * 覆盖（针对本轮 3 项改动）：
 *   D0  静态自包含 / <script> 内联 / 标题文案
 *   D1  DOM stub 中执行 10 关内嵌脚本，无异常
 *   D2  爱心命数：❤❤❤ → ❤❤♡ → ❤♡♡ → ♡♡♡，aria-label「剩余命数 n / 3」，槽位不跳动（CSS + 节点数近似）
 *   D3  失败 modal：踩爆 3 雷 → status=lost + role=dialog/aria-modal 卡片标题含「雷」+「重来本关」可用
 *   D4  通关 modal：10 关全部用【本轮自写求解器】的动作序列玩到 status=won，逐关断言 modal 出现/标题/按钮
 *   D5  modal 交互：重来本关重置本关、下一关进入下一关且关闭、最后一关「全部通关！」且第二按钮 disabled
 *   D6  键盘：modal 内 Tab 循环（含 Shift+Tab）、Enter（原生 button 语义近似）、Esc 关闭后仍有「结算」入口再次打开
 *   D7  document.body.dataset.gameState 字段齐全；status!=lost 时 DOM 不泄露雷坐标
 *   D8  进度记忆：localStorage 持久化；localStorage 不可用时静默降级
 *
 * 运行：node verification/t13_ui_check.js [HTML路径] [LEVELS路径] [序列路径]
 * 输出：stdout + verification/t13_out_d.json
 */
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const crypto = require('crypto');

const ROOT = path.resolve(__dirname, '..');
const HTML_PATH = process.argv[2] ? path.resolve(process.argv[2])
  : path.join(ROOT, 'dist', '冉政-游戏本体', 'index.html');
const LEVELS_PATH = process.argv[3] ? path.resolve(process.argv[3])
  : path.join(ROOT, 'tools', 'levels.json');
const SEQS_PATH = process.argv[4] ? path.resolve(process.argv[4])
  : path.join(ROOT, 'verification', 't13_play_sequences.json');

const html = fs.readFileSync(HTML_PATH, 'utf8');
const levels = JSON.parse(fs.readFileSync(LEVELS_PATH, 'utf8'));
const seqs = JSON.parse(fs.readFileSync(SEQS_PATH, 'utf8'));
const htmlSha = crypto.createHash('sha256').update(Buffer.from(html, 'utf8')).digest('hex');

const results = [];
function check(id, ok, detail) {
  results.push({ id, ok: !!ok, detail: String(detail) });
  console.log((ok ? '[PASS] ' : '[FAIL] ') + id + ' :: ' + detail);
  return !!ok;
}

/* ------------------------------------------------------------------ DOM stub */
let ACTIVE_DOC = null;

class El {
  constructor(tag) {
    this.tagName = String(tag || 'div').toUpperCase();
    this._tag = String(tag || 'div').toLowerCase();
    this._className = '';
    this._attrs = {};
    this._listeners = {};
    this._text = '';
    this._html = '';
    this.dataset = {};
    this.children = [];       // 子元素
    this.parentNode = null;
    this.disabled = false;
    this.hidden = false;
    this.type = this._tag === 'button' ? 'submit' : '';
    const props = {};
    this.style = {
      _props: props,
      setProperty(k, v) { props[k] = String(v); },
      removeProperty(k) { delete props[k]; },
      getPropertyValue(k) { return props[k] === undefined ? '' : props[k]; },
    };
  }
  get className() { return this._className; }
  set className(v) { this._className = String(v); }
  get childNodes() { return this.children; }
  get textContent() {
    if (this.children.length === 0) return this._text;
    return this.children.map(c => c.textContent).join('') + this._text;
  }
  set textContent(v) { this._text = (v === null || v === undefined) ? '' : String(v); this.children = []; }
  get innerHTML() { return this._html; }
  set innerHTML(v) {
    this._html = String(v);
    this.children = [];
    this._text = this._html === '' ? '' : this._html.replace(/<[^>]*>/g, '');
  }
  appendChild(child) {
    if (!child) return child;
    if (child._isFragment) {
      child.children.slice().forEach(c => this.appendChild(c));
      child.children = [];
      return child;
    }
    child.parentNode = this;
    this.children.push(child);
    return child;
  }
  setAttribute(k, v) { this._attrs[k] = String(v); }
  getAttribute(k) { return Object.prototype.hasOwnProperty.call(this._attrs, k) ? this._attrs[k] : null; }
  hasAttribute(k) { return Object.prototype.hasOwnProperty.call(this._attrs, k); }
  removeAttribute(k) { delete this._attrs[k]; }
  addEventListener(type, fn) { (this._listeners[type] = this._listeners[type] || []).push(fn); }
  removeEventListener(type, fn) {
    if (!this._listeners[type]) return;
    this._listeners[type] = this._listeners[type].filter(f => f !== fn);
  }
  __fire(type, ev) {
    const e = Object.assign({
      type, target: this, currentTarget: this, cancelable: false, button: 0,
      preventDefault() {}, stopPropagation() {}, key: '',
    }, ev || {});
    if (e.target === undefined || e.target === null) e.target = this;
    (this._listeners[type] || []).slice().forEach(fn => fn(e));
    if (this.parentNode && this.parentNode.__fire) {
      const e2 = Object.assign({}, e, { currentTarget: this.parentNode });
      this.parentNode.__fire(type, e2);
    }
    return e;
  }
  closest(sel) {
    let cur = this;
    const want = sel.replace(/^\./, '');
    while (cur) {
      if (cur._className && cur._className.split(/\s+/).includes(want)) return cur;
      cur = cur.parentNode;
    }
    return null;
  }
  focus() { if (ACTIVE_DOC) ACTIVE_DOC.activeElement = this; }
  blur() { if (ACTIVE_DOC && ACTIVE_DOC.activeElement === this) ACTIVE_DOC.activeElement = ACTIVE_DOC.body; }
  scrollIntoView() { /* stub */ }
  getBoundingClientRect() { return { width: 0, height: 0, top: 0, left: 0, right: 0, bottom: 0 }; }
}

function parseAttrs(str) {
  const attrs = {};
  const re = /([^\s=]+)(?:\s*=\s*"([^"]*)")?/g;
  let m;
  while ((m = re.exec(str))) {
    if (!m[1] || m[1] === '/') continue;
    attrs[m[1].toLowerCase()] = m[2] === undefined ? '' : m[2];
  }
  return attrs;
}

function parseBody(bodyHtml) {
  const body = new El('body');
  const map = new Map();
  map.set('__body__', body);
  const stack = [body];
  const tagRe = /<(\/?)([a-zA-Z][a-zA-Z0-9-]*)([^>]*?)(\/?)>/g;
  let last = 0, m;
  while ((m = tagRe.exec(bodyHtml))) {
    const closing = m[1] === '/', tag = m[2].toLowerCase(), attrStr = m[3] || '', selfClose = m[4] === '/' || /^(br|hr|img|input|meta|link|source|area|base|col|embed|param|track|wbr)$/.test(tag);
    if (closing) {
      if (stack.length > 1) stack.pop();
      continue;
    }
    if (tag === 'script' || tag === 'style') {
      const end = bodyHtml.indexOf('</' + tag, tagRe.lastIndex);
      if (end >= 0) { tagRe.lastIndex = bodyHtml.indexOf('>', end) + 1; }
      continue;
    }
    if (tag === 'br') continue;
    const el = new El(tag);
    const attrs = parseAttrs(attrStr);
    for (const k in attrs) el._attrs[k] = attrs[k];
    if (attrs.class) el._className = attrs.class;
    if (attrs.id) map.set(attrs.id, el);
    if (Object.prototype.hasOwnProperty.call(attrs, 'hidden')) el.hidden = true;
    if (attrs.type) el.type = attrs.type;
    if (attrs.disabled !== undefined) el.disabled = true;
    stack[stack.length - 1].appendChild(el);
    if (!selfClose) stack.push(el);
  }
  return { body, map };
}

function makeEnv(opts) {
  opts = opts || {};
  const { body, map } = parseBody(html);
  map.set('__body__', body);
  const documentStub = {
    _byId: map,
    createElement(tag) { return new El(tag); },
    createDocumentFragment() { const f = new El('#fragment'); f._isFragment = true; return f; },
    getElementById(id) { return this._byId.get(id) || null; },
    body,
    title: (html.match(/<title>([^<]*)<\/title>/) || [, ''])[1],
    activeElement: null,
  };
  ACTIVE_DOC = documentStub;
  documentStub.activeElement = body;
  const winListeners = {};
  const storage = opts.storage === undefined ? makeStorage() : opts.storage;
  const windowStub = {
    _listeners: winListeners,
    addEventListener(type, fn) { (winListeners[type] = winListeners[type] || []).push(fn); },
    removeEventListener(type, fn) {
      if (!winListeners[type]) return;
      winListeners[type] = winListeners[type].filter(f => f !== fn);
    },
    localStorage: storage,
  };
  const timers = [];
  const sandbox = {
    document: documentStub,
    window: windowStub,
    console,
    requestAnimationFrame: (cb) => { cb(); return 1; },
    setTimeout: (cb, ms) => { timers.push(cb); return timers.length; },
    clearTimeout: (id) => { if (id) timers[id - 1] = null; },
  };
  return {
    document: documentStub, window: windowStub, sandbox, body,
    el: (id) => documentStub._byId.get(id),
    fireWindowKey: (key, extra) => {
      (winListeners.keydown || []).forEach(fn => fn(Object.assign({
        type: 'keydown', key, target: body, preventDefault() {}, stopPropagation() {},
      }, extra || {})));
    },
    timers,
  };
}

let envRef = null;

function makeStorage() {
  const data = {};
  return {
    _data: data,
    getItem(k) { return Object.prototype.hasOwnProperty.call(data, k) ? data[k] : null; },
    setItem(k, v) { data[k] = String(v); },
    removeItem(k) { delete data[k]; },
  };
}

function throwingStorage() {
  return {
    getItem() { throw new Error('storage disabled'); },
    setItem() { throw new Error('storage disabled'); },
    removeItem() { throw new Error('storage disabled'); },
  };
}

/* ------------------------------------------------------------------ env API */
function attachApi(env) {
  const doc = env.document;
  env.state = () => {
    const raw = doc.body.dataset.gameState;
    if (!raw) return null;
    try { return JSON.parse(raw); } catch (e) { return null; }
  };
  env.cell = (r, c) => {
    const board = doc._byId.get('board');
    const n = env.state() ? env.state().size : 6;
    const want = String(r * n + c);
    for (const x of board.children) if (x.getAttribute('data-i') === want) return x;
    return null;
  };
  env.cellList = () => doc._byId.get('board').children.filter(x => x.getAttribute('data-i') !== null);
  env.overlayOpen = () => {
    const ov = doc._byId.get('overlay');
    return ov.className.split(/\s+/).includes('open') && ov.getAttribute('aria-hidden') === 'false';
  };
  env.overlayAriaHidden = () => doc._byId.get('overlay').getAttribute('aria-hidden');
  env.hearts = () => {
    const h = doc._byId.get('hearts');
    return {
      label: h.getAttribute('aria-label'),
      text: h.textContent,
      count: h.children.length,
      slots: h.children.map(x => ({ text: x.textContent, cls: x.className, len: x.textContent.length })),
      role: h.getAttribute('role'),
    };
  };
  env.modal = () => {
    const m = doc._byId.get('modal');
    const btns = doc._byId.get('modalBtns').children.slice();
    return {
      open: env.overlayOpen(),
      role: m.getAttribute('role'),
      ariaModal: m.getAttribute('aria-modal'),
      labelledby: m.getAttribute('aria-labelledby'),
      describedby: m.getAttribute('aria-describedby'),
      tabindex: m.getAttribute('tabindex'),
      title: doc._byId.get('modalTitle').textContent,
      sub: doc._byId.get('modalSub').textContent,
      buttons: btns.map(b => ({ text: b.textContent, disabled: !!b.disabled })),
      rawButtons: btns,
    };
  };
  env.strip = () => {
    const r = doc._byId.get('result');
    return { cls: r.className, text: r.textContent, buttons: r.children.map(c => c.textContent) };
  };
  env.statusCounts = () => doc._byId.get('statusCounts').textContent;
  env.teach = () => { const t = doc._byId.get('teach'); return { text: t.textContent, cls: t.className }; };
  env.click = (elOrId) => {
    const el = typeof elOrId === 'string' ? doc._byId.get(elOrId) : elOrId;
    el.__fire('click', { target: el });
  };
  env.pointer = (r, c, button) => {
    const el = env.cell(r, c);
    if (!el) throw new Error('cell not found ' + r + ',' + c);
    el.__fire('pointerdown', { target: el, button: button || 0, cancelable: true });
  };
  env.keyOn = (el, key, shift) => el.__fire('keydown', { target: el, key, shiftKey: !!shift, preventDefault() {} });
  env.runEscape = () => env.fireWindowKey('Escape');
  return env;
}

function loadEnv(opts) {
  const env = attachApi(makeEnv(opts));
  envRef = env;
  const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
  let err = null;
  try {
    vm.createContext(env.sandbox);
    vm.runInContext(scripts.join('\n;\n'), env.sandbox, { filename: 'dist-index-inline.js', timeout: 20000 });
  } catch (e) { err = e; }
  env.loadError = err;
  return env;
}

/* ------------------------------------------------------------------ D0 静态 */
console.log('== D0. 静态自包含 / 单文件 ==');
check('D0 被复核对象 sha256', htmlSha === 'f9c7d69ca249c067eaf8dac094c37e8b0d50e3c018f6539f2b8ee0668969b1a9',
  htmlSha.slice(0, 12) + '… (' + Buffer.byteLength(html, 'utf8') + ' B)');
const scriptTags = [...html.matchAll(/<script\b[^>]*>/g)];
check('D0 只有 1 段内联 <script> 且无 src', scriptTags.length === 1 && !/<script[^>]*\bsrc=/.test(html),
  '<script 标签数=' + scriptTags.length);
const forbidden = ['http://', 'https://', 'fetch(', 'XMLHttpRequest', 'WebSocket', '<img', '<link', 'import('];
for (const pat of forbidden) {
  const hits = html.split(pat).length - 1;
  check('D0 零外部引用 ' + JSON.stringify(pat), hits === 0, '出现次数=' + hits);
}
check('D0 <title> 与 10 关版本一致（不应写「3 关体验」）', !/3 关体验/.test(html),
  '实测 <title>=' + JSON.stringify((html.match(/<title>([^<]*)<\/title>/) || [, ''])[1]));
const cssFlat = html.replace(/\s+/g, ' ');
check('D0 CSS：overlay 全屏遮罩（fixed + inset:0 + flex 居中）',
  /\.overlay\{[^}]*position:fixed/.test(cssFlat) && /\.overlay\{[^}]*inset:0/.test(cssFlat) &&
  /\.overlay\{[^}]*align-items:center/.test(cssFlat) && /\.overlay\{[^}]*justify-content:center/.test(cssFlat),
  '需 .overlay{position:fixed;inset:0;align-items:center;justify-content:center}');
check('D0 CSS：overlay 有 z-index（遮住提示条，非棋盘点击层）', /\.overlay\{[^}]*z-index:\d+/.test(cssFlat), 'z-index 存在');
check('D0 CSS：modal 竖屏自适应（min(92vw,420px) + max-height）',
  /\.modal\{[^}]*width:min\(92vw,420px\)/.test(cssFlat) && /\.modal\{[^}]*max-height:82vh/.test(cssFlat),
  '需 width:min(92vw,420px) 与 max-height:82vh');
check('D0 CSS：modal 按钮 ≥44px（min-height:48px）',
  /\.modal-btns \.btn\{[^}]*min-height:48px/.test(cssFlat), '需 .modal-btns .btn{min-height:48px}');

/* ------------------------------------------------------------------ D1 启动 */
console.log('== D1. DOM stub 中执行内嵌脚本（localStorage 可用） ==');
const envA = loadEnv();
const storageA = envA.window.localStorage;
check('D1 脚本执行无异常', !envA.loadError, envA.loadError ? String(envA.loadError && envA.loadError.stack).slice(0, 400) : 'ok');
const ds0 = envA.state();
check('D1 body.dataset.gameState 可解析', !!ds0, ds0 ? JSON.stringify(ds0).slice(0, 160) : 'null');
check('D1 初始关卡=1 / 总关数=10', ds0 && ds0.level === 1 && ds0.totalLevels === 10,
  ds0 ? `level=${ds0.level} totalLevels=${ds0.totalLevels}` : 'n/a');
check('D1 初始命数=3 / status=playing', ds0 && ds0.lives === 3 && ds0.status === 'playing',
  ds0 ? `lives=${ds0.lives} status=${ds0.status}` : 'n/a');
check('D1 初始 hearts=❤❤❤', envA.hearts().text === '❤❤❤', JSON.stringify(envA.hearts()));

/* ------------------------------------------------------------------ D7 dataset 字段 */
console.log('== D7. dataset.gameState 字段 / 不泄露雷坐标 ==');
function requiredFields(ds) {
  const need = ['level', 'revealed', 'totalSafe', 'flagged', 'mines', 'lives', 'status', 'totalLevels', 'clearedLevels'];
  return need.filter(k => !(k in (ds || {})));
}
function leakScan(env, label) {
  const bad = [];
  for (const c of env.cellList()) {
    const cls = c.className.split(/\s+/);
    if (cls.includes('mine')) bad.push('class=mine:' + c.getAttribute('data-i'));
    if (c.textContent === '💣') bad.push('text=💣:' + c.getAttribute('data-i'));
  }
  const raw = env.document.body.dataset.gameState || '';
  if (/mineSet/.test(raw)) bad.push('dataset 含 mineSet');
  if (/"mines"\s*:\s*\[/.test(raw)) bad.push('dataset 含 mines 坐标数组');
  return { ok: bad.length === 0, bad: bad.slice(0, 8), label };
}
const dsFields = requiredFields(ds0);
check('D7 初始 dataset 字段齐全', dsFields.length === 0, dsFields.length ? '缺少 ' + dsFields.join(',') : '9/9 齐全');
let lk = leakScan(envA, 'L1 playing');
check('D7 初始 playing 时 DOM 不泄露雷坐标', lk.ok, lk.ok ? '0 处泄露' : lk.bad.join(' | '));

/* ------------------------------------------------------------------ D2 爱心 */
console.log('== D2. 爱心命数 3→2→1→0 ==');
const css = html;
check('D2 爱心容器 role=img', envA.hearts().role === 'img', 'role=' + envA.hearts().role);
check('D2 初始 aria-label=「剩余命数 3 / 3」', envA.hearts().label === '剩余命数 3 / 3', envA.hearts().label);
check('D2 爱心固定 3 槽位（不随命数增减节点）', envA.hearts().count === 3, '槽位=' + envA.hearts().count);
check('D2 每颗爱心单字符（等宽槽位近似）', envA.hearts().slots.every(s => s.len === 1),
  JSON.stringify(envA.hearts().slots.map(s => s.len)));
check('D2 CSS：hearts 固定最小宽度 3*1.15em（防换行/跳动）',
  /\.hearts\{[^}]*min-width:calc\(3\s*\*\s*1\.15em\)/.test(css.replace(/\s+/g, ' ')),
  '需 .hearts{min-width:calc(3 * 1.15em)}');
check('D2 CSS：每颗 heart 固定宽 1.15em', /\.hearts \.heart\{[^}]*width:1\.15em/.test(css.replace(/\s+/g, ' ')),
  '需 .hearts .heart{width:1.15em}');

/* L1 雷位（来自 levels.json，仅复核脚本内部使用，不写入断言细节） */
const l1mines = levels[0].mines;
const heartTrace = [];
envA.pointer(l1mines[0][0], l1mines[0][1], 0);
heartTrace.push({ ds: envA.state(), h: envA.hearts() });
check('D2 踩 1 雷：lives=2 / ❤❤♡ / aria-label 2/3 / 仍 playing',
  heartTrace[0].ds.lives === 2 && heartTrace[0].h.text === '❤❤♡' &&
  heartTrace[0].h.label === '剩余命数 2 / 3' && heartTrace[0].ds.status === 'playing',
  JSON.stringify({ lives: heartTrace[0].ds.lives, hearts: heartTrace[0].h.text, label: heartTrace[0].h.label, status: heartTrace[0].ds.status }));
check('D2 踩 1 雷：modal 不应出现（未失败）', !envA.overlayOpen(), 'overlayOpen=' + envA.overlayOpen());
envA.pointer(l1mines[1][0], l1mines[1][1], 0);
heartTrace.push({ ds: envA.state(), h: envA.hearts() });
check('D2 踩 2 雷：lives=1 / ❤♡♡ / aria-label 1/3',
  heartTrace[1].ds.lives === 1 && heartTrace[1].h.text === '❤♡♡' &&
  heartTrace[1].h.label === '剩余命数 1 / 3',
  JSON.stringify({ lives: heartTrace[1].ds.lives, hearts: heartTrace[1].h.text, label: heartTrace[1].h.label }));
check('D2 爱心槽位在 3→1 全程保持 3 个', heartTrace.every(t => t.h.count === 3), '槽位恒=3');

/* ------------------------------------------------------------------ D3 失败 modal */
console.log('== D3. 失败 modal（踩爆 3 雷） ==');
envA.pointer(l1mines[2][0], l1mines[2][1], 0);
const dsLost = envA.state();
const mLost = envA.modal();
check('D3 踩爆 3 雷：lives=0 / status=lost / ♡♡♡ / aria-label 0/3',
  dsLost.lives === 0 && dsLost.status === 'lost' && envA.hearts().text === '♡♡♡' &&
  envA.hearts().label === '剩余命数 0 / 3',
  JSON.stringify({ lives: dsLost.lives, status: dsLost.status, hearts: envA.hearts().text, label: envA.hearts().label }));
check('D3 失败时出现 modal', mLost.open, 'overlayOpen=true');
check('D3 modal 有 role=dialog / aria-modal=true / 有 aria-labelledby',
  mLost.role === 'dialog' && mLost.ariaModal === 'true' && !!mLost.labelledby,
  JSON.stringify({ role: mLost.role, ariaModal: mLost.ariaModal, labelledby: mLost.labelledby }));
check('D3 失败标题含「雷」', /雷/.test(mLost.title), '标题=' + JSON.stringify(mLost.title));
const lostAgain = envA.modal().buttons.find(b => /重来本关/.test(b.text));
check('D3 「重来本关」按钮存在且可用', !!lostAgain && !lostAgain.disabled, JSON.stringify(mLost.buttons));
const before = envA.state();
envA.pointer(l1mines[3][0], l1mines[3][1], 0);   // lost 后规则行为不变：点击无效
const after = envA.state();
check('D3 失败后规则行为不变（再踩雷无效，lives 仍 0、status 仍 lost）',
  after.lives === 0 && after.status === 'lost' && after.revealed === before.revealed,
  JSON.stringify({ lives: after.lives, status: after.status, revealed: after.revealed }));
check('D3 失败 modal 中无「下一关」（不应诱导越关）',
  !envA.modal().buttons.some(b => /下一关/.test(b.text)), JSON.stringify(envA.modal().buttons));
envA.click(envA.modal().rawButtons.find(b => /重来本关/.test(b.textContent)));
const dsReset = envA.state();
check('D3 点「重来本关」：重置本关、命数恢复 3、modal 关闭',
  dsReset.level === 1 && dsReset.lives === 3 && dsReset.status === 'playing' &&
  envA.hearts().text === '❤❤❤' && !envA.overlayOpen(),
  JSON.stringify({ level: dsReset.level, lives: dsReset.lives, status: dsReset.status, hearts: envA.hearts().text }));

/* ------------------------------------------------------------------ D4/D5 10 关通关 */
console.log('== D4/D5. 用独立求解序列把 10 关全部玩到 won（逐关断言 modal） ==');
const expectedReveal = [14, 6, 8, 6, 15, 6, 12, 11, 20, 9];
function modalCheckForLevel(env, levelIdx) {
  const m = env.modal();
  const ds = env.state();
  const n = levelIdx + 1;
  const out = { level: n, open: m.open, title: m.title, buttons: m.buttons, dsStatus: ds.status, lives: ds.lives };
  const titleOk = n < levels.length ? (m.title.includes('第 ' + n + ' 关') && /通关/.test(m.title))
    : /全部通关/.test(m.title);
  const btnTexts = m.buttons.map(b => b.text);
  let btnOk;
  if (n < levels.length) {
    btnOk = btnTexts.length === 2 && /重来本关/.test(btnTexts[0]) && /下一关/.test(btnTexts[1]);
  } else {
    btnOk = /重来本关/.test(btnTexts[0]) && btnTexts.length === 2 && m.buttons[1].disabled === true;
  }
  return { ...out, titleOk, btnOk };
}

/** 依次执行动作：雷=右键插旗，安全=左键探格；同时做“playing 时不泄露雷/不弹 modal”抽查。 */
function playLevel(env, actions, n) {
  const leaks = [];
  let livesOk = true;
  for (let i = 0; i < actions.length; i++) {
    const a = actions[i];
    env.pointer(a.r, a.c, a.act === 'mine' ? 2 : 0);
    const ds = env.state();
    if (ds.status === 'playing') {
      if (env.overlayOpen()) leaks.push('playing 时 modal 提前出现 step' + (i + 1));
      const lk2 = leakScan(env, 'step' + (i + 1));
      if (!lk2.ok) leaks.push('step' + (i + 1) + ':' + lk2.bad.join(','));
      if (ds.lives !== 3) livesOk = false;
      if (i % 17 === 0) {
        const f = requiredFields(ds);
        if (f.length) leaks.push('dataset 缺字段 ' + f.join(','));
      }
    }
  }
  const ds = env.state();
  return { ds, leaks, livesOk };
}

let lastModalInfo = null;
let wonAll = true;
for (let idx = 0; idx < levels.length; idx++) {
  const n = idx + 1;
  if (idx > 0) {
    // 由上一关 modal 的「下一关」进入（最后一关除外）
    const m = envA.modal();
    const nextBtn = m.rawButtons.find(b => /下一关/.test(b.textContent) && !b.disabled);
    check('D5 第' + idx + '关 modal 的「下一关」可用', !!nextBtn,
      JSON.stringify(m.buttons));
    if (nextBtn) envA.click(nextBtn);
    const dsIn = envA.state();
    check('D5 进入第' + n + '关：modal 关闭、status=playing、命数=3',
      !envA.overlayOpen() && dsIn.status === 'playing' && dsIn.lives === 3 && dsIn.level === n,
      JSON.stringify({ open: envA.overlayOpen(), level: dsIn.level, status: dsIn.status, lives: dsIn.lives }));
    check('D5 第' + n + '关开局展开格数=' + expectedReveal[idx],
      dsIn.revealed === expectedReveal[idx], 'revealed=' + dsIn.revealed);
  }
  const actions = seqs[String(n)] || [];
  check('D4 第' + n + '关有独立求解序列（' + actions.length + ' 步）', actions.length > 0, 'steps=' + actions.length);
  const played = playLevel(envA, actions, n);
  check('D4 第' + n + '关通关：status=won / lives=3',
    played.ds.status === 'won' && played.ds.lives === 3,
    JSON.stringify({ status: played.ds.status, lives: played.ds.lives }));
  check('D4 第' + n + '关游玩过程中无提前 modal / 无雷坐标泄露',
    played.leaks.length === 0, played.leaks.length ? played.leaks.slice(0, 3).join(' | ') : '0 处');
  const mi = modalCheckForLevel(envA, idx);
  check('D4 第' + n + '关通关 modal 出现（role=dialog/aria-modal）', mi.open && envA.modal().role === 'dialog' && envA.modal().ariaModal === 'true',
    JSON.stringify({ open: mi.open, role: envA.modal().role, ariaModal: envA.modal().ariaModal }));
  check('D4 第' + n + '关 modal 标题正确', mi.titleOk, JSON.stringify(mi.title));
  check('D4 第' + n + '关 modal 按钮正确', mi.btnOk, JSON.stringify(mi.buttons));
  check('D4 第' + n + '关 modal 打开后焦点在主按钮', envA.document.activeElement === envA.modal().rawButtons[envA.modal().rawButtons.length - 1] || envA.document.activeElement === envA.modal().rawButtons[0],
    'active=' + (envA.document.activeElement ? envA.document.activeElement.textContent : 'null'));
  if (n === levels.length) {
    lastModalInfo = { m: envA.modal(), ds: envA.state() };
    const btns = envA.modal().rawButtons;
    check('D5 最后一关：标题「全部通关！」', /全部通关/.test(envA.modal().title), JSON.stringify(envA.modal().title));
    check('D5 最后一关：第二个按钮 disabled（不是死按钮）',
      btns.length >= 2 && btns[1].disabled === true,
      JSON.stringify(envA.modal().buttons));
    const dsBefore = envA.state();
    envA.click(btns[1]);
    check('D5 最后一关：点 disabled 的「下一关位」无任何反应',
      envA.state().status === 'won' && envA.overlayOpen() && envA.state().level === dsBefore.level,
      JSON.stringify({ status: envA.state().status, open: envA.overlayOpen() }));
  } else {
    // 通关后「重来本关」测试（在第 2 关做，避免影响后续推进）
    if (n === 2) {
      const replayBtn = envA.modal().rawButtons.find(b => /重来本关/.test(b.textContent));
      check('D5 第2关 modal「重来本关」按钮存在', !!replayBtn, JSON.stringify(envA.modal().buttons));
      envA.click(replayBtn);
      const dsRe = envA.state();
      check('D5 点「重来本关」：留在第2关、重置开局、命数 3、modal 关闭',
        dsRe.level === 2 && dsRe.status === 'playing' && dsRe.lives === 3 &&
        dsRe.revealed === expectedReveal[1] && !envA.overlayOpen(),
        JSON.stringify({ level: dsRe.level, status: dsRe.status, lives: dsRe.lives, revealed: dsRe.revealed, open: envA.overlayOpen() }));
      // 重玩第 2 关以恢复“已通关”状态
      playLevel(envA, seqs['2'], 2);
      check('D5 第2关重玩后再次 won', envA.state().status === 'won', 'status=' + envA.state().status);
    }
  }
}

/* ------------------------------------------------------------------ D6 键盘 */
console.log('== D6. modal 键盘可达性（Tab 循环 / Enter / Esc + 再次打开入口） ==');
// 用独立会话在第 1 关通关 modal 上测（该 modal 两个按钮均可用，能完整测 Tab 循环）
const envD = loadEnv();
check('D6 独立会话启动：level=1 / playing', !!envD.state() && envD.state().level === 1 && envD.state().status === 'playing',
  JSON.stringify(envD.state() && { level: envD.state().level, status: envD.state().status }));
playLevel(envD, seqs['1'], 1);
const mD = envD.modal();
check('D6 第1关通关 modal 打开且两个按钮均可用',
  mD.open && mD.buttons.length === 2 && !mD.buttons[0].disabled && !mD.buttons[1].disabled,
  JSON.stringify(mD.buttons));
const btns = mD.rawButtons;
btns[0].focus();
envD.keyOn(btns[0], 'Tab');
const a1 = envD.document.activeElement;
check('D6 Tab 从按钮1 → 按钮2（焦点不跑出 modal）', a1 === btns[1],
  'active=' + (a1 ? a1.textContent : 'null'));
envD.keyOn(a1, 'Tab');
const a2 = envD.document.activeElement;
check('D6 Tab 从按钮2 → 循环回按钮1', a2 === btns[0], 'active=' + (a2 ? a2.textContent : 'null'));
envD.keyOn(btns[0], 'Tab', true);
const a3 = envD.document.activeElement;
check('D6 Shift+Tab 反向循环到按钮2', a3 === btns[1], 'active=' + (a3 ? a3.textContent : 'null'));
// Esc：关闭 modal，结算条接替且「结算」可再次打开（SPEC §4.6：若可关闭则需再次打开入口）
envD.runEscape();
check('D6 Esc 关闭 modal（aria-hidden=true、无 open）', !envD.overlayOpen() && envD.overlayAriaHidden() === 'true',
  JSON.stringify({ open: envD.overlayOpen(), ariaHidden: envD.overlayAriaHidden() }));
const strip = envD.strip();
check('D6 Esc 后底部结算条出现（保留入口，不是关了没入口）',
  strip.cls.split(/\s+/).includes('show') && /通关/.test(strip.text),
  JSON.stringify({ cls: strip.cls, text: strip.text.slice(0, 80) }));
const reopenRow = envD.document._byId.get('result').children.find(c => c.className === 'result-btns');
const reopenBtn = reopenRow ? reopenRow.children.find(b => /结算/.test(b.textContent)) : null;
check('D6 结算条含「结算」再次打开入口', !!reopenBtn, reopenRow ? reopenRow.children.map(b => b.textContent).join(' / ') : 'no row');
if (reopenBtn) envD.click(reopenBtn);
check('D6 点「结算」重新打开 modal', envD.overlayOpen() && envD.overlayAriaHidden() === 'false',
  JSON.stringify({ open: envD.overlayOpen(), ariaHidden: envD.overlayAriaHidden() }));
// Enter：原生 <button> 在 Enter 时会触发 click（HTML 标准默认行为，DOM 桩无法原生复现）；
// 这里先确认按钮是原生 button + 已绑 click，再「模拟浏览器默认行为」后验证路由正确。
const primary = envD.modal().rawButtons.find(b => /下一关/.test(b.textContent));
check('D6 Enter 前：主按钮是原生 <button> 且非 disabled',
  !!primary && primary.tagName === 'BUTTON' && !primary.disabled,
  primary ? primary.tagName + ' disabled=' + primary.disabled : 'missing');
primary.focus();
envD.keyOn(primary, 'Enter');
primary.__fire('click', { target: primary });   // 模拟原生 button 的 Enter→click 默认行为
const dsAfterEnter = envD.state();
check('D6 Enter 触发「下一关」→ 进入第2关、modal 关闭',
  dsAfterEnter.level === 2 && dsAfterEnter.status === 'playing' && !envD.overlayOpen(),
  JSON.stringify({ level: dsAfterEnter.level, status: dsAfterEnter.status, open: envD.overlayOpen() }));

/* ------------------------------------------------------------------ D8 进度记忆 */
console.log('== D8. localStorage 进度记忆 / 不可用降级 ==');
// 重新玩完第 10 关，使 clearedLevels=10 后，用同一 storage 开新会话
playLevel(envA, seqs[String(levels.length)], levels.length);
const dsEnd = envA.state();
check('D8 全部通关后 clearedLevels=10 / totalLevels=10',
  dsEnd.clearedLevels === 10 && dsEnd.totalLevels === 10,
  JSON.stringify({ clearedLevels: dsEnd.clearedLevels, totalLevels: dsEnd.totalLevels }));
const savedRaw = storageA.getItem('leixian.migong.progress.v1');
check('D8 localStorage 已写入进度', !!savedRaw, String(savedRaw).slice(0, 120));
const envB = loadEnv({ storage: storageA });
const dsB = envB.state();
check('D8 新会话沿用进度：全部通关后从最后一关开始（level=10）',
  dsB && dsB.level === 10 && dsB.clearedLevels === 10,
  dsB ? JSON.stringify({ level: dsB.level, clearedLevels: dsB.clearedLevels }) : 'null');
const envC = loadEnv({ storage: throwingStorage() });
const dsC = envC.state();
check('D8 localStorage 不可用时静默降级（仍能开始第1关、无异常）',
  !envC.loadError && dsC && dsC.level === 1 && dsC.status === 'playing',
  envC.loadError ? String(envC.loadError).slice(0, 200) : JSON.stringify({ level: dsC && dsC.level, status: dsC && dsC.status }));

/* ------------------------------------------------------------------ 汇总 */
const total = results.length;
const failed = results.filter(r => !r.ok);
console.log('\n===== D 汇总：' + (total - failed.length) + '/' + total + ' 通过 =====');
if (failed.length) {
  console.log('不通过项：');
  for (const f of failed) console.log('  - ' + f.id + ' :: ' + f.detail);
}
const out = {
  html: HTML_PATH, html_sha256: htmlSha, html_bytes: Buffer.byteLength(html, 'utf8'),
  levels: levels.length, total_checks: total, passed: total - failed.length,
  failed: failed.map(f => ({ id: f.id, detail: f.detail })),
  results,
};
fs.writeFileSync(path.join(ROOT, 'verification', 't13_out_d.json'), JSON.stringify(out, null, 2));
console.log('JSON -> verification/t13_out_d.json');
process.exit(failed.length ? 1 : 0);