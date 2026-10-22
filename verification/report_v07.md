# T18 独立复核报告 · v0.7「星织 / Asterweave」（10 关 · 星空主题 + 星座揭晓 + 杂星）

> 复核者：verify-t13（全新独立复核者，未参与实现）｜复核时间：2026-10-21 20:0x–（Asia/Shanghai）
> 状态：**进行中（边做边落盘）** —— 每完成一块即追加对应章节，报告不会等到最后才写。
> 独立性声明：本轮 A/B/C/D/发布包检查脚本均为**本轮自写**（`verification/t14_*.py` / `t14_*.js`），不 import、不复制 `tools/generate_levels.py` 与 `tools/fit_constellation_levels.py`；对前人脚本只做"先判断其正确性"后再决定是否复用。

## 0. 被复核对象（以 sha256 为准）与冻结副本

本轮开始时实测（`Get-FileHash -Algorithm SHA256`），并已冻结到 `verification/frozen_v07/`：

| 对象 | 字节 | sha256 |
|---|---|---|
| `dist/星织-游戏本体/index.html`（v0.7，10 关） | 91,575 | `fd2c9c817227779492c67020c1aaa147f62620a8fb5324f5c343b705052811ff` |
| `星织-游戏本体.zip` | 22,385 | `2a236e05a435a614abac73819f4f79505baeb93ae11a0a94d8fc275e29a21ddb` |
| `tools/levels.json` | 35,625 | `857f6fb28e79ecffa8f48b90b29f770860239e7ff199c3b110d20cc15bbd6ea6` |
| `docs/SPEC.md` | 10,858 | `26bb51459dd5df1eaf1eff89485e017687c4044fdd5f46f3332c539fd1b63d21` |
| `冉政-设计思路文档.md` | 20,017 | `ce82b070d0a65e92369b29904c2871d72f1def3aa4786fcf687da685faed7692` |
| `冉政-迭代优化过程文档.md` | 36,533 | `2e1c186a8ce7e77eaa0dae6caf8014f26cd18a9f8bd0d8f163f23b4debab8193` |
| `dist/build_manifest.json` | 835 | `141b9f90ab42da455bdcadf56ef8f02c02445128bfb457463f18cf967ba552f6` |
| 参考：`tools/fit_constellation_levels.py` | 15,249 | `42296326b2eef86212321a6de8cd368eb5e08f10743dcf432cdc26449a7fe55c` |
| 参考：`tools/generate_levels.py` | 36,252 | `03951b2f513466ddf20ae9e1087e468e358a81cc869c42899f6dae1850ae2508` |

冻结命令：

```powershell
$ErrorActionPreference='Stop'
New-Item -ItemType Directory -Force -Path 'verification\frozen_v07' | Out-Null
Copy-Item 'dist\星织-游戏本体\index.html' 'verification\frozen_v07\dist_index.html'
Copy-Item '星织-游戏本体.zip'              'verification\frozen_v07\release.zip'
Copy-Item 'tools\levels.json'             'verification\frozen_v07\levels.json'
Copy-Item 'docs\SPEC.md'                  'verification\frozen_v07\SPEC.md'
Copy-Item '冉政-设计思路文档.md'            'verification\frozen_v07\design_doc.md'
Copy-Item '冉政-迭代优化过程文档.md'         'verification\frozen_v07\iteration_doc.md'
Copy-Item 'dist\build_manifest.json'      'verification\frozen_v07\build_manifest.json'
```

> 说明：复核期间若有对象变动，将在对应章节注明并补冻结 live 版本 sha。