/* SKY_INJECT_END */

const boardEl = document.getElementById('board');
const statusEl = document.getElementById('status');
const teachEl = document.getElementById('teach');
const resultEl = document.getElementById('result');
const boardWrapEl = document.querySelector('.boardwrap');
const boardRevealEl = document.getElementById('boardReveal');
const soundBtnEl = document.getElementById('soundBtn');
const nameEl = document.getElementById('lvName');
const lvtagEl = document.getElementById('lvtag');
const replayBtn = document.getElementById('replay');
const lvBtn = document.getElementById('lvBtn');
const lvBtnNum = document.getElementById('lvBtnNum');
const lvBtnTotal = document.getElementById('lvBtnTotal');
const levelPanel = document.getElementById('levelPanel');
const replayActionsEl = document.getElementById('replayActions');
const drawerMask = document.getElementById('drawerMask');
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
let progress = { v: 1, cleared: {}, last: 0, devUnlock: false, devSkyLit: false, introSeen: false, sound: true };
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
      devUnlock: saved.devUnlock === true,
      devSkyLit: saved.devSkyLit === true,
      sound: saved.sound !== false,
      introSeen: saved.introSeen === true
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

function showIntro(){
  const el = document.getElementById('introOverlay');
  if (!el) return;
  el.hidden = false;
  const btn = document.getElementById('introStart');
  if (btn){ try { btn.focus(); } catch (e) {} }
}

function hideIntro(){
  const el = document.getElementById('introOverlay');
  if (el) el.hidden = true;
  progress.introSeen = true;      // 只弹一次
  saveProgress();
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
  refreshLevelGrid();
  refreshUnlockBtn();
  refreshSkyBadge();
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
  resetRevealVisuals();
  if (typeof cancelPress === 'function') cancelPress();
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
  const alreadyCleared = isCleared(S.index);   // 重玩已通关的关卡 → 揭晓走快速版
  S.status = 'won';
  markCleared(S.index);
  winRevealDone = false;
  winRevealPending = true;
  render();                                   // 先呈现终局盘面
  startBoardReveal(alreadyCleared);           // 揭晓搬回棋盘：杂星退场 → 星依次点亮 → 连线 → 名字浮起
}

function act(i, mode){
  if (mode === MODE_DIG || mode === MODE_FLAG) currentMode = mode;
  if (!S || S.status !== 'playing') return;
  if (S.revealedSafe[i] || S.revealedMine[i]) return;
  if (mode === MODE_FLAG){
    S.flagged[i] = S.flagged[i] ? 0 : 1;   // 插旗可取消
    S.fxFlag = i;                          // 特效：抖动 + 星形弹出
    S.fxFlagOn = !!S.flagged[i];
    sndMark();
    checkWin();
    render();
    return;
  }
  if (S.flagged[i]) return;                // 探格模式下不会误翻开已插旗的格
  if (S.mineSet.has(i)){
    S.revealedMine[i] = 1;                 // 踩雷：扣 1 命并标记该雷
    S.lastHitNoise = !!S.noiseSet.has(i);  // 只记录“踩到的这一颗”是不是杂星（不泄露其它）
    S.fxHit = i;                           // 特效：抖动（starHit 已含抖动）
    sndFail();
    S.lives -= 1;
    if (S.lives <= 0){ S.lives = 0; S.status = 'lost'; render(); return; }
    checkWin();
    render();
    return;
  }
  sndDig();
  // 记录翻开前的状态，用来给「本次翻开的所有格子」按距离错开特效
  const before = S.revealedSafe.slice();
  floodReveal(i);
  const n = S.n, list = [];
  for (let k = 0; k < before.length; k++){
    if (!before[k] && S.revealedSafe[k]){
      const d = Math.max(Math.abs((k / n | 0) - (i / n | 0)), Math.abs((k % n) - (i % n)));
      list.push({ i: k, d: d });
    }
  }
  S.fxReveal = list;
  checkWin();
  render();
}

// 播放「观测 / 标记」的动作特效（render 之后调用，播放完自动移除 class）
function applyCellFx(){
  if (!S) return;
  const reduce = (typeof window.matchMedia === 'function') &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (reduce){ S.fxReveal = null; S.fxFlag = null; S.fxHit = null; return; }
  const seq = S.fxReveal || [];
  for (let k = 0; k < seq.length; k++){
    const it = seq[k], el = cellEls[it.i];
    if (!el) continue;
    const delay = Math.min(it.d * 18, 240);
    el.style.animationDelay = delay + 'ms';
    el.classList.add('fx-reveal');
    (function (node, wait){
      setTimeout(function(){
        node.classList.remove('fx-reveal');
        node.style.animationDelay = '';
      }, wait + 340);
    })(el, delay);
  }
  S.fxReveal = null;
  if (S.fxFlag != null){
    const el = cellEls[S.fxFlag], cls = S.fxFlagOn ? 'fx-flag' : 'fx-unflag';
    S.fxFlag = null;
    if (el){
      el.classList.add(cls);
      setTimeout(function(){ el.classList.remove('fx-flag', 'fx-unflag'); }, 380);
    }
  }
  if (S.fxHit != null){
    const el = cellEls[S.fxHit];
    S.fxHit = null;
    if (el){
      el.classList.add('fx-hit');
      setTimeout(function(){ el.classList.remove('fx-hit'); }, 380);
    }
  }
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

  if (replayActionsEl) replayActionsEl.hidden = (S.status !== 'playing');   // 结算时只留 modal/结算条里的那一个
  nameEl.textContent = S.level.name ? (' · ' + S.level.name) : '';
  lvtagEl.textContent = '第 ' + (S.index + 1) + ' / ' + LEVELS.length + ' 关 · ' +
    S.n + '×' + S.n + (S.level.showRuns ? ' · 含行列线索' : ' · 仅邻域数字');

  applyCellFx();

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
  return panel;
}

function buildModal(){
  const won = S.status === 'won';
  const last = won && isLastLevel();
  modalEl.className = 'modal ' + (won ? 'win' : 'lose');
  if (won){
    const wt = (S.level && S.level.theme) ? S.level.theme : null;
    let best = null;
    for (let i = 0; i < ((wt && wt.stars) || []).length; i++){
      const st = wt.stars[i];
      const mag = (typeof st.mag === 'number' && isFinite(st.mag)) ? st.mag : 9;
      if (!best || mag < best.mag) best = { mag: mag, st: st };
    }
    modalTitleEl.textContent = last ? '全部通关！' : '第 ' + (S.index + 1) + ' 关 · 观测成功';
    modalSubEl.innerHTML = '';
    if (wt){
      const nm = document.createElement('span');
      nm.className = 'modal-cname';
      nm.textContent = wt.name + (wt.nameEn ? '  ' + wt.nameEn : '');
      modalSubEl.appendChild(nm);
      const meta = document.createElement('span');
      meta.className = 'modal-cmeta';
      meta.textContent = (best && best.st && best.st.name
          ? '最亮星 ' + best.st.name + '（' + best.mag + ' 等） · ' : '')
        + (last ? '全部 ' + LEVELS.length + ' 关观测完成' : '已收入星座图鉴');
      modalSubEl.appendChild(meta);
    } else {
      modalSubEl.textContent = last ? '所有 ' + LEVELS.length + ' 关观测完成。' : '本关观测完成。';
    }
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

  const canArchive = !!(won && theme && SKY.some(function(k){ return k.id === theme.id; }));
  if (won && !last){
    if (canArchive) modalBtnsEl.appendChild(mkBtn('★ 图鉴详情', 'btn ghost', function(){
      dismissModal();
      skySelected = theme.id;
      renderSkyDetail();
    }));
    modalBtnsEl.appendChild(mkBtn('↻ 重来本关', 'btn again', replayLevel));
    modalPrimaryBtn = mkBtn('下一关 →', 'btn primary', nextLevel);
    modalBtnsEl.appendChild(modalPrimaryBtn);
  } else if (won && last){
    if (canArchive) modalBtnsEl.appendChild(mkBtn('★ 图鉴详情', 'btn ghost', function(){
      dismissModal();
      skySelected = theme.id;
      renderSkyDetail();
    }));
    modalPrimaryBtn = mkBtn('↻ 重来本关', 'btn primary', replayLevel);
    modalBtnsEl.appendChild(modalPrimaryBtn);
    modalBtnsEl.appendChild(mkBtn('换个关卡', 'btn ghost', function(){ dismissModal(); openPanel(); }));
  } else {
    modalPrimaryBtn = mkBtn('↻ 重来本关', 'btn primary', replayLevel);
    modalBtnsEl.appendChild(modalPrimaryBtn);
    modalBtnsEl.appendChild(mkBtn('换个关卡', 'btn again', function(){ dismissModal(); openPanel(); }));
  }
}

// ===== 音效：WebAudio 合成，零外部文件 =====
let audioCtx = null;
function soundEnabled(){ return progress.sound !== false; }
function initAudio(){
  if (audioCtx) return;
  const AC = window.AudioContext || window.webkitAudioContext;
  if (!AC) return;
  try { audioCtx = new AC(); } catch (e) { audioCtx = null; }
}
function tone(freq, dur, delay, type, vol, freq2){
  if (!soundEnabled() || !audioCtx) return;
  try {
    const t0 = audioCtx.currentTime + (delay || 0);
    const osc = audioCtx.createOscillator(), g = audioCtx.createGain();
    osc.type = type || 'sine';
    osc.frequency.setValueAtTime(freq, t0);
    if (freq2) osc.frequency.exponentialRampToValueAtTime(freq2, t0 + dur);
    g.gain.setValueAtTime(0.0001, t0);
    g.gain.exponentialRampToValueAtTime(vol || 0.05, t0 + 0.01);
    g.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
    osc.connect(g); g.connect(audioCtx.destination);
    osc.start(t0); osc.stop(t0 + dur + 0.02);
  } catch (e) {}
}
function sndDig(){ tone(520, 0.05, 0, 'sine', 0.022); }
function sndMark(){ tone(760, 0.055, 0, 'square', 0.018); }
function sndStars(){ tone(587.33, 0.5, 0, 'sine', 0.042); tone(880, 0.5, 0.02, 'sine', 0.032);
  tone(1174.66, 0.62, 0.04, 'sine', 0.02); }
function sndLine(k){ tone(880 + (k % 3) * 110, 0.1, 0, 'triangle', 0.034);
  tone(1320 + (k % 3) * 110, 0.1, 0.05, 'triangle', 0.022); }
function sndWin(){ const seq = [523.25, 659.25, 783.99, 1046.5];
  for (let i = 0; i < seq.length; i++) tone(seq[i], 0.5, i * 0.1, 'sine', 0.058); }
function sndFail(){ tone(320, 0.5, 0, 'sawtooth', 0.05, 90); }
function refreshSoundBtn(){
  if (!soundBtnEl) return;
  const on = soundEnabled();
  soundBtnEl.className = 'lvbtn icononly' + (on ? '' : ' sndoff');
  soundBtnEl.setAttribute('aria-pressed', on ? 'true' : 'false');
  soundBtnEl.setAttribute('title', on ? '音效：开（点击关闭）' : '音效：关（点击开启）');
}
function setSound(on){
  progress.sound = !!on;
  saveProgress();
  refreshSoundBtn();
  if (on){ initAudio(); tone(880, 0.08, 0, 'sine', 0.05); }
}
if (soundBtnEl) soundBtnEl.addEventListener('click', function(){ setSound(!soundEnabled()); });
window.addEventListener('pointerdown', initAudio, true);
window.addEventListener('keydown', initAudio, true);

// ===== 通关揭晓：把星座画在玩家自己的棋盘上 =====
let revealTimers = [], winRevealPending = false, winRevealDone = false, revealSkipBound = false;

function prefersReduced(){
  return (typeof window.matchMedia === 'function') &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}
function cellIndexOfStar(st, n){
  if (!st || !st.rc || st.rc.length < 2) return -1;
  return (Number(st.rc[0]) || 0) * n + (Number(st.rc[1]) || 0);
}
function starPoints(theme, n, wrapRect){
  const stars = (theme && Array.isArray(theme.stars)) ? theme.stars : [];
  const pts = [];
  for (let i = 0; i < stars.length; i++){
    const cell = cellEls[cellIndexOfStar(stars[i], n)];
    if (!cell){ pts.push(null); continue; }
    const r = cell.getBoundingClientRect();
    pts.push([(r.left - wrapRect.left + r.width / 2).toFixed(1),
              (r.top - wrapRect.top + r.height / 2).toFixed(1)]);
  }
  return pts;
}
function markAllStarsLit(){
  const theme = (S && S.level && S.level.theme) || null;
  if (!theme || !Array.isArray(theme.stars) || !boardEl) return;
  boardEl.classList.add('reveal-stage');
  for (let i = 0; i < theme.stars.length; i++){
    const cell = cellEls[cellIndexOfStar(theme.stars[i], S.n)];
    if (cell) cell.classList.add('lit');
  }
}
function drawAllSegments(){
  const theme = (S && S.level && S.level.theme) || null;
  if (!theme || !boardRevealEl || !boardWrapEl) return;
  const lines = Array.isArray(theme.lines) ? theme.lines : [];
  const wrapRect = boardWrapEl.getBoundingClientRect();
  const pts = starPoints(theme, S.n, wrapRect);
  boardRevealEl.setAttribute('viewBox', '0 0 ' + Math.round(wrapRect.width) + ' ' + Math.round(wrapRect.height));
  let html = '';
  for (let i = 0; i < lines.length; i++){
    const seg = lines[i], a = seg && pts[seg[0]], b = seg && pts[seg[1]];
    if (!a || !b) continue;
    html += '<line x1="' + a[0] + '" y1="' + a[1] + '" x2="' + b[0] + '" y2="' + b[1] +
      '" stroke-dasharray="1" stroke-dashoffset="0" stroke-opacity=".7"></line>';
  }
  boardRevealEl.innerHTML = html;
}

function clearRevealTimers(){
  for (let i = 0; i < revealTimers.length; i++) clearTimeout(revealTimers[i]);
  revealTimers = [];
}
function unbindRevealSkip(){
  if (!revealSkipBound) return;
  revealSkipBound = false;
  document.removeEventListener('pointerdown', skipReveal, true);
  document.removeEventListener('keydown', skipRevealKey, true);
}
function bindRevealSkip(){
  if (revealSkipBound) return;
  revealSkipBound = true;
  document.addEventListener('pointerdown', skipReveal, true);
  document.addEventListener('keydown', skipRevealKey, true);
}
function skipReveal(){ if (winRevealPending) finishBoardReveal(); }
function skipRevealKey(e){
  if (!winRevealPending) return;
  if (e.key === 'Enter' || e.key === ' ' || e.key === 'Escape'){ finishBoardReveal(); }
}
function resetRevealVisuals(){
  clearRevealTimers();
  unbindRevealSkip();
  winRevealPending = false;
  winRevealDone = false;
  if (boardEl) boardEl.classList.remove('reveal-stage', 'reveal-flash');
  if (boardRevealEl) boardRevealEl.innerHTML = '';
}

// 揭晓总时长上限 ~3.2s（首次）/ ~1.5s（重玩或 reduced-motion 直接终态），随时可点击跳过
function startBoardReveal(fast){
  const theme = (S && S.level && S.level.theme) || null;
  if (!boardEl || !boardWrapEl || !theme || !Array.isArray(theme.stars) || !theme.stars.length || prefersReduced()){
    finishBoardReveal();
    return;
  }
  boardEl.classList.add('reveal-stage');
  bindRevealSkip();
  const n = S.n;
  // ① 杂星退场后，星座星一次性亮起（不再逐颗弹跳，避免"乱"），全程只发一声和弦
  const t0 = fast ? 160 : 400;
  for (let k = 0; k < theme.stars.length; k++){
    (function(k){
      revealTimers.push(setTimeout(function(){
        const cell = cellEls[cellIndexOfStar(theme.stars[k], n)];
        if (cell) cell.classList.add('lit');
        if (k === 0) sndStars();
      }, t0 + k * (fast ? 12 : 30)));
    })(k);
  }
  const starsDone = t0 + theme.stars.length * (fast ? 12 : 30) + (fast ? 300 : 620);
  // ② 唯一的主戏：逐段连线（放慢、加长描边）
  const lines = Array.isArray(theme.lines) ? theme.lines : [];
  const lineStep = fast ? 62 : 155;
  const wrapRect = boardWrapEl.getBoundingClientRect();
  const pts = starPoints(theme, n, wrapRect);
  boardRevealEl.setAttribute('viewBox', '0 0 ' + Math.round(wrapRect.width) + ' ' + Math.round(wrapRect.height));
  let html = '', drawn = 0;
  for (let i = 0; i < lines.length; i++){
    const seg = lines[i], a = seg && pts[seg[0]], b = seg && pts[seg[1]];
    if (!a || !b) continue;
    html += '<line x1="' + a[0] + '" y1="' + a[1] + '" x2="' + b[0] + '" y2="' + b[1] +
      '" stroke-dasharray="1" stroke-dashoffset="1" style="animation-delay:' +
      ((starsDone - t0) + drawn * lineStep) + 'ms"></line>';
    (function(k){
      revealTimers.push(setTimeout(function(){ sndLine(k); }, starsDone + k * lineStep));
    })(drawn);
    drawn++;
  }
  boardRevealEl.innerHTML = html;
  const segs = boardRevealEl.querySelectorAll('line');
  for (let i = 0; i < segs.length; i++) segs[i].classList.add('draw');
  revealTimers.push(setTimeout(function(){
    sndWin();
    try { if (navigator.vibrate) navigator.vibrate([12, 45, 12]); } catch (e) {}
  }, starsDone));
  // ③ 连线画完 → 弹小弹窗（名字、星图、三个按钮都在弹窗里）
  const end = starsDone + Math.max(0, drawn - 1) * lineStep + (fast ? 460 : 820);
  revealTimers.push(setTimeout(function(){ finishBoardReveal(); }, end));
}

// 结算/跳过：直接把盘面定格在“星座已成形 + 名字已显示”
function finishBoardReveal(){
  clearRevealTimers();
  unbindRevealSkip();
  winRevealPending = false;
  winRevealDone = true;
  render();                        // 画终局盘面；renderModal 会弹出结算小弹窗
  const theme = (S && S.level && S.level.theme) || null;
  if (theme && Array.isArray(theme.stars) && theme.stars.length){
    markAllStarsLit();
    drawAllSegments();
  }
}

function renderModal(){
  // 揭晓播放期间先不弹；揭晓结束（finishBoardReveal）后弹出结算小弹窗：
  // 星座名 + 最亮星 + 星图 + 三个按钮都在弹窗里，不用下滑找按钮
  if (winFlashPending || winRevealPending){ closeModal(false); return; }
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
  const won = S.status === 'won';
  const lost = S.status === 'lost';
  const showWin = won && winRevealDone && modalDismissed && !modalOpenNow;
  const showLose = lost && modalDismissed && !modalOpenNow;
  if (!showWin && !showLose){
    resultEl.className = 'result';
    resultEl.innerHTML = '';
    return;
  }
  const last = won && isLastLevel();
  resultEl.className = 'result show ' + (won ? 'win' : 'lose');
  resultEl.innerHTML = '';

  const p = document.createElement('div');
  p.className = 'msg';
  p.textContent = won
    ? (last ? '🎉 全部通关！可从「关卡」面板重玩任意关' : '✅ 第 ' + (S.index + 1) + ' 关 · 星座已收入图鉴')
    : '❌ 观测失败 · 命数耗尽';
  resultEl.appendChild(p);

  const row = document.createElement('div');
  row.className = 'result-btns';
  const theme = (S.level && S.level.theme) ? S.level.theme : null;
  if (won && theme && SKY.some(function(k){ return k.id === theme.id; })){
    row.appendChild(mkBtn('★ 图鉴详情', 'btn ghost', function(){
      skySelected = theme.id;
      renderSkyDetail();
    }));
  }
  row.appendChild(mkBtn('↻ 重来本关', 'btn again', replayLevel));
  if (won && !last) row.appendChild(mkBtn('下一关 →', 'btn primary', nextLevel));
  if (!won || last) row.appendChild(mkBtn('换个关卡', 'btn ghost', openPanel));
  resultEl.appendChild(row);
}

refreshSoundBtn();

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
  levelPanel.className = 'panel lvdrawer';
  drawerMask.hidden = false;
  lvBtn.setAttribute('aria-expanded', 'true');
  document.body.classList.add('drawer-open');
  refreshLevelGrid();
  // 强制 reflow 让 transition 生效（比 rAF 稳，后台标签/无头环境也能触发）
  void levelPanel.offsetWidth;
  levelPanel.className = 'panel lvdrawer open';
  drawerMask.className = 'drawer-mask open';
  const cur = lvlEls[S ? S.index : 0];
  if (cur && cur.scrollIntoView){
    try { cur.scrollIntoView({ block: 'center' }); }
    catch (e) { try { cur.scrollIntoView(); } catch (e2) {} }
  }
}

function closePanel(){
  panelOpen = false;
  levelPanel.className = 'panel lvdrawer';
  drawerMask.className = 'drawer-mask';
  lvBtn.setAttribute('aria-expanded', 'false');
  document.body.classList.remove('drawer-open');
  setTimeout(function(){
    if (!panelOpen){ levelPanel.hidden = true; drawerMask.hidden = true; }
  }, 240);
  resetArmed = false;
  resetBtn.textContent = '重置进度';
  resetBtn.className = 'mini';
}

function togglePanel(){
  if (panelOpen) closePanel();
  else openPanel();
}

// 基础操作（按设备区分，观测都是即时的，不再有延迟）：
//   📱 触摸：轻触(按下→抬起) = 观测；长按 LONG_PRESS_MS = 标记
//   💻 鼠标：单击 = 观测；右键 = 标记（不做双击标记，避免"第一击先探测"的歧义）
const LONG_PRESS_MS = 380;      // 长按判定
const MOVE_TOL = 12;            // 手指/鼠标移动超过这个距离视为"在拖动"，不算长按
let press = null;               // 触摸中的按下：{ i, x, y, timer, flagged }

function cancelPress(){
  if (press){ clearTimeout(press.timer); press = null; }
}
function flagWithHaptic(i){
  act(i, MODE_FLAG);
  try { if (navigator.vibrate) navigator.vibrate(12); } catch (e) {}
}

boardEl.addEventListener('pointerdown', function(e){
  const el = e.target && e.target.closest ? e.target.closest('.cell') : null;
  if (!el) return;
  const i = parseInt(el.getAttribute('data-i'), 10);
  if (isNaN(i)) return;

  if (e.button === 2){ cancelPress(); flagWithHaptic(i); return; }     // 右键 → 立即标记

  if (e.pointerType === 'touch'){
    cancelPress();
    press = {
      i: i, x: e.clientX, y: e.clientY, flagged: false,
      timer: setTimeout(function(){
        if (!press) return;
        press.flagged = true;
        flagWithHaptic(press.i);                                      // 长按 → 标记
      }, LONG_PRESS_MS)
    };
    return;
  }

  if (e.button !== 0) return;
  act(i, MODE_DIG);                                                   // 鼠标左键单击 → 观测
}, { passive: true });

// 触摸抬起：没被长按消费掉 → 轻触 = 立即观测
boardEl.addEventListener('pointerup', function(e){
  if (!press) return;
  const p = press;
  clearTimeout(p.timer); press = null;
  if (p.flagged) return;                                              // 长按已经标记过
  if (Math.abs((e.clientX || 0) - p.x) > MOVE_TOL ||
      Math.abs((e.clientY || 0) - p.y) > MOVE_TOL) return;            // 手指划过 → 不动作
  act(p.i, MODE_DIG);
}, { passive: true });

// 手指/鼠标移动超出容差 → 取消长按；被系统打断也取消
boardEl.addEventListener('pointermove', function(e){
  if (!press) return;
  if (Math.abs(e.clientX - press.x) > MOVE_TOL || Math.abs(e.clientY - press.y) > MOVE_TOL) cancelPress();
}, { passive: true });
boardEl.addEventListener('pointercancel', cancelPress);
boardEl.addEventListener('pointerleave', cancelPress);
window.addEventListener('blur', cancelPress);

boardEl.addEventListener('contextmenu', function(e){ e.preventDefault(); });

// 键盘可达性：Enter = 观测；空格 / Shift+Enter = 标记。
boardEl.addEventListener('keydown', function(e){
  const el = e.target;
  if (!el || !el.getAttribute || el.getAttribute('data-i') === null) return;
  const i = parseInt(el.getAttribute('data-i'), 10);
  if (isNaN(i)) return;
  if (e.key === 'Enter' && e.shiftKey){ e.preventDefault(); act(i, MODE_FLAG); return; }
  if (e.key === 'Enter'){ e.preventDefault(); act(i, MODE_DIG); return; }
  if (e.key === ' ' || e.key === 'Spacebar'){ e.preventDefault(); act(i, MODE_FLAG); }
});

replayBtn.addEventListener('click', function(){ if (S) startLevel(S.index); });

lvBtn.addEventListener('click', togglePanel);
drawerMask.addEventListener('click', function(){ if (panelOpen) closePanel(); });

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
document.getElementById('unlockBtn').addEventListener('click', toggleUnlockAll);

// 重置进度：两步确认，避免误触（进度只存在本机）
resetBtn.addEventListener('click', function(){
  if (!resetArmed){
    resetArmed = true;
    resetBtn.textContent = '再点一次确认重置';
    resetBtn.className = 'mini danger';
    return;
  }
  resetArmed = false;
  resetBtn.textContent = '重置进度';
  resetBtn.className = 'mini';
  progress = { v: 1, cleared: {}, last: 0, introSeen: true };
  saveProgress();
  startLevel(0);
  refreshLevelGrid();
});


// ===== 星座图鉴（天球投影）：横轴赤经 0–24h，纵轴赤纬 +90° → −90° =====
const skyEls = {
  btn: document.getElementById('skyBtn'),
  panel: document.getElementById('skyPanel'),
  close: document.getElementById('skyCloseBtn'),
  map: document.getElementById('skyMap'),
  detail: document.getElementById('skyDetail'),
  filters: document.getElementById('skyFilters'),
  litBtn: document.getElementById('skyLitBtn'),
  count: document.getElementById('skyCount'),
  total: document.getElementById('skyTotal')
};
let skyFilter = '全部';
let skySelected = null;
let skyOpen = false;

function skyIsOn(s){ return isCleared(s.level - 1) || progress.devSkyLit === true; }
function skyOnCount(){ return SKY.filter(skyIsOn).length; }
function skyProj(ra, dec){
  return [ 8 + (1 - ra / 24) * 184, 8 + (90 - dec) / 180 * 104 ];
}
function skyEsc(t){
  return String(t == null ? '' : t).replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function skyX(ra){ return 8 + (1 - ra / 24) * 184; }
function skyY(dec){ return 8 + (90 - dec) / 180 * 104; }
// 季节 -> 赤经板块（1 时 = 15°，一晚中天的范围约 6 小时）
const SKY_BANDS = {
  '春季': [[9, 15]],
  '夏季': [[15, 21]],
  '秋季': [[21, 24], [0, 3]],
  '冬季': [[3, 9]]
};
// 视图：translate(x,y) 之后 scale(s)，单位都是 viewBox 单位
let skyView = { s: 1, x: 0, y: 0 };
const skyPointers = new Map();
let skyPinch = null;
let skyDownPt = null, skyMoved = false, skyDownNode = null;

// 选中一个星座（多处共用；window.__skySel 供自动化核对）
function skySelect(id){
  if (!id) return;
  skySelected = id;
  window.__skySel = id;
  renderSky();
  if (skyEls.detail) skyEls.detail.scrollTop = 0;
}

function skyTransform(){
  return 'translate(' + skyView.x.toFixed(2) + ',' + skyView.y.toFixed(2) + ') scale(' + skyView.s.toFixed(3) + ')';
}
function skyApplyView(){
  const root = skyEls.map && skyEls.map.querySelector('.sky-root');
  if (root) root.setAttribute('transform', skyTransform());
}
function skyClampView(){
  skyView.s = Math.max(0.7, Math.min(4, skyView.s));
  const mx = 110 + 200 * (skyView.s - 1) / 2;
  const my = 50 + 120 * (skyView.s - 1) / 2;
  skyView.x = Math.max(-mx, Math.min(mx, skyView.x));
  skyView.y = Math.max(-my, Math.min(my, skyView.y));
}
// 以 viewBox 坐标 (cx,cy) 为锚点缩放
function skyZoomAt(factor, cx, cy){
  const old = skyView.s;
  const ns = Math.max(0.7, Math.min(4, old * factor));
  const k = ns / old;
  skyView.x = cx - (cx - skyView.x) * k;
  skyView.y = cy - (cy - skyView.y) * k;
  skyView.s = ns;
  skyClampView();
  skyApplyView();
}
function skyAnimateTo(target){
  const reduce = (typeof window.matchMedia === 'function') &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (reduce || typeof requestAnimationFrame !== 'function'){
    skyView = { s: target.s, x: target.x, y: target.y };
    skyApplyView(); return;
  }
  const from = { s: skyView.s, x: skyView.x, y: skyView.y };
  const t0 = (typeof performance !== 'undefined' ? performance.now() : Date.now());
  const dur = 420;
  function step(t){
    const k = Math.min(1, (t - t0) / dur), e = 1 - Math.pow(1 - k, 3);
    skyView.s = from.s + (target.s - from.s) * e;
    skyView.x = from.x + (target.x - from.x) * e;
    skyView.y = from.y + (target.y - from.y) * e;
    skyApplyView();
    if (k < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
  // 兜底：某些环境（无头/后台标签）rAF 会被节流，到点强制落到终态
  setTimeout(function(){ skyView = { s: target.s, x: target.x, y: target.y }; skyApplyView(); }, dur + 80);
}
// 聚焦到某个季节的赤经板块（放大 + 居中）
function skyFocusBands(bands){
  if (!bands || bands.length !== 1){
    skyAnimateTo({ s: 1, x: 0, y: 0 });
    return;
  }
  const b = bands[0];
  const xa = skyX(b[0]), xb = skyX(b[1]);
  const left = Math.min(xa, xb), right = Math.max(xa, xb);
  // 适度放大：既“聚焦板块”，又保留足够赤纬范围（用户可用滚轮/双指继续放大）
  const ns = 1.35;
  const cx = (left + right) / 2;
  skyAnimateTo({ s: ns, x: 100 - cx * ns, y: 60 - 60 * ns });
}

function renderSkyMap(){
  if (!skyEls.map) return;
  const defs = '<defs>' +
    '<radialGradient id="skyMw" cx="50%" cy="50%" r="62%">' +
      '<stop offset="0%" stop-color="#41609c" stop-opacity=".26"></stop>' +
      '<stop offset="70%" stop-color="#2a3f70" stop-opacity=".12"></stop>' +
      '<stop offset="100%" stop-color="#0a1024" stop-opacity="0"></stop>' +
    '</radialGradient>' +
    '<radialGradient id="skyVig" cx="50%" cy="45%" r="70%">' +
      '<stop offset="60%" stop-color="#000" stop-opacity="0"></stop>' +
      '<stop offset="100%" stop-color="#000" stop-opacity=".55"></stop>' +
    '</radialGradient>' +
  '</defs>';

  // 确定性星尘（同一张图每次一致）
  let dust = '', seed = 20261022;
  function rnd(){ seed = (seed * 1103515245 + 12345) % 2147483648; return seed / 2147483648; }
  for (let i = 0; i < 80; i++){
    dust += '<circle cx="' + (rnd() * 200).toFixed(1) + '" cy="' + (rnd() * 120).toFixed(1) +
      '" r="' + (0.25 + rnd() * 0.7).toFixed(2) + '" fill="#cfe0ff" opacity="' +
      (0.12 + rnd() * 0.45).toFixed(2) + '"></circle>';
  }
  // 银河带
  const mw = '<ellipse cx="100" cy="60" rx="160" ry="26" fill="url(#skyMw)" transform="rotate(-16 100 60)"></ellipse>';

  // 季节板块
  let sector = '';
  const bands = (skyFilter !== '全部') ? (SKY_BANDS[skyFilter] || []) : [];
  for (let i = 0; i < bands.length; i++){
    const b = bands[i];
    const xa = skyX(b[1]), xb = skyX(b[0]);
    sector += '<rect class="sky-sector" x="' + Math.min(xa, xb).toFixed(1) + '" y="6" width="' +
      Math.abs(xa - xb).toFixed(1) + '" height="104" rx="4"></rect>';
  }

  // 网格：赤纬
  let grid = '';
  for (let dec = -60; dec <= 60; dec += 30){
    const y = skyY(dec).toFixed(1);
    grid += '<line class="sky-grid' + (dec === 0 ? ' sky-grid-eq' : '') + '" x1="8" y1="' + y +
      '" x2="192" y2="' + y + '"></line>';
    grid += '<text class="sky-lbl" x="4" y="' + (+y + 1) + '" text-anchor="middle">' +
      (dec > 0 ? '+' : '') + dec + '°</text>';
  }
  // 网格：赤经
  for (let ra = 0; ra <= 24; ra += 3){
    const x = skyX(ra).toFixed(1);
    grid += '<line class="sky-grid" x1="' + x + '" y1="8" x2="' + x + '" y2="112"></line>';
    if (ra % 6 === 0){
      grid += '<text class="sky-lbl" x="' + x + '" y="117" text-anchor="middle">' + ra + 'h</text>';
    }
  }

  // 星座节点
  let nodes = '';
  for (let i = 0; i < SKY.length; i++){
    const s = SKY[i];
    const on = skyIsOn(s);
    const inSeason = (skyFilter === '全部') || (s.season === skyFilter);
    if (!inSeason) continue;                    // 非当季：直接不显示（“只在全部和夏季出现”）
    const p = [skyX(s.ra), skyY(s.dec)];
    const sel = (skySelected === s.id) ? ' sel' : '';
    const cls = 'skynode' + (on ? ' on' : '') + sel;
    const r = on ? 1.9 : 1.1;
    nodes += '<g class="' + cls + '" data-sky="' + skyEsc(s.id) + '" role="button" tabindex="0" ' +
      'aria-label="' + skyEsc(s.zh) + (on ? '，已观测' : '，未观测') + '">' +
      '<circle class="hit" cx="' + p[0].toFixed(1) + '" cy="' + p[1].toFixed(1) + '" r="5"></circle>';
    const phase = ' style="animation-delay:-' + ((i % 12) * 0.29).toFixed(2) + 's"';
    if (on){
      nodes += '<circle class="halo" cx="' + p[0].toFixed(1) + '" cy="' + p[1].toFixed(1) + '" r="' + (r * 2.6).toFixed(1) + '"' + phase + '></circle>';
    }
    nodes += '<circle class="dot" cx="' + p[0].toFixed(1) + '" cy="' + p[1].toFixed(1) + '" r="' + r + '"' +
      (on ? phase : '') + '></circle>';
    // 已观测：亮白名字；未观测：同样的名字但暗色（不再用问号）
    const ly = (p[1] + (s.dec >= 20 ? -4.2 : 5.6)).toFixed(1);
    nodes += '<text class="lbl' + (on ? '' : ' off') + '" x="' + p[0].toFixed(1) + '" y="' + ly + '">' +
      skyEsc(s.zh.replace('座', '')) + '</text>';
    nodes += '</g>';
  }

  skyEls.map.innerHTML = defs +
    '<g class="sky-root" transform="' + skyTransform() + '">' +
      mw + dust + sector + grid + nodes +
    '</g>' +
    '<rect class="sky-vignette" x="0" y="0" width="200" height="120" fill="url(#skyVig)" pointer-events="none"></rect>';
}

function renderSkyFilters(){
  if (!skyEls.filters) return;
  const opts = ['全部', '春季', '夏季', '秋季', '冬季'];
  skyEls.filters.innerHTML = opts.map(function(o){
    return '<button type="button" class="mini' + (skyFilter === o ? ' on' : '') +
      '" data-season="' + o + '" aria-pressed="' + (skyFilter === o) + '">' + o + '</button>';
  }).join('');
}

function skyDetailHtml(){
  if (!skySelected) return '';
  const s = SKY.find(function(x){ return x.id === skySelected; });
  if (!s) return '';
  const on = skyIsOn(s);
  const closeBtnGap = '';
  if (!on){
    return '<div class="sky-card"><h3>未观测</h3>' +
      '<div class="sub">第 ' + s.level + ' 关 · 通关后点亮</div>' +
      '<dl class="sky-meta">' +
        '<dt>星座</dt><dd>' + skyEsc(s.zh) + '（' + skyEsc(s.en) + '）</dd>' +
        '<dt>方位</dt><dd>赤经 ' + s.raText + '，赤纬 ' + s.decText + '</dd>' +
        '<dt>天区</dt><dd>' + s.zone + ' · ' + s.season + '星空</dd>' +
      '</dl>' +
      '<p class="sky-locked">先去第 ' + s.level + ' 关观测它，返回来就能看到星图与相邻星座。</p></div>';
  }
  const lv = LEVELS[s.level - 1];
  const nb = s.neighbors.map(function(n){
    const known = n.id && SKY.some(function(k){ return k.id === n.id; });
    const unlocked = known && isCleared(n.level - 1);
    const cls = unlocked ? 'link' : '';
    const attr = unlocked ? ' data-jump="' + skyEsc(n.id) + '"' : '';
    return '<button type="button" class="' + cls + '"' + attr + '>' + skyEsc(n.zh) +
      (unlocked ? '' : (known ? '（未观测）' : '')) + '</button>';
  }).join('');
  const starMap = (lv && lv.theme) ? constSvg(lv.theme, lv.size, lv.noise) : '';
  return '<div class="sky-card">' +
      '<h3>' + skyEsc(s.zh) + ' <span class="sub">' + skyEsc(s.en) + ' · ' + skyEsc(s.abbr) + '</span></h3>' +
      '<div class="sub">第 ' + s.level + ' 关 · 已观测' + closeBtnGap + '</div>' +
      '<dl class="sky-meta">' +
        '<dt>中心坐标</dt><dd>赤经 ' + s.raText + '，赤纬 ' + s.decText + '</dd>' +
        '<dt>天区</dt><dd>' + s.zone + ' · ' + s.season + '星空</dd>' +
        '<dt>面积</dt><dd>全天第 ' + s.areaRank + ' 大</dd>' +
        '<dt>最亮星</dt><dd>' + skyEsc(s.brightest.zh) + '（' + skyEsc(s.brightest.en) +
          '，' + s.brightest.mag + ' 等）</dd>' +
      '</dl>' +
      '<div class="sky-map-slot">' + starMap + '</div>' +
      ((lv && lv.theme && lv.theme.fact) ? '<p class="sky-fact">' + skyEsc(lv.theme.fact) + '</p>' : '') +
      '<div class="sky-neigh">' + nb + '</div>' +
    '</div>';
}

function showConstModal(){
  const m = document.getElementById('constModal');
  if (!m) return;
  m.hidden = false;
  void m.offsetWidth;                 // 强制 reflow，保证过渡生效
  m.className = 'const-modal open';
  document.body.classList.add('drawer-open');
}
function hideConstModal(){
  const m = document.getElementById('constModal');
  if (!m) return;
  m.className = 'const-modal';
  document.body.classList.remove('drawer-open');
  setTimeout(function(){
    const cur = document.getElementById('constModal');
    if (cur && cur.className.indexOf('open') < 0) cur.hidden = true;
  }, 200);
}

function renderSkyDetail(){
  const body = document.getElementById('constModalBody');
  if (!body) return;
  if (!skySelected){ hideConstModal(); body.innerHTML = ''; return; }
  body.innerHTML = skyDetailHtml();
  showConstModal();
}

function skyHintText(){
  if (skyFilter === '全部'){
    return '全天总览 · 亮字 = 已观测（会闪烁），暗字 = 未观测 · 按住拖动可平移 · 滚轮/双指缩放 · 双击复位';
  }
  const bands = SKY_BANDS[skyFilter] || [];
  const range = bands.map(function(b){ return b[0] + '–' + b[1] + ' 时'; }).join(' 与 ');
  return skyFilter + '星空 = 赤经 ' + range + ' · 其它季节的星座已隐藏 · 按住拖动可平移 · 滚轮/双指缩放';
}

function renderSky(){
  renderSkyFilters();
  const hintEl = document.getElementById('skyHint');
  if (hintEl) hintEl.textContent = skyHintText();
  renderSkyMap();
  renderSkyDetail();
  const on = skyOnCount();
  if (skyEls.count) skyEls.count.textContent = String(on);
  if (skyEls.total) skyEls.total.textContent = String(SKY.length);
}

function refreshSkyBadge(){
  if (skyEls.btnNum) skyEls.btnNum.textContent = String(skyOnCount());
  if (skyEls.btnTotal) skyEls.btnTotal.textContent = String(SKY.length);
}

function refreshSkyLitBtn(){
  const b = document.getElementById('skyLitBtn');
  if (!b) return;
  const on = progress.devSkyLit === true;
  b.textContent = on ? '🔆 已全部点亮（预览中）' : '🔆 一键点亮（预览）';
  b.setAttribute('aria-pressed', on ? 'true' : 'false');
  b.className = 'mini' + (on ? ' on' : '');
}
function toggleSkyLit(){
  progress.devSkyLit = progress.devSkyLit !== true;
  saveProgress();
  refreshSkyLitBtn();
  renderSky();
}

function openSky(){
  if (!skyEls.panel) return;
  skyOpen = true;
  skyView = { s: 1, x: 0, y: 0 };
  skySelected = null;
  refreshSkyLitBtn();
  skyEls.panel.hidden = false;
  skyEls.panel.className = 'panel sky-panel open';
  if (skyEls.btn) skyEls.btn.setAttribute('aria-expanded', 'true');
  renderSky();
}
function closeSky(){
  if (!skyEls.panel) return;
  skySelected = null;
  renderSkyDetail();
  skyOpen = false;
  skyEls.panel.hidden = true;
  skyEls.panel.className = 'panel sky-panel';
  if (skyEls.btn) skyEls.btn.setAttribute('aria-expanded', 'false');
}

if (skyEls.btn) skyEls.btn.addEventListener('click', function(){ skyOpen ? closeSky() : openSky(); });
if (skyEls.litBtn) skyEls.litBtn.addEventListener('click', toggleSkyLit);
if (skyEls.close) skyEls.close.addEventListener('click', closeSky);
if (skyEls.filters) skyEls.filters.addEventListener('click', function(e){
  const b = e.target.closest('[data-season]');
  if (!b) return;
  skyFilter = b.getAttribute('data-season');
  if (skySelected){
    const cur = SKY.find(function(x){ return x.id === skySelected; });
    if (cur && skyFilter !== '全部' && cur.season !== skyFilter) skySelected = null;
  }
  // 选中季节：放大并聚焦该季节的赤经板块
  renderSky();
  skyFocusBands(SKY_BANDS[skyFilter]);
});
if (skyEls.map) skyEls.map.addEventListener('keydown', function(e){
  if (e.key !== 'Enter' && e.key !== ' ' && e.key !== 'Spacebar') return;
  const node = e.target && e.target.closest ? e.target.closest('[data-sky]') : null;
  if (!node) return;
  e.preventDefault();
  skySelect(node.getAttribute('data-sky'));
});

if (skyEls.map) skyEls.map.addEventListener('click', function(e){
  if (skyMoved){ skyMoved = false; return; }   // 拖动结束不算点击
  const hit = (e.target && e.target.closest) ? e.target.closest('[data-sky]') : null;
  const node = hit || skyDownNode;             // 兜底：pointer capture 后 target 可能变成 SVG 根
  if (!node) return;
  skySelect(node.getAttribute('data-sky'));
});

// 按住拖动 = 平移；滚轮 / 双指 = 缩放；单击（位移 < 8px）= 选中
if (skyEls.map){
  function vbox(e){
    const rect = skyEls.map.getBoundingClientRect();
    return {
      x: (e.clientX - rect.left) / Math.max(1, rect.width) * 200,
      y: (e.clientY - rect.top) / Math.max(1, rect.height) * 120,
      sx: 200 / Math.max(1, rect.width),
      sy: 120 / Math.max(1, rect.height),
      rect: rect
    };
  }
  skyEls.map.addEventListener('pointerdown', function(e){
    skyPointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
    try { skyEls.map.setPointerCapture(e.pointerId); } catch (_) {}
    if (skyPointers.size === 1){
      skyDownPt = { x: e.clientX, y: e.clientY };
      skyMoved = false;
      skyDownNode = (e.target && e.target.closest) ? e.target.closest('[data-sky]') : null;
      skyDragLast = { x: e.clientX, y: e.clientY };
    } else if (skyPointers.size === 2){
      const pts = Array.from(skyPointers.values());
      skyPinch = {
        d: Math.hypot(pts[0].x - pts[1].x, pts[0].y - pts[1].y),
        mid: { x: (pts[0].x + pts[1].x) / 2, y: (pts[0].y + pts[1].y) / 2 },
        view: { s: skyView.s, x: skyView.x, y: skyView.y }
      };
      skyMoved = true;
    }
    skyEls.map.classList.add('dragging');
  });

  skyEls.map.addEventListener('pointermove', function(e){
    if (!skyPointers.has(e.pointerId)) return;
    skyPointers.set(e.pointerId, { x: e.clientX, y: e.clientY });

    if (skyPointers.size >= 2 && skyPinch){
      const pts = Array.from(skyPointers.values()).slice(0, 2);
      const d = Math.hypot(pts[0].x - pts[1].x, pts[0].y - pts[1].y);
      const mid = { x: (pts[0].x + pts[1].x) / 2, y: (pts[0].y + pts[1].y) / 2 };
      const factor = d / Math.max(1, skyPinch.d);
      // 从捏合起始状态重新计算，避免累计误差
      skyView = { s: skyPinch.view.s, x: skyPinch.view.x, y: skyPinch.view.y };
      const v0 = vbox({ clientX: skyPinch.mid.x, clientY: skyPinch.mid.y });
      const v1 = vbox({ clientX: mid.x, clientY: mid.y });
      skyZoomAt(factor, v0.x, v0.y);
      skyView.x += (v1.x - v0.x);
      skyView.y += (v1.y - v0.y);
      skyClampView(); skyApplyView();
      e.preventDefault();
      return;
    }

    if (skyPointers.size === 1 && skyDownPt){
      if (Math.hypot(e.clientX - skyDownPt.x, e.clientY - skyDownPt.y) > 8) skyMoved = true;
      if (skyMoved){
        const scale = 200 / Math.max(1, skyEls.map.getBoundingClientRect().width);
        skyView.x += (e.clientX - skyDragLast.x) * scale;
        skyView.y += (e.clientY - skyDragLast.y) * (120 / Math.max(1, skyEls.map.getBoundingClientRect().height));
        skyDragLast = { x: e.clientX, y: e.clientY };
        skyClampView(); skyApplyView();
        e.preventDefault();
      }
    }
  });

  function skyPointerEnd(e){
    const wasSingle = skyPointers.size === 1;
    skyPointers.delete(e.pointerId);
    if (skyPointers.size < 2) skyPinch = null;
    if (skyPointers.size === 0){
      skyEls.map.classList.remove('dragging');
      // 单击（本次手势未拖动）→ 选中；pointer capture 会让 click.target 变成 SVG 根节点，
      // 所以这里用按下时记录的节点判定，不依赖 click。
      if (wasSingle && !skyMoved && skyDownNode){
        skySelect(skyDownNode.getAttribute('data-sky'));
      }
      // 手势结束就复位，避免 skyMoved 粘住害得之后永远点不开
      skyDownNode = null;
      skyDownPt = null;
      skyMoved = false;
    }
  }
  skyEls.map.addEventListener('pointerup', skyPointerEnd);
  skyEls.map.addEventListener('pointercancel', skyPointerEnd);

  skyEls.map.addEventListener('wheel', function(e){
    e.preventDefault();
    const v = vbox(e);
    skyZoomAt(Math.exp(-e.deltaY * 0.0016), v.x, v.y);
  }, { passive: false });

  skyEls.map.addEventListener('dblclick', function(){
    skyAnimateTo({ s: 1, x: 0, y: 0 });
  });
}

let skyDragLast = { x: 0, y: 0 };
// 弹窗内相邻星座跳转（事件委托）
const constModalBody = document.getElementById('constModalBody');
if (constModalBody) constModalBody.addEventListener('click', function(e){
  const b = e.target.closest('[data-jump]');
  if (!b) return;
  skySelect(b.getAttribute('data-jump'));
});
// ===== 玩法规则弹窗 =====
const ruleModalEl = document.getElementById('ruleModal');
function openRules(){
  if (!ruleModalEl) return;
  ruleModalEl.hidden = false;
  void ruleModalEl.offsetWidth;                 // 强制 reflow，保证过渡生效
  ruleModalEl.className = 'const-modal open';
  document.body.classList.add('drawer-open');
}
function closeRules(){
  if (!ruleModalEl) return;
  ruleModalEl.className = 'const-modal';
  document.body.classList.remove('drawer-open');
  setTimeout(function(){
    if (ruleModalEl.className.indexOf('open') < 0) ruleModalEl.hidden = true;
  }, 200);
}
const ruleBtnEl = document.getElementById('ruleBtn');
if (ruleBtnEl) ruleBtnEl.addEventListener('click', openRules);
const ruleCloseEl = document.getElementById('ruleClose');
if (ruleCloseEl) ruleCloseEl.addEventListener('click', closeRules);
const ruleMaskEl = document.getElementById('ruleModalMask');
if (ruleMaskEl) ruleMaskEl.addEventListener('click', closeRules);
if (ruleModalEl) ruleModalEl.addEventListener('click', function(e){
  if (e.target === ruleModalEl) closeRules();   // 点卡片外空白也关
});

// 右上角 × 关闭
const constCloseBtn = document.getElementById('constClose');
if (constCloseBtn) constCloseBtn.addEventListener('click', function(){ skySelected = null; renderSkyDetail(); });
// 点空白区域（遮罩）关闭
const constModalMask = document.getElementById('constModalMask');
if (constModalMask) constModalMask.addEventListener('click', function(){ skySelected = null; renderSkyDetail(); });
const constModalEl = document.getElementById('constModal');
if (constModalEl) constModalEl.addEventListener('click', function(e){
  // 点在卡片外的空白也算关闭
  if (e.target === constModalEl){ skySelected = null; renderSkyDetail(); }
});

window.addEventListener('keydown', function(e){
  if (e.key === 'Escape' || e.key === 'Esc'){
    if (modalOpenNow){ dismissModal(); return; }   // Esc 收起结算，结算条保留入口
    if (ruleModalEl && ruleModalEl.className.indexOf('open') >= 0){ closeRules(); return; }
    const cm = document.getElementById('constModal');
    if (cm && cm.className.indexOf('open') >= 0){ skySelected = null; renderSkyDetail(); return; }
    if (skyOpen){ closeSky(); return; }
    if (panelOpen) closePanel();
  }
});

if (Array.isArray(LEVELS) && LEVELS.length){
  loadProgress();
  buildLevelGrid();
  refreshUnlockBtn();
  refreshSkyBadge();
  const idx0 = startIndex();
  startLevel(idx0);
  if (!progress.introSeen && idx0 === 0) showIntro();
  const ib = document.getElementById('introStart');
  if (ib) ib.addEventListener('click', hideIntro);
  const io = document.getElementById('introOverlay');
  if (io) io.addEventListener('click', function(e){ if (e.target === io) hideIntro(); });
} else {
  boardEl.innerHTML = '<p class="err">关卡数据缺失。</p>';
}
})();
