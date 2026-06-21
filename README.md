# ImageGen PPTX Pipeline

[![CI](https://github.com/eddyzzl/imagegen-pptx-pipeline/actions/workflows/ci.yml/badge.svg)](https://github.com/eddyzzl/imagegen-pptx-pipeline/actions/workflows/ci.yml)

| English | 中文 |
|---|---|
| **ImageGen PPTX Pipeline** is an agent skill for creating high-taste, editable PowerPoint decks from rough ideas, outlines, templates, reference decks, data, brand assets, generated slide comps, or user-supplied final slide images. | **ImageGen PPTX Pipeline** 是一个用于生成高质量、可编辑 PowerPoint 的 Codex/Agent skill。它可以从粗略想法、提纲、模板、参考 PPT、品牌资料、数据、生成图，或者用户已经给好的幻灯片图片出发，完成从内容讨论到最终 PPTX 导出的完整流程。 |
| It is designed for the hard version of deck generation: not only making slides look good, but helping an agent discuss the story, lock the central message, confirm every page, explore multiple visual directions, generate final slide images, upscale comps and icons with Real-ESRGAN, and convert them into faithful editable PPTX with strict native reconstruction and real render QA. | 它不只是“把文字塞进 PPT 模板”，而是把专业 PPT 顾问、视觉总监、逐页审稿人、图片生成器、4K 高清化、图片转 PPTX 工程师和 QA 审计员串成一条可暂停、可确认、可追踪的工作流。 |

## Showcase / 效果图

| English | 中文 |
|---|---|
| These examples are generated 3x3 contact sheets showing final ImageGen-style slide comps for different deck themes. Density is intentionally mixed: some pages are minimal narrative pages, while technical, financial, decision, and strategy pages carry heavier evidence, tables, charts, and diagrams. | 下面是多张 3x3 的最终 ImageGen 风格效果图，用来展示这个 skill 可以组织和产出的不同主题 deck。信息密度不是全部拉满：有些页保留极简叙事和视觉冲击，技术、财报、决策、战略等页面则会承载更多表格、图表、流程和证据块。 |

### Chinese-First Examples / 中文场景展示

| 产品介绍 | 技术汇报 | 财报 |
|---|---|---|
| <img src="docs/assets/showcase-zh-product-intro.png" alt="中文产品介绍 3x3 PPT 效果图" width="100%"> | <img src="docs/assets/showcase-zh-technical-report.png" alt="中文技术汇报 3x3 PPT 效果图" width="100%"> | <img src="docs/assets/showcase-zh-financial-report.png" alt="中文财报 3x3 PPT 效果图" width="100%"> |

| 战略规划 | 决策汇报 | 销售方案 |
|---|---|---|
| <img src="docs/assets/showcase-zh-strategic-planning.png" alt="中文战略规划 3x3 PPT 效果图" width="100%"> | <img src="docs/assets/showcase-zh-decision-package.png" alt="中文决策汇报 3x3 PPT 效果图" width="100%"> | <img src="docs/assets/showcase-zh-sales-proposal.png" alt="中文销售方案 3x3 PPT 效果图" width="100%"> |

| 新员工培训 | 金融科技公司介绍 | 晋升答辩 |
|---|---|---|
| <img src="docs/assets/showcase-zh-onboarding-training.png" alt="中文新员工培训 3x3 PPT 效果图" width="100%"> | <img src="docs/assets/showcase-fintech-company.png" alt="金融科技公司介绍 3x3 PPT 效果图" width="100%"> | <img src="docs/assets/showcase-promotion-defense.png" alt="晋升答辩 3x3 PPT 效果图" width="100%"> |

### Broader Theme Range / 更多主题展示

| Product Introduction | Technical Report | Annual Financial Report |
|---|---|---|
| <img src="docs/assets/showcase-product-intro.png" alt="3x3 product introduction deck showcase" width="100%"> | <img src="docs/assets/showcase-technical-report.png" alt="3x3 technical report deck showcase" width="100%"> | <img src="docs/assets/showcase-financial-report.png" alt="3x3 financial report deck showcase" width="100%"> |

| Strategic Planning | Thesis Defense | New Employee Training |
|---|---|---|
| <img src="docs/assets/showcase-strategic-planning.png" alt="3x3 strategic planning deck showcase" width="100%"> | <img src="docs/assets/showcase-thesis-defense.png" alt="3x3 thesis defense deck showcase" width="100%"> | <img src="docs/assets/showcase-onboarding-training.png" alt="3x3 onboarding training deck showcase" width="100%"> |

| Decision Package | Sales Proposal | Investor Roadshow |
|---|---|---|
| <img src="docs/assets/showcase-decision-package.png" alt="3x3 executive decision package deck showcase" width="100%"> | <img src="docs/assets/showcase-sales-proposal.png" alt="3x3 enterprise sales proposal deck showcase" width="100%"> | <img src="docs/assets/showcase-investor-roadshow.png" alt="3x3 investor roadshow deck showcase" width="100%"> |

| Performance Review | Academic Research | Fintech Company Profile |
|---|---|---|
| <img src="docs/assets/showcase-performance-review.png" alt="3x3 performance review deck showcase" width="100%"> | <img src="docs/assets/showcase-academic-research.png" alt="3x3 academic research deck showcase" width="100%"> | <img src="docs/assets/showcase-fintech-company.png" alt="3x3 fintech company profile deck showcase" width="100%"> |

## Why It Is Powerful / 它强在哪里

| Capability | English | 中文 |
|---|---|---|
| Multi-round thinking | Discuss content, audience, central idea, outline, narrative arc, proof strategy, and slide-by-slide intent before drawing anything. | 可以多轮讨论内容、受众、中心思想、大纲、叙事结构、证据策略和逐页页面意图，再开始做视觉。 |
| Page-by-page confirmation | Lock titles, claims, evidence, visual intent, text sources, and conversion plans through stateful artifacts such as `deck_spec.json`, `slide_intent_matrix.md`, `narrative_matrix.md`, `visual_contract.json`, and `conversion_manifest.json`. | 可以逐页确认标题、主张、证明对象、视觉意图、文字来源和转换方案，避免边做边丢信息。 |
| Task-aware style exploration | Choose concrete, task-fit style IDs in `references/style-library.md`, generate materially different visual lanes, preview contact sheets, and let the user confirm one or more directions before production. | 会先根据实际任务、受众和场合推荐风格；多风格不只是换颜色或图标，而是改变版式原型、证据呈现、密度节奏、字体气质、图表语言和图标语言；先预览风格，再确认方向。 |
| Parallel production | Supports page-level subagents and specialist reviewers for conversion feasibility, typography, visual fidelity, icon extraction, template fidelity, and final export decisions when the runtime supports multi-agent work. | 在支持多 agent 的运行时里，可以按页面或角色拆分生产和审查，例如 PPTX 可行性、文字排版、视觉保真、图标抠图、模板一致性和最终导出评审。 |
| Mandatory 4K comp upscaling | Every generated or supplied slide image must be processed through Python `RealESRGANer` with `RealESRGAN_x4plus.pth`, CPU, and tile splitting into an exact 3840x2160 comp before measurement and PPTX conversion, with a manifest proving the engine, model file, device, tile settings, output size, and checksum. | 每页生成图或用户图片都会强制用 Python `RealESRGANer` + `RealESRGAN_x4plus.pth` + CPU + tile 分块高清化到精确 3840x2160，再进入测量和 PPTX 转换；manifest 会记录引擎、模型文件、设备、tile 参数、输出尺寸和校验和。 |
| Image-to-editable-PPTX | Treats generated or supplied slide images as measurement targets, then rebuilds slides with native PowerPoint text, shapes, connectors, charts, tables, and only validated image assets. | 可以把生成图或用户截图转换成真正可编辑 PPTX：页面图只是测量目标，最终用原生 PowerPoint 文本、形状、线条、图表、表格和连接器重建。 |
| HD icon extraction | `iconcut3.py` fails closed on clipped icons, extracts real source pictograms instead of redrawing generic glyphs, then the extracted assets are Real-ESRGAN-upscaled before PPTX placement while preserving feathered alpha for fused art slices. | `iconcut3.py` 可以严格高清抠图标：遇到裁切风险直接失败；真实图标默认提取，不用通用几何图标糊弄；抠出的图标还会再走 Real-ESRGAN 高清化后才贴进 PPTX。 |
| Real QA | `qa_gate.py` reads actual PPTX XML/media, render files, icon manifests, and region metrics. Final conversion requires at least 10 real render-compare-fix rounds with distinct exported render files. | `qa_gate.py` 会读取真实 PPTX XML、媒体文件、图标 manifest、真实渲染图和区域差异指标。最终要求至少 10 轮真实导出、对比、修复，而不是口头说“看起来差不多”。 |

## Workflow / 工作流

| Step | English | 中文 |
|---:|---|---|
| 1 | Read the brief, template, historical decks, sources, data, and brand assets. | 读取 brief、模板、历史 PPT、资料、数据和品牌资产。 |
| 2 | Discuss and lock the central message, audience, outline, and slide intent. | 讨论并锁定中心思想、受众、大纲和逐页意图。 |
| 3 | Confirm narrative treatment and proof strategy. | 确认叙事方式和证据策略。 |
| 4 | Generate multiple high-taste ImageGen style lanes and preview contact sheets. | 生成多种高 taste ImageGen 风格方向，并预览 contact sheet。 |
| 5 | Let the user confirm one or more visual directions. | 让用户确认一个或多个视觉方向。 |
| 6 | Generate high-resolution per-slide ImageGen comps for the selected style lane. | 为已选风格逐页生成高清 ImageGen 幻灯片图。 |
| 7 | Review content, clarity, taste, template fidelity, and PPTX feasibility. | 审查内容、清晰度、设计 taste、模板一致性和 PPTX 可行性。 |
| 8 | Real-ESRGAN-upscale each comp to exact 3840x2160, then measure in a 1920x1080 coordinate basis. | 先用 Real-ESRGAN 把每页 comp 强制高清化到 3840x2160，再按 1920x1080 basis 测量。 |
| 9 | Extract icons with strict fail-closed guards, Real-ESRGAN-upscale them, and place only the enhanced assets. | 严格图标抠图，失败即修坐标；再用 Real-ESRGAN 高清化图标，PPTX 只贴高清化后的资产。 |
| 10 | Rebuild the deck as native editable PPTX with `slidelib.py`. | 用 `slidelib.py` 重建原生可编辑 PPTX。 |
| 11 | Run 10+ real render-compare-fix rounds and mechanical QA gates. | 跑至少 10 轮真实渲染对比修复和机械 QA gate。 |
| 12 | Export the final editable PPTX. | 导出最终可编辑 PPTX。 |

```mermaid
flowchart TD
  A[Brief / 模板 / 数据 / 资产] --> B[Content & central idea / 内容与中心思想]
  B --> C[Slide intent / 逐页意图]
  C --> D[Narrative & proof / 叙事与证据]
  D --> E[Style lanes / 多风格方向]
  E --> F[Contact sheet preview / 风格预览]
  F --> G[Style confirmation / 风格确认]
  G --> H[Per-slide ImageGen comps / 逐页生成图]
  H --> I[Review / 审查]
  I --> J[Real-ESRGAN 4K comps / 4K 高清化]
  J --> K[Measurement / 测量]
  K --> L[HD icon extraction + Real-ESRGAN / 图标抠图与高清化]
  L --> M[Editable PPTX rebuild / 可编辑 PPTX 重建]
  M --> N[10+ render QA rounds / 10+ 轮渲染 QA]
  N --> O[Final PPTX / 最终 PPTX]
```

## Use Cases / 适合场景

| English | 中文 |
|---|---|
| Product, company, model/technical, sales, GTM, strategy, investor, training, and internal review decks. | 产品介绍、公司介绍、模型/技术方案、销售/GTM、战略汇报、投融资、培训、内部评审等 PPT。 |
| Decks that need a real narrative and central argument, not just pretty pages. | 需要先讲清楚叙事和中心论点，而不是直接生成漂亮页面的 PPT。 |
| Decks that need several high-taste visual directions before authoring. | 需要多种高质量视觉风格供选择的 PPT。 |
| Decks that must preserve a supplied PowerPoint template. | 需要严格保留用户提供模板的 PPT。 |
| CJK-heavy slides where text wrapping, icon clipping, and visual drift matter. | 中文/CJK 内容很多、文字换行和图标细节容易出错的 PPT。 |
| Slide images, screenshots, or mockups that must become faithful editable PPTX. | 已经有幻灯片图片、截图、mockup，但需要转换成可编辑 PPTX 的场景。 |

## Repository Layout / 仓库结构

| English | 中文 |
|---|---|
| The installable skill is the inner `imagegen-pptx-pipeline/` directory. | 可安装的 skill 是仓库内层的 `imagegen-pptx-pipeline/` 目录。 |

```text
imagegen-pptx-pipeline/
  README.md
  LICENSE
  COMPATIBILITY.md
  CONTRIBUTING.md
  CHANGELOG.md
  SECURITY.md
  docs/assets/
  imagegen-pptx-pipeline/
    SKILL.md
    slidelib.py
    iconcut3.py
    qa_gate.py
    PITFALLS.md
    agents/openai.yaml
    references/
    scripts/
  examples/
  tests/
```

## Installation / 安装

| English | 中文 |
|---|---|
| Copy the installable skill directory into your Codex skill folder. If `CODEX_HOME` is not set, use the skill directory supported by your agent runtime. | 把可安装 skill 目录复制到 Codex skill 目录。如果没有设置 `CODEX_HOME`，请使用你的 agent 运行时支持的 skill 目录。 |

```bash
mkdir -p "$CODEX_HOME/skills"
cp -R imagegen-pptx-pipeline "$CODEX_HOME/skills/imagegen-pptx-pipeline"
```

## Minimal Usage / 最小用法

| English | 中文 |
|---|---|
| Create a full deck from a brief. | 从 brief 创建完整 PPT。 |

```text
Use $imagegen-pptx-pipeline to create a 10-slide product launch deck.

Inputs:
- Brief: ...
- Audience: executive product review
- Template: attached PPTX
- References: attached historical deck
- Style directions: 4

First confirm slide_intent_matrix.md, then narrative_matrix.md, then generate ImageGen style options.
```

```text
使用 $imagegen-pptx-pipeline 帮我做一个 10 页产品发布会 PPT。

输入：
- Brief: ...
- 受众：产品/管理层评审
- 模板：已上传 PPTX
- 参考：已上传历史 deck
- 风格方向：4 个

先确认 slide_intent_matrix.md，再确认 narrative_matrix.md，然后生成 ImageGen 风格选项。
```

| English | 中文 |
|---|---|
| Convert final slide images into editable PPTX. | 直接把最终幻灯片图片转换成可编辑 PPTX。 |

```text
Use $imagegen-pptx-pipeline to convert these final slide images into a faithful editable PPTX.
Use strict HD icon extraction and run at least 10 render-compare rounds, each with a new exported render file.
```

```text
使用 $imagegen-pptx-pipeline 把这些最终幻灯片图片转换成高保真、可编辑 PPTX。
需要严格高清图标抠图，并至少跑 10 轮真实渲染对比修复。
```

## Required Capabilities / 运行能力要求

| English | 中文 |
|---|---|
| ImageGen/Image2-style image generation for contact sheets and per-slide comps. | 用于风格 contact sheet 和逐页 comp 的 ImageGen/Image2 类图片生成能力。 |
| Python 3 with `Pillow`, `numpy`, and `python-pptx`. | Python 3，以及 `Pillow`、`numpy`、`python-pptx`。 |
| Python `realesrgan`, `basicsr`, `torch`, and `RealESRGAN_x4plus.pth` for mandatory CPU/tile 4K comp upscaling and icon upscaling. | Python `realesrgan`、`basicsr`、`torch` 和 `RealESRGAN_x4plus.pth`，用于用 CPU/tile 强制每页 comp 高清化到 4K，并对抽取图标做高清化处理。 |
| LibreOffice `soffice` and Poppler `pdftoppm` for render-based PPTX QA. | 用于 PPTX 渲染 QA 的 LibreOffice `soffice` 和 Poppler `pdftoppm`。 |
| Image viewing for paired crops and icon contact sheets. | 用于查看 paired crops 和图标 contact sheet 的图片查看能力。 |
| Optional `markitdown` for text QA and optional subagents for parallel production/review. | 可选 `markitdown` 做文字 QA；可选多子 agent 做并行生产和审查。 |

Without ImageGen, the skill can still run direct slide-image conversion from user-supplied images. Without Python RealESRGANer, `RealESRGAN_x4plus.pth`, LibreOffice/Poppler, or image viewing, it cannot complete the strict conversion loop.

没有 ImageGen 时，这个 skill 仍然可以把用户提供的最终幻灯片图片转换成 PPTX。没有 Python RealESRGANer、`RealESRGAN_x4plus.pth`、LibreOffice/Poppler 或图片查看能力时，它无法完成严格转换闭环。

## Validation / 验证

| English | 中文 |
|---|---|
| Run smoke tests. | 运行 smoke tests。 |

```bash
python -m unittest discover -s tests
```

| English | 中文 |
|---|---|
| Run the gate checker manually. | 手动运行 gate checker。 |

```bash
python imagegen-pptx-pipeline/scripts/check_pipeline_gates.py \
  --workspace /path/to/workspace \
  --stage before-pptx
```

## Local Codex Sync / 本地 Codex 同步

| English | 中文 |
|---|---|
| Treat this repository as the source of truth. For local development, prefer a symlink. | 把这个仓库当作 source of truth。本地开发时优先使用 symlink。 |

```bash
mkdir -p ~/.codex/skills
ln -sfn "$PWD/imagegen-pptx-pipeline" ~/.codex/skills/imagegen-pptx-pipeline
```

| English | 中文 |
|---|---|
| For runtimes that do not support symlinked skills, use the sync script. | 对不支持 symlink skill 的运行时，使用同步脚本。 |

```bash
tools/sync-to-codex.sh --dry-run
tools/sync-to-codex.sh
```

## Design Principles / 设计原则

| English | 中文 |
|---|---|
| Generated images are visual targets, not the source of truth for text or data. | 生成图是视觉目标，不是文字和数据的事实来源。 |
| Final text and numbers come from `deck_spec.json`. | 最终文字和数字来自 `deck_spec.json`。 |
| User-supplied templates are hard constraints. | 用户提供的模板是硬约束。 |
| Style options must differ by visual system, not just color. | 风格选项必须是视觉系统差异，不只是换颜色。 |
| ImageGen prompts should request crisp text, sharp icons, clean fine lines, and the highest available detail. | ImageGen prompt 应要求清晰文字、锐利图标、干净细线和最高可用细节。 |
| Every approved comp must be Real-ESRGAN-processed to exact 3840x2160 before PPTX conversion. | 每页确认后的 comp 必须先经 Real-ESRGAN 处理成精确 3840x2160，才能进入 PPTX 转换。 |
| PPTX conversion uses measurement, not eyeballing. | PPTX 转换使用测量，不靠肉眼估计。 |
| Full-slide and large region image layers are not the conversion path. | 整页图或大区域图层不是最终转换路径。 |
| Text, numbers, labels, cards, lines, charts, arrows, tables, and page chrome should be native editable PowerPoint objects. | 文本、数字、标签、卡片、线条、图表、箭头、表格和页眉页脚等都应是原生可编辑 PowerPoint 对象。 |
| Complex icons are extracted with `iconcut3.py`, then upscaled with Real-ESRGAN before placement; `ClipError` means fix the measurement, not bypass the extractor. | 复杂图标用 `iconcut3.py` 抽取，再用 Real-ESRGAN 高清化后贴入 PPTX；遇到 `ClipError` 应修测量，不应绕过提取器。 |
| Final decks require at least 10 render-compare-fix rounds with distinct render files and passing `qa_gate.py` audits. | 最终 deck 至少需要 10 轮真实渲染对比修复，并通过 `qa_gate.py` 审计。 |
| Every user pause is stateful through `pipeline_state.json`. | 每次暂停都通过 `pipeline_state.json` 保持状态。 |
