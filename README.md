# abyss-vercel-dist

Vercel 静态分发仓库：`public/` 内为加密后的翻译文件（XOR + Base64，`ENC:` 前缀，密钥 c13an），目录结构与 `dotabyss-translation/translations` 同构。

## 更新方式

本仓库内容独立维护，与主翻译仓库（anosu/dotabyss-translation）解耦：

- 批量重建：主仓库发布流程生成 `bigwalk` 后，将 `bigwalk/` 覆盖到 `public/`，提交推送即可，Vercel 自动部署。
- 手工微调：直接编辑 `public/` 下的密文文件（注意保持 `ENC:` 格式可解密）。

## 结构

- `public/manifest/zh_Hans.json` — 内容哈希清单（游戏按此比对更新）
- `public/ui_texts|names|static|novels|replacements/…` — 加密译文与资源
