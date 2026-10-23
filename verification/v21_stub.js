'use strict';
/* v21 复核：自写 DOM 桩 + 虚拟时钟，用 vm 直跑 dist 内联脚本（不 npm install、不改动被复核文件） */
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const VOID = new Set(['area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr']);
const RAWTEXT = new Set(['style', 'script', 'title', 'textarea']);

const kebab = s => s.replace(/[A-Z]/g, m => '-' + m.toLowerCase());
const camel = s => s.replace(/-([a-z])/g, (_, c) => c.toUpperCase());
let DOC = null; // 每次 boot 重建

function findTagEnd(s, i) {
  let q = null;
  for (let j = i; j < s.length; j++) {
    const ch = s[j];
    if (q) { if (ch === q) q = null; continue; }
    if (ch === '"' || ch === "'") { q = ch; continue; }
    if (ch === '>') return j;
  }
  return s.length - 1;
}
function parseAttrs(body) {
  const out = {};
  const re = /([^\s=\/]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+)))?/g;
  let m;
  while ((m = re.exec(body))) {
    const k = m[1];
    out[k] = (m[2] !== undefined) ? m[2] : (m[3] !== undefined) ? m[3] : (m[4] !== undefined) ? m[4] : '';
  }
  return out;
}

class El {
  constructor(tag, ns) {
    this.nodeType = tag === '#fragment' ? 11 : 1;
    this.tagName = String(tag).toUpperCase();
    this.nodeName = this.tagName;
    this.childNodes = [];
    this.parentNode = null;
    this.attrs = {};
    this._ev = {};
    this._html = null;
    this._style = {};
    const self = this;
    this._style.setProperty = function (k, v) { self._style[k] = String(v); };
    this._style.getPropertyValue = function (k) { return self._style[k] === undefined ? '' : self._style[k]; };
    this._style.removeProperty = function (k) { delete self._style[k]; };
    this.style = this._style;
    this.dataset = new Proxy({}, {
      get: (t, k) => self.attrs['data-' + kebab(String(k))],
      set: (t, k, v) => { self.attrs['data-' + kebab(String(k))] = String(v); return true; },
      has: (t, k) => ('data-' + kebab(String(k))) in self.attrs,
      ownKeys: () => Object.keys(self.attrs).filter(a => a.indexOf('data-') === 0).map(a => camel(a.slice(5))),
      getOwnPropertyDescriptor: (t, k) => ({ enumerable: true, configurable: true, value: self.attrs['data-' + kebab(String(k))] })
    });
  }
  get id() { return this.attrs.id || ''; }
  set id(v) { this.attrs.id = String(v); }
  get className() { return this.attrs.class || ''; }
  set className(v) { this.attrs.class = String(v); }
  get classList() {
    const self = this;
    const list = () => (self.attrs.class ? String(self.attrs.class).split(/\s+/).filter(Boolean) : []);
    return {
      add(...cs) { const l = list(); for (const c of cs) if (l.indexOf(c) < 0) l.push(c); self.attrs.class = l.join(' '); },
      remove(...cs) { self.attrs.class = list().filter(c => cs.indexOf(c) < 0).join(' '); },
      contains(c) { return list().indexOf(c) >= 0; },
      toggle(c, on) { const has = list().indexOf(c) >= 0; const want = on === undefined ? !has : !!on; if (want && !has) this.add(c); if (!want && has) this.remove(c); return want; },
      get length() { return list().length; },
      item(i) { return list()[i] || null; },
      get value() { return self.attrs.class || ''; }
    };
  }
  get hidden() { return 'hidden' in this.attrs; }
  set hidden(v) { if (v) this.attrs.hidden = ''; else delete this.attrs.hidden; }
  get disabled() { return 'disabled' in this.attrs; }
  set disabled(v) { if (v) this.attrs.disabled = ''; else delete this.attrs.disabled; }
  get value() { return this._val === undefined ? (this.attrs.value || '') : this._val; }
  set value(v) { this._val = String(v); }
  get firstChild() { return this.childNodes[0] || null; }
  get children() { return this.childNodes.filter(n => n.nodeType === 1); }
  get offsetWidth() { return 0; }
  get offsetHeight() { return 0; }
  get innerText() { return this.textContent; }
  set innerText(v) { this.textContent = v; }
  get textContent() {
    let out = '';
    for (const n of this.childNodes) out += (n.nodeType === 3 ? n.textContent : n.textContent);
    return out;
  }
  set textContent(v) {
    this.childNodes = []; this._html = null;
    const s = v === null || v === undefined ? '' : String(v);
    if (s !== '') { const t = new TextNode(s); t.parentNode = this; this.childNodes.push(t); }
  }
  get innerHTML() { return this._html !== null ? this._html : this.serialize(); }
  set innerHTML(v) {
    this.childNodes = [];
    const s = v === null || v === undefined ? '' : String(v);
    this._html = s;
    if (s) parseInto(this, s);
  }
  serialize() {
    let out = '';
    for (const n of this.childNodes) {
      if (n.nodeType === 3) out += n.textContent;
      else out += '<' + n.tagName.toLowerCase() + Object.keys(n.attrs).map(k => ' ' + k + '="' + n.attrs[k] + '"').join('') + '>' + n.serialize() + '</' + n.tagName.toLowerCase() + '>';
    }
    return out;
  }
  setAttribute(k, v) { this.attrs[k] = String(v); }
  getAttribute(k) { return (k in this.attrs) ? this.attrs[k] : null; }
  hasAttribute(k) { return k in this.attrs; }
  removeAttribute(k) { delete this.attrs[k]; }
  appendChild(n) {
    if (n && n.nodeType === 11) { for (const c of n.childNodes.slice()) this.appendChild(c); return n; }
    if (n.parentNode) n.parentNode.removeChild(n);
    n.parentNode = this; this._html = null; this.childNodes.push(n); return n;
  }
  removeChild(n) { const i = this.childNodes.indexOf(n); if (i >= 0) { this.childNodes.splice(i, 1); n.parentNode = null; } return n; }
  insertBefore(n, ref) { const i = this.childNodes.indexOf(ref); this._html = null; n.parentNode = this; if (i < 0) this.childNodes.push(n); else this.childNodes.splice(i, 0, n); return n; }
  addEventListener(t, fn, opts) {
    const cap = !!(opts === true || (opts && opts.capture));
    (this._ev[t] = this._ev[t] || []).push({ fn, capture: cap });
  }
  removeEventListener(t, fn, opts) {
    const cap = !!(opts === true || (opts && opts.capture));
    const l = this._ev[t]; if (!l) return;
    const i = l.findIndex(x => x.fn === fn && x.capture === cap);
    if (i >= 0) l.splice(i, 1);
  }
  matches(sel) { return matchesSelector(this, sel); }
  closest(sel) { let p = this; while (p && p.nodeType === 1) { if (matchesSelector(p, sel)) return p; p = p.parentNode; } return null; }
  querySelector(sel) { const r = queryAll(this, sel); return r.length ? r[0] : null; }
  querySelectorAll(sel) { return queryAll(this, sel); }
  focus() { if (DOC) DOC.activeElement = this; }
  blur() { if (DOC && DOC.activeElement === this) DOC.activeElement = DOC.body; }
  scrollIntoView() {}
  setPointerCapture() {}
  releasePointerCapture() {}
  getBoundingClientRect() {
    if (this.attrs['data-i'] !== undefined) {
      const r = Number(this.attrs['data-r']) || 0, c = Number(this.attrs['data-c']) || 0;
      return { left: c * 30, top: r * 30, width: 30, height: 30, right: c * 30 + 30, bottom: r * 30 + 30 };
    }
    if (/boardwrap/.test(this.attrs.class || '')) return { left: 0, top: 0, width: 400, height: 400, right: 400, bottom: 400 };
    return { left: 0, top: 0, width: 200, height: 120, right: 200, bottom: 120 };
  }
  get animVal() { return this; }
}
class TextNode {
  constructor(t) { this.nodeType = 3; this.tagName = '#text'; this.textContent = String(t); this.parentNode = null; this.childNodes = []; this._ev = {}; }
  addEventListener() {} removeEventListener() {}
}

function matchesCompound(el, comp) {
  if (!el || el.nodeType !== 1) return false;
  let rest = comp.trim();
  const tagM = /^[a-zA-Z][a-zA-Z0-9-]*/.exec(rest);
  if (tagM) { if (el.tagName.toLowerCase() !== tagM[0].toLowerCase()) return false; rest = rest.slice(tagM[0].length); }
  const re = /([.#]?)([a-zA-Z0-9_-]+)|\[([a-zA-Z0-9_-]+)(?:=("[^"]*"|'[^']*'|[^\]]*))?\]/g;
  let mm;
  while ((mm = re.exec(rest))) {
    if (mm[1] === '.') { if (!el.classList.contains(mm[2])) return false; }
    else if (mm[1] === '#') { if (el.attrs.id !== mm[2]) return false; }
    else if (mm[3]) {
      const k = mm[3];
      if (!(k in el.attrs)) return false;
      if (mm[4] !== undefined) {
        let v = mm[4];
        if ((v[0] === '"' && v[v.length - 1] === '"') || (v[0] === "'" && v[v.length - 1] === "'")) v = v.slice(1, -1);
        if (el.attrs[k] !== v) return false;
      }
    }
  }
  return true;
}
function matchesSelector(el, sel) {
  const parts = String(sel).trim().split(/\s+/);
  if (parts.length === 1) return matchesCompound(el, parts[0]);
  if (!matchesCompound(el, parts[parts.length - 1])) return false;
  let p = el.parentNode;
  for (let i = parts.length - 2; i >= 0; i--) {
    let found = false;
    while (p) { if (matchesCompound(p, parts[i])) { found = true; p = p.parentNode; break; } p = p.parentNode; }
    if (!found) return false;
  }
  return true;
}
function queryAll(root, sel) {
  const out = [];
  const walk = n => {
    for (const c of n.childNodes) {
      if (c.nodeType !== 1) continue;
      if (matchesSelector(c, sel)) out.push(c);
      walk(c);
    }
  };
  walk(root);
  return out;
}

function parseInto(root, html) {
  const stack = [root];
  let i = 0;
  const pushText = t => {
    if (!t || !t.trim()) return;
    const n = new TextNode(t); n.parentNode = stack[stack.length - 1];
    stack[stack.length - 1].childNodes.push(n);
  };
  while (i < html.length) {
    const lt = html.indexOf('<', i);
    if (lt < 0) { pushText(html.slice(i)); break; }
    if (lt > i) pushText(html.slice(i, lt));
    if (html.startsWith('<!--', lt)) { const e = html.indexOf('-->', lt); i = e < 0 ? html.length : e + 3; continue; }
    if (html.startsWith('<!', lt)) { const e = html.indexOf('>', lt); i = e < 0 ? html.length : e + 1; continue; }
    const gt = findTagEnd(html, lt);
    const raw = html.slice(lt + 1, gt);
    i = gt + 1;
    if (raw[0] === '/') {
      const name = raw.slice(1).trim().toLowerCase();
      for (let k = stack.length - 1; k > 0; k--) if (stack[k].tagName.toLowerCase() === name) { stack.length = k; break; }
      continue;
    }
    const selfClose = /\/\s*$/.test(raw);
    const body = selfClose ? raw.replace(/\/\s*$/, '') : raw;
    const tm = /^([a-zA-Z0-9:-]+)/.exec(body.trim());
    if (!tm) continue;
    const tag = tm[1];
    const el = DOC.createElement(tag);
    const at = parseAttrs(body.slice(body.indexOf(tag) + tag.length));
    for (const k in at) el.setAttribute(k, at[k]);
    const parent = stack[stack.length - 1];
    el.parentNode = parent; parent.childNodes.push(el);
    if (RAWTEXT.has(tag.toLowerCase())) {
      const close = html.toLowerCase().indexOf('</' + tag.toLowerCase(), i);
      const end = close < 0 ? html.length : close;
      el.textContent = html.slice(i, end);
      i = close < 0 ? html.length : (html.indexOf('>', close) + 1);
      continue;
    }
    if (selfClose || VOID.has(tag.toLowerCase())) continue;
    stack.push(el);
  }
}

function makeStorage(seed) {
  const d = Object.assign({}, seed || {});
  return {
    _d: d,
    getItem(k) { return (k in d) ? d[k] : null; },
    setItem(k, v) { d[k] = String(v); },
    removeItem(k) { delete d[k]; },
    clear() { for (const k in d) delete d[k]; },
    key(i) { return Object.keys(d)[i] || null; },
    get length() { return Object.keys(d).length; }
  };
}

function boot(opts) {
  opts = opts || {};
  const htmlPath = opts.html || process.env.V21_HTML || path.join(__dirname, 'frozen_v21b', 'dist_index.html');
  const html = fs.readFileSync(htmlPath, 'utf8');
  const a = html.indexOf('<script>') + '<script>'.length;
  const b = html.lastIndexOf('</script>');
  const pre = html.slice(0, html.indexOf('<script>'));
  const script = html.slice(a, b);

  DOC = {
    nodeType: 9, _ev: {}, activeElement: null,
    createElement(tag) { return new El(tag); },
    createDocumentFragment() { return new El('#fragment'); },
    getElementById(id) { const all = queryAll(DOC.documentElement, '#' + id); return all.length ? all[0] : null; },
    querySelector(s) { const r = queryAll(DOC.documentElement, s); return r.length ? r[0] : null; },
    querySelectorAll(s) { return queryAll(DOC.documentElement, s); },
    addEventListener(t, fn, o) { El.prototype.addEventListener.call(DOC, t, fn, o); },
    removeEventListener(t, fn, o) { El.prototype.removeEventListener.call(DOC, t, fn, o); },
    hidden: false
  };
  const rootEl = new El('html');
  DOC.documentElement = rootEl;
  parseInto(rootEl, pre.slice(pre.indexOf('<html')));
  if (!rootEl.childNodes.length) parseInto(rootEl, pre);
  DOC.body = (function find(n) { if (n.nodeType === 1 && n.tagName === 'BODY') return n; for (const c of n.childNodes) { const r = find(c); if (r) return r; } return null; })(rootEl);
  if (!DOC.body) { DOC.body = new El('body'); rootEl.appendChild(DOC.body); }
  DOC.activeElement = DOC.body;

  const clock = { now: 1000, timers: [], seq: 1 };
  const errors = [];
  function setTimeoutV(fn, ms) { const t = { id: clock.seq++, at: clock.now + (Number(ms) || 0), fn: fn, cancel: false }; clock.timers.push(t); return t; }
  function clearTimeoutV(id) { if (id && typeof id === 'object') id.cancel = true; else { const t = clock.timers.find(x => x.id === id); if (t) t.cancel = true; } }
  function advance(ms) {
    const end = clock.now + (ms || 0);
    for (;;) {
      const due = clock.timers.filter(t => !t.cancel && t.at <= end).sort((x, y) => x.at - y.at || x.id - y.id)[0];
      if (!due) break;
      clock.timers.splice(clock.timers.indexOf(due), 1);
      clock.now = Math.max(clock.now, due.at);
      try { due.fn(); } catch (e) { errors.push('timer: ' + (e && e.stack || e)); }
    }
    clock.now = end;
  }
  const reduce = !!opts.reduce;
  const sandbox = {
    console: console, JSON: JSON, Math: Math, Date: Date, Set: Set, Map: Map, Array: Array,
    Object: Object, String: String, Number: Number, Boolean: Boolean, isNaN: isNaN, isFinite: isFinite,
    parseInt: parseInt, parseFloat: parseFloat, Int16Array: Int16Array, Uint8Array: Uint8Array, Uint16Array: Uint16Array,
    Error: Error, TypeError: TypeError, RegExp: RegExp, Promise: Promise, Symbol: Symbol, Proxy: Proxy,
    document: DOC,
    setTimeout: setTimeoutV, clearTimeout: clearTimeoutV, setInterval: setTimeoutV, clearInterval: clearTimeoutV,
    requestAnimationFrame: fn => setTimeoutV(() => fn(clock.now), 16),
    cancelAnimationFrame: clearTimeoutV,
    performance: { now: () => clock.now },
    navigator: { userAgent: 'v21-stub', vibrate: null },
    localStorage: opts.storage || makeStorage(),
    matchMedia: q => ({ matches: reduce && /reduce/.test(q), media: q, addEventListener() {}, removeEventListener() {}, addListener() {}, removeListener() {} }),
    location: { href: 'file:///index.html', search: '' },
    _ev: {}, _errors: errors
  };
  sandbox.addEventListener = function (t, fn, o) { El.prototype.addEventListener.call(sandbox, t, fn, o); };
  sandbox.removeEventListener = function (t, fn, o) { El.prototype.removeEventListener.call(sandbox, t, fn, o); };
  const ctx = vm.createContext(sandbox);
  vm.runInContext('var window = globalThis; var self = globalThis;', ctx);

  function fire(node, ev, capture) {
    const l = (node._ev && node._ev[ev.type]) || [];
    for (const x of l.slice()) {
      if (x.capture !== capture) continue;
      ev.currentTarget = node;
      try { x.fn.call(node, ev); } catch (e) { errors.push('listener[' + ev.type + ']: ' + (e && e.stack || e)); }
    }
  }
  function dispatch(target, type, props) {
    const ev = Object.assign({
      type: type, target: target, defaultPrevented: false, _stop: false,
      preventDefault() { this.defaultPrevented = true; }, stopPropagation() { this._stop = true; }
    }, props || {});
    const pathArr = [];
    let p = target;
    while (p) { pathArr.push(p); p = p.parentNode; }
    if (pathArr.indexOf(DOC) < 0) pathArr.push(DOC);
    pathArr.push(sandbox);
    for (let i = pathArr.length - 1; i >= 0; i--) { fire(pathArr[i], ev, true); if (ev._stop) return ev; }
    for (let i = 0; i < pathArr.length; i++) { fire(pathArr[i], ev, false); if (ev._stop) return ev; }
    return ev;
  }

  try { vm.runInContext(script, ctx, { filename: 'dist-index-inline.js' }); }
  catch (e) { errors.push('boot: ' + (e && e.stack || e)); }

  return { doc: DOC, win: sandbox, ctx, clock, advance, dispatch, errors, storage: sandbox.localStorage, run: s => vm.runInContext(s, ctx) };
}

module.exports = { boot, makeStorage, El };
