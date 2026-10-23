'use strict';
/* v21 复核 E（运行时）：六种进度态 #skyCount + 未通关星座不泄露星图 */
const fs = require('fs');
const path = require('path');
const { boot, makeStorage } = require('./v21_stub.js');
const P = require('./v21_play.js');
const { q, qa, textOf } = P;

const R = [];
const check = (id, name, ok, detail) => { R.push({ id, name, ok: !!ok, detail: String(detail === undefined ? '' : detail) }); };

function clearedMap(ks) { const c = {}; ks.forEach(k => { c[String(k)] = 1; }); return c; }
function seed(ks) { return makeStorage({ 'leixian.migong.progress.v1': JSON.stringify({ v: 1, cleared: clearedMap(ks), last: 0, devUnlock: false, devSkyLit: false, introSeen: true, sound: true }) }); }

const STATES = [
  { name: '0 关通关', ks: [] },
  { name: '1 关通关', ks: [0] },
  { name: '7 关通关（前缀）', ks: [0, 1, 2, 3, 4, 5, 6] },
  { name: '25 关通关（前缀）', ks: Array.from({ length: 25 }, (_, i) => i) },
  { name: '49 关通关（前缀）', ks: Array.from({ length: 49 }, (_, i) => i) },
  { name: '50 关通关', ks: Array.from({ length: 50 }, (_, i) => i) }
];
const detail = [];
let okAll = true;
for (const s of STATES) {
  const g = boot({ storage: seed(s.ks) });
  // 找当前关卡：全通关时 startIndex 停在最后一关
  g.dispatch(q(g, '#skyBtn'), 'click', {});
  g.advance(600);
  const count = Number(textOf(g, '#skyCount'));
  const total = Number(textOf(g, '#skyTotal'));
  const expect = s.ks.length;
  const ok = count === expect && total === 50;
  if (!ok) okAll = false;
  detail.push(`${s.name}: #skyCount=${count} (期望 ${expect}) #skyTotal=${total}${ok ? '' : ' ✗'}`);
  // 图鉴标题计数也一致
  if (Number(textOf(g, '#skyCount')) !== expect) okAll = false;
}
check('E1', '六种进度态下 #skyCount == 实际通关数（#skyTotal == 50）', okAll, detail.join(' | '));

/* 未通关星座不泄露星图 */
(function () {
  const g = boot({ storage: seed([0, 1]) });          // 只通关前 2 关
  g.dispatch(q(g, '#skyBtn'), 'click', {});
  g.advance(600);
  const nodes = qa(g, '#skyMap [data-sky]');
  const lockedNode = nodes.find(n => { const id = n.getAttribute('data-sky'); const s = P.SKY.find(x => x.id === id); return !s || !(s.level - 1 < 2); });
  const lockedId = lockedNode && lockedNode.getAttribute('data-sky');
  // 用 Enter 选中（#skyMap 上的 keydown 委托）
  g.dispatch(lockedNode, 'keydown', { key: 'Enter' });
  g.advance(300);
  const body = q(g, '#constModalBody');
  const html = body ? body.innerHTML : '';
  const lockedMeta = P.SKY.find(x => x.id === lockedId);
  const leakedStars = (html.match(/class="gstar"/g) || []).length;
  const leakedLines = (html.match(/class="gline"/g) || []).length;
  const leakedNoise = (html.match(/class="gnoise"/g) || []).length;
  const hasJump = /data-jump=/.test(html);
  const hasFact = /sky-fact/.test(html);
  const otherNames = P.SKY.filter(x => x.id !== lockedId).map(x => x.zh).filter(z => html.indexOf(z) >= 0);
  const showsLockedTitle = html.indexOf('未观测') >= 0 && html.indexOf(lockedMeta.zh) >= 0;
  check('E2', '未通关星座：无 gstar/gline/gnoise、无相邻星座名/跳转、无 fact',
    leakedStars === 0 && leakedLines === 0 && leakedNoise === 0 && !hasJump && !hasFact && otherNames.length === 0 && showsLockedTitle,
    `选中 ${lockedId}(${lockedMeta && lockedMeta.zh})：gstar=${leakedStars} gline=${leakedLines} gnoise=${leakedNoise} data-jump=${hasJump} sky-fact=${hasFact} 其它星座名=${
    JSON.stringify(otherNames)} 标题含未观测=${showsLockedTitle}`);

  // 已通关星座：星图/连线/杂星齐全 + fact
  const onNode = qa(g, '#skyMap [data-sky]').find(n => { const s = P.SKY.find(x => x.id === n.getAttribute('data-sky')); return s && s.level <= 2; });
  g.dispatch(onNode, 'keydown', { key: 'Enter' });
  g.advance(300);
  const html2 = q(g, '#constModalBody').innerHTML;
  const id2 = onNode.getAttribute('data-sky');
  const lv2 = P.LV[P.SKY.find(x => x.id === id2).level - 1];
  const c2 = [(html2.match(/class="gstar"/g) || []).length, (html2.match(/class="gline"/g) || []).length, (html2.match(/class="gnoise"/g) || []).length];
  check('E3', '已通关星座：gstar/gline/gnoise == stars/lines/noise 且显示 fact',
    c2[0] === lv2.theme.stars.length && c2[1] === lv2.theme.lines.length && c2[2] === lv2.noise.length && /sky-fact/.test(html2),
    `${id2}: gstar=${c2[0]}/${lv2.theme.stars.length} gline=${c2[1]}/${lv2.theme.lines.length} gnoise=${c2[2]}/${lv2.noise.length} fact=${/sky-fact/.test(html2)}`);

  // 图鉴节点环形/map 上未通关星座只显示暗色名字（不显示星图）
  const mapHtml = q(g, '#skyMap').innerHTML;
  check('E4', '图鉴地图节点：未观测星座显示暗色名字（.lbl.off），无任何星图 SVG',
    /class="lbl off"/.test(mapHtml) && !/gstar/.test(mapHtml),
    `lbl.off=${/class="lbl off"/.test(mapHtml)} gstar-in-map=${/gstar/.test(mapHtml)}`);
})();

const out = { results: R, pass: R.filter(r => r.ok).length, fail: R.filter(r => !r.ok).length };
fs.writeFileSync(path.join(__dirname, 'v21_out_e.json'), JSON.stringify(out, null, 1), 'utf8');
console.log('=== E 图鉴运行时 ===');
R.forEach(r => console.log(`${r.ok ? 'PASS' : 'FAIL'}  ${r.id}  ${r.name}\n        ${r.detail}`));
console.log(`E 合计 PASS ${out.pass} / FAIL ${out.fail}`);
