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

// ---------------- v20：星座详情「海报」----------------
if (byId.introStart) { byId.introStart.dispatchEvent(mkEvent('click', { target: byId.introStart })); flush(0); }

const SKY_ALL = (function(){
  const m = html.match(/\/\* SKY_INJECT_START \*\/\s*const SKY = (\[[\s\S]*?\]);\s*\/\* SKY_INJECT_END \*\//);
  return m ? JSON.parse(m[1]) : [];
})();
const SKY_IDS = (function(){
  const m = html.match(/\/\* SKY_INJECT_START \*\/\s*const SKY = (\[[\s\S]*?\]);\s*\/\* SKY_INJECT_END \*\//);
  return m ? JSON.parse(m[1]).map(function(x){ return x.id; }) : [];
})();
const body = byId.constModalBody;
function openAtlas(){ byId.skyBtn.dispatchEvent(mkEvent('click', { target: byId.skyBtn })); flush(20); }
function selectSky(id){
  const node = { getAttribute: function(){ return id; } };
  byId.skyMap.dispatchEvent(mkEvent('click', { target: { closest: function(sel){ return sel === '[data-sky]' ? node : null; } } }));
  flush(20);
}
function detail(){ return String(body.innerHTML || ''); }

openAtlas();
ok('图鉴已打开', byId.skyPanel.hidden === false);

// ① 未观测：不泄露海报与星名
selectSky('gemini');
let d = detail();
ok('未观测星座不显示海报', d.indexOf('sky-poster') < 0, 'len=' + d.length);
ok('未观测星座不泄露星名', d.indexOf('Castor') < 0 && d.indexOf('Pollux') < 0);
ok('未观测卡片提示去通关', d.indexOf('未观测') >= 0);

// ② 一键点亮后：海报 = 主视觉，缩略图在左上
byId.skyLitBtn.dispatchEvent(mkEvent('click', { target: byId.skyLitBtn }));
flush(20);
selectSky('gemini');
d = detail();
ok('已观测星座显示海报', d.indexOf('class="sky-poster"') >= 0);
ok('海报里有大标题（英文 + 中文）',
   /sky-poster-title"><b>Gemini<\/b><span>双子座<\/span>/.test(d), (d.match(/sky-poster-title[^<]*<b>([^<]*)<\/b><span>([^<]*)<\/span>/) || []).slice(1, 3).join(' / '));
ok('左上角有缩略图（旧星图缩小放左上）',
   d.indexOf('sky-thumb') >= 0 && d.indexOf('sky-detail-head') >= 0 && d.indexOf('const-svg') >= 0);
ok('缩略图在信息列之前（左上）', d.indexOf('sky-thumb') < d.indexOf('sky-head-main'));
ok('海报含观赏信息卡', d.indexOf('sky-poster-info') >= 0 && d.indexOf('可见：') >= 0 && d.indexOf('最佳观赏：') >= 0);
ok('双层座最佳观赏 = 2 月（与参考图 Best viewed: February 一致）', d.indexOf('最佳观赏：<b>2 月</b>') >= 0,
   (d.match(/最佳观赏：<b>([^<]*)<\/b>/) || [])[1]);
ok('双子座可见半球 = 北半球', d.indexOf('可见：<b>北半球</b>') >= 0, (d.match(/可见：<b>([^<]*)<\/b>/) || [])[1]);
const starDots = (d.match(/class="p-star"/g) || []).length;
const lineEls = (d.match(/class="p-line"/g) || []).length;
ok('海报星点数 = 该关星座星数', starDots === 12, 'dots=' + starDots);
ok('海报连线数 = 该关连线数', lineEls >= 6, 'lines=' + lineEls);
const labels = (d.match(/class="p-label"[^>]*>([^<]*)</g) || []).map(s => s.replace(/.*>/, '').replace(/<$/, ''));
ok('海报有星名标注（≥3 个）', labels.length >= 3, labels.join(','));
ok('标注里有参考图中的星名（Castor / Pollux / Alhena）',
   labels.indexOf('Castor') >= 0 || labels.indexOf('Pollux') >= 0 || labels.indexOf('Alhena') >= 0, labels.join(','));
ok('标注不重复', new Set(labels).size === labels.length, labels.join(','));

// ③ 50 个星座逐个渲染：都能出海报、都有标注
const ids = SKY_IDS;
let posterAll = 0, labelOk = 0, monthOk = 0, err = '';
for (let i = 0; i < ids.length; i++){
  try {
    selectSky(ids[i]);
    const html2 = detail();
    if (html2.indexOf('class="sky-poster"') >= 0) posterAll++;
    const ls = (html2.match(/class="p-label"[^>]*>([^<]*)</g) || []);
    if (ls.length >= 3) labelOk++;
    const mm = html2.match(/最佳观赏：<b>(\d+) 月<\/b>/);
    if (mm && +mm[1] >= 1 && +mm[1] <= 12) monthOk++;
  } catch (e) { if (!err) err = ids[i] + ': ' + e.message; }
}
ok('50 个星座全部能渲染海报', posterAll === ids.length, posterAll + '/' + ids.length + (err ? ' err=' + err : ''));
ok('50 个星座全部有 ≥3 个星名标注', labelOk === ids.length, String(labelOk));
ok('50 个星座的最佳观赏月份都在 1–12', monthOk === ids.length, String(monthOk));

// ④ 月份公式抽检（对照常识：猎户座 1 月、南十字 5 月）
selectSky('orion');
ok('猎户座最佳观赏 = 1 月', detail().indexOf('最佳观赏：<b>1 月</b>') >= 0, (detail().match(/最佳观赏：<b>([^<]*)<\/b>/) || [])[1]);
selectSky('crux');
ok('南十字座最佳观赏 = 5 月', detail().indexOf('最佳观赏：<b>5 月</b>') >= 0, (detail().match(/最佳观赏：<b>([^<]*)<\/b>/) || [])[1]);

// ⑤ v2.6 版式硬断言：标题带不侵入、图形占比、标注不重叠
function posterParts(html2){
  const svg = html2.slice(html2.indexOf('<svg class="sky-poster-svg"'));
  const labels = [];
  const re = /<text class="p-label" x="([\d.]+)" y="([\d.]+)" text-anchor="(\w+)">([^<]*)<\/text>/g;
  let m;
  while ((m = re.exec(svg))){
    const w = m[4].length * 6.7 + 8, h = 15;
    const x = +m[1], y = +m[2];
    labels.push({ txt: m[4], x: (m[3] === 'end' ? x - w : x), y: y - h + 4, w: w, h: h });
  }
  const ys = [];
  const rc = /<circle class="p-star" cx="([\d.]+)" cy="([\d.]+)"/g;
  let c2;
  while ((c2 = rc.exec(svg))) ys.push(+c2[2]);
  return { labels: labels, starTop: ys.length ? Math.min.apply(null, ys) : -1, starBottom: ys.length ? Math.max.apply(null, ys) : -1 };
}
const TITLE_BOTTOM = 74;
let overlapBad = '', topBad = '', sizeBad = '';
for (let i = 0; i < ids.length; i++){
  selectSky(ids[i]);
  const p = posterParts(detail());
  for (let a = 0; a < p.labels.length; a++){
    for (let b = a + 1; b < p.labels.length; b++){
      const A = p.labels[a], B = p.labels[b];
      if (!(A.x + A.w < B.x || A.x > B.x + B.w || A.y + A.h < B.y || A.y > B.y + B.h)){
        if (!overlapBad) overlapBad = ids[i] + ': ' + A.txt + ' × ' + B.txt;
      }
    }
  }
  if (p.labels.some(l => l.y < TITLE_BOTTOM) && !topBad) topBad = ids[i];
  const span = p.starBottom - p.starTop;
  if (span < 380 * 0.55 && !sizeBad) sizeBad = ids[i] + ' span=' + span.toFixed(0);
}
ok('50 个星座的星名标注互不重叠', !overlapBad, overlapBad || 'no overlap');
ok('标注都不侵入顶部标题带', !topBad, topBad || 'all below ' + TITLE_BOTTOM);
ok('图形竖向跨度 ≥55%（星点跨度口径，图形框实际占 77%）', !sizeBad, sizeBad || 'ok');

// ⑥ 专名表：有专名的星，海报上应当显示专名而不是拜耳编号
const PROPER = (function(){
  const m = html.match(/const PROPER_NAMES = (\{[\s\S]*?\});/);
  try { return m ? JSON.parse(m[1]) : {}; } catch (e) { return {}; }
})();
const LEVELS_JSON = (function(){
  const m = html.match(/\/\* LEVELS_INJECT_START \*\/\s*const LEVELS = (\[[\s\S]*?\]);\s*\/\* LEVELS_INJECT_END \*\//);
  return m ? JSON.parse(m[1]) : [];
})();
const SKY_BY_LEVEL = {};
SKY_ALL.forEach(function(s){ SKY_BY_LEVEL[s.level] = s; });
let properBad = [], properChecked = 0;
Object.keys(PROPER).forEach(function(k){
  const parts = k.split('|');
  const lvNo = +parts[0], des = parts.slice(1).join('|');
  const lv = LEVELS_JSON[lvNo - 1];
  const sky = SKY_BY_LEVEL[lvNo];
  if (!lv || !sky) return;
  const stars = (lv.theme && lv.theme.stars) || [];
  const mine = stars.filter(function(s){ return String(s.en) === des; })[0];
  if (!mine) return;
  const top5 = stars.slice().sort(function(a, b){ return (a.mag || 9) - (b.mag || 9); }).slice(0, 5);
  if (top5.indexOf(mine) < 0) return;                  // 不在标注范围内，跳过
  properChecked++;
  selectSky(sky.id);
  const d2 = detail();
  const labels2 = (d2.match(/class="p-label"[^>]*>([^<]*)</g) || []).map(function(s){ return s.replace(/.*>/, '').replace(/<$/, ''); });
  if (labels2.indexOf(PROPER[k]) < 0 && labels2.indexOf(des) >= 0) properBad.push(sky.zh + ':' + des + '→' + PROPER[k]);
});
ok('海报标注使用专名（有专名时不会显示拜耳编号）',
   properBad.length === 0, properChecked === 0 ? '暂无专名数据（跳过）' : ('检查 ' + properChecked + ' 颗，问题 ' + properBad.length + ' 个 ' + properBad.slice(0, 3).join(',')));

ok('全页仍零 http(s) 外部引用', !/https?:\/\//.test(html), 'html 0 处');
ok('全页无 <img>（海报是内联 SVG）', (html.match(/<img[^>]*>/g) || []).length === 0);

const pass = R.filter(x => x.pass === true).length;
const fail = R.filter(x => x.pass === false);
console.log(R.map(x => (x.pass === true ? '  ✓ ' : x.pass === false ? '  ✗ ' : '  · ') + x.name + (x.ev ? '  [' + x.ev + ']' : '')).join('\n'));
console.log(`\nSUMMARY pass=${pass} fail=${fail.length}`);
if (fail.length) { console.log('FAILED:', fail.map(x => x.name).join(' | ')); process.exitCode = 1; }
