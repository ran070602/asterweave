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

// ---------------- v21：图鉴 3D 天球 ----------------
if (byId.introStart) { byId.introStart.dispatchEvent(mkEvent('click', { target: byId.introStart })); flush(0); }
const SKY_IDS = (function(){
  const m = html.match(/\/\* SKY_INJECT_START \*\/\s*const SKY = (\[[\s\S]*?\]);\s*\/\* SKY_INJECT_END \*\//);
  return m ? JSON.parse(m[1]).map(function(x){ return x.id; }) : [];
})();
const SKY_ALL = (function(){
  const m = html.match(/\/\* SKY_INJECT_START \*\/\s*const SKY = (\[[\s\S]*?\]);\s*\/\* SKY_INJECT_END \*\//);
  return m ? JSON.parse(m[1]) : [];
})();
function mapHtml(){ return String(byId.skyMap.innerHTML || ''); }
function nodeXY(h){
  const out = [];
  const re = /<g class="sky3d-node[^"]*"[^>]*opacity="([\d.]+)"[^>]*>[\s\S]*?<circle class="hit" cx="(-?[\d.]+)" cy="(-?[\d.]+)"/g;
  let m;
  while ((m = re.exec(h))) out.push({ op: +m[1], x: +m[2], y: +m[3] });
  return out;
}
function openAtlas(){ byId.skyBtn.dispatchEvent(mkEvent('click', { target: byId.skyBtn })); flush(20); }

ok('默认是 3D 天球（按钮高亮 + 提示文案）',
   String(byId.skyMode3d.className).indexOf('on') >= 0 && String(byId.skyHint.textContent).indexOf('3D 天球') >= 0,
   byId.skyHint.textContent);
openAtlas();
let h = mapHtml();
ok('3D 地图包含天赤道环', h.indexOf('sky3d-eq') >= 0);
ok('3D 地图包含赤纬/赤经网格', (h.match(/class="sky3d-g"/g) || []).length >= 12, String((h.match(/class="sky3d-g"/g) || []).length));
ok('3D 地图包含银道带', h.indexOf('sky3d-mw') >= 0);
ok('3D 地图包含确定性星尘', (h.match(/fill="#cfe0ff"/g) || []).length >= 50, String((h.match(/fill="#cfe0ff"/g) || []).length));

// 未观测：50 个节点都在，但一个名字都不显示（不泄露）
let nodes = nodeXY(h);
ok('50 个星座节点全部渲染', nodes.length === 50, String(nodes.length));
ok('未观测时没有任何星座名字', (h.match(/class="lbl"/g) || []).length === 0);
ok('未观测节点是暗色（op 上限 < 0.75）', Math.max.apply(null, nodes.map(n => n.op)) < 0.75, 'maxOp=' + Math.max.apply(null, nodes.map(n => n.op)));

// 投影范围：全部落在 viewBox 200×120 内
ok('所有节点都投影在可视区内',
   nodes.every(n => Math.abs(n.x) <= 100 && Math.abs(n.y) <= 60),
   'maxX=' + Math.max.apply(null, nodes.map(n => Math.abs(n.x))).toFixed(1) + ' maxY=' + Math.max.apply(null, nodes.map(n => Math.abs(n.y))).toFixed(1));
ok('深度线索：远侧不透明度明显低于近侧',
   Math.min.apply(null, nodes.map(n => n.op)) < Math.max.apply(null, nodes.map(n => n.op)) - 0.3,
   'min=' + Math.min.apply(null, nodes.map(n => n.op)).toFixed(2) + ' max=' + Math.max.apply(null, nodes.map(n => n.op)).toFixed(2));
ok('__sky3d 状态可读', !!win.__sky3d && win.__sky3d.nodes === 50, JSON.stringify(win.__sky3d));

// 一键点亮后：正面半球出现名字，且只显示近侧
byId.skyLitBtn.dispatchEvent(mkEvent('click', { target: byId.skyLitBtn }));
flush(20);
h = mapHtml();
const labels = (h.match(/class="lbl"/g) || []).length;
ok('点亮后出现星座名标注', labels > 0, 'labels=' + labels);
ok('标注只给正面半球（数量少于总数一半）', labels <= 25, 'labels=' + labels);
ok('__sky3d 记录了标注数', win.__sky3d.labels === labels, String(win.__sky3d.labels));

// 拖动 = 转动天球
const before = win.__sky3d.yaw;
const nodesBefore = nodeXY(mapHtml());
byId.skyMap.dispatchEvent(mkEvent('pointerdown', { target: byId.skyMap, pointerId: 1, clientX: 100, clientY: 100, button: 0 }));
byId.skyMap.dispatchEvent(mkEvent('pointermove', { target: byId.skyMap, pointerId: 1, clientX: 168, clientY: 118, button: 0 }));
flush(0);
ok('拖动改变了天球朝向', win.__sky3d.yaw !== before, 'yaw ' + before.toFixed(3) + ' → ' + win.__sky3d.yaw.toFixed(3));
const nodesAfter = nodeXY(mapHtml());
ok('拖动后节点坐标随之变化', nodesBefore.some((n, i) => nodesAfter[i] && Math.abs(n.x - nodesAfter[i].x) > 0.5));
byId.skyMap.dispatchEvent(mkEvent('pointerup', { target: byId.skyMap, pointerId: 1, clientX: 168, clientY: 118, button: 0 }));
flush(0);

// 双击复位
byId.skyMap.dispatchEvent(mkEvent('dblclick', { target: byId.skyMap }));
flush(0);
ok('双击复位（yaw 回到 0.95）', Math.abs(win.__sky3d.yaw - 0.95) < 0.001, String(win.__sky3d.yaw));

// 自转：等待 hold 结束后应自动前进
const yawA = win.__sky3d.yaw;
flush(2600);
const yawB = win.__sky3d.yaw;
ok('松手后自动缓慢自转', yawB > yawA, yawA.toFixed(3) + ' → ' + yawB.toFixed(3));
ok('自转速度很慢（2.6 秒内 < 0.2 rad）', (yawB - yawA) < 0.2, (yawB - yawA).toFixed(3));

// 季节筛选在 3D 下生效
function pickSeason(name){
  const node = { getAttribute: function(){ return name; } };
  byId.skyFilters.dispatchEvent(mkEvent('click', { target: { closest: function(sel){ return sel === '[data-season]' ? node : null; } } }));
  flush(60);
}
pickSeason('春季');
const seasonCnt = SKY_ALL.filter(s => s.season === '春季').length;
ok('季节筛选后节点数 = 该季节星座数', nodeXY(mapHtml()).length === seasonCnt,
   nodeXY(mapHtml()).length + ' vs ' + seasonCnt);
pickSeason('全部');
ok('切回全部后节点恢复 50', nodeXY(mapHtml()).length === 50, String(nodeXY(mapHtml()).length));

// 切到 2D 投影：3D 元素消失、提示文案变化
byId.skyMode2d.dispatchEvent(mkEvent('click', { target: byId.skyMode2d }));
flush(20);
h = mapHtml();
ok('切到 2D 后不再有 3D 网格', h.indexOf('sky3d-eq') < 0 && h.indexOf('sky3d-node') < 0);
ok('切到 2D 后提示文案变成 2D 投影', String(byId.skyHint.textContent).indexOf('2D 投影') >= 0, byId.skyHint.textContent);
ok('2D 模式仍是原来的「横向赤经/纵向赤纬」布局', h.indexOf('sky-sector') >= 0 || (h.match(/class="sky-grid/g) || []).length >= 5);
ok('2D 下 50 个节点也都在', (h.match(/data-sky="/g) || []).length === 50, String((h.match(/data-sky="/g) || []).length));

// 切回 3D
byId.skyMode3d.dispatchEvent(mkEvent('click', { target: byId.skyMode3d }));
flush(20);
ok('可以切回 3D 天球', mapHtml().indexOf('sky3d-eq') >= 0);
ok('模式选择已持久化到 progress', /"sky3d":true/.test(String(store['leixian.migong.progress.v1'] || '')), 'progress 已写入');

// 关闭图鉴后自转停止
byId.skyCloseBtn.dispatchEvent(mkEvent('click', { target: byId.skyCloseBtn }));
flush(20);
const yawC = win.__sky3d.yaw;
flush(1500);
ok('关闭图鉴后停止自转（不再前进）', Math.abs(win.__sky3d.yaw - yawC) < 1e-9, String(win.__sky3d.yaw - yawC));

ok('全页零 http(s) 外部引用', !/https?:\/\//.test(html), 'html 0 处');
ok('未引入任何 3D 库（无 three / three.js 引用）', !/three\.min|threejs|THREE\./i.test(html));

const pass = R.filter(x => x.pass === true).length;
const fail = R.filter(x => x.pass === false);
console.log(R.map(x => (x.pass === true ? '  ✓ ' : x.pass === false ? '  ✗ ' : '  · ') + x.name + (x.ev ? '  [' + x.ev + ']' : '')).join('\n'));
console.log(`\nSUMMARY pass=${pass} fail=${fail.length}`);
if (fail.length) { console.log('FAILED:', fail.map(x => x.name).join(' | ')); process.exitCode = 1; }
