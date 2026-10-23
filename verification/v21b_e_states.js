'use strict';
/* v21b 复核 E（运行时，独立实现）：任务书要求的六种进度态 + 未通关星座全量不泄露星图 */
const fs = require('fs');
const path = require('path');
const { boot, makeStorage } = require('./v21b_stub.js');
const P = require('./v21b_play.js');
const { q, qa, textOf } = P;

const R = [];
const check = (id, name, ok, detail) => { R.push({ id, name, ok: !!ok, detail: String(detail === undefined ? '' : detail) }); };

/* 存档键与结构以当前 dist 为准：leixian.migong.progress.v1 = {v,cleared,last,devUnlock,devSkyLit,introSeen,sound} */
const KEY = 'leixian.migong.progress.v1';
function seed(levels0) {            // 传入 0-based 关卡索引
  const cleared = {};
  levels0.forEach(k => { cleared[String(k)] = 1; });
  return makeStorage({ [KEY]: JSON.stringify({ v: 1, cleared, last: 0, devUnlock: false, devSkyLit: false, introSeen: true, sound: true }) });
}
const upTo = n => Array.from({ length: n }, (_, i) => i);

/* 任务书要求的六种进度态：{} / {1} / {1,21} / 前21 / 前49 / 全部50（题面为关卡号，1-based） */
const STATES = [
  { name: '{}', ks: [], expect: 0, note: '空进度' },
  { name: '{1}', ks: [0], expect: 1, note: '仅第 1 关' },
  { name: '{1,21}', ks: [0, 20], expect: 2, note: '非连续，关键用例' },
  { name: '前21', ks: upTo(21), expect: 21, note: '前缀 21' },
  { name: '前49', ks: upTo(49), expect: 49, note: '前缀 49' },
  { name: '全部50', ks: upTo(50), expect: 50, note: '全通关' }
];

const detail = [];
let okAll = true;
for (const s of STATES) {
  const g = boot({ storage: seed(s.ks) });
  g.dispatch(q(g, '#skyBtn'), 'click', {});
  g.advance(600);
  const count = Number(textOf(g, '#skyCount'));
  const total = Number(textOf(g, '#skyTotal'));
  const lvPanel = Number(textOf(g, '#clearedCount'));   // 侧栏「已通关 N/50」交叉校验
  const lvTotal = Number(textOf(g, '#totalCount'));
  const ok = count === s.expect && total === 50 && lvPanel === s.expect && lvTotal === 50;
  if (!ok) okAll = false;
  detail.push(`${s.name}: #skyCount=${count} (期望 ${s.expect}) #skyTotal=${total} #clearedCount=${lvPanel}/${lvTotal}${ok ? '' : ' ✗'}`);
}
check('E1', '六种进度态下 #skyCount == 实际通关数（{}、{1}、{1,21}、前21、前49、全部50）',
  okAll, detail.join(' | '));

/* 未通关星座不泄露星图：对「全部未通关星座」逐个打开，而不是只抽查一个 */
(function () {
  const UNLOCKED = [0, 20];                       // 星表里只有第 1、21 关已通关（非连续）
  const g = boot({ storage: seed(UNLOCKED) });
  g.dispatch(q(g, '#skyBtn'), 'click', {});
  g.advance(600);
  const unlockedIds = new Set(P.SKY.filter(s => UNLOCKED.indexOf(s.level - 1) >= 0).map(s => s.id));
  const locked = P.SKY.filter(s => !unlockedIds.has(s.id));
  const bad = [];
  let badTitle = 0, leakedAny = 0;
  for (const meta of locked) {
    const node = qa(g, '#skyMap [data-sky]').find(n => n.getAttribute('data-sky') === meta.id);
    if (!node) { bad.push(meta.id + ':节点缺失'); continue; }
    g.dispatch(node, 'keydown', { key: 'Enter' });
    g.advance(300);
    const body = q(g, '#constModalBody');
    const html = body ? body.innerHTML : '';
    const nStar = (html.match(/class="gstar"/g) || []).length;
    const nLine = (html.match(/class="gline"/g) || []).length;
    const nNoise = (html.match(/class="gnoise"/g) || []).length;
    const hasJump = /data-jump=/.test(html);
    const hasFact = /sky-fact/.test(html);
    // 先剥掉自身名字再查别的星座名：中文星座名存在包含关系（半人马座 ⊃ 人马座），
    // 直接子串匹配会把自身名字误判成「泄露了别的星座名」。
    const htmlNoSelf = html.split(meta.zh).join('');
    const otherNames = P.SKY.filter(x => x.id !== meta.id).map(x => x.zh)
      .filter(z => z && htmlNoSelf.indexOf(z) >= 0);
    const titleOk = html.indexOf('未观测') >= 0 || html.indexOf(meta.zh) >= 0;
    if (!titleOk) badTitle++;
    if (nStar || nLine || nNoise || hasJump || hasFact || otherNames.length) {
      leakedAny++;
      bad.push(`${meta.id}: gstar=${nStar} gline=${nLine} gnoise=${nNoise} jump=${hasJump} fact=${hasFact} 其它名=${JSON.stringify(otherNames)}`);
    }
  }
  check('E2', '未通关星座（全部 ' + locked.length + ' 个）不泄露：无 gstar/gline/gnoise、无跳转/fact、不显示别的星座名',
    bad.length === 0 && badTitle === 0, `未通关=${locked.length} 泄露=${leakedAny} 标题异常=${badTitle} ${bad.slice(0, 4).join(' ; ')}`);

  /* 已通关星座：gstar/gline/gnoise 数量与文件一致 + 显示 fact */
  const on = P.SKY.filter(s => UNLOCKED.indexOf(s.level - 1) >= 0);
  const det2 = [];
  let ok2 = true;
  for (const meta of on) {
    const node = qa(g, '#skyMap [data-sky]').find(n => n.getAttribute('data-sky') === meta.id);
    g.dispatch(node, 'keydown', { key: 'Enter' });
    g.advance(300);
    const html = q(g, '#constModalBody').innerHTML;
    const lv = P.LV[meta.level - 1];
    const got = [(html.match(/class="gstar"/g) || []).length,
                 (html.match(/class="gline"/g) || []).length,
                 (html.match(/class="gnoise"/g) || []).length];
    const want = [lv.theme.stars.length, lv.theme.lines.length, lv.noise.length];
    const fact = /sky-fact/.test(html);
    if (got[0] !== want[0] || got[1] !== want[1] || got[2] !== want[2] || !fact) ok2 = false;
    det2.push(`${meta.id}: gstar=${got[0]}/${want[0]} gline=${got[1]}/${want[1]} gnoise=${got[2]}/${want[2]} fact=${fact}`);
  }
  check('E3', '已通关星座：gstar/gline/gnoise == stars/lines/noise 且显示 fact', ok2, det2.join(' | '));

  /* 未通关星座在图鉴地图上只显示暗色名字，地图里不存在任何星图元素 */
  const mapHtml = q(g, '#skyMap').innerHTML;
  check('E4', '图鉴地图：未观测节点为暗色名字（.lbl.off），地图内无星图元素',
    /class="lbl off"/.test(mapHtml) && !/gstar|gline|gnoise/.test(mapHtml),
    `lbl.off=${/class="lbl off"/.test(mapHtml)} 星图元素=${/gstar|gline|gnoise/.test(mapHtml)}`);
})();

const out = { states: STATES.map(s => s.name), results: R, pass: R.filter(r => r.ok).length, fail: R.filter(r => !r.ok).length };
fs.writeFileSync(path.join(__dirname, 'v21b_out_e.json'), JSON.stringify(out, null, 1), 'utf8');
console.log('=== E 图鉴运行时 ===');
R.forEach(r => console.log(`${r.ok ? 'PASS' : 'FAIL'}  ${r.id}  ${r.name}\n        ${r.detail}`));
console.log(`E 合计 PASS ${out.pass} / FAIL ${out.fail}`);
