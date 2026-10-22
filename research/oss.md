# 开源弹药库（T2）：H5 引擎 / AI 原生游戏生成 / 关卡生成器与求解器

> **采集与口径（先读这段，决定你信多少）**
>
> - **采集时间**：2026-10-20（Asia/Shanghai）。star 数、license、最近 push 时间会随时间变化，引用时请带上"截至 2026-10-20"。
> - **数据来源**：`star`、`license`、`最近 push`、`archived` **全部**来自 GitHub REST API（`api.github.com`，2026-10-20 实抓）返回的 `stargazers_count` / `license.spdx_id` / `pushed_at` / `archived`，**没有一条来自记忆、博客或搜索结果摘要**。`license` 列显示 `-` = API 返回 `license: null`（仓库没挂许可证），**这不等于"随便用"**，商用前必须自己确认。
> - **体积数据**：2026-10-20 从 jsDelivr CDN 实际下载对应 dist 文件，用 gzip -9 实测，见 §1.3 / §6.2。CDN 文件与 npm 发布物一致，但**不等于你自己打包后的体积**（tree-shaking 后通常更小）。
> - **能力描述的证据等级**：本文件凡涉及"能否批量生成 / 保证可解 / 难度分级"，都标了证据来源。`README` = 我读过仓库 README 原文；`desc` = 只有 GitHub 描述字段，**未逐行验证代码**。未被标为 `README` 的能力请自行验证后再用。
> - **工具限制（已知）**：`web_search` 工具故障（HTTP 401），本文件完全未使用它；改用 `curl.exe` 直连 GitHub API + `https://kenney.nl` 站点直抓。GitHub 未认证搜索限流 10 次/分钟、核心 API 60 次/小时，本次共用 5 批约 90 次搜索 + 8 次核心 API 调用。
> - **本文件的价格**：约 90 次 API 调用换来的"可查证 repo 清单 + 5 个真实体积数字 + 3 条可直接抄的架构套路"。

---

## 0. 一页结论（先看这个）

### 0.1 对本比赛的推荐栈（详细论证见 §6）

| 优先级 | 方案 | inlined 后 index.html 量级（实测推算） | 什么时候选它 |
|---|---|---|---|
| **首选** | **零依赖 Canvas 2D + TypeScript + Vite + `vite-plugin-singlefile`** | **40–150 KB**（只有你自己的代码） | 50 关网格/逻辑类玩法：数独、扫雷、箭头解谜、配对、消除、拼图。**本比赛的默认答案** |
| 备选 A | **KAPLAY**（Kaboom 续作）+ Vite | ≈ **200–260 KB** raw / ≈ 75 KB gzip | 需要精灵动画、tween、粒子、音频管理（麻将消除、堆叠消除、三消） |
| 备选 B | **LittleJS**（零依赖小引擎，内置 ZzFX 音效） | ≈ **500–560 KB** raw / ≈ 150 KB gzip | 想要"一个引擎文件 + 音效开箱即用"，又不想碰 Phaser 的大 API |
| 备选 C | **Phaser 3** + `template-vite-ts` | ≈ **1.2–1.3 MB** raw / ≈ 310 KB gzip | 团队已熟 Phaser，或要吃"AI 训练语料最多"的红利（让 AI 写 Phaser 代码最不容易跑偏） |
| 不推荐 | Babylon.js / three.js / Cocos / LayaAir / GDevelop / p5.js | Babylon 实测 **7.5 MB** raw | 只有真的要做 3D 才考虑；本赛题明说"不需要复杂美术" |

**一句话**：这是一道**数据 + 规则**题（≥50 关、评审 50% 看玩法 / 30% 看关卡曲线），不是渲染题。把引擎的重量换成**关卡生成器的正确性**，是本次调研最确定的结论。

### 0.2 三条最值钱的可复用资产

1. **`richardtallent/vite-plugin-singlefile`**（1,236★，MIT，2026-10-17 push）——把 JS/CSS 全部内联进 `dist/index.html`，官方 README 明确写了 `file://` 双击打开时可用的能力清单（含 **localStorage 可用**）。这是"单个可打开就能玩的 H5"的**唯一必要工具**。核实细节见 §6.1。
2. **`robatron/sudoku.js`**（498★，MIT，2025-12-17）——JS 数独**生成器 + 求解器**，README 里直接给出 `sudoku.generate("easy"|"medium"|"hard")` 与"难度 = 给定格数"的 API。是全清单里**唯一一个"生成 + 求解 + 难度分级"三件套都在 README 里写明**的 JS 库（`README` 证据）。§3.3 给了怎么把它扩成 50 关流水线。
3. **`KilledByAPixel/LittleJS` + `KilledByAPixel/ZzFX`**（4,307★ / 804★，均 MIT，2026-10 活跃）——同一个作者做的零依赖小引擎 + 微型音效合成器，天然适合单文件交付（§1.2 / §4.2）。

### 0.3 五个必须避开的坑（速查）

| 坑 | 事实（API/README 证据） |
|---|---|
| **Kaboom.js 已归档** | `replit/kaboom` 2,732★ MIT，**`archived: true`，最后 push 2024-08-04**。续作是 `kaplayjs/kaplay`（1,812★ MIT，2026-10-19）。别再照抄 Kaboom 教程 |
| **麻将有"真麻将"和"连连看/上海麻将"两种** | `Pomax/mahjong`（115★）是**四人真麻将**规则引擎，不是 Vita Mahjong 那种单人匹配消除 |
| **匹配/三消类没有成熟的开源关卡生成器** | 搜遍 `match3 generator` / `triple tile` / `matching puzzle generator` 三个方向，最高星候选只有个位数 star（如 `igorhosantos/Match3-Engine` 1★）。**这块必须自己写**（§3.2） |
| **`thomasahle/numberlink` 是 AGPL-3.0** | Flow Free 类生成器+求解器，110★，2026-01-26。AGPL 对"联网服务"有传染性；**闭源/IAA 商用前必须评估**，或改用 MIT 的替代 |
| **单文件内联会让"内联资源"变成 1.33 倍** | 图片/音频内联为 base64 data URL 会膨胀约 33%，且 `public/` 目录下的资源**不会**被 singlefile 内联（README 明说）。所有美术/音效必须从 `src/` import |

---

## 1. H5 休闲游戏引擎与极简模板

### 1.1 事实表（全部来自 GitHub API，2026-10-20）

| Repo | ★ | License | 最近 push | 语言 | 定位 |
|---|---|---|---|---|---|
| [phaserjs/phaser](https://github.com/phaserjs/phaser) | 40,510 | MIT | 2026-08-21 | JS | 2D 游戏框架（Canvas/WebGL），生态与教程最多 |
| [phaserjs/template-vite-ts](https://github.com/phaserjs/template-vite-ts) | 196 | MIT | 2026-04-21 | TS | 官方 Vite+TS 模板（**最适合配 singlefile**） |
| [phaserjs/template-webpack](https://github.com/phaserjs/template-webpack) | 1,175 | MIT | 2026-04-10 | JS | 官方 Webpack 5 模板 |
| [phaserjs/phaser-ce](https://github.com/phaserjs/phaser-ce) | 1,393 | MIT | 2026-10-20 | JS | 老 Phaser 2 的社区维护分支，**新项目别用** |
| [pixijs/pixijs](https://github.com/pixijs/pixijs) | 48,425 | MIT | 2026-10-17 | TS | 纯 2D WebGL 渲染器（不管玩法逻辑） |
| [pixijs/open-games](https://github.com/pixijs/open-games) | 452 | MIT | 2025-11-11 | TS | 官方开源小游戏示例集 |
| [pixijs/pixijs-skills](https://github.com/pixijs/pixijs-skills) | 357 | MIT | 2026-10-01 | — | **面向 AI coding agent 的官方 PixiJS 技能包**（教 AI 正确用 PixiJS） |
| [kaplayjs/kaplay](https://github.com/kaplayjs/kaplay) | 1,812 | MIT | 2026-10-19 | TS | Kaboom 续作，极简 2D 游戏库 |
| [kaplayjs/create-kaplay](https://github.com/kaplayjs/create-kaplay) | 18 | - | 2026-09-02 | — | KAPLAY 初始化 CLI |
| [replit/kaboom](https://github.com/replit/kaboom) | 2,732 | MIT | 2024-08-04 | JS | **已归档（archived: true）** |
| [excaliburjs/Excalibur](https://github.com/excaliburjs/Excalibur) | 2,356 | BSD-2-Clause | 2026-10-18 | TS | TS 优先的 2D 引擎 |
| [excaliburjs/template-ts-vite](https://github.com/excaliburjs/template-ts-vite) | 41 | BSD-2-Clause | 2026-10-15 | TS | 官方 Vite 模板 |
| [melonjs/melonJS](https://github.com/melonjs/melonJS) | 6,414 | MIT | 2026-10-20 | JS | 轻量 HTML5 引擎（老牌，仍在维护） |
| [melonjs/typescript-boilerplate](https://github.com/melonjs/typescript-boilerplate) | 9 | MIT | 2026-09-05 | TS | Vite + TS 起步模板 |
| [mrdoob/three.js](https://github.com/mrdoob/three.js) | 116,640 | MIT | 2026-10-20 | JS | 3D 渲染库（事实标准） |
| [BabylonJS/Babylon.js](https://github.com/BabylonJS/Babylon.js) | 26,197 | Apache-2.0 | 2026-10-19 | TS | 全功能 3D 引擎（含编辑器、物理、GUI） |
| [playcanvas/engine](https://github.com/playcanvas/engine) | 17,090 | MIT | 2026-10-20 | TS | WebGL/WebGPU/WebXR 运行时 + MIT 编辑器 |
| [cocos/cocos-engine](https://github.com/cocos/cocos-engine) | 9,867 | NOASSERTION | 2026-10-08 | C++ | Cocos Creator 引擎开源部分（**编辑器开源**） |
| [cocos/cocos4](https://github.com/cocos/cocos4) | 1,499 | MIT | 2026-10-19 | C++ | Cocos 4 引擎仓库 |
| [layabox/LayaAir](https://github.com/layabox/LayaAir) | 2,219 | MIT | 2026-10-19 | TS | LayaAir 引擎（2D/3D） |
| [layabox/layaair-skills](https://github.com/layabox/layaair-skills) | 13 | MIT | 2026-10-19 | — | **面向 AI agent 的 LayaAir 技能包** |
| [4ian/GDevelop](https://github.com/4ian/GDevelop) | 27,747 | NOASSERTION | 2026-10-19 | TS | 开源可视化游戏编辑器 |
| [processing/p5.js](https://github.com/processing/p5.js) | 24,148 | **LGPL-2.1** | 2026-10-19 | JS | 创意编程库（艺术/教学向） |
| [KilledByAPixel/LittleJS](https://github.com/KilledByAPixel/LittleJS) | 4,307 | MIT | 2026-10-15 | JS | **零依赖极小 2D/3D HTML5 引擎**（内置音效/粒子/物理） |
| [IceCreamYou/HTML5-Canvas-Game-Boilerplate](https://github.com/IceCreamYou/HTML5-Canvas-Game-Boilerplate) | 263 | NOASSERTION | 2026-10-01 | JS | 基础 Canvas 游戏脚手架（含游戏状态循环） |
| [herebefrogs/gamejam-boilerplate](https://github.com/herebefrogs/gamejam-boilerplate) | 48 | MIT | 2026-09-20 | JS | 小体量 2D canvas 脚手架（含键鼠/触摸） |
| [gamedev-skills/awesome-gamedev-agent-skills](https://github.com/gamedev-skills/awesome-gamedev-agent-skills) | 1,739 | Apache-2.0 | 2026-10-09 | — | **游戏开发 AI agent 技能合集（含 Phaser/PixiJS）** |
| [majidmanzarpour/threejs-game-skills](https://github.com/majidmanzarpour/threejs-game-skills) | 2,546 | MIT | 2026-09-28 | — | 让 AI 写出"可玩且打磨过"的 Three.js 浏览器游戏 |
| [vibe-stack/ggez](https://github.com/vibe-stack/ggez) | 236 | MIT | 2026-04-19 | ? | 为 "vibe coding" 设计的 three.js 游戏框架 |

### 1.2 逐项：能复用什么 / 坑在哪

- **phaserjs/phaser（40,510★ MIT）**
  - 可复用：官方 Vite/TS 模板可直接 + singlefile；社区插件与示例最丰富；**AI 训练语料最多**——对"让 AI 写代码"这件事，Phaser 是错误率最低的引擎选择（这是选型里最容易被低估的一条）。
  - 坑：①体积是全场最大档之一（见 §1.3，Phaser 4 inlined ≈1.31 MB raw）；②Phaser 3 → 4 是大版本跨越（**推论**：仅由 CDN 上 `phaser@3` 与 `phaser@4` 两条产物线并存推断，我未逐个核对 changelog），AI 生成的代码极易混用 3/4 的 API，**必须锁死一个主版本并在 prompt 里声明**；③`phaserjs/phaser` 最近 push 2026-08-21，比 PixiJS/melonJS 慢一些，但仍是活跃项目。
- **pixijs/pixijs（48,425★ MIT）**
  - 可复用：只做渲染，`pixijs/open-games` 有官方小游戏示例；`pixijs/pixijs-skills`（357★）是**官方给 AI agent 的技能包**，如果你打算让 AI 全量写渲染层，这个比通用 prompt 可靠。
  - 坑：PixiJS **不含**场景管理、输入抽象、音频、关卡状态——这些要自己写，对"3 天出原型"来说未必比零依赖更快。
- **kaplayjs/kaplay（1,812★ MIT）**
  - 可复用：API 极简（`onKeyPress`、`add([sprite(), pos(), area()])`），内置音频/粒子/物理/文字；体积小（实测 raw 184.7 KB / gzip 68.1 KB）。
  - 坑：①**不要再用 `replit/kaboom`**（已归档 2024-08-04）；②社区与教程体量远小于 Phaser，AI 对 KAPLAY（而非 Kaboom）的语料较少，容易生成 Kaboom 旧 API；③`.js`（非 `.min`）路径的 dist 我在 CDN 上直接拿到的是可用的全量文件，但官方产物命名/结构会变，打包时请以 `npm view kaplay dist` 为准。
- **excaliburjs/Excalibur（2,356★ BSD-2-Clause）**
  - 可复用：TypeScript 一等公民，类型体验最好；有官方 Vite 模板；体积中档（实测 raw 321.8 KB / gzip 78.5 KB）。
  - 坑：BSD-2-Clause 要求保留版权声明（内联进单文件后**版权头必须保留**，不要用压缩器剥掉 license banner）；社区规模小于 Phaser。
- **melonjs/melonJS（6,414★ MIT）**
  - 可复用：成熟稳定、体积中档（实测 raw 326.1 KB / gzip 96.1 KB）、有 Vite+TS 模板；2026-10-20 仍在 push。
  - 坑：官方旧模板多已归档（`boilerplate`、`examples` 均 archived），**只跟 `typescript-boilerplate`**；中文资料少。
- **mrdoob/three.js（116,640★ MIT）**
  - 可复用：如果做 3D 就是它；2026-10-20 push，生态最大。
  - 坑：**three 现在拆成两个文件** —— 实测 `build/three.core.min.js` 406.1 KB + `build/three.module.min.js` 383.6 KB，打包器会把两者都并入（≈790 KB raw，≈190 KB gzip）。别只按 `three.module.min.js` 估体积。轻休闲用 3D 收益极低，与"不需要复杂美术"直接冲突。
- **BabylonJS/Babylon.js（26,197★ Apache-2.0）**
  - 可复用：功能最全（物理/GUI/编辑器/导出器）。
  - 坑：**实测 npm 包内 `babylon.js` = 7,716 KB raw / 1,591 KB gzip**。对"单文件 + 手机打开"是灾难级。除非做 3D 重度场景，直接排除。
- **playcanvas/engine（17,090★ MIT）**
  - 可复用：`playcanvas/editor`（1,345★ MIT）是**开源浏览器可视化编辑器**，MIT 很干净。
  - 坑：定位偏 3D/WebGPU/XR，编辑器导出物是多文件资源包，与"单 HTML 文件"目标冲突。
- **cocos/cocos-engine（9,867★，license = NOASSERTION）、cocos/cocos4（1,499★ MIT）**
  - 可复用：国内生态、Cocos Creator 对 H5 支持成熟。
  - 坑：①**`cocos/cocos-engine` 的 license 字段被 GitHub 识别为 NOASSERTION**（不是干净的 SPDX 标识），**商用前必须人工读 LICENSE 文件**；②Creator 编辑器本身闭源，产物是 `assets/` + `index.html` 多文件，**要变成单文件交付需要额外工作**；③构建链重，不适合 1–3 周单人项目。
- **layabox/LayaAir（2,219★ MIT）+ layabox/layaair-skills（13★ MIT）**
  - 可复用：引擎 MIT、有 AI agent 技能包；国内小游戏生态好。
  - 坑：引擎与 IDE 的边界要自己分清楚（`LayaAir` 是引擎，`layaair-ide-*` 多为无 license 的旧仓库）；同样是多文件产物。
- **4ian/GDevelop（27,747★，license = NOASSERTION）**
  - 可复用：可视化编辑器 + 事件系统，非程序员也能做关卡；能导 Web。
  - 坑：①license 为 NOASSERTION，**核心是 MIT 但含多许可组件，商用前必须读 LICENSE**；②导出物是 Web 包（多文件），且用编辑器就等于放弃"让 AI 直接写代码"这条主线；③对"50 关批量生成"没有帮助（关卡仍靠手拖）。
- **processing/p5.js（24,148★ LGPL-2.1）**
  - 可复用：极简、适合小游戏原型。
  - 坑：**LGPL-2.1**。对 JS 动态链接通常没传染问题，但它是全场唯一 LGPL 引擎，会给"闭源/IAA 商用"增加一份法律审查成本；p5 的 sketch 模式（每帧重绘全部）对网格类游戏不是最优。
- **KilledByAPixel/LittleJS（4,307★ MIT）**
  - 可复用：**零依赖**单文件引擎，自带 tween、粒子、音频（同作者的 ZzFX）、2D 甚至 3D；一个 `<script>` 就能起，天然适合单文件交付；作者同时维护 ZzFX（804★ MIT），音效方案统一。
  - 坑：实测 `dist/littlejs.min.js` = **476.8 KB raw / 147.0 KB gzip**，比 KAPLAY 大一档（因为它把 3D、插件都打进同一产物）；中文资料极少，AI 语料也少。
- **IceCreamYou/HTML5-Canvas-Game-Boilerplate（263★，license = NOASSERTION）**
  - 可复用：给"游戏状态循环 + 输入 + 渲染"一套默认骨架，适合当零依赖起点的参考。
  - 坑：**API 没返回 license**，直接复制代码有风险；建议只读思路、自己写。
- **herebefrogs/gamejam-boilerplate（48★ MIT）**
  - 可复用：MIT 干净、体量小、含键盘/鼠标/触摸输入脚手架，适合 game jam 式起步。
  - 坑：星数低、维护弱（2026-09-20 最后一次 push），当模板用可以，别当依赖。
- **gamedev-skills/awesome-gamedev-agent-skills（1,739★ Apache-2.0）** / **majidmanzarpour/threejs-game-skills（2,546★ MIT）**
  - 可复用：这两条是**给 AI agent 的"游戏开发技能包"**——把引擎最佳实践喂给 AI，减少 AI 生成跑偏代码的概率。对"AI Native 创作"这个赛题本身也很契合（迭代过程文档可以写这一层）。
  - 坑：技能包内容是 prompt/文档，不是运行时依赖；质量参差，需自己筛。

### 1.3 实测体积（2026-10-20 从 jsDelivr 下载 + gzip -9）

> 这是本文件**最有决策价值的一张表**：单文件交付时，用户双击打开的是**未压缩的 HTML**（文件系统不会帮你 gzip），所以 **raw 列才是"打开就能玩"的成本**，gzip 列只在有 HTTP 服务器时才是传输成本。

| 产物 | raw | gzip -9 | 占比 |
|---|---|---|---|
| Phaser 4 `dist/phaser.min.js` | **1,343.7 KB** | 344.2 KB | 25.6% |
| Phaser 3.90.0 `dist/phaser.min.js` | **1,168.1 KB** | 307.5 KB | 26.3% |
| PixiJS 8 `dist/pixi.min.js` | **821.0 KB** | 231.2 KB | 28.2% |
| Babylon.js 8 包内 `babylon.js` | **7,716.1 KB** | 1,591.5 KB | 20.6% |
| three.js `three.core.min.js` | 406.1 KB | 101.8 KB | 25.1% |
| three.js `three.module.min.js`（依赖 core） | 383.6 KB | 87.7 KB | 22.9% |
| melonJS `dist/melonjs.min.js` | 326.1 KB | 96.1 KB | 29.5% |
| Excalibur `dist/excalibur.min.js` | 321.8 KB | 78.5 KB | 24.4% |
| KAPLAY `dist/kaplay.js` | **184.7 KB** | **68.1 KB** | 36.9% |
| LittleJS `dist/littlejs.min.js` | 476.8 KB | 147.0 KB | 30.8% |
| howler.js `dist/howler.min.js` | 35.3 KB | 9.5 KB | 26.8% |
| Tone.js `build/Tone.js` | 337.4 KB | 77.4 KB | 22.9% |
| localForage `dist/localforage.min.js` | 29.0 KB | 8.8 KB | 30.5% |
| matter-js `build/matter.min.js` | 81.5 KB | 25.3 KB | 31.0% |
| **零依赖 Canvas 2D** | **0** | 0 | — |

CSV/JSON 原始记录：`.scratch/sizetest/sizes.json`（同目录还有下载下来的 `.js` 文件，可复核）。

**怎么读这张表**
- **Phaser inlined ≈ 1.25 MB 的 HTML 文件**：手机浏览器解析 1.3 MB JS 通常多花 **100–300 ms 首帧时间（估算，未实测）**，可接受但不免费；用 `file://` 传阅（微信/QQ 发文件）时也是 1.3 MB。
- **KAPLAY inlined ≈ 190 KB**：这是"有引擎"里性价比最高的一档；另外它 raw/gzip 比最低（36.9%），意味着压缩收益最小 —— 即**必须把压缩后的 68 KB 当成"服务器场景"数字，`file://` 打开仍是 185 KB**。
- **零依赖**：单文件体积完全由你自己决定。50 关网格游戏的全部代码 + 关卡数据（JSON）通常落在 **40–150 KB raw**，比最小的引擎方案还小 2–4 倍。
- 内联图片/音频会以 base64 膨胀 ~33%（见 §6.2 的压缩换算）。

### 1.4 针对"50 关轻休闲 + 移动端触摸 + 单文件交付"的推荐

**结论：首选零依赖 Canvas 2D，按需升到 KAPLAY / LittleJS，Phaser 3 只作为"想要最多 AI 语料"的备选。**

判断依据（逐条对应约束）：

1. **玩法本质**：赛题给的品类（数独×扫雷、麻将消除、箭头解谜、堆叠消除、单词、拼图）几乎全是**网格 + 规则 + 状态机**。引擎提供的物理、场景图、资源加载、摄像机基本用不到。
2. **评审权重**：玩法 50% + 关卡 30% + 迭代 20%，**代码质量不计分**。把时间花在"关卡生成器 + 难度曲线"上，回报率远高于选一个"架构更优雅"的引擎。
3. **单文件交付**：raw 体积直接决定"发给评委的文件多大、打开多快"。零依赖方案在这条上碾压。
4. **触摸输入**：无论用不用引擎，都要自己处理这几件事（引擎帮不了多少）：`touch-action: none` 禁止双击缩放/滚动、`pointerdown/pointerup` 统一鼠标与触摸、`<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">`、`env(safe-area-inset-*)` 避开刘海、命中半径放大到 ≥44px、`devicePixelRatio` 缩放 canvas 避免模糊。
5. **什么时候值得上引擎**：出现下列任一需求时，引擎开始回本 —— ①精灵表动画与补间（麻将/消除的掉落、闪烁、缩放）；②粒子与屏幕震动（反馈手感）；③大量动态对象（60+ 同时移动的方块）；④音频统一管理（BGM + 多路 SFX + 音量持久化）。此时优先 **KAPLAY**（68 KB gzip）或 **LittleJS**（147 KB gzip，且自带 ZzFX 音效）。
6. **为什么 Phaser 3 排第三**：它唯一的不可替代优势是 **AI 语料量**（"让 AI 写代码不跑偏"在 AI Native 赛题里是真优势），但代价是 1.17 MB raw。**如果决定用 Phaser，请锁 Phaser 3 + `template-vite-ts`，并在每次 prompt 里写明版本**，否则 AI 会混用 3/4 的 API。
7. **明确排除**：Babylon（7.5 MB）、three.js（3D，≈790 KB 双文件）、Cocos/LayaAir/GDevelop（编辑器重、产物多文件、license 有 NOASSERTION 风险）、p5.js（LGPL + 重绘模型）。

---

## 2. AI 原生游戏生成 / LLM-in-the-loop

### 2.1 事实表

| Repo | ★ | License | 最近 push | 是什么 |
|---|---|---|---|---|
| [wellingfeng/UltraGameStudio](https://github.com/wellingfeng/UltraGameStudio) | 324 | MIT | 2026-10-11 | 游戏开发 AI coding agent：引擎工作流 + 资产生成 + 多 provider 路由 |
| [acatovic/ai-game-studio](https://github.com/acatovic/ai-game-studio) | 174 | MIT | **2026-10-20** | "Wombo"：文生角色四视图 + 动画 + 音效，产出 PNG/Aseprite |
| [Anil-matcha/awesome-ai-game-generation](https://github.com/Anil-matcha/awesome-ai-game-generation) | 52 | NOASSERTION | 2026-09-02 | AI 生成游戏的工具/模型/论文清单（含 world model） |
| [lappemic/awesome-ai-built-games](https://github.com/lappemic/awesome-ai-built-games) | 93 | CC0-1.0 | 2026-10-17 | **"vibe-coded 且现在就能玩"的游戏清单**（含引擎与工具署名） |
| [bowen-aigame/awesome-ai-game](https://github.com/bowen-aigame/awesome-ai-game) | 111 | MIT | 2026-06-13 | "AI 驱动玩法本身"的游戏合集（NPC/生成世界） |
| [Eurekaleo/awesome-ai-for-games](https://github.com/Eurekaleo/awesome-ai-for-games) | 397 | MIT | 2026-10-20 | AI × 游戏的研究合集（可检索） |
| [simoninithomas/awesome-ai-tools-for-game-dev](https://github.com/simoninithomas/awesome-ai-tools-for-game-dev) | 1,056 | CC0-1.0 | 2024-11-19 | AI 游戏开发工具清单（2024 年停更，偏历史） |
| [Donchitos/Claude-Code-Game-Studios](https://github.com/Donchitos/Claude-Code-Game-Studios) | **26,906** | MIT | 2026-10-19 | 把 Claude Code 变成"游戏工作室"：49 个 agent + 72 个 workflow skill |
| [a16z-infra/ai-town](https://github.com/a16z-infra/ai-town) | 10,672 | MIT | 2026-08-26 | 生成式智能体小镇（可部署 starter kit） |
| [joonspk-research/generative_agents](https://github.com/joonspk-research/generative_agents) | 22,250 | Apache-2.0 | 2024-08-05 | 《Generative Agents》论文官方实现 |
| [MineDojo/Voyager](https://github.com/MineDojo/Voyager) | 7,273 | MIT | 2024-04-03 | LLM 驱动的开放式 embodied agent（Minecraft） |
| [git-cloner/ai-town](https://github.com/git-cloner/ai-town) | 42 | MIT | 2024-01-03 | 用 GPT + **Phaser3** 做的 AI town 变体 |
| [Innate-Labs/Noobi.ai](https://github.com/Innate-Labs/Noobi.ai) | 251 | - | 2026-09-26 | **本地优先**：把一句 prompt 变成"经过审查的可玩浏览器游戏" |
| [tettethu/VibeGame](https://github.com/tettethu/VibeGame) | 275 | Apache-2.0 | 2026-10-13 | 自演化多 agent 游戏生成框架 |
| [ByteTitan-star/GameForge-Copilot](https://github.com/ByteTitan-star/GameForge-Copilot) | 68 | MIT | 2026-10-11 | 浏览器里的"AI 游戏工作室" |
| [zenstory-ai/novel-to-game](https://github.com/zenstory-ai/novel-to-game) | 897 | MIT | 2026-10-19 | 小说 → 游戏的 agent 技能（题材改编） |
| [JiangZehua/AgenticPCG](https://github.com/JiangZehua/AgenticPCG) | 21 | MIT | 2026-07-11 | **用工具调用型 LLM 做程序化内容生成（PCG）** |
| [seehiong/prompt-to-puzzle](https://github.com/seehiong/prompt-to-puzzle) | 54 | - | 2025-09-13 | 一句 prompt 生成"找不同"可玩游戏（§3/§5 详述） |
| [ahreinhardt/verification-gates](https://github.com/ahreinhardt/verification-gates) | 0 | MIT | 2026-08-19 | 对 LLM 生成/程序化内容做确定性校验闸门 |
| [dungnotnull/game-balancing-difficulty-optimizer](https://github.com/dungnotnull/game-balancing-difficulty-optimizer) | 4 | MIT | 2026-06-29 | 独立游戏难度/数值调优引擎 |
| [DolbyUUU/Sudoku4LLM](https://github.com/DolbyUUU/Sudoku4LLM) | 11 | - | 2025-04-28 | 用数独数据集评测/训练 LLM 的生成器 |

### 2.2 架构套路：预生成 vs 运行时调用（本赛题最关键的一张决策表）

把清单里的项目按"LLM 在哪一步介入"分类，可以直接抄它们的取舍：

| 套路 | 代表项目（证据） | 优点 | 缺点 | 对本比赛的适用性 |
|---|---|---|---|---|
| **A. 设计时预生成（build-time）**：LLM 在开发阶段生成关卡/文案/代码，产物固化成 JSON/常量嵌进包 | 赛题原文"AI 帮你批量生成关卡，你负责设计规则和难度曲线"；`AgenticPCG`（工具调用型 LLM 做 PCG，21★ MIT） | 零运行时依赖、零延迟、可离线、可 review、可版本控制、**单文件可行** | 内容量受"开发期工作量"限制 | **★ 强烈推荐**：50 关完全够用 |
| **B. 运行时 AI 生成 + 确定性代码校验**：AI 出素材，普通代码算答案 | **`seehiong/prompt-to-puzzle`**：Imagen 4 出底图 → Gemini 2.5 Flash Image 做"细微改动" → **差异用浏览器 Canvas 数学比对算出来**（README 原文：避免再一次 AI 调用带来的成本与延迟） | 无限内容、AI 只做它擅长的部分、答案由代码保证正确 | 需要 API key + 网络 + 存储后端（该项目还要 Appwrite） | **思路可抄，形态不可抄**：把"AI 生成 + 确定性校验"降级为设计时流程 |
| **C. 运行时 AI 驱动玩法（NPC/世界）**：LLM 每次交互都调用 | `a16z-infra/ai-town`（PixiJS 前端 + **Convex** 后端做状态/事务/向量检索，LLM 走 Ollama/OpenAI/Together，用 embedding 做记忆检索，靠 Convex query 缓存） | 涌现式体验 | **必须后端 + API key**，无缓存就烧 token、有延迟 | **本比赛不要做**：破坏"单文件、打开就能玩" |
| **D. Agent 工程化（不是运行时）**：用多 agent/技能包把"做游戏"流程化 | `Donchitos/Claude-Code-Game-Studios`（26,906★ MIT，49 agents + 72 skills）、`wellingfeng/UltraGameStudio`（40+ 专家角色；README 列出 6 种策略：classify-and-act / fan-out-and-synthesize / **adversarial-verification** / generate-and-filter / tournament / loop-until-done）、`gamedev-skills/awesome-gamedev-agent-skills` | 直接提升"迭代打磨"那 20% 的过程分，还能写进迭代文档 | 与游戏本体无关，属于方法论 | **★ 推荐**：这是本赛题"AI Native"叙事的现成弹药 |
| **E. 生成即校验的闸门** | `ahreinhardt/verification-gates`（0★ MIT，仅作概念参考）、`Innate-Labs/Noobi.ai`（251★，prompt → **经过审查**的可玩浏览器游戏） | 把"AI 生成不可信"变成工程流程 | 星数低/不成熟 | 概念推荐，代码别依赖 |

**缓存与降级（若要碰运行时 LLM，最小实现）**
1. **内容哈希缓存**：`key = sha256(prompt + model + params)`，命中即回放，写进 `localStorage`（容量 ~5 MB）或 `IndexedDB`。
2. **降级链**：`远端 LLM → 本地缓存 → 预生成的兜底关卡`。**最后一级必须是"永远能玩"**——这是单文件游戏的底线。
3. **超时即回退**：给运行时调用设 1.5–3 s 硬超时，超时直接用兜底内容，别让玩家看转圈。
4. **别把 API key 放进 H5**：单文件里的任何字符串都是公开的。若真要运行时调用，用你自己的中转服务（那就不是"host-free"了）。

### 2.3 本比赛到底该在哪用 LLM（结论）

| 阶段 | 用法 | 是否需要运行时 |
|---|---|---|
| 玩法设计 | 让 AI 批量提"两个成熟元素融合"的组合方案（对齐 Meowdoku 范式） | 否 |
| 关卡生成 | **脚本 + 求解器**批量产出并校验（§3），LLM 只负责给关卡起名/写提示语/生成语义标签 | 否 |
| 难度曲线 | 用求解器指标（给定格数、回溯次数、解空间大小）做量化分档；LLM 做"曲线是否单调递进"的 review | 否 |
| 代码实现 | 与 AI 迭代式写码（这是 100M token 的主要去向） | 否 |
| 素材 | 设计时生成一批图标/背景/音效，内联进包（§4） | 否 |
| 迭代留痕 | 用 C/D 类 agent 工作流，把每轮"做→测→改"记录成迭代文档 | 否 |

---

## 3. 关卡/谜题生成器 + 求解器（按评委品类优先级排）

> 这是本文件**复用价值最高**的一节。评委口味来自主办方代表作：数独、扫雷、麻将消除、堆叠消除、箭头解谜、单词、拼图、填色、纸牌。

### 3.0 能力总览：先看"三件套"齐不齐

三件套 = ①批量生成 ②保证可解（求解器校验）③难度分级。

| 品类（对应主办方作品） | 开源方案现状 | 三件套齐否 | 结论 |
|---|---|---|---|
| **数独**（Sudoku / Meowdoku） | 成熟，多语言多实现 | ✅ 生成+求解+难度（README 证据） | **直接复用** |
| **扫雷**（Meowdoku 的融合元素） | 求解器多；**带"无猜(no-guess)"保证的生成器很少** | ⚠️ 生成弱 | 求解器复用，生成器自己写（规则简单） |
| **数织/Nonogram** | 有 JS 库与多种求解器 | ✅ 生成+求解（README/desc） | 可复用 |
| **逻辑网格/数独变体/填字** | OR-Tools CP-SAT 求解器集（puzzlekit） | ⚠️ 求解强、生成弱 | 求解器复用 |
| **推箱子 Sokoban** | 多个小型生成器，license 多为空 | ⚠️ 生成+求解有、难度分级无 | 参考实现 |
| **迷宫 Maze** | 非常成熟 | ✅ 生成+求解+难度（按尺寸/分支） | 直接复用 |
| **Flow Free / Numberlink** | 有生成+求解，但 **AGPL** | ✅ 但许可有坑 | 评估许可或自研 |
| **箭头解谜**（Amaze Go!） | 极小众，最高 102★；**有一个专门的关卡生成器但无 license** | ❌ 基本靠自己 | 自研（规则简单，收益高） |
| **堆叠消除 / 三消 / 麻将配对**（Tile Explorer / Vita Mahjong） | **没有成熟生成器**，最高星候选个位数 | ❌ | **必须自研**（§3.3 给方案） |
| **找不同** | 只有 AI 生成型项目，无纯算法生成器 | ❌ | 自研或 AI 生成 + Canvas 校验（抄 prompt-to-puzzle） |
| **拼图 Jigsaw** | 有生成器（切图），最大 290★ 但无 license | ⚠️ | 用 MIT 的替代 |
| **单词/Word Search/填字** | 成熟 | ✅ 生成+难度（按网格尺寸/词长） | 可复用 |
| **水管/冰面滑动/华容道类** | 零散小项目 | ⚠️ | 参考 |

### 3.1 事实表（★/license/push 均来自 API，2026-10-20）

**数独 Sudoku**

| Repo | ★ | License | push | 生成 | 求解 | 难度分级 | 证据 |
|---|---|---|---|---|---|---|---|
| [robatron/sudoku.js](https://github.com/robatron/sudoku.js) | 498 | MIT | 2025-12-17 | ✅ | ✅ | ✅ | `README`：`generate("easy"/"medium"/"hard")`，难度=给定格数，可传数字（如 60） |
| [t-dillon/tdoku](https://github.com/t-dillon/tdoku) | 284 | BSD-2-Clause | 2024-07-16 | ✅ | ✅ | ⚠️ | `desc`："fast solver and generator with a benchmark suite" |
| [MorvanZhou/sudoku](https://github.com/MorvanZhou/sudoku) | 184 | MIT | 2026-07-18 | ✅ | ✅ | ⚠️ | `desc`：数独生成器和解题器（Python） |
| [dachev/sudoku](https://github.com/dachev/sudoku) | 157 | **-** | 2026-08-24 | ✅ | ✅ | ⚠️ | `desc`：node.js 生成器+求解器；**无 license** |
| [stephenostermiller/qqwing](https://github.com/stephenostermiller/qqwing) | 144 | **-** | 2023-01-27 | ✅ | ✅ | ✅ | `desc`：经典生成器+求解器（C++）；**无 license** |
| [RutledgePaulV/sudoku-generator](https://github.com/RutledgePaulV/sudoku-generator) | 130 | MIT | 2020-11-27 | ✅ | ✅ | ✅ | `desc`："varying difficulties"；**已归档** |
| [JoeKarlsson/python-sudoku-generator-solver](https://github.com/JoeKarlsson/python-sudoku-generator-solver) | 95 | MIT | 2026-09-15 | ✅ | ✅ | ✅ | `desc`：可生成唯一解、多难度；**已归档** |
| [einaregilsson/sudoku.js](https://github.com/einaregilsson/sudoku.js) | 26 | MIT | 2021-01-06 | ⚠️ | ✅ | ❌ | `desc`：基于 Norvig 的求解器 |

**扫雷 Minesweeper**

| Repo | ★ | License | push | 说明 | 证据 |
|---|---|---|---|---|---|
| [lucky-bai/MSolver](https://github.com/lucky-bai/MSolver) | 193 | MIT | 2016-11-22 | 自包含求解器（Java） | `desc` |
| [DavidNHill/JSMinesweeper](https://github.com/DavidNHill/JSMinesweeper) | 176 | MIT | 2026-10-04 | **JS 求解器 + 分析器**（活跃，最新） | `desc`："player, solver and analyser in javascript" |
| [haveaLukeatthis/SelfSolvingMinesweeper](https://github.com/haveaLukeatthis/SelfSolvingMinesweeper) | 89 | MIT | 2023-02-18 | 自解扫雷（Python） | `desc` |
| [mrgriscom/minesweepr](https://github.com/mrgriscom/minesweepr) | 74 | Apache-2.0 | 2021-09-19 | 求解器 + **HTML5 客户端** | `desc` |
| [Minesweepervariants-Fanmade/MinesweeperVariants](https://github.com/Minesweepervariants-Fanmade/MinesweeperVariants) | 13 | GPL-3.0 | 2026-10-14 | **变体生成器 + 游戏（14mv）** | `desc` |

**数织/Nonogram**

| Repo | ★ | License | push | 说明 |
|---|---|---|---|---|
| [HandsomeOne/Nonogram](https://github.com/HandsomeOne/Nonogram) | 152 | MIT | 2020-05-01 | 编辑器 + 游玩（非生成器） |
| [Izaron/Nonograms](https://github.com/Izaron/Nonograms) | 62 | MIT | 2018-08-07 | **求解器 + 生成器**（README/desc 称 very fast） |
| [monkeyArms/nonogram](https://github.com/monkeyArms/nonogram) | 54 | MIT | 2023-01-04 | **JS 小库：create/solve/play** |
| [tsionyx/nonogrid](https://github.com/tsionyx/nonogrid) | 34 | MIT | 2021-11-22 | 极快求解器 + **网页版** |
| [ThomasR/nonogram-solver](https://github.com/ThomasR/nonogram-solver) | 30 | Apache-2.0 | 2021-08-24 | 求解/格式化 |

**通用逻辑谜题求解（CP-SAT）**

| Repo | ★ | License | push | 说明 |
|---|---|---|---|---|
| [SmilingWayne/puzzlekit](https://github.com/SmilingWayne/puzzlekit) | 36 | MIT | 2026-07-30 | **100+ 逻辑谜题求解器（Google OR-Tools CP-SAT）+ 41k+ 实例数据集（130+ 题型）**，含 Nonogram/Slitherlink/Akari/Fillomino/Hitori/Kakuro/数独变体。阅读 README 后确认：**它是"求解器 + 数据集"，README 未提到生成器，也未提难度标签** → 用它做**校验**和**难度标定**，不要指望它生成 |
| [tuchandra/zebra](https://github.com/tuchandra/zebra) | 33 | MIT | 2024-03-01 | 逻辑网格（斑马题）**生成器 + 求解器** |
| [kairess/pane-by-pane](https://github.com/kairess/pane-by-pane) | 7 | NOASSERTION | 2026-09-22 | `desc` 称"puzzle engine（generator, logical solver…）"——**最贴近"生成+求解+难度"三件套，但星数极低且 license 不明** |

**迷宫 / 字谜 / 逻辑**

| Repo | ★ | License | push | 说明 |
|---|---|---|---|---|
| [jostbr/pymaze](https://github.com/jostbr/pymaze) | 300 | MIT | 2024-04-01 | 生成 + 求解 + 可视化（Python） |
| [keesiemeijer/maze-generator](https://github.com/keesiemeijer/maze-generator) | 159 | MIT | 2025-03-18 | JS 递归回溯迷宫生成 |
| [codebox/mazes](https://github.com/codebox/mazes) | 135 | MIT | 2026-07-05 | JS 迷宫生成 |
| [joshbduncan/word-search-generator](https://github.com/joshbduncan/word-search-generator) | 116 | MIT | 2026-04-11 | 字谜（word search）生成器，支持难度参数 |
| [Magoninho/word-search-puzzle-generator](https://github.com/Magoninho/word-search-puzzle-generator) | 29 | MIT | 2023-06-20 | 简单字谜生成（Python） |
| [thomasahle/numberlink](https://github.com/thomasahle/numberlink) | 110 | **AGPL-3.0** | 2026-01-26 | Flow Free / Numberlink **生成 + 求解**；**AGPL 是商用风险点** |
| [madhav-datt/number-link-gameboard](https://github.com/madhav-datt/number-link-gameboard) | 1 | NOASSERTION | 2016-01-14 | 棋盘 + 解生成（太小，仅参考） |

**推箱子 / 滑动 / 华容道 / 箭头**

| Repo | ★ | License | push | 说明 |
|---|---|---|---|---|
| [mpSchrader/gym-sokoban](https://github.com/mpSchrader/gym-sokoban) | 409 | MIT | 2023-11-08 | Gym 环境（含大量现成关卡，可直接当关卡库） |
| [AlliBalliBaba/Sokoban-Level-Generator](https://github.com/AlliBalliBaba/Sokoban-Level-Generator) | 60 | **-** | 2019-11-05 | 随机关卡生成器；无 license |
| [miki151/sokoban](https://github.com/miki151/sokoban) | 40 | **-** | 2017-04-07 | 随机关卡生成；无 license |
| [xbandrade/sokoban-solver-generator](https://github.com/xbandrade/sokoban-solver-generator) | 22 | MIT | 2023-11-12 | **生成 + 求解（BFS/A*/Dijkstra）** |
| [sidhant947/ArrowEscape](https://github.com/sidhant947/ArrowEscape) | 102 | GPL-3.0 | 2026-10-13 | **箭头解谜完整游戏**（Amaze Go! 同品类） |
| [PanAkatsuki/ArrowsPuzzleEscape-LevelGenerator](https://github.com/PanAkatsuki/ArrowsPuzzleEscape-LevelGenerator) | 11 | **-** | 2025-10-16 | **箭头关卡生成器**（同品类，直接对口；无 license） |
| [sergev/goarrows](https://github.com/sergev/goarrows) | 10 | MIT | 2026-05-30 | "Arrows – Puzzle Escape" 的 MIT 克隆 |
| [ttsiodras/UnblockMeSolver](https://github.com/ttsiodras/UnblockMeSolver) | 29 | **-** | 2021-02-24 | 华容道/Rush Hour 自动求解 |
| [Unknowncmbk/unblock-me-generator](https://github.com/Unknowncmbk/unblock-me-generator) | 10 | **-** | 2017-08-05 | **CSP 生成华容道谜题** |
| [benletchford/prisoner](https://github.com/benletchford/prisoner) | 5 | MIT | 2016-06-12 | Rush Hour **表示/求解/生成**三合一（MIT） |
| [hkociemba/WaterBallSortPuzzleOptimalSolver](https://github.com/hkociemba/WaterBallSortPuzzleOptimalSolver) | 41 | **-** | 2022-05-24 | 水排序**最优解**求解器 |
| [sidhant947/water-sort](https://github.com/sidhant947/water-sort) | 85 | GPL-3.0 | 2026-10-16 | 水排序游戏 |
| [kuking/WaterSortPuzzleSolver](https://github.com/kuking/WaterSortPuzzleSolver) | 24 | MIT | 2023-08-18 | 水排序求解器（MIT） |

**消除 / 匹配 / 麻将 / 拼图 / 找不同（评委核心品类，开源最薄弱）**

| Repo | ★ | License | push | 说明 | 缺口 |
|---|---|---|---|---|---|
| [LibraStack/Match3-SDK](https://github.com/LibraStack/Match3-SDK) | 561 | MIT | 2024-06-10 | 三消 SDK（C#） | 非 JS |
| [chenxch/xlegex](https://github.com/chenxch/xlegex) | 257 | MIT | 2023-02-10 | **"简化版羊了个羊"堆叠消除模板** | 没有关卡生成器 |
| [igorhosantos/Match3-Engine](https://github.com/igorhosantos/Match3-Engine) | 1 | **-** | 2026-08-26 | 简单三消棋盘生成 + 匹配检测 | 星数 1，不可依赖 |
| [sasverdlov/my_secret_candy_crush](https://github.com/sasverdlov/my_secret_candy_crush) | 1 | **-** | 2022-11-06 | 三消生成器 + 求解器 | 星数 1 |
| [Alexviolent/FishBallMahjong](https://github.com/alexviolent/FishBallMahjong) | 40 | Apache-2.0 | 2020-09-14 | 开源 H5 **福州麻将**（四人麻将，非消除类） | 品类不同 |
| [Pomax/mahjong](https://github.com/Pomax/mahjong) | 115 | **-** | 2023-07-24 | "Proper mahjong" 规则引擎 | **不是连连看/上海麻将** |
| [danbeck/green-mahjong](https://github.com/danbeck/green-mahjong) | 105 | **-** | 2026-07-12 | 单人纸牌麻将（多主题/布局），Android | 无 license，非 Web |
| [Draradech/jigsaw](https://github.com/Draradech/jigsaw) | 290 | **-** | 2022-12-14 | **拼图切图生成器**（最流行的那个） | **无 license** |
| [proceduraljigsaw/Fractalpuzzlejs](https://github.com/proceduraljigsaw/Fractalpuzzlejs) | 29 | MIT | 2021-11-07 | **JS 圆形/分形拼图生成器**（MIT，可替代上面那个） | 功能较窄 |
| [proceduraljigsaw/CircleGridPuzzle](https://github.com/proceduraljigsaw/CircleGridPuzzle) | 9 | MIT | 2020-12-28 | 分形拼图生成（Python） | — |
| [nemanja-m/gaps](https://github.com/nemanja-m/gaps) | 772 | MIT | 2026-09-20 | 遗传算法**拼图求解器**（用于难度标定/自动校验） | 求解非生成 |
| [Kawaboongawa/Zolver](https://github.com/Kawaboongawa/Zolver) | 209 | MIT | 2025-10-02 | 自动拼图求解 | 同上 |
| [shamim-akhtar/jigsaw-puzzle](https://github.com/shamim-akhtar/jigsaw-puzzle) | 133 | **-** | 2025-12-28 | 完整 Unity 拼图游戏 | Unity，非 H5 |
| [darkstornmetu/BlockPuzzleLevelEditor](https://github.com/darkstornmetu/BlockPuzzleLevelEditor) | 33 | MIT | 2025-03-13 | **方块拼图关卡编辑器**（设计思路可抄） | Unity 编辑器工具 |
| [seehiong/prompt-to-puzzle](https://github.com/seehiong/prompt-to-puzzle) | 54 | **-** | 2025-09-13 | AI 生成找不同 + Canvas 校验（§2.2 套路 B） | 需 API key + Appwrite |
| [jhsdw123/spot-difference-studio](https://github.com/jhsdw123/spot-difference-studio) | 0 | **-** | 2026-07-06 | 可打印找不同生成器 | 星数 0 |

**难度评估 / 数据集**

| Repo | ★ | License | push | 说明 |
|---|---|---|---|---|
| [SmilingWayne/puzzlekit](https://github.com/SmilingWayne/puzzlekit) | 36 | MIT | 2026-07-30 | 求解器集 + **41k+ 带解实例**，可当作"难度基准数据集" |
| [DolbyUUU/Sudoku4LLM](https://github.com/DolbyUUU/Sudoku4LLM) | 11 | **-** | 2025-04-28 | 面向 LLM 的数独数据集生成器（可用于校准"LLM 觉得哪档难"） |
| [dungnotnull/game-balancing-difficulty-optimizer](https://github.com/dungnotnull/game-balancing-difficulty-optimizer) | 4 | MIT | 2026-06-29 | 难度/数值调优引擎（概念参考） |
| [synnwang/sudoku_dataset_difficulty](https://github.com/synnwang/sudoku_dataset_difficulty) | 5 | CC0-1.0 | 2025-10-26 | 带**人类实测难度**的数独数据集 |

### 3.2 结论：开源能给你什么，给不了什么

**能给（直接复用）**
1. **数独**：`robatron/sudoku.js`（MIT，JS）一站式生成+求解+三档难度 → 这是**最快能凑出 50 关**的品类。若要做 Meowdoku 那种"数独×扫雷"融合，还需自己写一层掩码/雷区逻辑。
2. **迷宫 / 字谜 / 数织**：都有 MIT 且活跃的实现（`pymaze`、`word-search-generator`、`monkeyArms/nonogram`）。
3. **校验与难度标定**：用 `puzzlekit`（CP-SAT 求解器集）或专门的求解器（`tdoku`、`JSMinesweeper`、`gaps`）来**证明每一关可解**，并把"求解耗时/回溯次数"当难度指标。这是把"难度曲线"从感觉变成数字的关键。

**给不了（必须自研，且这是拿分点）**
1. **三消 / 堆叠消除 / 麻将配对的关卡生成器：开源空缺**。搜索 `match3 generator`、`triple tile`、`matching puzzle generator`、`tile stacking` 四个方向，最高星候选仅 1★ 级。**这个空缺正好是"50 关"赛题的核心工作量**。
2. **扫雷"无猜"生成器**：求解器不少，但保证"纯逻辑可解、无需猜"的生成器很少见。
3. **箭头解谜生成器**：仅 `PanAkatsuki/ArrowsPuzzleEscape-LevelGenerator`（11★，无 license）一条线索。
4. **找不同生成器**：只有 AI 生成路线。
5. **"难度分级"的通用方案**：除了数独，多数品类的难度只能自己定义指标。

### 3.3 本比赛最可能复用的 5 条流水线（可直接开工）

> 统一骨架：**生成器（随机/构造）→ 求解器（证明可解）→ 指标（给难度打分）→ 分档 → 人工抽检 → 固化成 JSON**。全流程在 Node/Python 里跑，产物嵌进 H5。

1. **数独系（Meowdoku 向）**：`robatron/sudoku.js` 生成 + 求解 → 难度=给定格数/回溯次数 → 50 关按 [30..45 给定] 递进。融合创新点加在"掩码/雷区"层，不改数独内核。
2. **消除系（三消/堆叠/麻将配对）**：自研。推荐做法 —— **反向生成**：先随机铺满，再用求解器"倒着消"直到清空，把消除顺序反过来就得到一个**保证可解**的关卡与解序列（这是消除类关卡生成的标准技巧；本清单里没有现成库，只能自己实现）。难度指标 = 颜色种类数 / 步数限制 / 死局率。
3. **箭头解谜系（Amaze Go! 向）**：自研。棋盘 + 方向块，用 BFS **反向从"空棋盘"回推**加水箭，生成必然可解的盘面；难度 = 最少步数（BFS 距离）+ 分支数。
4. **推箱子系**：抄 `xbandrade/sokoban-solver-generator`（MIT）的"生成后用 A* 验证"结构，或直接用 `gym-sokoban` 的现成关卡做 50 关素材。
5. **单词/字谜系（Zen Word 向）**：`joshbduncan/word-search-generator`（MIT）生成字谜；或用词表 + 模板出题，难度 = 词长/网格尺寸/干扰词数。

### 3.4 用 LLM 做"难度曲线编排 / 关卡语义标签"的开源做法

> 直接说结论：**没有成熟的开源项目专门做这件事**。搜索 `level direficulty curve`、`llm level design`、`difficulty rating puzzle` 三个方向，返回的全部是 <5★ 的玩具项目或无关仓库。可抄的是**套路**而不是代码：

| 环节 | 可抄的项目/做法 | 具体怎么用 |
|---|---|---|
| LLM 做 PCG | [JiangZehua/AgenticPCG](https://github.com/JiangZehua/AgenticPCG)（21★ MIT）：**工具调用型 LLM 做程序化生成** | 让 LLM 不直接"写关卡"，而是**调用你的生成器 + 求解器工具**（给参数：尺寸/难度/主题），拿求解器返回的可解性作为反馈循环 —— 这正是"LLM 编排 + 确定性校验" |
| 生成后确定性校验 | [ahreinhardt/verification-gates](https://github.com/ahreinhardt/verification-gates)（MIT，0★，概念参考） | 每个关卡过闸门：可解？解唯一？步数在预期区间？不满足就打回重生成 |
| 难度标签 | [synnwang/sudoku_dataset_difficulty](https://github.com/synnwang/sudoku_dataset_difficulty)（CC0）用**人类实测难度**做标签；[DolbyUUU/Sudoku4LLM](https://github.com/DolbyUUU/Sudoku4LLM) 用 LLM 评测难度 | 两者结合：先用求解器指标做机器分档，再用 LLM/人工给少量关卡打"体感难度"，回归出一张**指标→体感**映射表 |
| 语义标签/关卡命名 | 无开源先例，直接用 LLM API | 给每关生成 `{主题, 一句话提示, 语义标签}`，作为"关卡之间有变化/惊喜"的证据写进设计文档 |
| 曲线 review | 无开源先例 | 把 50 关的指标序列 + 标签丢给 LLM，让它判断"是否单调递进/有无节奏断点/哪几关是惊喜点"——**这是能直接写进迭代文档的过程证据** |
| 数值调优 | [dungnotnull/game-balancing-difficulty-optimizer](https://github.com/dungnotnull/game-balancing-difficulty-optimizer)（MIT，4★） | 概念参考：把难度当优化目标，而非手调 |

**关键提醒**：难度曲线**不要交给 LLM 拍脑袋**。正确顺序是 **求解器给客观指标 → 人工设计曲线形状 → LLM 做文案与 review**。

---

## 4. 轻量 2D 素材 / 音效 / 字体

### 4.0 先说结论

- 赛题明说"**不需要复杂美术和故事**"。所以这一节的目标不是"找好看的图"，而是**用最小成本拿到 CC0/MIT 可商用素材 + 可程序化生成的音效**。
- **首选组合**：**Kenney（CC0）素材 + ZzFX/jsfxr（程序化音效，零素材文件）+ Google Fonts OFL 字体 / ark-pixel-font（MIT）**。这套组合几乎不增加内联体积（音效是代码生成的，不是音频文件）。

### 4.1 素材站点与仓库（许可逐条标注）

| 来源 | License | 证据 | 说明 / 坑 |
|---|---|---|---|
| **[kenney.nl/assets](https://kenney.nl/assets)** | **CC0（Creative Commons CC0）** | **2026-10-20 实抓资产页**：`License Creative Commons CC0`（抽查 [Tiny City](https://kenney.nl/assets/tiny-city)，130 个 16×16 贴图） | 2D/3D/UI/音频/像素全品类；**CC0 = 可商用、可修改、无需署名**。坑：站点底部写 `All rights reserved`（那是站点本身版权，不影响资产 CC0）；单个资产页才有 License 字段，**批量下载前逐页确认**（老包与新包都标 CC0，但以页面为准） |
| [KenneyNL/Starter-Kit-City-Builder](https://github.com/KenneyNL/Starter-Kit-City-Builder) 等 | MIT | API `spdx_id = MIT` | Kenney 的**起步工程**（Godot 等）是 MIT；注意这些是模板不是素材库 |
| [devanshutak25/3d-resources](https://github.com/devanshutak25/3d-resources) | CC0-1.0 | API | 999★，3,400+ 工具/资源索引 |
| [SpriteCook/spritecook-free-game-assets](https://github.com/SpriteCook/spritecook-free-game-assets) | CC0-1.0 | API | 27★，免费 CC0 素材包 |
| [Tiddybub/2d-assets](https://github.com/Tiddybub/2d-assets) | **NOASSERTION** | API | 16★；描述自称"CC0 素材精选"，但**仓库未挂 SPDX 许可** → 逐个素材回源确认 |
| [tabler/tabler-icons](https://github.com/tabler/tabler-icons) | MIT | API | 22,378★，6,200+ SVG 图标，**UI/按钮/提示图标首选** |
| [lucide-icons/lucide](https://github.com/lucide-icons/lucide) | NOASSERTION | API | 25,158★（实际为 ISC，但 API 字段是 NOASSERTION）→ **以内联的 LICENSE 文件为准** |
| [simple-icons/simple-icons](https://github.com/simple-icons/simple-icons) | CC0-1.0 | API | 26,046★，品牌图标（用于"分享"按钮等） |
| [comficker/simplepixelart](https://github.com/comficker/simplepixelart) | MIT | API | 19★，**浏览器像素画编辑器**（自己画素材的兜底方案） |
| [BabylonJS/Assets](https://github.com/BabylonJS/Assets) | CC-BY-4.0 | API | 166★，公共领域数字资产（**CC-BY 需署名**） |

### 4.2 音效与音乐（程序化生成，不占体积）

| Repo | ★ | License | push | 说明 |
|---|---|---|---|---|
| [grumdrig/jsfxr](https://github.com/grumdrig/jsfxr) | 283 | **Unlicense** | 2023-05-04 | sfxr 的 HTML5 移植，**一行代码生成 8-bit 音效**；Unlicense = 公共领域，最宽松 |
| [KilledByAPixel/ZzFX](https://github.com/KilledByAPixel/ZzFX) | 804 | MIT | 2026-10-01 | **微型 JS 音效系统**（同作者=LittleJS 作者），一行 play 调用出音效，**零音频文件** |
| [excaliburjs/excalibur-jsfxr](https://github.com/excaliburjs/excalibur-jsfxr) | 3 | BSD-2-Clause | 2026-10-18 | jsfxr 的 Excalibur 插件（若用 Excalibur 可直接接） |
| [Tonejs/Tone.js](https://github.com/Tonejs/Tone.js) | 14,785 | MIT | 2026-10-17 | Web Audio 框架，做**交互式音乐/BGM**（实测 337.4 KB raw，比 howler 大一个量级） |
| [goldfire/howler.js](https://github.com/goldfire/howler.js) | 25,399 | MIT | 2025-11-23 | 音频播放库（实测仅 35.3 KB raw / 9.5 KB gzip），**多路 SFX + 音量持久化的稳妥选择** |
| [mmontag/chip-player-js](https://github.com/mmontag/chip-player-js) | 501 | GPL-3.0 | 2026-10-15 | 网页 chiptune 播放器（GPL，谨慎） |

**推荐**：**ZzFX 或 jsfxr 生成全部 SFX（点击/匹配/成功/失败/连击），单文件里只有几十行代码，零字节音频资源**；BGM 若必须有，用 Tone.js 的极简包或用 ZzFX 合成短循环。这样"单文件"+ "有音效手感"两个目标同时达成——**这是本文件里性价比最高的一条建议**。

### 4.3 字体

| Repo / 来源 | ★ | License | push | 说明 |
|---|---|---|---|---|
| [TakWolf/ark-pixel-font](https://github.com/TakWolf/ark-pixel-font) | 4,806 | MIT | 2026-10-20 | **开源泛拉丁 + 泛中日韩像素字体**，中文像素字，含简体中文 |
| [TakWolf/fusion-pixel-font](https://github.com/TakWolf/fusion-pixel-font) | 3,362 | MIT | 2026-10-19 | 同作者另一款像素字体 |
| [qwerasd205/PixelCode](https://github.com/qwerasd205/PixelCode) | 502 | **OFL-1.1** | 2026-09-23 | 为编程优化的像素字体（OFL 允许嵌入，**但保留字体名有约束**） |
| [rektdeckard/departure-mono](https://github.com/rektdeckard/departure-mono) | 3,587 | MIT | 2026-09-13 | 等宽像素风字体 |
| [SolidZORO/zpix-pixel-font](https://github.com/SolidZORO/zpix-pixel-font) | 3,081 | **-** | 2026-09-24 | 中文像素字体（**API 无 license，需读仓库 LICENSE 文件**） |
| [wixette/dotted-chinese-fonts](https://github.com/wixette/dotted-chinese-fonts) | 439 | GPL-2.0 | 2022-12-04 | 点点像素中文（**GPL 字体嵌入需谨慎**） |

**坑（字体是单文件交付里最容易翻车的一块）**
1. **中文字体文件巨大**（几 MB），内联进单文件会直接毁掉体积目标。**UI 文案尽量用英文/数字，中文只在必要处使用系统字体**（`system-ui, "PingFang SC", "Microsoft YaHei"`），这样零体积。
2. 若必须内联中文像素字体，用 `pyftsubset`/`fonttools` **子集化到只含用到的字符**（50 关的文案通常 < 500 字，可压到几十 KB）。
3. **OFL 字体**允许嵌入与商用，但**改名分发**有约束；GPL 字体嵌入对闭源分发有风险 → 优先 MIT / CC0 / OFL。
4. **woff2 是唯一值得内联的格式**（比 ttf 小 50%+），用 base64 内联。

### 4.4 商用许可速查（红线）

| License | 本比赛能否用 | 注意 |
|---|---|---|
| CC0 / Unlicense / MIT / BSD / Apache-2.0 | ✅ 可以 | MIT/BSD/Apache 需**保留版权声明**（内联后别被压缩器剥掉） |
| CC-BY | ✅ 可以 | **必须署名**，并在作品内标注 |
| OFL-1.1（字体） | ✅ 可以 | 保留 LICENSE，改名有约束 |
| **GPL / AGPL / LGPL** | ⚠️ 谨慎 | `numberlink`(AGPL)、`water-sort`(GPL-3.0)、`chip-player-js`(GPL-3.0)、`p5.js`(LGPL)、`dotted-chinese-fonts`(GPL-2.0)。**闭源/IAA 产品化前必须法律评估**；最安全的做法是换 MIT 替代或自研 |
| **API 返回 `license: null`** | ⚠️ 高风险 | 约 15 个候选（qqwing、jsfxr 之外的多数、Draradech/jigsaw、Pomax/mahjong、dachev/sudoku、ArrowsPuzzleEscape 等）。**没有许可证 ≠ 免费**，默认按"保留所有权利"处理 |

---

## 5. 已发布的开源 AI 原生浏览器小游戏案例（≥3 个）

### 5.1 案例表

| 案例 | Repo / 地址 | ★ | License | push | 引擎 | 是否浏览器可玩 |
|---|---|---|---|---|---|---|
| **AI Town** | [a16z-infra/ai-town](https://github.com/a16z-infra/ai-town) | 10,672 | MIT | 2026-08-26 | PixiJS | ✅ [在线 Demo](https://www.convex.dev/ai-town) |
| **Tower of Time** | [maciej-trebacz/tower-of-time-game](https://github.com/maciej-trebacz/tower-of-time-game) | 377 | MIT | 2025-07-04 | Three.js | ✅ |
| **vibe-jet** | [cedrickchee/vibe-jet](https://github.com/cedrickchee/vibe-jet) | 71 | MIT | 2025-04-07 | Three.js | ✅ |
| **长风 Long Wind** | [jbang2004/long-wind](https://github.com/jbang2004/long-wind) | 97 | NOASSERTION | 2026-10-13 | Three.js | ✅ |
| **VibeGame** | [tettethu/VibeGame](https://github.com/tettethu/VibeGame) | 275 | Apache-2.0 | 2026-10-13 | 多 agent 框架 | ⚠️ 描述称生成游戏，浏览器产物未实测 |
| **Noobi.ai** | [Innate-Labs/Noobi.ai](https://github.com/Innate-Labs/Noobi.ai) | 251 | - | 2026-09-26 | 本地桌面 agent | ⚠️ 描述称产出可玩浏览器游戏，未实测 |
| **vibe-coded 游戏索引** | [lappemic/awesome-ai-built-games](https://github.com/lappemic/awesome-ai-built-games) | 93 | CC0-1.0 | 2026-10-17 | — | 收录 60+ 款**现在就能玩**的 AI 造浏览器游戏 |
| **Ink Side Down / One Step Late** | [arkai.win/games/ink-side-down](https://arkai.win/games/ink-side-down/) | — | — | — | HTML5 Canvas | ✅ 每日逻辑谜题，**"由自主 AI agent 端到端设计与编码"** |
| **Wildlife** | [wildlife-game.netlify.app](https://wildlife-game.netlify.app/) | — | — | — | — | ✅ 点击同色方块组，25 回合内得分（消除类） |
| **Type Battles** | [typebattles.com](https://www.typebattles.com/) | — | — | — | — | ✅ 10 关 + 最终 boss + 每日挑战（**关卡递进结构可直接抄**） |

> 上表后三行来自 [lappemic/awesome-ai-built-games](https://github.com/lappemic/awesome-ai-built-games) 的目录条目（该文件我读了原文），它们不是 GitHub repo，所以没有 star/license 数据 —— **不要给它们编造 star**。
> 该清单还指向两个正在进行的赛道：[AI Browser Game Jam](https://itch.io/jam/ai-jam-5)（2026-10-17 ~ 10-31，第五届）与 [Vibe Jam](https://vibejam.com/)（2025+2026 累计 2,000+ 参赛作品）——**可作为"同赛道对手都在做什么"的侦察入口**。

### 5.2 逐个架构套路（预生成 vs 运行时 / 缓存 / 降级）

**案例 1：AI Town（10,672★ MIT）→ 典型的"运行时 LLM + 后端"架构**
- **前端**：PixiJS 渲染城镇；**后端**：Convex 提供全局状态、事务、**向量检索**与 simulation engine（README 原文）。
- **LLM**：可配置（本地 Ollama / OpenAI / Together.ai 等），默认 `llama3` + `mxbai-embed-large` 做记忆 embedding。
- **缓存**：依赖 Convex query 的 caching/reactivity 机制；对话与记忆存在后端，玩家端不重复推理。
- **降级**：LLM 不可用时主要靠已存的对话/记忆回放，无"离线可玩"设计。
- **对本比赛的价值**：**反面教材**。它的架构需要后端 + API key + 常驻成本，**与"单个可打开就能玩的 H5"直接冲突**。可以抄的是"**记忆=向量检索**"和"**状态全部走后端事务**"这两个思想，用在你 50 关的进度存档上属于过度设计。

**案例 2：Tower of Time（377★ MIT）/ vibe-jet（71★ MIT）/ 长风（97★）→ "AI 写代码，运行时零 LLM"**
- 三者的共同点：**AI 只参与开发阶段**（vibe coding），产物是**纯静态浏览器游戏**，运行时没有任何 AI 调用、没有后端。
- 降级路径：无 —— 因为它们本来就不依赖外部服务，**这恰恰是"永不失败"的降级**。
- 缓存：不需要。
- **对本比赛的价值**：**正面范式**。它证明了"用 AI 端到端做出可玩浏览器游戏"这条路走得通，而且**静态化才是这类作品能长期存活的原因**。`Tower of Time` 是 game jam 产物（说明几天可交付）；`vibe-jet` 在 README 里明确标注"由 AI 创建"。

**案例 3：Ink Side Down / One Step Late（arkai.win）→ 最适合本比赛的形态**
- 形态：**每日逻辑谜题**，HTML5 Canvas，**由自主 AI agent 端到端设计与编码**（清单原文）。
- 架构套路：极大概率是**离线预生成 + 静态托管**（每日一题只需提前生成题库），运行时零 LLM。
- **可借鉴点**：①60 秒级单局、规则一句话说清；②"每日一题"天然解决内容量问题 —— 而本比赛要求 50 关，等价于"预生成 50 天的每日题"；③纯 Canvas，**没有引擎依赖**，与 §1 的推荐一致。

**案例 4：Noobi.ai（251★）/ VibeGame（275★）/ GameForge-Copilot（68★）→ "prompt → 审查 → 可玩游戏"的流水线**
- `Noobi.ai` README 描述：本地优先 agent，把 prompt 变成**"经过审查的"**可玩浏览器游戏 —— 关键词是 **reviewed**：生成后有一道校验/检讨环节。
- `VibeGame`：自演化多 agent 框架。
- **可借鉴点**：把"生成"和"验收"拆成两步，并把验收结果留痕 —— 这直接对应评审的"迭代打磨 20%"。

**案例 5：prompt-to-puzzle（54★）→ "AI 生成 + 确定性校验"的混合架构**
- 流程（README 原文）：Imagen 4 出底图 → Gemini 2.5 Flash Image 按 prompt 做 3–5 处结构性改动（**明确要求避免单纯变色**）→ **浏览器端 JS + Canvas 数学比对算出差异**（刻意避免第二次 AI 调用，省成本与延迟）→ 还提供**人工编辑模式**增删改差异。
- **可借鉴点（本文件最值得抄的一条工程思想）**：**让 AI 生成"素材"，让确定性代码生成"答案"**。这样既拿到了 AI 的多样性，又保证了关卡的可判定性 —— 迁移到本比赛就是："LLM 生成主题/文案/风格，生成器+求解器保证每关可解"。

### 5.3 从案例里提炼的 4 条结论

1. **能不能"运行时零 LLM"决定了作品能不能"单文件、离线、永不降级"**。获奖/可玩案例里，静态化的那一类活得最久。
2. **"prompt → 生成 → 校验 → 人工抽检"是共通的四步**，`Noobi.ai`（reviewed）与 `prompt-to-puzzle`（Canvas 校验 + 人工编辑）各自验证了后两步的必要性。
3. **AI Native 的叙事重心在"过程"**：`Claude-Code-Game-Studios`（26,906★）这种把工作流工程化的项目能拿到极高 star，说明"如何与 AI 协作"本身就是可展示、可评分的产出 —— 正好对应本赛题 20% 的迭代分。
4. **同类赛道很挤**：AI Browser Game Jam 正在跑、Vibe Jam 有 2,000+ 作品。差异化只能来自**玩法微创新 + 关卡曲线**（也就是评审权重最高的那 80%），而不是"用了 AI"本身。

---

## 6. 给本比赛的推荐技术栈

### 6.1 单文件打包方案核实：`vite-plugin-singlefile`

**核实结果（我读了 README 原文，不是凭印象）**

| 项 | 事实 |
|---|---|
| Repo | [richardtallent/vite-plugin-singlefile](https://github.com/richardtallent/vite-plugin-singlefile) — **1,236★，MIT，2026-10-17 push** |
| 做什么 | 把**所有 JS 与 CSS 内联**进最终的 `dist/index.html`，产出**一个 HTML 文件、没有其他文件** |
| 官方定位 | README 原文：对"托管在普通 Web 服务器"**不推荐**（性能角度）；但对**离线/双击直接打开**的场景"非常方便"——**这正是本赛题"单个可打开就能玩的 H5"的诉求** |
| `file://` 下**可用** | `localStorage`、新的 Persistent Storage API、FileSystem API、同目录相对路径的本地文件、外部图片/字体、外部 API（`fetch` 需 `{mode:'no-cors'}`）、hash 路由、WebXR |
| `file://` 下**不可用** | History API 路由（SPA 路由）、Cookies、Worklets、Sourcemaps |
| 已知限制 | ①**只支持单一入口**（多 HTML 入口不支持，官方 wontfix）；②`public/` 目录下的静态资源**不会内联**（如 favicon）——但可用相对路径与 HTML 放在一起；③**SVG 不能直接内联**（需插件或把 SVG 写进模板）；④CSP 的 `script-src` 必须有 `'unsafe-inline'` 或 hash/nonce，否则内联脚本被拦；⑤遗留的动态 `import()` 分包在 `file://` 下会失败 |

**推荐的打包配方（已核实的选项）**

```ts
// vite.config.ts
import { defineConfig } from "vite";
import { viteSingleFile } from "vite-plugin-singlefile";

export default defineConfig({
  base: "./",                      // file:// 下必须相对路径
  plugins: [viteSingleFile({ removeViteModuleLoader: true })],
  build: {
    assetsInlineLimit: 100 * 1024 * 1024,  // 让图片/音频都变 data URL 内联
    cssCodeSplit: false,                    // 只出一个 CSS
    target: "es2020",                       // 现代手机浏览器
  },
});
```

**同类/补充项目（都来自 API，2026-10-20）**

| Repo | ★ | License | push | 用途 |
|---|---|---|---|---|
| [vite-plugin-singlefile](https://github.com/richardtallent/vite-plugin-singlefile) | 1,236 | MIT | 2026-10-17 | **主方案** |
| [bddjr/vite-plugin-singlefile-compression](https://github.com/bddjr/vite-plugin-singlefile-compression) | 12 | MIT | 2026-10-17 | **把资源压缩后再嵌进 `index.html`**（见 §6.2 的压缩讨论）；星数极低，**需自己验证** |
| [richardtallent/vite-plugin-singlefile-example](https://github.com/richardtallent/vite-plugin-singlefile-example) | 13 | - | 2025-07-02 | 官方示例工程（用来验证你的配置） |
| [marco-prontera/vite-plugin-css-injected-by-js](https://github.com/marco-prontera/vite-plugin-css-injected-by-js) | 509 | MIT | 2026-07-17 | 把 CSS 通过 JS 注入（与 singlefile 互补/替代） |
| [woowabros/critical-script](https://github.com/woowabros/critical-script) | 211 | MIT | 2026-09-28 | 把 TS 模块内联成关键 HTML 脚本 |
| [postcss/postcss-url](https://github.com/postcss/postcss-url) | 383 | MIT | 2026-10-19 | 把 `url()` 资源内联成 base64（CSS 侧） |
| [sormy/rollup-plugin-smart-asset](https://github.com/sormy/rollup-plugin-smart-asset) | 35 | MIT | 2024-02-28 | rollup 层资源内联/重定位 |
| [vite-pwa/vite-plugin-pwa](https://github.com/vite-pwa/vite-plugin-pwa) | 4,300 | MIT | 2026-10-09 | 若要**加一个可安装的 PWA 外壳**（离线缓存、桌面图标）；与单文件方案叠加需评估 |

### 6.2 inlined 后的体积量级（实测推算，含压缩方案）

**基线实测**（§1.3）：Phaser 4 = 1,343.7 KB raw / 344.2 KB gzip；Phaser 3 = 1,168.1 KB / 307.5 KB；KAPLAY = 184.7 KB / 68.1 KB；LittleJS = 476.8 KB / 147.0 KB；零依赖 = 0。

**推算（说明推算依据，不是实测）**
- 单文件 `index.html` 的磁盘体积 ≈ **引擎 raw + 你的代码 raw + 关卡数据 + 内联资源（base64 后 ≈ 原体积 ×1.33）**。
- 50 关网格游戏的关卡数据（JSON）通常 **10–60 KB**；游戏代码 **20–80 KB**（未压缩）。
- 所以：

| 方案 | index.html 磁盘体积（推算） | 有 HTTP 服务器时的传输体积（gzip 后） |
|---|---|---|
| 零依赖 Canvas + 50 关数据 | **≈ 40–150 KB** | ≈ 15–50 KB |
| KAPLAY + 游戏 | ≈ 210–280 KB | ≈ 75–95 KB |
| LittleJS + 游戏 | ≈ 500–570 KB | ≈ 155–185 KB |
| Phaser 3 + 游戏 | ≈ 1.19–1.26 MB | ≈ 315–340 KB |
| Phaser 4 + 游戏 | ≈ 1.37–1.44 MB | ≈ 350–380 KB |
| Babylon + 游戏 | ≈ 7.8 MB | ≈ 1.6 MB |

**关键工程结论**
1. **双击打开时没有 gzip**：文件系统不会压缩，所以 **raw 体积**就是玩家的加载成本。**交付给评委的文件大小看 raw 列**。
2. 如果要兼顾两者，可用 **"内联 + 自解压"**：把打包产物 gzip 后 base64 内联，运行时用 `DecompressionStream("gzip")` 解压再 eval/blob。算术上：Phaser 4 的 344.2 KB gzip → base64 后约 **459 KB** 字符串，仍比 1,343.7 KB raw 小 **约 66%**；代价是**依赖 `DecompressionStream`（现代 Chromium/Safari 16.4+ 可用）**，老浏览器直接白屏。`bddjr/vite-plugin-singlefile-compression`（12★ MIT）正是在做这件事，但**星数太低，务必自己压测 + 保留不支持时的降级分支**。
3. **最稳的组合是"零依赖 + 不加压缩"**：40–150 KB 的文件，任何浏览器、任何年份、任何网络都能秒开，**没有兼容性风险**。
4. 内联图片请优先 **SVG（文本，压缩率高）** 或 **小尺寸 PNG + 子集化**；大背景图会以 1.33 倍膨胀。

### 6.3 预生成 vs 运行时：基于"100M Token + 缓存"的取舍

> 这是本赛题的架构前提，写清楚比写漂亮重要。

| 维度 | 预生成（build-time） | 运行时（run-time） |
|---|---|---|
| Token 消耗 | 一次性，可控（50 关 × 每关几百 token ≈ **几万 token**，相对 1 亿额度可忽略） | 每次游玩都消耗；玩家越多越贵 |
| 延迟 | 0 | 1–5 s（不可接受，除非有缓存命中） |
| 单文件可行 | ✅ | ❌（需 key + 网络） |
| 可校验性 | ✅ 可在构建期跑求解器证明每关可解 | ⚠️ 只能运行时校验，失败就崩 |
| 可 review | ✅ 你能逐关检查难度曲线 | ❌ |
| 迭代留痕 | ✅ 生成脚本 + 校验报告就是迭代文档素材 | 一般 |
| 内容量上限 | 受开发期算力限制 | 无限 |

**本比赛的结论**
- **100M token 的主要用途不是"游戏运行时"，而是"开发期的代码迭代 + 设计期关卡/文案生成"**。把 token 花在"让 AI"做→测→改""的循环上，直接对应 20% 的迭代分。
- **关卡必须预生成**：50 关是固定内容，没有理由运行时生成。生成脚本（含求解器校验日志）**本身就是交付物的一部分**（设计思路 + 迭代过程文档）。
- **唯一值得考虑的运行时 AI**：单局结束后的"个性化提示/点评"这种**非阻塞、可降级**的锦上添花，且必须有"关闭时完全不影响玩"的兜底。**不要**把核心玩法押在运行时 LLM 上。
- **缓存策略（若真做运行时）**：`contentHash → localStorage/IndexedDB`，命中直接回放；超时 1.5–3 s 回退到预生成兜底；永远保留"离线可玩"路径。

### 6.4 存档 / 关卡进度（轻量方案）

| 方案 | Repo | ★ | License | push | 结论 |
|---|---|---|---|---|---|
| **原生 `localStorage`** | — | — | — | — | **推荐**。50 关的进度数据是几 KB 级，没必要上库。`vite-plugin-singlefile` README 明确 `file://` 下 `localStorage` 可用（但仅在 Chromium 系实测，**请自己再验一次 Safari**） |
| [localForage](https://github.com/localForage/localForage) | 25,801 | Apache-2.0 | **2024-07-30** | 封装 IndexedDB/WebSQL/localStorage，异步 API | 体积 29.0 KB raw / 8.8 KB gzip；**但 2 年多没 push，维护停滞**；本需求下属于过度设计 |
| [idb-keyval](https://github.com/jakearchibald/idb-keyval) | 3,252 | **NOASSERTION** | 2026-07-08 | 极小 IndexedDB keyval | license 字段是 NOASSERTION（实为 ISC），**用前读 LICENSE**；只有要存图片/大数据时才需要 |

**推荐实现（约 30 行）**
- 单一 JSON，带版本号：`{ v: 1, progress: {maxLevel, stars:{}}, best: {}, settings:{} }`；
- 写入用**节流**（500 ms）+ 关键节点（过关/退出）立即写；
- **所有访问包 try/catch**，失败降级到内存对象（`file://` + 隐私模式下 localStorage 可能抛异常）；
- 提供**导出/导入存档**：`Blob` + `URL.createObjectURL` 下载 JSON（README 确认 `file://` 下 FileSystem API 可用）；
- **不要**用 History API 做关卡路由（README 明说 `file://` 下不可用）——用 `#hash` 或纯状态机。

### 6.5 45 天最小工程骨架（按交付物倒推）

```
project/
├─ index.html                 # 单入口（singlefile 只支持一个）
├─ src/
│  ├─ main.ts                 # 状态机：boot → level → result → next
│  ├─ game/                   # 核心玩法（纯逻辑，可单测）
│  │  ├─ rules.ts             # 规则：合法性判定
│  │  ├─ solver.ts            # 求解器（生产环境用于提示/校验）
│  │  └─ state.ts
│  ├─ ui/                     # Canvas 绘制 + 触摸输入（pointer events）
│  ├─ save.ts                 # localStorage 存档（带降级）
│  ├─ audio.ts                # ZzFX/jsfxr 程序化音效
│  └─ levels.json             # ★ 50 关数据（生成脚本产物，嵌入包内）
├─ tools/
│  ├─ generate.mjs            # 生成器：批量出关卡
│  ├─ verify.mjs              # 求解器：证明可解 + 算难度指标
│  └─ report.md               # 校验报告 → 直接进"迭代过程文档"
└─ vite.config.ts
```

**顺序建议**（对齐官方指南"先做 3 关"）
1. Day 1–3：玩法最小闭环，3 关手写，**手机上真机玩**。
2. Day 4–7：`generate.mjs` + `verify.mjs` 跑通 → 一次性出 50 关 + 可解性报告。
3. Day 8–12：难度曲线成型（用求解器指标排序，人工调 5–8 个"惊喜关"）。
4. Day 13–18：打磨手感（音效、动效、失败反馈）+ 真机适配（安全区、触摸、横竖屏）。
5. Day 19+：迭代文档 + 设计文档（把 `report.md` 的校验日志、AI 协作记录整理进去）。

### 6.6 明确不推荐的清单（省时间）

| 不推荐 | 原因（证据） |
|---|---|
| Babylon.js | 实测 7.5 MB raw；本赛题不需要 3D |
| three.js | 3D，且实测拆成 core+module 两文件 ≈790 KB；"不需要复杂美术" |
| Cocos / LayaAir / GDevelop | 编辑器重、产物多文件、license 字段为 NOASSERTION，商用审查成本高 |
| p5.js | LGPL-2.1 + sketch 全局重绘模型不适合网格游戏 |
| Kaboom.js | `replit/kaboom` **已归档**（2024-08-04）；用 KAPLAY 替代 |
| 运行时 LLM 驱动核心玩法 | 破坏单文件/离线，延迟与成本不可控，无缓存必炸 |
| Recraft/闭源 3D 生成服务 | 与"不需要美术"和"可商用许可"两条都冲突 |
| 引入 match-3/sokoban 的**生成器**库 | 实测这类库几乎全是 1★ 级且多为无 license（§3.2），**自研更快更安全** |

---

## 7. 不确定项与风险（诚实清单）

**数据层面**
1. **star/license/push 是 2026-10-20 的快照**，赛事 11-15 截止前可能变化；`license: null` 的仓库随时可能补上许可证，也可能永远没有。
2. **`cocos/cocos-engine`、`4ian/GDevelop`、`jbang2004/long-wind`、`kairess/pane-by-pane`、`lucide-icons/lucide`、`jakearchibald/idb-keyval` 的 API license 字段是 NOASSERTION** —— 这不是"无许可"，而是"GitHub 无法识别为标准 SPDX 之一"。**商用前必须人工读仓库 LICENSE 文件**，我没有逐个读。
3. **能力描述的证据等级不一**：`robatron/sudoku.js`（难度分级）、`vite-plugin-singlefile`（`file://` 能力清单）、`seehiong/prompt-to-puzzle`（AI+Canvas 校验流程）这三条我**读了 README 原文**；§3 中大量 `desc` 级条目（如 `Izaron/Nonograms` 的生成能力、`AlliBalliBaba` 生成器质量）**我没有运行验证**，请抽样自测后再依赖。

**技术层面**
4. **`localStorage` 在 `file://` 下并非所有浏览器都可靠**：`vite-plugin-singlefile` README 自己写的是"I've only tested some of the above in Chromium-based browsers"。**Safari / iOS 微信内置浏览器必须实测**，且必须有无存储降级路径。
5. **体积数字是 CDN 原产物，不是你的打包产物**：Vite + tree-shaking 后通常更小；反之若引入多个库会更大。**以 `npm run build` 后 `dist/index.html` 的实际字节数为准**（建议在 CI 里加一条体积断言）。
6. **`bddjr/vite-plugin-singlefile-compression` 只有 12★**，我没读它的实现，也没压测。"内联 gzip + `DecompressionStream`"的算术是可靠的，但**插件可用性未验证**；若要采用，请自己实现那 20 行解压逻辑，比依赖它更稳。
7. **KAPLAY 的 CDN 产物结构与官方文档可能不一致**：我测的是 `npm:kaplay@latest/dist/kaplay.js`（实测可用），但未验证其是否含全部子路径。打包请以 `npm view kaplay` 为准。
8. **未验证的猜想（标注为推论，请勿当结论）**：§3.3 的"反向生成消除类关卡（倒着消出解序列）"是行业通用技巧，但**本清单里没有开源实现可参照**，属于需要自己验证的工程方案。

**没做的事（留给其他人/后续）**
9. 未验证任何仓库的**运行时正确性**（没有 clone 运行过任何一个候选库）——本次交付是"选型证据"，不是"集成验证"。
10. 未评估**微信小游戏 / 抖音小游戏**平台的适配（本赛题只要求 H5，故未做）。
11. 未核查**赛题是否限制使用第三方开源库**（官方文档未见限制条款；若评委要求"AI 完成全过程"，大量使用第三方库的叙事风险需自行权衡）。
12. `web_search` 故障导致**非 GitHub 信息**（如各商业 prompt-to-game 平台的真实免费额度）未核实；§2 中涉及平台（Rosebud / Summer Engine 等）的信息只来自那两份 awesome 清单，**未独立验证**。