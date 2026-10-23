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

// ---------------- v19（v2.3）：意见箱（离线优先 / 居中 modal / 无扫码）----------------
if (byId.introStart) { byId.introStart.dispatchEvent(mkEvent('click', { target: byId.introStart })); flush(0); }

ok('顶栏有「意见」按钮', !!byId.fbBtn && (byId.fbBtn.textContent || '').includes('意见'), byId.fbBtn && byId.fbBtn.textContent);
ok('意见箱初始隐藏', byId.fbOverlay.hidden === true);
ok('详情/邮箱 modal 初始隐藏', byId.fbFloat.hidden === true);
ok('隐私说明（不保存任何内容 / 不会自动上传）',
   html.includes('这里不保存任何内容') && html.includes('不会自动上传'), '隐私说明在 HTML 里');

byId.fbCtx.checked = true;
byId.fbBtn.dispatchEvent(mkEvent('click', { target: byId.fbBtn }));
flush(0);
ok('点击后意见箱打开', byId.fbOverlay.hidden === false);

// ① 「查看」→ 屏幕中间弹 modal（不再向下展开）
ok('有「查看」入口', !!byId.fbCtxMore && String(byId.fbCtxMore.textContent).includes('查看'), byId.fbCtxMore && byId.fbCtxMore.textContent);
ok('未点开前 modal 仍隐藏（不占位置）', byId.fbFloat.hidden === true);
byId.fbCtxMore.dispatchEvent(mkEvent('click', { target: byId.fbCtxMore }));
flush(0);
ok('点「查看」弹出居中 modal', byId.fbFloat.hidden === false);
ok('modal 标题是「会附带这些信息」', String(byId.fbFloatTitle.textContent).includes('会附带这些信息'), byId.fbFloatTitle.textContent);
const ctxText = String(byId.fbCtxView.textContent || '');
ok('modal 里含当前关卡', ctxText.includes('关卡') && ctxText.includes('第 1'), ctxText.split('\n')[1] || '');
ok('modal 里含设备与版本', ctxText.includes('设备') && ctxText.includes('版本'), ctxText.replace(/\n/g, ' | ').slice(0, 120));
ok('modal 是固定定位在屏幕中央（不是内联下拉）',
   /\.fb-float\{[^}]*position:fixed/.test(html) && /\.fb-float\{[^}]*align-items:center/.test(html), 'CSS 断言');
byId.fbFloatOk.dispatchEvent(mkEvent('click', { target: byId.fbFloatOk }));
flush(0);
ok('「知道了」关闭 modal', byId.fbFloat.hidden === true);

// ② 第三个按钮 = 查看作者邮箱（已无扫码）
ok('第三个按钮是「✉ 查看作者邮箱」', !!byId.fbMailBtn && String(byId.fbMailBtn.textContent).includes('查看作者邮箱'), byId.fbMailBtn && byId.fbMailBtn.textContent);
ok('已无「扫码提交」按钮与二维码图', !byId.fbQrBtn && !byId.fbQrImg && !byId.fbQrBox);
byId.fbMailBtn.dispatchEvent(mkEvent('click', { target: byId.fbMailBtn }));
flush(0);
ok('点「查看作者邮箱」打开 modal', byId.fbFloat.hidden === false);
ok('modal 标题是「作者邮箱」', String(byId.fbFloatTitle.textContent).includes('作者邮箱'), byId.fbFloatTitle.textContent);
ok('显示真实邮箱地址', String(byId.fbMailAddr.textContent).includes('@') && String(byId.fbMailAddr.textContent).includes('.'), byId.fbMailAddr.textContent);
ok('已删除「用邮件 App 打开」', !byId.fbMailLink && !html.includes('fbMailLink') && !html.includes('用邮件 App 打开'));
ok('「复制」小按钮紧跟邮箱地址（同一行）',
   /class="fb-mail-line"><span class="fb-mail-addr" id="fbMailAddr">—<\/span><button[^>]*id="fbCopyMail">复制<\/button>/.test(html),
   'HTML 结构断言');
ok('小按钮文案是「复制」', String(byId.fbCopyMail.textContent).trim() === '复制', byId.fbCopyMail.textContent);
ok('详情/邮箱 modal 一页呈现（无内部滚动条）',
   !/\.fb-pop-body\{[^}]*max-height/.test(html) && !/\.fb-pop-body\{[^}]*overflow/.test(html), 'CSS 断言：无 max-height / overflow');
byId.fbCopyMail.dispatchEvent(mkEvent('click', { target: byId.fbCopyMail }));
flush(0);
ok('「复制邮箱」给出提示', String(byId.fbStatus.textContent || '').includes('邮箱') || String(byId.fbStatus.textContent || '').length > 0, byId.fbStatus.textContent);
(win._h['keydown'] || []).forEach(function(fn){ fn(mkEvent('keydown', { key: 'Escape', target: win })); });
flush(0);
ok('Esc 先关 modal（意见箱仍开着）', byId.fbFloat.hidden === true && byId.fbOverlay.hidden === false,
   `float=${byId.fbFloat.hidden} overlay=${byId.fbOverlay.hidden}`);

// ③ 复制：不落盘
byId.fbText.value = '第 3 关的行线索我看不懂';
byId.fbText.dispatchEvent(mkEvent('input', { target: byId.fbText }));
byId.fbCopy.dispatchEvent(mkEvent('click', { target: byId.fbCopy }));
flush(0);
ok('复制后给出状态提示', String(byId.fbStatus.textContent || '').length > 0, byId.fbStatus.textContent);
ok('不落盘：没有任何 feedback 键写入 localStorage',
   Object.keys(store).every(k => k.toLowerCase().indexOf('feedback') < 0), JSON.stringify(Object.keys(store)));
ok('已去掉「本机记录」UI', !byId.fbList && !byId.fbCount && !byId.fbClear);
let exportOk = true;
try { byId.fbSave.dispatchEvent(mkEvent('click', { target: byId.fbSave })); flush(0); } catch (e) { exportOk = false; }
ok('导出按钮不抛异常且不落盘',
   exportOk && Object.keys(store).every(k => k.toLowerCase().indexOf('feedback') < 0), JSON.stringify(Object.keys(store)));
ok('意见箱不影响游戏进度（仍可玩）', state().status === 'playing', `status=${state().status}`);

// ④ 关闭
(win._h['keydown'] || []).forEach(function(fn){ fn(mkEvent('keydown', { key: 'Escape', target: win })); });
flush(0);
ok('Esc 关闭意见箱', byId.fbOverlay.hidden === true);
byId.fbBtn.dispatchEvent(mkEvent('click', { target: byId.fbBtn })); flush(0);
byId.fbOverlay.dispatchEvent(mkEvent('click', { target: byId.fbOverlay })); flush(0);
ok('点遮罩关闭意见箱', byId.fbOverlay.hidden === true);

// ⑤ 离线自包含
ok('全页无 http(s) 外部引用', !/https?:\/\//.test(html), 'html 里 0 处 http(s)://');
ok('页面里没有外部 <img>（二维码已移除）',
   (html.match(/<img[^>]*>/g) || []).every(t => t.indexOf('src="data:') >= 0),
   `img 数=${(html.match(/<img[^>]*>/g) || []).length}`);

const pass = R.filter(x => x.pass === true).length;
const fail = R.filter(x => x.pass === false);
console.log(R.map(x => (x.pass === true ? '  ✓ ' : x.pass === false ? '  ✗ ' : '  · ') + x.name + (x.ev ? '  [' + x.ev + ']' : '')).join('\n'));
console.log(`\nSUMMARY pass=${pass} fail=${fail.length}`);
if (fail.length) { console.log('FAILED:', fail.map(x => x.name).join(' | ')); process.exitCode = 1; }
