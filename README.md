# abyss-vercel-dist

Vercel 静态分发仓库：`public/` 内为加密后的翻译文件（XOR + Base64，`ENC:` 前缀，密钥 c13an），目录结构与 `dotabyss-translation/translations` 同构。

## 更新方式

本仓库内容独立维护，与主翻译仓库（anosu/dotabyss-translation）解耦：

- 正式服发布：在 `DotAbyss正式服翻译仓库更新` 模块运行 `python flow.py publish --apply`，主仓库成功推送后直接同步本仓库的 `public/` 并推送，Vercel 自动部署。
- 本仓库接受冗余：保留既有非空译文、旧静态键及额外剧情，只补缺失和空值，按实际内容重建清单。主仓库剔除过期静态条目时，不同步删除这里的条目。
- 本仓库已接替原 Gitee `bigwalk` 的分发职能，继续沿用相同密钥与加密格式。`bigwalk` 已停用。
- 手工微调：直接编辑 `public/` 下的密文文件（注意保持 `ENC:` 格式可解密）。

## 结构

- `public/manifest/zh_Hans.json` — 内容哈希清单（游戏按此比对更新）
- `public/ui_texts|names|static|novels|replacements/…` — 加密译文与资源
