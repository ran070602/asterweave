// v10 独立复核 D：自写 DOM stub（零 npm），把 20 关全部玩到 won。
'use strict';
const fs = require('fs');
const vm = require('vm');
const path = require('path');

const ROOT = 'D:\\Asterweave';
const HTML_PATH = path.join(ROOT, 'dist', '星织-游戏本体', 'index.html');
const LEVELS = JSON.parse(fs.readFileSync(path.join(ROOT, 'tools', 'levels.json'), 'utf8'));
const html = fs.readFileSync(HTML_PATH, 'utf8');

const results = [];
function check(name, ok, detail) {
  results.push({ name, ok: !!ok, detail: detail === undefined ? '' : String(detail) });
}
function eq(name, got, want) {
  check(name, JSON.stringify(got) === JSON.stringify(want), 'got=' + JSON.stringify(got) + ' want=' + JSON.stringify(want));
}

// ---------------- DOM stub ----------------
class El {
  constructor(doc, tag, id, cls, text) {
    this.doc = doc; this.tagName = String(tag).toUpperCase(); this.id = id || '';
    this._class = cls || ''; this._text = text || ''; this._html = '';
    this.children = []; this.parentNode = null; this.attrs = new Map();
    this.listeners = {}; this.disabled = false; this.dataset = {};
    this.style = { setProperty() {} };
    this._rect = { width: 0 };
  }
  get className() { return this._class; }
  set className(v) { this._class = String(v); }
  get classList() {
    const self = this;
    const list = () => self._class.split(/\s+/).filter(Boolean);
    return {
      add(c) { if (!list().includes(c)) self._class = (self._class + ' ' + c).trim(); },
      remove(c) { self._class = list().filter(x => x !== c).join(' '); },
      contains(c) { return list().includes(c); },
      toggle(c) { if (list().includes(c)) this.remove(c); else this.add(c); },
    };
  }
  get textContent() { return this._text; }
  set textContent(v) { this._text = v == null ? '' : String(v); this._html = ''; this.children = []; }
  get innerHTML() { return this._html; }
  set innerHTML(v) { this._html = v == null ? '' : String(v); this._text = ''; this.children = []; }
  get childNodes() { return this.children; }
  appendChild(node) {
    if (node && node.isFragment) {
      for (const c of node.children) { c.parentNode = this; this.children.push(c); }
      node.children = [];
      return node;
    }
    node.parentNode = this; this.children.push(node); return node;
  }
  setAttribute(k, v) { this.attrs.set(k, String(v)); if (k === 'class') this._class = String(v); }
  getAttribute(k) { if (k === 'class') return this._class; return this.attrs.has(k) ? this.attrs.get(k) : null; }
  hasAttribute(k) { return this.attrs.has(k); }
  addEventListener(t, fn) { (this.listeners[t] = this.listeners[t] || []).push(fn); }
  removeEventListener(t, fn) { this.listeners[t] = (this.listeners[t] || []).filter(x => x !== fn); }
  click() {
    for (const fn of (this.listeners.click || [])) fn({ target: this, preventDefault() {}, stopPropagation() {} });
    return true;
  }
  focus() { this.doc.activeElement = this; }
  blur() {}
  scrollIntoView() {}
  closest(sel) {
    if (sel === '.cell' && this.classList.contains('cell')) return this;
    return this.parentNode ? this.parentNode.closest(sel) : null;
  }
  getBoundingClientRect() { return this._rect; }
  querySelector() { return null; }
}

class Doc {
  constructor() {
    this.byId = new Map(); this.activeElement = null; this.body = new El(this, 'body', 'body', '', '');
  }
  createElement(tag) { return new El(this, tag); }
  createDocumentFragment() { const f = new El(this, '#fragment'); f.isFragment = true; return f; }
  getElementById(id) { return this.byId.get(id) || null; }
}

function parseMarkupIds(bodyHtml, doc) {
  const re = /<(\w+)([^>]*\bid="([^"]+)"[^>]*)>/g;
  let m;
  while ((m = re.exec(bodyHtml))) {
    const tag = m[1], attrs = m[2], id = m[3];
    const cm = /class="([^"]*)"/.exec(attrs);
    let text = '';
    if (tag.toLowerCase() === 'button') {
      const start = m.index + m[0].length;
      const end = bodyHtml.indexOf('</button>', start);
      if (end > start) {
        text = bodyHtml.slice(start, end)
          .replace(/<[^>]*>/g, '')
          .replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>')
          .replace(/&quot;/g, '"').replace(/&#39;/g, "'")
          .replace(/\s+/g, ' ').trim();
      }
    }
    doc.byId.set(id, new El(doc, tag, id, cm ? cm[1] : '', text));
  }
}

function boot() {
  const doc = new Doc();
  const bodyStart = html.indexOf('<body>');
  const scriptStart = html.indexOf('<script>');
  parseMarkupIds(html.slice(bodyStart, scriptStart), doc);
  // title
  const titleM = /<title>([\s\S]*?)<\/title>/.exec(html);
  doc.title = titleM ? titleM[1] : '';

  let timers = []; let tid = 1;
  const sandbox = {
    console,
    document: doc,
    setTimeout(fn) { const id = tid++; timers.push({ id, fn }); return id; },
    clearTimeout(id) { timers = timers.filter(t => t.id !== id); },
    requestAnimationFrame(fn) { fn(); return 1; },
    localStorage: (() => {
      const store = new Map();
      return { getItem(k) { return store.has(k) ? store.get(k) : null; }, setItem(k, v) { store.set(k, String(v)); }, removeItem(k) { store.delete(k); } };
    })(),
    addEventListener() {}, removeEventListener() {},
    matchMedia() { return { matches: false, addListener() {}, removeListener() {} }; },
    alert() {}, confirm() { return true; },
  };
  sandbox.window = sandbox;
  sandbox.globalThis = sandbox;
  const ctx = vm.createContext(sandbox);
  const js = /<script>([\s\S]*?)<\/script>/.exec(html)[1];
  vm.runInContext(js, ctx, { timeout: 10000 });
  sandbox.__flush = () => { const t = timers; timers = []; for (const x of t) x.fn(); };
  sandbox.__doc = doc;
  sandbox.__ctx = ctx;
  return sandbox;
}

function gameState(ctx) { return JSON.parse(ctx.document.body.dataset.gameState); }
function cellsOf(doc) {
  const m = new Map();
  for (const ch of doc.byId.get('board').children) {
    if (ch.classList.contains('cell')) m.set(Number(ch.getAttribute('data-i')), ch);
  }
  return m;
}
function levelButton(doc, idx) {
  return doc.byId.get('lvGrid').children.find(b => Number(b.getAttribute('data-level')) === idx + 1);
}
function pointer(ctx, cell) {
  const board = ctx.document.byId.get('board');
  const h = (board.listeners.pointerdown || [])[0];
  h({ target: cell, button: 0, cancelable: true, preventDefault() {}, stopPropagation() {} });
}
function findMap(root) {
  if (root.className && String(root.className).split(/\s+/).includes('const-map')) return root;
  for (const c of root.children) { const r = findMap(c); if (r) return r; }
  return null;
}

// ============ 静态/初始 ============
check('title 含 星织 Asterweave', /星织 Asterweave/.test((/<title>([\s\S]*?)<\/title>/.exec(html) || [])[1] || ''), doc1Title());
function doc1Title() { const m = /<title>([\s\S]*?)<\/title>/.exec(html); return m ? m[1] : ''; }

// ============ 全新页面：解锁按钮 ============
{
  const ctx = boot();
  const doc = ctx.document;
  const unlock = doc.byId.get('unlockBtn');
  eq('初始「关卡」总数显示 20', doc.byId.get('lvBtnTotal').textContent, '20');
  eq('初始解锁按钮文案', unlock.textContent, '🔓 全部解锁');
  const before = unlock.textContent;
  const beforeSaved = JSON.parse(ctx.localStorage.getItem('leixian.migong.progress.v1') || '{}');
  unlock.click();
  const afterSaved = JSON.parse(ctx.localStorage.getItem('leixian.migong.progress.v1') || '{}');
  check('全新页面点「全部解锁」生效', afterSaved.devUnlock === true,
    'click 前 devUnlock=' + String(beforeSaved.devUnlock) + ' click 后=' + String(afterSaved.devUnlock) +
    ' 文案=' + unlock.textContent + '（期望点击后立即 true）');
  // 复现根因：重置按钮第一次点击才绑定 unlock 监听
  doc.byId.get('resetBtn').click();
  unlock.click();
  check('先点一次「重置进度」后「全部解锁」才生效（根因证据）',
    unlock.textContent === '🔒 恢复进度锁', '文案=' + unlock.textContent);
  const saved = JSON.parse(ctx.localStorage.getItem('leixian.migong.progress.v1') || '{}');
  eq('devUnlock 写入 localStorage', saved.devUnlock, true);
  check('解锁后第 19 关按钮可用', !levelButton(doc, 18).disabled, 'disabled=' + levelButton(doc, 18).disabled);
  eq('按钮文案「🔭 观测」', doc.byId.get('modeDig').textContent, '🔭 观测');
  eq('按钮文案「★ 标记」', doc.byId.get('modeFlag').textContent, '★ 标记');
}

// ============ 20 关通关 ============
const ctx = boot();
const doc = ctx.document;
const won = [];

for (let li = 0; li < LEVELS.length; li++) {
  const lv = LEVELS[li];
  const n = lv.size;
  const mineSet = new Set(lv.mines.map(([r, c]) => r * n + c));
  const noiseSet = new Set(lv.noise.map(([r, c]) => r * n + c));

  if (li > 0) {
    // 优先用通关 modal 的「下一关 →」
    const btns = doc.byId.get('modalBtns').children;
    const nx = btns.find(b => b.textContent.indexOf('下一关') >= 0);
    if (nx) nx.click(); else levelButton(doc, li).click();
  }
  let gs = gameState(ctx);
  check('L' + lv.id + ' 进入关卡', gs.levelId === lv.id, 'levelId=' + gs.levelId);

  // 行列线索
  const clueCount = doc.byId.get('board').children.filter(c => c.classList.contains('clue')).length;
  if (li === 0) eq('L1 无行列线索', clueCount, 0);
  if (li === 1) eq('L2 有行列线索', clueCount, 2 * n + 1);

  // 未通关时不得泄露雷位（含杂星）
  const cells0 = cellsOf(doc);
  let leak = [];
  for (const [i, el] of cells0) {
    if (!mineSet.has(i)) continue;
    const cls = el.className, txt = el.textContent, ih = el.innerHTML;
    if (cls !== 'cell' || txt !== '' || ih !== '') leak.push([i, cls, txt, ih.slice(0, 40)]);
  }
  check('L' + lv.id + ' 未won时DOM不泄露雷位(含杂星)', leak.length === 0, JSON.stringify(leak.slice(0, 3)));
  const gs0 = gameState(ctx);
  check('L' + lv.id + ' 未won时gameState无坐标', !("minesPos" in gs0) && JSON.stringify(gs0).indexOf('[[') < 0, JSON.stringify(gs0));

  // 标记全部雷
  doc.byId.get('modeFlag').click();
  for (const [r, c] of lv.mines) pointer(ctx, cellsOf(doc).get(r * n + c));
  // 翻开所有安全格
  doc.byId.get('modeDig').click();
  for (let i = 0; i < n * n; i++) if (!mineSet.has(i)) pointer(ctx, cellsOf(doc).get(i));

  gs = gameState(ctx);
  const ok = gs.status === 'won';
  won.push({ id: lv.id, status: gs.status });
  check('L' + lv.id + ' 玩到 won', ok, 'status=' + gs.status + ' lives=' + gs.lives);

  if (!ok) { check('L' + lv.id + ' 揭晓检查跳过', false, '未通关'); continue; }

  // 通关后棋盘：星座星 ✦ / 杂星暗点
  let badMine = [];
  for (const [r, c] of lv.mines) {
    const i = r * n + c, el = cellsOf(doc).get(i);
    const isNoise = noiseSet.has(i);
    if (isNoise) { if (!el.classList.contains('wonoise') || el.innerHTML.indexOf('noise-star') < 0) badMine.push([i, 'noise', el.className]); }
    else { if (!el.classList.contains('wonstar') || el.textContent !== '✦') badMine.push([i, 'star', el.className, el.textContent]); }
  }
  check('L' + lv.id + ' 通关棋盘星/杂星区分', badMine.length === 0, JSON.stringify(badMine.slice(0, 3)));

  // 闪烁期间不弹窗
  check('L' + lv.id + ' 闪烁期 modal 未打开', doc.byId.get('overlay').className.indexOf('open') < 0,
    'overlay=' + doc.byId.get('overlay').className);

  ctx.__flush();

  const map = findMap(doc.byId.get('constSlot'));
  check('L' + lv.id + ' 揭晓图存在', !!map);
  if (map) {
    const svg = map.innerHTML;
    const nstar = (svg.match(/class="gstar"/g) || []).length;
    const nline = (svg.match(/class="gline"/g) || []).length;
    const nnoise = (svg.match(/class="gnoise"/g) || []).length;
    eq('L' + lv.id + ' 揭晓星座星数', nstar, lv.theme.stars.length);
    eq('L' + lv.id + ' 揭晓连线数', nline, lv.theme.lines.length);
    eq('L' + lv.id + ' 揭晓杂星暗点数', nnoise, lv.noise.length);
    const starXY = new Set();
    for (const m of svg.matchAll(/<circle class="gstar"[^>]*cx="([\d.]+)"[^>]*cy="([\d.]+)"/g)) starXY.add(m[1] + ',' + m[2]);
    let overlap = 0;
    for (const m of svg.matchAll(/<circle class="gnoise"[^>]*cx="([\d.]+)"[^>]*cy="([\d.]+)"/g)) if (starXY.has(m[1] + ',' + m[2])) overlap++;
    eq('L' + lv.id + ' 杂星不与星座星重叠', overlap, 0);
  }
  check('L' + lv.id + ' 通关 modal 打开', doc.byId.get('overlay').className.indexOf('open') >= 0,
    'overlay=' + doc.byId.get('overlay').className);
}

eq('20 关全部 won', won.filter(x => x.status === 'won').length, 20);

// ============ 失败路径 ============
levelButton(doc, 0).click();
doc.byId.get('modeDig').click();
const l0 = LEVELS[0];
for (const [r, c] of l0.mines.slice(0, 3)) pointer(ctx, cellsOf(doc).get(r * l0.size + c));
let gf = gameState(ctx);
eq('踩爆 3 颗后 status=lost', gf.status, 'lost');
eq('命数归零', gf.lives, 0);
ctx.__flush();
eq('失败 modal 标题', doc.byId.get('modalTitle').textContent, '观测失败');
let hitCount = 0;
for (const el of cellsOf(doc).values()) if (el.classList.contains('hitstar') || el.classList.contains('hitnoise')) hitCount++;
check('失败只亮出踩爆的 3 颗雷', hitCount === 3, 'hitCount=' + hitCount);

// ---------------- 输出 ----------------
const fails = results.filter(r => !r.ok);
fs.writeFileSync(path.join(ROOT, 'verification', 'v10_out_d.json'), JSON.stringify({ results, fails: fails.length }, null, 1), 'utf8');
for (const r of results) console.log((r.ok ? 'PASS ' : 'FAIL ') + r.name + (r.ok ? '' : ' :: ' + r.detail));
console.log('D total', results.length, 'fails', fails.length);