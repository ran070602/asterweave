'use strict';
/*
 * T8 独立复核 · D 部分：运行时行为（Node + 自写最小 DOM stub，零依赖、不 npm install）。
 *
 * 覆盖：
 *   D1 抽出 game/index.html 的 <script> 在 DOM stub 里执行：无异常、LEVELS 解析、渲染数量
 *   D2 离线自包含静态扫描
 *   D3 用 verification/out_b.json 里「我自己求解器」的动作序列把 3 关都玩到 status==="won"
 *   D3b 胜利条件反向验证（只翻完不插旗 → 不赢）
 *   D4 反向测试：踩雷扣命 / 连踩 3 颗 lost / 插旗可取消
 *   D5 playing 时 DOM 不泄露雷位置
 *   D6 线索文本与独立重算一致；第 1 关无线索格
 *   D7 SPEC 边界：teach 文案、结果面板文案、踩炸未插旗是否算已标记、flood fill 遇插旗
 *   D8 v2 新增：关卡解锁（锁定/解锁）、localStorage 进度持久化与不可用时的静默降级
 *
 * 运行：  node verification/d_runtime_check.js
 * 输出：  stdout 日志 + verification/out_d.json
 */
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const crypto = require('crypto');

const ROOT = path.resolve(__dirname, '..');
// 可选：argv[2] = 被复核的 HTML 路径（默认 game/index.html；冻结副本用于复现同一修订）
const HTML_PATH = process.argv[2] ? path.resolve(process.argv[2]) : path.join(ROOT, 'game', 'index.html');
const LEVELS_JSON_PATH = process.env.T8_LEVELS
  ? path.resolve(process.env.T8_LEVELS) : path.join(ROOT, 'tools', 'levels.json');
const expectedLevels = JSON.parse(fs.readFileSync(LEVELS_JSON_PATH, 'utf8'));
const html = fs.readFileSync(HTML_PATH, 'utf8');
const htmlSha = crypto.createHash('sha256').update(html, 'utf8').digest('hex');
const outA = JSON.parse(fs.readFileSync(path.join(ROOT, 'verification', 'out_a.json'), 'utf8'));
const outB = JSON.parse(fs.readFileSync(path.join(ROOT, 'verification', 'out_b.json'), 'utf8'));

const results = [];
function check(id, ok, detail) {
  results.push({ id, ok: !!ok, detail: String(detail) });
  console.log((ok ? '[PASS] ' : '[FAIL] ') + id + ' :: ' + detail);
  return !!ok;
}

/* ------------------------------------------------------------------ DOM stub */
class ClassList {
  constructor(el) { this.el = el; }
  get _list() { return (this.el._className || '').split(/\s+/).filter(Boolean); }
  _set(l) { this.el._className = l.join(' '); }
  add(...cs) { const l = this._list; cs.forEach(c => { if (!l.includes(c)) l.push(c); }); this._set(l); }
  remove(...cs) { this._set(this._list.filter(c => !cs.includes(c))); }
  contains(c) { return this._list.includes(c); }
  toggle(c) { this.contains(c) ? this.remove(c) : this.add(c); }
}

class El {
  constructor(tag) {
    this.tagName = String(tag || 'div').toUpperCase();
    this._tag = String(tag || 'div').toLowerCase();
    this._className = '';
    this._attrs = {};
    this._listeners = {};
    this._text = '';
    this.dataset = {};
    this.children = [];
    this.parentNode = null;
    this._isFragment = false;
    this.disabled = false;
    this.classList = new ClassList(this);
    const props = {};
    this.style = {
      _props: props,
      setProperty(k, v) { props[k] = v; },
      removeProperty(k) { delete props[k]; },
      getPropertyValue(k) { return props[k] === undefined ? '' : props[k]; },
    };
  }
  get className() { return this._className; }
  set className(v) { this._className = String(v); }
  get textContent() {
    if (this.children.length === 0) return this._text;
    return this.children.map(c => c.textContent).join('') + this._text;
  }
  set textContent(v) { this._text = v === null || v === undefined ? '' : String(v); }
  set innerHTML(v) {
    this._html = String(v);
    this.children = [];
    this._text = this._html === '' ? '' : this._html.replace(/<[^>]*>/g, '');
  }
  get innerHTML() { return this._html === undefined ? '' : this._html; }
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
  addEventListener(type, fn) { (this._listeners[type] = this._listeners[type] || []).push(fn); }
  removeEventListener(type, fn) {
    if (!this._listeners[type]) return;
    this._listeners[type] = this._listeners[type].filter(f => f !== fn);
  }
  __fire(type, ev) {
    const e = Object.assign({
      target: this, currentTarget: this, cancelable: false, button: 0,
      preventDefault() { }, stopPropagation() { }, key: '',
    }, ev || {});
    (this._listeners[type] || []).slice().forEach(fn => fn(e));
    if (this.parentNode && this.parentNode.__fire) {
      this.parentNode.__fire(type, Object.assign({}, e, { target: e.target }));
    }
  }
  closest(sel) {
    let cur = this;
    const want = sel.replace(/^\./, '');
    while (cur) {
      if (cur.classList && cur.classList.contains(want)) return cur;
      cur = cur.parentNode;
    }
    return null;
  }
  scrollIntoView() { /* stub */ }
  getBoundingClientRect() { return { width: 0, height: 0, top: 0, left: 0, right: 0, bottom: 0 }; }
}

function makeEnv(opts) {
  opts = opts || {};
  const documentStub = {
    _byId: new Map(),
    createElement(tag) { return new El(tag); },
    createDocumentFragment() { const f = new El('#fragment'); f._isFragment = true; return f; },
    getElementById(id) { return this._byId.get(id) || null; },
    body: new El('body'),
  };
  for (const m of html.matchAll(/\sid="([^"]+)"/g)) {
    if (!documentStub._byId.has(m[1])) documentStub._byId.set(m[1], new El('div'));
  }
  let raf = 0;
  const windowStub = {
    _listeners: {},
    addEventListener(type, fn) { (this._listeners[type] = this._listeners[type] || []).push(fn); },
  };
  if (opts.storage) windowStub.localStorage = opts.storage;
  const sandbox = {
    document: documentStub, window: windowStub,
    requestAnimationFrame: (cb) => { raf++; cb(); return raf; },
    setTimeout: (cb) => { cb(); return 0; },
    console,
  };
  return { document: documentStub, window: windowStub, sandbox, rafCount: () => raf };
}

function runScript(env) {
  try {
    vm.createContext(env.sandbox);
    vm.runInContext(SCRIPT, env.sandbox, { filename: 'game-index-inline.js', timeout: 15000 });
    return null;
  } catch (e) { return e; }
}

/* ------------------------------------------------------------------ 静态扫描 + 抽 script */
console.log('== D2. 离线自包含静态扫描 ==');
const forbidden = ['http://', 'https://', 'fetch(', 'XMLHttpRequest', 'WebSocket', '<img', '<link', 'import('];
for (const pat of forbidden) {
  const hits = html.split(pat).length - 1;
  check('D2 不含 ' + JSON.stringify(pat), hits === 0, `出现次数=${hits}`);
}
check('D2 <script> 标签数', (html.match(/<script/g) || []).length === 1,
  `<script 数=${(html.match(/<script/g) || []).length}`);
const SCRIPT_M = html.match(/<script>([\s\S]*?)<\/script>/);
const SCRIPT = SCRIPT_M ? SCRIPT_M[1] : '';

console.log('== D1. 在自写 DOM stub 中执行 <script>（无 localStorage：模拟 file:// 隐私模式/禁用） ==');
check('D1 找到 <script> 块', !!SCRIPT_M, SCRIPT_M ? `长度=${SCRIPT.length}` : '未找到');
const env = makeEnv();
const runErr = runScript(env);
check('D1 脚本执行无异常抛出（无 localStorage 时静默降级）', runErr === null,
  runErr ? `${runErr.name}: ${runErr.message}` : '无异常');
check('D1 requestAnimationFrame/fitBoard 路径被执行', env.rafCount() > 0,
  `requestAnimationFrame 调用次数=${env.rafCount()}`);

const inject = html.match(/\/\*\s*LEVELS_INJECT_START\s*\*\/([\s\S]*?)\/\*\s*LEVELS_INJECT_END\s*\*\//);
let levels = null;
try { levels = JSON.parse(inject[1].match(/const\s+LEVELS\s*=\s*(\[[\s\S]*\])\s*;/)[1]); } catch (e) { }
check('D1 内嵌 LEVELS 解析成功', Array.isArray(levels) && levels.length === expectedLevels.length,
  levels ? `关卡数=${levels.length}（期望 ${expectedLevels.length}）` : '解析失败');
check('D1 内嵌 LEVELS 与冻结数据逐关 id 一致',
  Array.isArray(levels) && levels.map(l => l.id).join(',') === expectedLevels.map(l => l.id).join(','),
  Array.isArray(levels) ? `ids=${levels.map(l => l.id).join(',')}` : '解析失败');

const doc = env.document;
const boardEl = doc.getElementById('board');
const stateOf = () => JSON.parse(doc.body.dataset.gameState || 'null');
const cellsOf = () => boardEl.children.filter(c => c.tagName === 'BUTTON' && c.classList.contains('cell'));
const cluesOf = () => boardEl.children.filter(c => c.classList.contains('clue'));
const clueRows = () => boardEl.children.filter(c => c.classList.contains('clue-row'));
const clueCols = () => boardEl.children.filter(c => c.classList.contains('clue-col'));
const lvGrid = doc.getElementById('lvGrid');
const lvlEls = () => lvGrid.children;
const digBtn = doc.getElementById('modeDig');
const flagBtn = doc.getElementById('modeFlag');
const replayBtn = doc.getElementById('replay');
const lvBtn = doc.getElementById('lvBtn');
const levelPanel = doc.getElementById('levelPanel');
const resetBtn = doc.getElementById('resetBtn');
const resultEl = doc.getElementById('result');
const teachEl = doc.getElementById('teach');

function selectLevel(i) { lvlEls()[i].__fire('click', {}); }
function fireCell(idx, button) {
  boardEl.__fire('pointerdown', { target: cellsOf()[idx], button: button || 0, cancelable: true });
}
function setMode(m) { (m === 'flag' ? flagBtn : digBtn).__fire('click', {}); }
function clickResultBtn() {
  const b = resultEl.children.find(c => c.id === 'resultBtn');
  if (b) b.__fire('click', {});
  return !!b;
}
function neighborsOf(n, i) {
  const r = Math.floor(i / n), c = i % n, out = [];
  for (let dr = -1; dr <= 1; dr++) for (let dc = -1; dc <= 1; dc++) {
    if (dr === 0 && dc === 0) continue;
    const rr = r + dr, cc = c + dc;
    if (rr >= 0 && cc >= 0 && rr < n && cc < n) out.push(rr * n + cc);
  }
  return out;
}
const bLevels = {};
outB.levels.forEach(l => { bLevels[l.id] = l; });

/* ------------------------------------------------------------------ D8a 关卡解锁 */
console.log('== D8a. 关卡解锁（v2 新增） ==');
{
  const st = stateOf();
  check('D8a 首次进入从第 1 关开始', st.level === 1, `level=${st.level} cleared=${st.clearedLevels}/${st.totalLevels}`);
  const locked = lvlEls().map((b, i) => i > 0 && b.classList.contains('locked') && b.disabled === true);
  check(`D8a 未通关时第 2..${levels.length} 关锁定（10 关解锁链起点）`,
    locked.length === levels.length && locked.slice(1).every(Boolean) && locked[0] === false,
    `lvl class=[${lvlEls().map(b => b.className).join(' | ')}]`);
  lvBtn.__fire('click', {});
  const panelOpen = !levelPanel.hidden && levelPanel.classList.contains('open');
  check('D8a 关卡面板可打开', panelOpen, `panel.hidden=${levelPanel.hidden} class=${levelPanel.className}`);
  lvBtn.__fire('click', {});
  check('D8a 面板可再次关闭', levelPanel.hidden === true && !levelPanel.classList.contains('open'),
    `panel.hidden=${levelPanel.hidden}`);
}

/* ------------------------------------------------------------------ D1/D6 渲染与线索 */
console.log('== D1/D6. 逐关渲染与线索文本 ==');
const aPerLevel = {};
outA.extras.per_level.forEach(p => { aPerLevel[p.id] = p; });
function renderingChecks(li) {
  const lv = levels[li];
  const n = lv.size;
  selectLevel(li);
  const cells = cellsOf();
  check(`D1 第${lv.id}关 棋盘格数 = n²`, cells.length === n * n, `cells=${cells.length} n²=${n * n}`);
  const expectClues = lv.showRuns ? (n + 1) * (n + 1) - n * n : 0;
  check(`D1 第${lv.id}关 线索格数 = (n+1)²-n²`, cluesOf().length === expectClues,
    `clues=${cluesOf().length} 期望=${expectClues} showRuns=${lv.showRuns}`);
  const st = stateOf();
  check(`D1 第${lv.id}关 gameState 可读且 status=playing`, st && st.status === 'playing', JSON.stringify(st));
  if (lv.showRuns) {
    const rowTxt = clueRows().map(d => d.children.map(s => s.textContent).join(' ') || '0');
    const colTxt = clueCols().map(d => d.children.map(s => s.textContent).join(' ') || '0');
    const expRow = aPerLevel[lv.id].rowRuns_calc.map(r => r.length ? r.join(' ') : '0');
    const expCol = aPerLevel[lv.id].colRuns_calc.map(r => r.length ? r.join(' ') : '0');
    check(`D6 第${lv.id}关 左侧行线索文本 == 独立重算`, JSON.stringify(rowTxt) === JSON.stringify(expRow),
      `DOM=${JSON.stringify(rowTxt)} 期望=${JSON.stringify(expRow)}`);
    check(`D6 第${lv.id}关 上方列线索文本 == 独立重算`, JSON.stringify(colTxt) === JSON.stringify(expCol),
      `DOM=${JSON.stringify(colTxt)} 期望=${JSON.stringify(expCol)}`);
  } else {
    check(`D6 第${lv.id}关 不显示行列线索（SPEC §1）`, cluesOf().length === 0, `线索元素数=${cluesOf().length}`);
  }
}
for (let li = 0; li < levels.length; li++) renderingChecks(li);

/* ------------------------------------------------------------------ D5 不泄露雷位置 */
console.log('== D5. 未失败前 DOM 不泄露雷位置 ==');
for (let li = 0; li < levels.length; li++) {
  const lv = levels[li];
  selectLevel(li);
  const mines = new Set(bLevels[lv.id].mines_true);
  const cells = cellsOf();
  let leakedClass = 0, leakedText = 0, leakedFlag = 0;
  cells.forEach(el => {
    if (el.classList.contains('mine') || el.classList.contains('wonmine')) leakedClass++;
    if (el.textContent === '💣') leakedText++;
    if (el.textContent === '🚩') leakedFlag++;
  });
  const sigShape = (el) => JSON.stringify({
    tag: el.tagName, cls: el.className, text: el.textContent, keys: Object.keys(el._attrs).sort(),
  });
  const shapes = new Set(cells.filter(el => !el.classList.contains('revealed')).map(sigShape));
  const posOk = cells.every((el, i) => {
    const r = Math.floor(i / lv.size), c = i % lv.size;
    return el.getAttribute('data-i') === String(i) && el.getAttribute('data-r') === String(r) &&
      el.getAttribute('data-c') === String(c) && el.getAttribute('aria-label') === `第${r + 1}行 第${c + 1}列`;
  });
  check(`D5 第${lv.id}关 playing 时无 mine/wonmine 类`, leakedClass === 0, `命中=${leakedClass}`);
  check(`D5 第${lv.id}关 playing 时无 💣 文本`, leakedText === 0, `命中=${leakedText}`);
  check(`D5 第${lv.id}关 playing 时未插旗`, leakedFlag === 0, `命中=${leakedFlag}`);
  check(`D5 第${lv.id}关 全部未翻开格形态同构（未翻开格之间无差异标注）`, shapes.size === 1,
    `未翻开格的不同形态数=${shapes.size}（1=同构）`);
  check(`D5 第${lv.id}关 每格属性值都是位置的纯函数（不含雷信息）`, posOk,
    posOk ? 'data-i/data-r/data-c/aria-label 全部与索引一致' : '存在与索引不一致的属性值');
  const keySig = (el) => Object.keys(el._attrs).sort().join(',');
  const mineKeySigs = new Set(cells.filter((el, i) => mines.has(i)).map(keySig));
  const safeKeySigs = new Set(cells.filter((el, i) => !mines.has(i)).map(keySig));
  check(`D5 第${lv.id}关 雷格与安全格属性键集合一致（无差异化标注）`,
    mineKeySigs.size === 1 && safeKeySigs.size === 1 && [...mineKeySigs][0] === [...safeKeySigs][0],
    `雷格=${[...mineKeySigs]} 安全格=${[...safeKeySigs]}`);
}

/* ------------------------------------------------------------------ D3 依序通关 3 关 */
console.log(`== D3. 用独立求解器的动作序列依次通关 ${levels.length} 关（走真实「下一关」流程） ==`);
{
  replayBtn.__fire('click', {});           // 回到第 1 关
  selectLevel(0);
  for (let li = 0; li < levels.length; li++) {
    const lv = levels[li];
    const acts = bLevels[lv.id].a_plus_b.solve_actions;
    let step = 0;
    for (const a of acts) {
      setMode(a.kind === 'mine' ? 'flag' : 'dig');
      fireCell(a.r * lv.size + a.c, 0);
      step++;
    }
    const st = stateOf();
    check(`D3 第${lv.id}关 按独立序列(${step} 步)通关 status=won`, st.status === 'won',
      `status=${st.status} revealed=${st.revealed}/${st.totalSafe} flagged=${st.flagged}/${st.mines} lives=${st.lives}`);
    check(`D3 第${lv.id}关 胜利时所有安全格已翻开且所有雷已插旗`,
      st.revealed === st.totalSafe && st.flagged === st.mines,
      `revealed=${st.revealed}/${st.totalSafe} flagged=${st.flagged}/${st.mines}`);
    if (li < levels.length - 1) {
      const okBtn = clickResultBtn();
      const st2 = stateOf();
      check(`D3 点「下一关」进入第 ${li + 2} 关`, okBtn && st2.level === li + 2, `level=${st2.level}`);
      check(`D8a 通关第 ${li + 1} 关后第 ${li + 2} 关解锁`,
        !lvlEls()[li + 1].classList.contains('locked') && lvlEls()[li + 1].disabled === false,
        `class=${lvlEls()[li + 1].className} disabled=${lvlEls()[li + 1].disabled}`);
    } else {
      check(`SPEC §4.6 第${lv.id}关（末关）通关显示「全部通关」`, resultEl.textContent.includes('全部通关'),
        `result="${resultEl.textContent}"`);
      check(`D8a ${levels.length} 关全部通关后 clearedLevels=${levels.length}`,
        stateOf().clearedLevels === levels.length,
        `cleared=${stateOf().clearedLevels}/${stateOf().totalLevels}`);
      check(`D8a gameState.totalLevels == ${levels.length}`, stateOf().totalLevels === levels.length,
        `totalLevels=${stateOf().totalLevels}`);
    }
  }
}

/* ------------------------------------------------------------------ D3b 胜利条件反向验证 */
console.log('== D3b. 胜利条件反向验证（只翻完 → 不赢；插满旗才赢）==');
{
  const li = 1, lv = levels[li];
  const mines = new Set(bLevels[lv.id].mines_true);
  selectLevel(li);
  setMode('dig');
  for (let i = 0; i < lv.size * lv.size; i++) if (!mines.has(i)) fireCell(i, 0);
  let st = stateOf();
  check('D3b 全部安全格翻开但未插旗 → status 仍为 playing', st.status === 'playing',
    `status=${st.status} revealed=${st.revealed}/${st.totalSafe} flagged=${st.flagged}/${st.mines}`);
  setMode('flag');
  const arr = [...mines];
  for (let k = 0; k < arr.length - 1; k++) fireCell(arr[k], 0);
  st = stateOf();
  check('D3b 差 1 颗雷未插旗 → status 仍为 playing', st.status === 'playing',
    `status=${st.status} flagged=${st.flagged}/${st.mines}`);
  fireCell(arr[arr.length - 1], 0);
  st = stateOf();
  check('D3b 最后一颗雷插旗后 → status=won', st.status === 'won',
    `status=${st.status} revealed=${st.revealed}/${st.totalSafe} flagged=${st.flagged}/${st.mines}`);
}

/* ------------------------------------------------------------------ D4 反向测试 */
console.log('== D4. 反向测试（踩雷扣命 / 连踩 3 颗 lost / 插旗可取消）==');
{
  const lv = levels[0];
  const mines = [...new Set(bLevels[1].mines_true)];
  selectLevel(0);
  const st0 = stateOf();
  setMode('dig');
  fireCell(mines[0], 0);
  let st = stateOf();
  check('D4 探格模式点雷 → 命数 -1', st.lives === st0.lives - 1, `lives ${st0.lives} -> ${st.lives}`);
  check('D4 点雷后 status 仍 playing（还有命）', st.status === 'playing', `status=${st.status}`);
  fireCell(mines[1], 0);
  st = stateOf();
  check('D4 再点一颗雷 → 命数再 -1', st.lives === st0.lives - 2, `lives=${st.lives}`);
  fireCell(mines[2], 0);
  st = stateOf();
  check('D4 连点 3 颗雷 → status=lost', st.status === 'lost', `status=${st.status} lives=${st.lives}`);
  check('SPEC §4.6 失败显示「重来」', resultEl.textContent.includes('重来'), `result="${resultEl.textContent}"`);
}
{
  const lv = levels[0];
  const mines = new Set(bLevels[1].mines_true);
  const safeIdx = [...Array(lv.size * lv.size).keys()].find(i => !mines.has(i));
  selectLevel(0);
  setMode('flag');
  fireCell(safeIdx, 0);
  let st = stateOf();
  const flaggedOn = st.flagged, clsOn = cellsOf()[safeIdx].className, txtOn = cellsOf()[safeIdx].textContent;
  fireCell(safeIdx, 0);
  st = stateOf();
  check('D4 插旗 → 计数 +1', flaggedOn === 1, `flagged=${flaggedOn}`);
  check('D4 插旗 → 格子显示 🚩', txtOn === '🚩' && clsOn.includes('flagged'), `class=${clsOn} text=${txtOn}`);
  check('D4 再点一次插旗 → 取消（计数归 0）', st.flagged === 0, `flagged=${st.flagged}`);
  check('D4 取消后格子恢复未标记',
    cellsOf()[safeIdx].textContent === '' && !cellsOf()[safeIdx].classList.contains('flagged'),
    `class=${cellsOf()[safeIdx].className}`);
}
{
  const lv = levels[0];
  const mines = new Set(bLevels[1].mines_true);
  const safeIdx = [...Array(lv.size * lv.size).keys()].find(i => !mines.has(i));
  selectLevel(0);
  fireCell(safeIdx, 2); // 右键
  check('D4b 右键（button=2）直接插旗', stateOf().flagged === 1, `flagged=${stateOf().flagged}`);
  replayBtn.__fire('click', {});
  const st2 = stateOf();
  check('D4b 重玩本关 → 回到 playing/满命/0 旗',
    st2.status === 'playing' && st2.flagged === 0 && st2.lives === 3, JSON.stringify(st2));
}

/* ------------------------------------------------------------------ D7 SPEC 边界 */
console.log('== D7. SPEC 边界行为 ==');
const netCounts = (li) => {
  const n = levels[li].size;
  const ms = new Set(bLevels[levels[li].id].mines_true);
  const out = new Array(n * n).fill(0);
  for (let r = 0; r < n; r++) for (let c = 0; c < n; c++) {
    let k = 0;
    for (const nb of neighborsOf(n, r * n + c)) if (ms.has(nb)) k++;
    out[r * n + c] = k;
  }
  return out;
};
{
  // SPEC §4.5：teach 非空则显示、为空则隐藏（10 关逐关核对；SPEC 正文只点名第 3 关）
  let teachOk = true;
  const teachDetail = [];
  for (let li = 0; li < levels.length; li++) {
    const lv = levels[li];
    selectLevel(li);
    const empty = (lv.teach || '') === '';
    const visible = teachEl.textContent !== '' && !teachEl.classList.contains('hidden');
    const ok = empty ? (teachEl.textContent === '' && teachEl.classList.contains('hidden')) : visible;
    if (!ok) teachOk = false;
    teachDetail.push(`L${lv.id}:${empty ? '空/隐藏' : '有/显示'}${ok ? '' : '★不符'}`);
  }
  check('SPEC §4.5 10 关 teach 显示规则与数据一致（空则隐藏、非空则显示）', teachOk, teachDetail.join(' '));
  selectLevel(2);
  check('SPEC §4.5 第 3 关 teach 为空且隐藏（正文点名项）',
    teachEl.textContent === '' && teachEl.classList.contains('hidden'),
    `teach=${JSON.stringify(teachEl.textContent)} class=${teachEl.className}`);
}
{
  // SPEC v1.1 §1：胜利口径 = 插旗 **或** 已探爆都算标出
  const li = 1, lv = levels[li];
  const ms = [...new Set(bLevels[lv.id].mines_true)];
  selectLevel(li);
  setMode('dig');
  fireCell(ms[0], 0);                       // 踩爆 1 颗（扣 1 命，该格变成「已翻开的雷」）
  setMode('flag');
  ms.slice(1).forEach(i => fireCell(i, 0)); // 其余雷全部插旗
  setMode('dig');
  for (let i = 0; i < lv.size * lv.size; i++) if (!new Set(ms).has(i)) fireCell(i, 0);
  const st = stateOf();
  const blastEl = cellsOf()[ms[0]];
  check('SPEC v1.1 §1 踩爆的雷算「已标出」→ 应判 won，且该格是 revealed mine 而非 flagged',
    st.status === 'won' && blastEl.classList.contains('revealed') && blastEl.classList.contains('mine') &&
    !blastEl.classList.contains('flagged'),
    `status=${st.status} 该雷 class="${blastEl.className}" text="${blastEl.textContent}" ` +
    `gameState.flagged=${st.flagged}/${st.mines}（实际插旗数=${cellsOf().filter(e => e.classList.contains('flagged')).length}）`);
}
{
  // 0 格 flood fill 遇到玩家插旗的安全格
  let tested = false;
  for (let li = 0; li < levels.length && !tested; li++) {
    const lv = levels[li];
    const n = lv.size;
    const counts = netCounts(li);
    const acts = bLevels[lv.id].a_plus_b.solve_actions;
    for (const a of acts) {
      if (a.kind !== 'safe') continue;
      const ci = a.r * n + a.c;
      if (counts[ci] !== 0) continue;
      const region = new Set([ci]);
      const stack = [ci];
      while (stack.length) {
        const cur = stack.pop();
        for (const nb of neighborsOf(n, cur)) {
          if (region.has(nb)) continue;
          region.add(nb);
          if (counts[nb] === 0) stack.push(nb);
        }
      }
      selectLevel(li);
      const revealedNow = new Set(cellsOf().map((el, i) => i).filter(i => cellsOf()[i].classList.contains('revealed')));
      const minesSet = new Set(levels[li] && bLevels[lv.id].mines_true);
      const target = [...region].find(i => i !== ci && !revealedNow.has(i) && !minesSet.has(i));
      if (target === undefined) continue;
      tested = true;
      setMode('flag'); fireCell(target, 0);
      setMode('dig'); fireCell(ci, 0);
      const targetEl = cellsOf()[target];
      const blocked = !targetEl.classList.contains('revealed');
      check('SPEC v1.1 §1 已插旗的格子会挡住 flood fill（与文档一致）', blocked,
        `第${lv.id}关：先插旗安全格 (${Math.floor(target / n) + 1},${target % n + 1})，再探开 0 格 ` +
        `(${Math.floor(ci / n) + 1},${ci % n + 1}) → 该边界格 class="${targetEl.className}" ` +
        `${blocked ? '未被翻开（符合 v1.1「插旗挡住 flood fill」）' : '★被翻开了，与 v1.1 措辞不符★'}`);
      setMode('flag'); fireCell(target, 0);
      setMode('dig'); fireCell(target, 0);
      check('SPEC v1.1 §1 该行为可恢复（取消插旗后可正常翻开）',
        cellsOf()[target].classList.contains('revealed'), `取消插旗后再探 → class="${cellsOf()[target].className}"`);
    }
  }
  if (!tested) check('SPEC v1.1 §1 插旗挡住 flood fill 测试', true, '10 关开局后没有可构造的后续 0 格探格点，跳过');
}

/* ------------------------------------------------------------------ D8b localStorage 进度 */
console.log('== D8b. localStorage 进度持久化 / 重置 ==');
{
  const mem = new Map();
  const storage = {
    getItem: (k) => (mem.has(k) ? mem.get(k) : null),
    setItem: (k, v) => { mem.set(k, String(v)); },
    removeItem: (k) => { mem.delete(k); },
  };
  const env2 = makeEnv({ storage });
  const err2 = runScript(env2);
  check('D8b 带 localStorage 时脚本仍无异常', err2 === null, err2 ? String(err2) : '无异常');
  const doc2 = env2.document;
  const st2 = () => JSON.parse(doc2.body.dataset.gameState);
  const board2 = doc2.getElementById('board');
  const cells2 = () => board2.children.filter(c => c.tagName === 'BUTTON' && c.classList.contains('cell'));
  const grid2 = doc2.getElementById('lvGrid');
  // 通关第 1 关
  const acts = bLevels[levels[0].id].a_plus_b.solve_actions;
  const n1 = levels[0].size;
  const dig2 = doc2.getElementById('modeDig'), flag2 = doc2.getElementById('modeFlag');
  for (const a of acts) {
    (a.kind === 'mine' ? flag2 : dig2).__fire('click', {});
    board2.__fire('pointerdown', { target: cells2()[a.r * n1 + a.c], button: 0, cancelable: true });
  }
  check('D8b 第 1 关通关', st2().status === 'won', `status=${st2().status}`);
  const raw = mem.get('leixian.migong.progress.v1');
  check('D8b 进度写入 localStorage', !!raw && JSON.parse(raw).cleared['0'] === 1,
    `STORAGE=${raw || '(空)'}`);
  // 新会话（同一 storage）应恢复进度并停在第 2 关
  const env3 = makeEnv({ storage });
  runScript(env3);
  const doc3 = env3.document;
  const st3 = JSON.parse(doc3.body.dataset.gameState);
  const grid3 = doc3.getElementById('lvGrid').children;
  check('D8b 新会话恢复进度（clearedLevels=1，当前第 2 关）',
    st3.clearedLevels === 1 && st3.level === 2, JSON.stringify(st3));
  check('D8b 新会话中第 1 关标记为已通关、第 3 关仍锁定',
    grid3[0].classList.contains('cleared') && grid3[2].classList.contains('locked'),
    `grid=[${[...grid3].map(b => b.className).join(' | ')}]`);
  // 重置进度：两步确认
  const reset3 = doc3.getElementById('resetBtn');
  reset3.__fire('click', {});
  const armed = reset3.textContent.includes('确认');
  reset3.__fire('click', {});
  const st3b = JSON.parse(doc3.body.dataset.gameState);
  const grid3b = doc3.getElementById('lvGrid').children;
  check('D8b 重置进度为两步确认且生效', armed && st3b.clearedLevels === 0 && st3b.level === 1 &&
    grid3b[1].classList.contains('locked'),
    `armed=${armed} state=${JSON.stringify(st3b)} grid=[${[...grid3b].map(b => b.className).join(' | ')}]`);
}

/* ------------------------------------------------------------------ D9 注入块契约 */
console.log('== SPEC §4.7 注入块契约 ==');
check('SPEC §4.7 LEVELS 位于注入注释块之间', !!inject, inject ? '存在' : '缺失');
check('SPEC §4.7 注入块自成一体（不含外部变量引用）',
  inject && /const\s+LEVELS\s*=\s*\[/.test(inject[1]),
  inject ? inject[1].trim().slice(0, 40).replace(/\s+/g, ' ') + ' …' : '');
check('SPEC §4.7 内嵌 LEVELS == 冻结的 levels.json',
  JSON.stringify(levels) === JSON.stringify(JSON.parse(fs.readFileSync(LEVELS_JSON_PATH, 'utf8'))),
  `对比文件=${LEVELS_JSON_PATH}（逐字段比较）`);

/* ------------------------------------------------------------------ 汇总 */
const pass = results.filter(r => r.ok).length;
const fail = results.length - pass;
const summary = {
  html_path: HTML_PATH,
  html_sha256: htmlSha, html_utf8_bytes: fs.statSync(HTML_PATH).size,
  html_mtime: fs.statSync(HTML_PATH).mtime.toISOString(),
  total: results.length, pass, fail,
  failed: results.filter(r => !r.ok),
  rafCalls: env.rafCount(),
  script_error: runErr ? String(runErr) : null,
};
fs.writeFileSync(path.join(ROOT, 'verification', 'out_d.json'),
  JSON.stringify({ summary, results }, null, 2), 'utf8');
console.log('');
console.log(`== D 部分小结：${pass}/${results.length} 通过，${fail} 不通过 ==`);
results.filter(r => !r.ok).forEach(r => console.log('  不通过: ' + r.id + ' :: ' + r.detail));
console.log(`被复核的 game/index.html: sha256=${htmlSha} bytes=${html.length} mtime=${summary.html_mtime}`);
console.log('JSON -> verification/out_d.json');
process.exit(fail === 0 ? 0 : 1);