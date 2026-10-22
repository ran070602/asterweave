/* LEVELS_INJECT_END */

const boardEl = document.getElementById('board');
const statusEl = document.getElementById('status');
const teachEl = document.getElementById('teach');
const resultEl = document.getElementById('result');
const nameEl = document.getElementById('lvName');
const lvtagEl = document.getElementById('lvtag');
const digBtn = document.getElementById('modeDig');
const flagBtn = document.getElementById('modeFlag');
const replayBtn = document.getElementById('replay');
const lvBtn = document.getElementById('lvBtn');
const lvBtnNum = document.getElementById('lvBtnNum');
const lvBtnTotal = document.getElementById('lvBtnTotal');
const levelPanel = document.getElementById('levelPanel');
const lvGrid = document.getElementById('lvGrid');
const clearedCountEl = document.getElementById('clearedCount');
const totalCountEl = document.getElementById('totalCount');
const resetBtn = document.getElementById('resetBtn');
const constSlotEl = document.getElementById('constSlot');
const statusCountsEl = document.getElementById('statusCounts');
const scopesEl = document.getElementById('scopes');
const overlayEl = document.getElementById('overlay');
const modalEl = document.getElementById('modal');
const modalTitleEl = document.getElementById('modalTitle');
const modalSubEl = document.getElementById('modalSub');
const modalBtnsEl = document.getElementById('modalBtns');

const MODE_DIG = 'dig';
const MODE_FLAG = 'flag';

let currentMode = MODE_DIG;
let S = null;          // 当前关卡的全部状态
let cellEls = [];      // 索引 -> 格子元素
let lvlEls = [];       // 关卡面板按钮
let panelOpen = false;
let resetArmed = false;

// 结算 modal 状态
let modalDismissed = false;  // 按 Esc / 点遮罩收起后，改由底部结算条保留入口
let modalOpenNow = false;
let modalSignature = '';     // 内容未变就不重建，避免每次 render 抢焦点
let winFlashPending = false; // 通关：先在棋盘上点亮星座并闪一下，再弹结算弹窗
let modalPrimaryBtn = null;  // 打开时把焦点放到主按钮
let lastFocusEl = null;
let lastShownLives = -1;     // 用于爱心受击动画
let flashTimer = null;
let flashing = false;

// ---------- 进度记忆：localStorage 不可用时静默降级为内存进度，绝不弹错 ----------
const STORAGE_KEY = 'leixian.migong.progress.v1';
let progress = { v: 1, cleared: {}, last: 0, devUnlock: false };
let storageOK = true;

function loadProgress(){
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return;
    const saved = JSON.parse(raw);
    if (!saved || typeof saved !== 'object') return;
    const cleared = {};
    if (saved.cleared && typeof saved.cleared === 'object'){
      for (const key in saved.cleared){
        if (Object.prototype.hasOwnProperty.call(saved.cleared, key) && saved.cleared[key]){
          cleared[String(key)] = 1;
        }
      }
    }
    progress = {
      v: 1,
      cleared: cleared,
      last: (typeof saved.last === 'number' && saved.last >= 0) ? Math.floor(saved.last) : 0,
      devUnlock: saved.devUnlock === true
    };
  } catch (e) {
    storageOK = false;          // 本地文件或隐私模式下存储被禁用：静默降级
  }
}

function saveProgress(){
  if (!storageOK) return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(progress));
  } catch (e) {
    storageOK = false;          // 写失败也不打断游戏
  }
}

function isCleared(i){ return !!progress.cleared[String(i)]; }

// 已通关连续段之后的第一个未通关关卡 = 当前关卡；全部通关则返回 LEVELS.length
function frontier(){
  const total = LEVELS.length;
  for (let i = 0; i < total; i++) if (!isCleared(i)) return i;
  return total;
}

function isUnlocked(i){ return progress.devUnlock === true || i <= frontier(); }

function clearedTotal(){
  let k = 0;
  for (let i = 0; i < LEVELS.length; i++) if (isCleared(i)) k++;
  return k;
}

function markCleared(i){
  if (isCleared(i)) return;
  progress.cleared[String(i)] = 1;
  progress.last = i;
  saveProgress();
  refreshUnlockBtn();
refreshLevelGrid();
}

function startIndex(){
  const total = LEVELS.length;
  if (total === 0) return 0;
  const f = frontier();
  if (f >= total) return total - 1;    // 全部通关：停在最后一关，方便重玩
  return f;
}

function clampIndex(i){
  const total = Array.isArray(LEVELS) ? LEVELS.length : 0;
  if (total === 0) return 0;
  if (typeof i !== 'number' || isNaN(i) || i < 0) return 0;
  return i > total - 1 ? total - 1 : i;
}

function runsFromMines(mineSet, n, byRow, k){
  const runs = [];
  let cur = 0;
  for (let t = 0; t < n; t++){
    const i = byRow ? (k * n + t) : (t * n + k);
    if (mineSet.has(i)) cur++;
    else { if (cur > 0) runs.push(cur); cur = 0; }
  }
  if (cur > 0) runs.push(cur);
  return runs;
}

function startLevel(rawIndex){
  if (!Array.isArray(LEVELS) || LEVELS.length === 0){
    boardEl.innerHTML = '<p class="err">关卡数据缺失。</p>';
    return;
  }
  const index = clampIndex(rawIndex);
  const level = LEVELS[index];
  const n = level.size;
  const mineSet = new Set();
  const mines = Array.isArray(level.mines) ? level.mines : [];
  for (let m = 0; m < mines.length; m++){
    const cell = mines[m];
    if (!cell || cell.length < 2) continue;
    const r = cell[0], c = cell[1];
    if (r >= 0 && c >= 0 && r < n && c < n) mineSet.add(r * n + c);
  }

  // 杂星（不属于星座的雷）：只用于「图标区分/是否参与揭晓」。
  // 数据约定 mines 已含杂星；这里再把 noise 并进雷集，避免数据漏写导致杂星能踩穿。
  const noiseSet = new Set();
  const noise = Array.isArray(level.noise) ? level.noise : [];
  for (let m = 0; m < noise.length; m++){
    const cell = noise[m];
    if (!cell || cell.length < 2) continue;
    const r = cell[0], c = cell[1];
    if (r >= 0 && c >= 0 && r < n && c < n){
      const ni = r * n + c;
      noiseSet.add(ni);
      mineSet.add(ni);
    }
  }

  const total = n * n;
  const nbrs = new Array(total);
  const counts = new Int16Array(total);
  for (let i = 0; i < total; i++){
    const r = Math.floor(i / n), c = i % n, list = [];
    for (let dr = -1; dr <= 1; dr++){
      for (let dc = -1; dc <= 1; dc++){
        if (dr === 0 && dc === 0) continue;
        const rr = r + dr, cc = c + dc;
        if (rr < 0 || cc < 0 || rr >= n || cc >= n) continue;
        list.push(rr * n + cc);
      }
    }
    nbrs[i] = list;
    let k = 0;
    for (let j = 0; j < list.length; j++) if (mineSet.has(list[j])) k++;
    counts[i] = k;
  }

  // 线索优先用关卡数据；缺字段时按 mines 现算（只展示线索本身，不展示 mines）。
  const rowRuns = new Array(n), colRuns = new Array(n);
  for (let r = 0; r < n; r++){
    rowRuns[r] = (Array.isArray(level.rowRuns) && Array.isArray(level.rowRuns[r]))
      ? level.rowRuns[r] : runsFromMines(mineSet, n, true, r);
  }
  for (let c = 0; c < n; c++){
    colRuns[c] = (Array.isArray(level.colRuns) && Array.isArray(level.colRuns[c]))
      ? level.colRuns[c] : runsFromMines(mineSet, n, false, c);
  }

  const lives = (typeof level.lives === 'number' && level.lives > 0) ? Math.floor(level.lives) : 3;

  S = {
    index: index,
    level: level,
    n: n,
    mineSet: mineSet,
    noiseSet: noiseSet,
    lastHitNoise: false,
    nbrs: nbrs,
    counts: counts,
    rowRuns: rowRuns,
    colRuns: colRuns,
    lives: lives,
    livesMax: lives,
    totalSafe: total - mineSet.size,
    revealedSafe: new Uint8Array(total),
    revealedMine: new Uint8Array(total),
    flagged: new Uint8Array(total),
    status: 'playing'
  };

  modalDismissed = false;
  modalSignature = '';
  lastShownLives = -1;
  flashing = false;
  scopesEl.className = 'scopes';
  progress.last = index;
  saveProgress();

  buildBoard();

  // 开局赠送：opening 是 0 格，自动 flood fill。
  const op = Array.isArray(level.opening) ? level.opening : null;
  if (op && op.length >= 2){
    const oi = op[0] * n + op[1];
    if (oi >= 0 && oi < total && !mineSet.has(oi)) floodReveal(oi);
  }
  checkWin();
  render();
}

function buildBoard(){
  const n = S.n;
  const withRuns = !!S.level.showRuns;
  const cols = n + (withRuns ? 1 : 0);
  boardEl.style.setProperty('--cols', String(cols));
  boardEl.innerHTML = '';
  cellEls = new Array(n * n);

  const frag = document.createDocumentFragment();
  if (withRuns){
    frag.appendChild(clueEl('clue clue-corner', null));
    for (let c = 0; c < n; c++) frag.appendChild(clueEl('clue clue-col', S.colRuns[c]));
  }
  for (let r = 0; r < n; r++){
    if (withRuns) frag.appendChild(clueEl('clue clue-row', S.rowRuns[r]));
    for (let c = 0; c < n; c++){
      const i = r * n + c;
      const b = document.createElement('button');
      b.type = 'button';
      b.className = 'cell';
      b.setAttribute('data-i', String(i));
      b.setAttribute('data-r', String(r));
      b.setAttribute('data-c', String(c));
      b.setAttribute('aria-label', '第' + (r + 1) + '行 第' + (c + 1) + '列');
      cellEls[i] = b;
      frag.appendChild(b);
    }
  }
  boardEl.appendChild(frag);
  if (typeof requestAnimationFrame === 'function') requestAnimationFrame(fitBoard);
  else fitBoard();
}

function clueEl(cls, runs){
  const d = document.createElement('div');
  d.className = cls;
  if (!runs) return d;
  const list = runs.length ? runs : [0];   // 无雷的行/列显示 0
  for (let k = 0; k < list.length; k++){
    const s = document.createElement('span');
    s.textContent = String(list[k]);
    d.appendChild(s);
  }
  return d;
}

// 棋盘随容器宽度自适应：用实测格子宽度推字号，保证不横向溢出。
function fitBoard(){
  const first = cellEls[0];
  if (!first) return;
  const w = first.getBoundingClientRect().width;
  if (w > 0) boardEl.style.setProperty('--fs', (w * 0.5).toFixed(2) + 'px');
}
window.addEventListener('resize', function(){ if (typeof requestAnimationFrame === 'function') requestAnimationFrame(fitBoard); else fitBoard(); });
window.addEventListener('orientationchange', function(){ setTimeout(fitBoard, 150); });

function floodReveal(start){
  const n = S.n;
  const stack = [start];
  while (stack.length){
    const i = stack.pop();
    if (S.revealedSafe[i] || S.revealedMine[i] || S.flagged[i]) continue;
    if (S.mineSet.has(i)) continue;
    S.revealedSafe[i] = 1;
    if (S.counts[i] === 0){
      const list = S.nbrs[i];
      for (let k = 0; k < list.length; k++){
        const j = list[k];
        if (S.revealedSafe[j] || S.revealedMine[j] || S.flagged[j]) continue;
        if (S.mineSet.has(j)) continue;
        stack.push(j);
      }
    }
  }
}

function checkWin(){
  if (!S || S.status !== 'playing') return;
  const total = S.n * S.n;
  for (let i = 0; i < total; i++){
    if (S.mineSet.has(i)){
      if (!S.flagged[i] && !S.revealedMine[i]) return;  // 所有雷必须已标出
    } else if (!S.revealedSafe[i]){
      return;                                          // 所有安全格必须已翻开
    }
  }
  S.status = 'won';
  markCleared(S.index);
  // 通关小细节：星座在棋盘上点亮并闪一下，再弹结算弹窗（reduced-motion 下直接弹）
  winFlashPending = true;
  if (boardEl) boardEl.classList.add('reveal-flash');
  const reduce = (typeof window.matchMedia === 'function') &&
                 window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  setTimeout(function(){
    if (boardEl) boardEl.classList.remove('reveal-flash');
    winFlashPending = false;
    render();
  }, reduce ? 120 : 900);
}

function act(i, mode){
  if (!S || S.status !== 'playing') return;
  if (S.revealedSafe[i] || S.revealedMine[i]) return;
  if (mode === MODE_FLAG){
    S.flagged[i] = S.flagged[i] ? 0 : 1;   // 插旗可取消
    checkWin();
    render();
    return;
  }
  if (S.flagged[i]) return;                // 探格模式下不会误翻开已插旗的格
  if (S.mineSet.has(i)){
    S.revealedMine[i] = 1;                 // 踩雷：扣 1 命并标记该雷
    S.lastHitNoise = !!S.noiseSet.has(i);  // 只记录“踩到的这一颗”是不是杂星（不泄露其它）
    S.lives -= 1;
    if (S.lives <= 0){ S.lives = 0; S.status = 'lost'; render(); return; }
    checkWin();
    render();
    return;
  }
  floodReveal(i);
  checkWin();
  render();
}

function setMode(m){
  currentMode = m;
  render();
}

function render(){
  if (!S) return;
  const total = S.n * S.n;
  let revealed = 0, flags = 0, blasted = 0;
  for (let i = 0; i < total; i++){
    if (S.revealedSafe[i]) revealed++;
    if (S.flagged[i]) flags++;
    if (S.revealedMine[i]) blasted++;
  }
  const marked = flags + blasted;          // 踩爆的雷也算“已标记”
  const minesTotal = S.mineSet.size;

  for (let i = 0; i < total; i++){
    const el = cellEls[i];
    if (!el) continue;
    let cls = 'cell';
    let text = '';
    let svg = '';                          // 杂星用内联 SVG，避免 ✧ 在某些安卓字体里变方框
    if (S.revealedSafe[i]){
      const v = S.counts[i];
      cls += ' revealed n' + v + (v > 0 ? ' tick' : '');
      text = v === 0 ? '' : String(v);
    } else if (S.revealedMine[i]){
      // 踩爆：星座星 = 亮白 ✦ + 光晕；杂星 = 冷灰四角星（一眼区分）
      if (S.noiseSet.has(i)){ cls += ' revealed hitnoise'; svg = NOISE_STAR_SVG; }
      else { cls += ' revealed hitstar'; text = '✦'; }
    } else if (S.status === 'won' && S.mineSet.has(i)){
      // 通关揭晓：星座星点亮为亮白 ✦，杂星只留暗灰四角星（不参与星座）
      if (S.noiseSet.has(i)){ cls += ' revealed wonoise'; svg = NOISE_STAR_SVG; }
      else { cls += ' revealed wonstar'; text = '✦'; }
    } else if (S.flagged[i]){
      cls += ' flagged';                    // 玩家标记的星
      text = '★';
    }
    if (el.className !== cls) el.className = cls;
    if (svg){
      if (el.textContent !== '') el.textContent = '';
      if (el.innerHTML !== svg) el.innerHTML = svg;
    } else {
      if (el.innerHTML !== '') el.innerHTML = '';
      if (el.textContent !== text) el.textContent = text;
    }
  }

  statusCountsEl.textContent = '已翻开 ' + revealed + '/' + S.totalSafe +
    ' · 已标记 ★ ' + marked + '/' + minesTotal;
  renderScopes();

  const teach = (typeof S.level.teach === 'string') ? S.level.teach : '';
  teachEl.textContent = teach;
  teachEl.className = teach ? 'teach' : 'teach hidden';

  nameEl.textContent = S.level.name ? (' · ' + S.level.name) : '';
  lvtagEl.textContent = '第 ' + (S.index + 1) + ' / ' + LEVELS.length + ' 关 · ' +
    S.n + '×' + S.n + (S.level.showRuns ? ' · 含行列线索' : ' · 仅邻域数字');

  digBtn.className = currentMode === MODE_DIG ? 'btn on' : 'btn';
  flagBtn.className = currentMode === MODE_FLAG ? 'btn on' : 'btn';
  digBtn.setAttribute('aria-pressed', currentMode === MODE_DIG ? 'true' : 'false');
  flagBtn.setAttribute('aria-pressed', currentMode === MODE_FLAG ? 'true' : 'false');

  refreshLevelGrid();
  renderModal();
  renderStrip();

  document.body.dataset.gameState = JSON.stringify({
    level: S.index + 1,
    levelId: (typeof S.level.id === 'number' ? S.level.id : S.index + 1),
    size: S.n,
    revealed: revealed,
    totalSafe: S.totalSafe,
    flagged: marked,
    mines: minesTotal,
    lives: S.lives,
    status: S.status,
    mode: currentMode,
    totalLevels: LEVELS.length,
    clearedLevels: clearedTotal(),
    noise: S.noiseSet.size
  });
}

// ---------- 望远镜命数 ----------
// 固定 3 个槽位（livesMax），同一架望远镜「点亮/熄灭」，读屏器只念整组的 aria-label。
// 图标用 innerHTML 拼内联 SVG（不出现命名空间字面量），跨平台观感一致。
const SCOPE_SVG = '<svg viewBox="0 0 24 24" class="scope-svg" aria-hidden="true" focusable="false">' +
  '<path class="scope-tube" d="M3.4 13.1 14.9 4.2l3.1 4.1-11.5 8.9z"></path>' +
  '<circle class="scope-lens" cx="16.9" cy="6.1" r="2.8"></circle>' +
  '<path class="scope-leg" d="M8.5 15.9 6.2 21M9.5 16.7l1.7 4.3"></path>' +
  '</svg>';

// 杂星图形：内联 SVG 四角星（小、冷灰、无光晕）——避免 ✧ 字符在部分安卓字体里变成方框
const NOISE_STAR_SVG = '<svg class="noise-star" viewBox="0 0 24 24" aria-hidden="true" focusable="false">' +
  '<path d="M12 2.2l2.1 7.7 7.7 2.1-7.7 2.1L12 21.8l-2.1-7.7L2.2 12l7.7-2.1z"></path></svg>';

function renderScopes(){
  const max = (typeof S.livesMax === 'number' && S.livesMax > 0) ? S.livesMax : 3;
  const cur = Math.max(0, Math.min(max, S.lives));
  scopesEl.setAttribute('aria-label', '剩余命数 ' + cur + ' / ' + max);

  if (scopesEl.childNodes.length !== max){
    scopesEl.innerHTML = '';
    for (let i = 0; i < max; i++){
      const sp = document.createElement('span');
      sp.setAttribute('aria-hidden', 'true');
      sp.innerHTML = SCOPE_SVG;
      scopesEl.appendChild(sp);
    }
  }
  for (let i = 0; i < max; i++){
    const sp = scopesEl.childNodes[i];
    const cls = 'scope ' + (i < cur ? 'full' : 'empty');   // 熄灭 = 同一图标变暗，不换符号
    if (sp.className !== cls) sp.className = cls;
  }

  if (lastShownLives >= 0 && cur < lastShownLives){
    flashing = true;
    scopesEl.className = 'scopes flash';       // 轻量受击反馈
    if (flashTimer) clearTimeout(flashTimer);
    flashTimer = setTimeout(function(){ flashing = false; scopesEl.className = 'scopes'; }, 240);
  } else if (!flashing){
    scopesEl.className = 'scopes';
  }
  lastShownLives = cur;
}

// ---------- 结算 modal（通关 / 失败共用） ----------
function isLastLevel(){ return S.index >= LEVELS.length - 1; }

function mkBtn(label, cls, handler, disabled){
  const b = document.createElement('button');
  b.type = 'button';
  b.className = cls;
  b.textContent = label;
  if (disabled) b.disabled = true;
  if (handler && !disabled) b.addEventListener('click', handler);
  return b;
}

function replayLevel(){
  if (!S) return;
  const i = S.index;
  startLevel(i);
  focusBoard();
}

function nextLevel(){
  if (!S) return;
  const i = S.index;
  if (i < LEVELS.length - 1){
    startLevel(i + 1);
    focusBoard();
  } else {
    dismissModal();               // 保险：最后一关不会出现“点了没反应”的按钮
  }
}

function focusBoard(){
  const el = cellEls[0];
  if (el && el.focus){ try { el.focus(); } catch (e) {} }
}

// ---------- 通关揭晓：星座图（星点 + 连线） ----------
function escHtml(s){
  return String(s == null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

// ---------- 深空摄影感：视星等 / 星色 / 确定性星尘 ----------
const STAR_TINT = {
  warm:    { core:'#fff2df', glow:'#ffc98d', spike:'#ffd9ae' },
  cool:    { core:'#e8f4ff', glow:'#8fc4ff', spike:'#bcd9ff' },
  neutral: { core:'#f7faff', glow:'#c9dcff', spike:'#dbe8ff' }
};
function tintOf(st){
  return STAR_TINT[(st && (st.tint === 'warm' || st.tint === 'cool')) ? st.tint : 'neutral'];
}
// 视星等 -> 半径（越小越亮；0.13 等≈2.9，3.05 等≈1.8，6 等≈0.9）
function magToRadius(mag){
  const m = (typeof mag === 'number' && isFinite(mag)) ? Math.max(-1.5, Math.min(6, mag)) : 3;
  return 0.9 + 2.6 * Math.pow((6 - m) / 7.5, 1.1);
}
// 确定性伪随机（FNV-1a + LCG）：同一 theme.id 星尘完全一致
function seedFrom(s){
  let h = 2166136261; s = String(s == null ? '' : s);
  for (let i = 0; i < s.length; i++){ h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); }
  return h >>> 0;
}
function rngFrom(seed){
  let s = seed >>> 0;
  return function(){ s = (Math.imul(s, 1664525) + 1013904223) >>> 0; return s / 4294967296; };
}
function dustHtml(theme){
  const rnd = rngFrom(seedFrom(theme && theme.id ? theme.id : 'sky'));
  let out = '';
  for (let i = 0; i < 30; i++){
    out += '<circle class="gdust" cx="' + (3 + rnd() * 94).toFixed(1) + '" cy="' + (3 + rnd() * 94).toFixed(1) +
      '" r="' + (0.25 + rnd() * 0.25).toFixed(2) + '" opacity="' + (0.1 + rnd() * 0.4).toFixed(2) + '"></circle>';
  }
  return out;
}
// 把 theme.stars 的格子坐标 [r,c] 映射到 0..100 的 viewBox
function constSvg(theme, n, noise){
  const stars = (theme && Array.isArray(theme.stars)) ? theme.stars : [];
  const lines = (theme && Array.isArray(theme.lines)) ? theme.lines : [];
  const size = n > 0 ? n : 1, pad = 8, span = 84;
  const at = function(rc){
    const r = rc && rc.length > 1 ? Number(rc[0]) || 0 : 0, c = rc && rc.length > 1 ? Number(rc[1]) || 0 : 0;
    return [ (pad + (c + 0.5) / size * span).toFixed(1), (pad + (r + 0.5) / size * span).toFixed(1) ];
  };
  let linesHtml = '';
  for (let i = 0; i < lines.length; i++){
    const seg = lines[i], a = seg && stars[seg[0]], b = seg && stars[seg[1]];
    if (!a || !b) continue;
    const p = at(a.rc), q = at(b.rc);
    const g = ' x1="' + p[0] + '" y1="' + p[1] + '" x2="' + q[0] + '" y2="' + q[1] + '"';
    linesHtml += '<line class="gline-glow"' + g + '></line><line class="gline"' + g +
      ' style="animation-delay:' + (0.04 + i * 0.045).toFixed(2) + 's"></line>';
  }
  let starsHtml = '';
  for (let i = 0; i < stars.length; i++){
    const st = stars[i] || {}, p = at(st.rc), tc = tintOf(st);
    const mag = (typeof st.mag === 'number' && isFinite(st.mag)) ? st.mag : 3;
    const r = magToRadius(mag), d = (0.03 + i * 0.03).toFixed(2) + 's';
    const x = p[0], y = p[1];
    const label = escHtml(st.name || '') + (st.en ? ' ' + escHtml(st.en) : '') + ' · ' + mag + ' 等';
    let spike = '';
    if (mag <= 2.5){
      const L = r * 3, op = r >= 2.6 ? 0.5 : 0.34;
      spike = '<g class="gspike" stroke="' + tc.spike + '" stroke-opacity="' + op +
        '" stroke-width=".45" stroke-linecap="round" style="animation-delay:' + d + '">' +
        '<line x1="' + (x - L).toFixed(2) + '" y1="' + y + '" x2="' + (+x + L).toFixed(2) + '" y2="' + y + '"></line>' +
        '<line x1="' + x + '" y1="' + (y - L).toFixed(2) + '" x2="' + x + '" y2="' + (+y + L).toFixed(2) + '"></line></g>';
    }
    starsHtml += '<circle class="ghalo" cx="' + x + '" cy="' + y + '" r="' + (r * 3.4).toFixed(2) +
      '" fill="' + tc.glow + '" fill-opacity=".14" style="animation-delay:' + d + '"></circle>' +
      '<circle class="ghalo2" cx="' + x + '" cy="' + y + '" r="' + (r * 1.9).toFixed(2) +
      '" fill="' + tc.glow + '" fill-opacity=".26" style="animation-delay:' + d + '"></circle>' + spike +
      '<circle class="gstar" cx="' + x + '" cy="' + y + '" r="' + r.toFixed(2) + '" fill="' + tc.core +
      '" style="animation-delay:' + d + '"><title>' + label + '</title></circle>';
  }
  // 杂星：冷灰小暗点，先亮一下再淡出 —— 让玩家看清"这些灰点不属于星座、不参与连线"
  let noiseHtml = '';
  const nz = Array.isArray(noise) ? noise : [];
  const starSet = new Set(stars.map(x => String(x && x.rc && x.rc[0]) + ',' + String(x && x.rc && x.rc[1])));
  for (let k = 0; k < nz.length; k++){
    const rc = nz[k];
    if (!rc || rc.length < 2) continue;
    if (starSet.has(String(rc[0]) + ',' + String(rc[1]))) continue;   // 与星座星重叠的跳过
    const p2 = at(rc);
    noiseHtml += '<circle class="gnoise" cx="' + p2[0] + '" cy="' + p2[1] + '" r="1.15" ' +
      'style="animation-delay:' + (0.05 + k * 0.02).toFixed(2) + 's"></circle>';
  }
  return '<svg class="const-svg" viewBox="0 0 100 100" role="img" aria-label="' + escHtml(theme.name || '') +
    ' 星座星图">' + dustHtml(theme) + noiseHtml + linesHtml + starsHtml + '</svg>';
}

function buildConstPanel(theme, n, noise){
  const panel = document.createElement('div');
  panel.className = 'const-panel';
  panel.setAttribute('data-constellation', String(theme.id || ''));

  const name = document.createElement('div');
  name.className = 'const-name';
  name.textContent = theme.name || '';
  if (theme.nameEn){
    const en = document.createElement('span');
    en.textContent = theme.nameEn;
    name.appendChild(en);
  }
  panel.appendChild(name);

  const map = document.createElement('div');
  map.className = 'const-map';
  map.innerHTML = constSvg(theme, n, noise);   // 用 innerHTML 建内联 SVG（无命名空间字面量）
  panel.appendChild(map);

  if (theme.fact){
    const fact = document.createElement('p');
    fact.className = 'const-fact';
    fact.textContent = theme.fact;
    panel.appendChild(fact);
  }
  const tag = document.createElement('div');
  tag.className = 'const-tag';
  tag.textContent = '✦ 星座图鉴 +1';
  panel.appendChild(tag);
  return panel;
}

function buildModal(){
  const won = S.status === 'won';
  const last = won && isLastLevel();
  modalEl.className = 'modal ' + (won ? 'win' : 'lose');
  if (won){
    modalTitleEl.textContent = last ? '全部通关！' : '第 ' + (S.index + 1) + ' 关 · 通关！';
    modalSubEl.textContent = last
      ? '所有 ' + LEVELS.length + ' 关观测完成，可从右上角「关卡」面板重玩任意关。'
      : '观测完成：所有安全格已翻开、全部星星已标记。';
  } else {
    modalTitleEl.textContent = '观测失败';
    modalSubEl.textContent = S.lastHitNoise
      ? '踩到了背景里的杂星（它不属于这个星座），命数耗尽。可以重来，或换个关卡。'
      : '踩掉了一颗还没标记的星星，命数耗尽。可以重来，或换个关卡。';
  }

  // 通关揭晓区：只有本关带 theme 才渲染（老数据自动省略，向后兼容）
  if (constSlotEl) constSlotEl.innerHTML = '';
  const theme = (won && S.level && S.level.theme) ? S.level.theme : null;
  if (theme && Array.isArray(theme.stars) && theme.stars.length && constSlotEl){
    constSlotEl.appendChild(buildConstPanel(theme, S.n, S.level.noise));
  }

  modalBtnsEl.innerHTML = '';
  modalPrimaryBtn = null;

  if (won && !last){
    modalBtnsEl.appendChild(mkBtn('↻ 重来本关', 'btn again', replayLevel));
    modalPrimaryBtn = mkBtn('下一关 →', 'btn primary', nextLevel);
    modalBtnsEl.appendChild(modalPrimaryBtn);
  } else if (won && last){
    modalPrimaryBtn = mkBtn('↻ 重来本关', 'btn primary', replayLevel);
    modalBtnsEl.appendChild(modalPrimaryBtn);
    // 最后一关：“下一关”位置改成禁用的「全部通关」，不是死按钮
    modalBtnsEl.appendChild(mkBtn('全部通关', 'btn', null, true));
  } else {
    modalPrimaryBtn = mkBtn('↻ 重来本关', 'btn primary', replayLevel);
    modalBtnsEl.appendChild(modalPrimaryBtn);
    modalBtnsEl.appendChild(mkBtn('换个关卡', 'btn again', function(){ dismissModal(); openPanel(); }));
  }
}

function renderModal(){
  // 通关闪烁播放期间先不弹窗，让玩家看清星座
  if (winFlashPending){ closeModal(false); return; }
  const result = (S.status === 'won' || S.status === 'lost');
  if (!result || modalDismissed){ closeModal(false); return; }
  const sig = S.status + '|' + S.index + '|' + LEVELS.length;
  if (modalSignature !== sig){ modalSignature = sig; buildModal(); }
  if (!modalOpenNow){
    modalOpenNow = true;
    overlayEl.className = 'overlay open';
    overlayEl.setAttribute('aria-hidden', 'false');
    lastFocusEl = document.activeElement || null;
    const target = modalPrimaryBtn || modalEl;
    if (target && target.focus){ try { target.focus(); } catch (e) {} }
  }
}

function closeModal(restoreFocus){
  if (!modalOpenNow){
    overlayEl.className = 'overlay';
    overlayEl.setAttribute('aria-hidden', 'true');
    return;
  }
  modalOpenNow = false;
  modalSignature = '';
  overlayEl.className = 'overlay';
  overlayEl.setAttribute('aria-hidden', 'true');
  if (restoreFocus && lastFocusEl && lastFocusEl.focus){
    try { lastFocusEl.focus(); } catch (e) {}
  }
  lastFocusEl = null;
}

function dismissModal(){
  if (!modalOpenNow) return;
  modalDismissed = true;
  closeModal(true);
  render();          // 结算条接替 modal，保留「下一关 / 重来」入口
}

// 底部结算条：仅在 modal 被 Esc/遮罩收起后出现，避免“关了就没入口”
function renderStrip(){
  const result = (S.status === 'won' || S.status === 'lost');
  if (!result || modalOpenNow || !modalDismissed){
    resultEl.className = 'result';
    resultEl.innerHTML = '';
    return;
  }
  const won = S.status === 'won';
  const last = won && isLastLevel();
  resultEl.className = 'result show ' + (won ? 'win' : 'lose');
  resultEl.innerHTML = '';

  const p = document.createElement('div');
  p.className = 'msg';
  p.textContent = won ? (last ? '🎉 全部通关！' : '✅ 本关已通关') : '❌ 观测失败 · 命数耗尽';
  resultEl.appendChild(p);

  const row = document.createElement('div');
  row.className = 'result-btns';
  if (won && !last) row.appendChild(mkBtn('下一关 →', 'btn primary', nextLevel));
  row.appendChild(mkBtn('↻ 重来本关', 'btn again', replayLevel));
  if (!won || last) row.appendChild(mkBtn('换个关卡', 'btn ghost', openPanel));
  row.appendChild(mkBtn('结算', 'btn ghost', function(){ modalDismissed = false; render(); }));
  resultEl.appendChild(row);
}

function buildLevelGrid(){
  lvGrid.innerHTML = '';
  lvlEls = [];
  for (let i = 0; i < LEVELS.length; i++){
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'lvl';
    b.textContent = String(i + 1);                 // 关卡号
    b.setAttribute('data-level', String(i + 1));
    b.setAttribute('data-index', String(i));
    b.addEventListener('click', (function(k){
      return function(){ startLevel(k); closePanel(); };
    })(i));
    lvGrid.appendChild(b);
    lvlEls.push(b);
  }
  refreshLevelGrid();
}

// 三态：已通关 / 当前（解锁但未通关）/ 未解锁；另用 playing 标出正在玩的关卡
function refreshLevelGrid(){
  const f = frontier();
  for (let i = 0; i < lvlEls.length; i++){
    const b = lvlEls[i];
    const cleared = isCleared(i);
    const unlocked = progress.devUnlock === true || i <= f;
    const playing = !!S && S.index === i;
    let cls = 'lvl';
    let label = '第 ' + (i + 1) + ' 关';
    if (cleared){ cls += ' cleared'; label += '，已通关'; }
    else if (!unlocked){ cls += ' locked'; label += '，未解锁'; }
    else if (i === f && progress.devUnlock !== true){ cls += ' current'; label += '，当前关卡'; }
    if (playing) cls += ' playing';
    if (b.className !== cls) b.className = cls;
    b.disabled = !(unlocked || cleared);
    b.setAttribute('aria-label', label);
    b.setAttribute('aria-current', playing ? 'true' : 'false');
  }
  lvBtnNum.textContent = String((S ? S.index : 0) + 1);
  lvBtnTotal.textContent = String(LEVELS.length);
  totalCountEl.textContent = String(LEVELS.length);
  clearedCountEl.textContent = String(clearedTotal());
}

function refreshUnlockBtn(){
  const btn = document.getElementById('unlockBtn');
  if (!btn) return;
  const on = progress.devUnlock === true;
  btn.textContent = on ? '🔒 恢复进度锁' : '🔓 全部解锁';
  btn.setAttribute('aria-pressed', on ? 'true' : 'false');
  btn.className = 'mini' + (on ? ' on' : '');
}

function toggleUnlockAll(){
  progress.devUnlock = progress.devUnlock !== true;
  saveProgress();
  refreshUnlockBtn();
  refreshLevelGrid();
}

function openPanel(){
  panelOpen = true;
  levelPanel.hidden = false;
  levelPanel.className = 'panel open';
  lvBtn.setAttribute('aria-expanded', 'true');
  refreshLevelGrid();
  const cur = lvlEls[S ? S.index : 0];
  if (cur && cur.scrollIntoView){
    try { cur.scrollIntoView({ block: 'nearest' }); }
    catch (e) { try { cur.scrollIntoView(); } catch (e2) {} }
  }
}

function closePanel(){
  panelOpen = false;
  levelPanel.hidden = true;
  levelPanel.className = 'panel';
  lvBtn.setAttribute('aria-expanded', 'false');
  resetArmed = false;
  resetBtn.textContent = '重置进度';
  resetBtn.className = 'mini';
}

function togglePanel(){
  if (panelOpen) closePanel();
  else openPanel();
}

// 触摸与鼠标统一用 pointer events；右键直接插旗。
boardEl.addEventListener('pointerdown', function(e){
  const el = e.target && e.target.closest ? e.target.closest('.cell') : null;
  if (!el) return;
  const i = parseInt(el.getAttribute('data-i'), 10);
  if (isNaN(i)) return;
  if (e.cancelable) e.preventDefault();
  if (e.button === 2){ act(i, MODE_FLAG); return; }
  act(i, currentMode);
}, { passive: false });

boardEl.addEventListener('contextmenu', function(e){ e.preventDefault(); });

// 键盘可达性：Enter/空格 = 当前模式的点击。
boardEl.addEventListener('keydown', function(e){
  const el = e.target;
  if (!el || !el.getAttribute || el.getAttribute('data-i') === null) return;
  if (e.key === 'Enter' || e.key === ' ' || e.key === 'Spacebar'){
    e.preventDefault();
    const i = parseInt(el.getAttribute('data-i'), 10);
    if (!isNaN(i)) act(i, currentMode);
  }
});

digBtn.addEventListener('click', function(){ setMode(MODE_DIG); });
flagBtn.addEventListener('click', function(){ setMode(MODE_FLAG); });
replayBtn.addEventListener('click', function(){ if (S) startLevel(S.index); });

lvBtn.addEventListener('click', togglePanel);

// 结算 modal：Tab 在两个按钮间循环（焦点不跑到棋盘上）；点遮罩=收起，改由结算条接替
overlayEl.addEventListener('keydown', function(e){
  if (!modalOpenNow || e.key !== 'Tab') return;
  const list = [];
  for (let i = 0; i < modalBtnsEl.childNodes.length; i++){
    const b = modalBtnsEl.childNodes[i];
    if (b && !b.disabled) list.push(b);
  }
  if (!list.length) return;
  const idx = list.indexOf(document.activeElement);
  let nextIdx;
  if (e.shiftKey) nextIdx = idx <= 0 ? list.length - 1 : idx - 1;
  else nextIdx = (idx < 0 || idx >= list.length - 1) ? 0 : idx + 1;
  if (e.preventDefault) e.preventDefault();
  list[nextIdx].focus();
});

overlayEl.addEventListener('click', function(e){
  if (modalOpenNow && e.target === overlayEl) dismissModal();
});

// 重置进度：两步确认，避免误触（进度只存在本机）
resetBtn.addEventListener('click', function(){
document.getElementById('unlockBtn').addEventListener('click', toggleUnlockAll);
  if (!resetArmed){
    resetArmed = true;
    resetBtn.textContent = '再点一次确认重置';
    resetBtn.className = 'mini danger';
    return;
  }
  resetArmed = false;
  resetBtn.textContent = '重置进度';
  resetBtn.className = 'mini';
  progress = { v: 1, cleared: {}, last: 0 };
  saveProgress();
  startLevel(0);
  refreshLevelGrid();
});

window.addEventListener('keydown', function(e){
  if (e.key === 'Escape' || e.key === 'Esc'){
    if (modalOpenNow){ dismissModal(); return; }   // Esc 收起结算，结算条保留入口
    if (panelOpen) closePanel();
  }
});

if (Array.isArray(LEVELS) && LEVELS.length){
  loadProgress();
  buildLevelGrid();
  startLevel(startIndex());
} else {
  boardEl.innerHTML = '<p class="err">关卡数据缺失。</p>';
}
})();
</script>
</body>
</html>