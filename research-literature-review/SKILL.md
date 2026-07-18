---
name: research-literature-review
description: 当用户明确要求系统综述、文献综述、related work、相关工作或文献调研时使用。执行多源检索、去重、逐篇相关性评分、证据抽取、选文、主题综合与硬校验，默认交付带首次出现顺序数字引文和关键开放许可原文图的 Markdown 综述及 BibTeX，不生成 Word；仅在用户明确要求时额外导出 PDF。
---

# Research Literature Review

## 目标与默认交付

在隔离任务目录内完成检索、去重、评分、选文、证据综合、写作和验证。默认交付：

- `{主题}_review.md`：唯一正式正文，包含文内数字引文、原文图及按被引先后排列的 GB/T 7714—2015 顺序编码制参考文献。
- `{主题}_参考文献.bib`：所引文献的结构化元数据。
- `{主题}_review_assets/`：获准复用的关键原文图及来源记录。
- `{主题}_工作条件.md`：检索、评分、选文和结构记录。
- `{主题}_验证报告.md`：字数、文献数、引用顺序、图片来源及章节校验。
- 字数预算 CSV 和必要的 JSONL 中间产物。

不得生成 `.docx`。PDF 不属于默认交付；只有用户明确要求 PDF 时才从最终 Markdown 额外导出。

## 任务目录

新任务中间文件写入 `./.bensz-api/task-{yyyymmdd-hhmm}-{简短描述}/research-literature-review/input|output|log/`。正式交付物放在用户指定目录或当前工作目录根部。不要把检索缓存、临时脚本或下载原图散落在交付目录。

## 输入

至少需要主题。时间、语言、研究类型、数据库、字数和文献数可选；未指定时读取 `config.yaml`。档位为 `premium`、`standard` 或 `basic`。

## 硬约束

- 正文字数与参考文献数必须处于用户或配置指定范围。
- 正文固定包含摘要、引言、至少一个主体主题、讨论、展望、结论。
- 主体一级主题通常为 3 至 7 个；若用户要求更紧凑，优先合并相近主题。
- 摘要必须为单段。
- 正文禁止出现检索、去重、评分、选文和字数预算等流程元叙事。
- 每条文献必须在正文实际被引；参考文献表不得出现未引条目。
- 文内引用必须紧跟所支撑的主张，并显示为方括号数字。
- 引用编号必须按正文第一次出现的顺序分配，从 `[1]` 连续递增。
- 参考文献表必须与首次被引顺序完全一致。
- 参考文献著录必须符合 GB/T 7714—2015 顺序编码制：条目使用 `[1]` 方括号序号、包含文献类型/载体标识，并按相应文献类型组织著录项。
- 只嵌入来源、图号和复用许可均已核验的原文图；无法确认许可时不得复制。
- 不为凑数量引入低相关文献或装饰性图片。

## 开始前读取

- 查询规划：`references/ai_query_generation_prompt.md`
- 评分与证据抽取：`references/ai_scoring_prompt.md`
- 专家写作：`references/expert-review-writing.md`
- Markdown 结构、引用和图注：`references/review-md-section-template.md`
- GB/T 7714—2015 顺序编码著录：`references/gbt7714-2015.md`
- 多语言任务再读：`references/multilingual-guide.md`

## 流程

### 1. 多源检索

自主规划 5 至 15 组查询变体。优先使用 OpenAlex；按主题补充 Crossref、PubMed、IEEE Xplore、Semantic Scholar、出版社页面或机构仓储。对关键论文必须打开原始页面、摘要页或全文核验，不以搜索结果摘要代替阅读。

### 2. 去重与评分

运行 `dedupe_papers.py`。依据 `references/ai_scoring_prompt.md` 阅读标题与摘要，按 1 至 10 分评分并提取设计、关键结果、局限和子主题。仅给 5 分及以上文献分配子主题。

### 3. 选文与证据卡

按目标文献范围、高分优先和主题覆盖选文。生成 `selected_papers.jsonl`、BibTeX 和证据卡。摘要缺失或过短的论文标记为 `do_not_cite`，除非已从可靠全文补足证据。

### 4. 关键原文图筛选

从高相关核心论文中选择通常 2 至 5 幅能够概括机制、方法、实验构型、关键对比或综合结论的原文图。每幅图必须同时满足：

1. 直接服务中心论点，删去后会明显损失理解。
2. 原文图号、作者、年份、DOI 或稳定链接可核验。
3. 许可明确允许复用，优先 CC BY、CC0、公共领域或作者明确授权版本。
4. 图像来自出版社、PMC、机构仓储或作者正式版本，不使用搜索缩略图和二手转载图。
5. 分辨率足够，文字可读；下载后必须实际查看。

将图片保存到 `{主题}_review_assets/`。Markdown 使用相对路径：

```markdown
![图意明确的替代文本]({主题}_review_assets/sourcekey_fig03.png)

图 1. 图的中文解释。来源：Author et al. (Year)，原文图 3，DOI：[链接](https://doi.org/...)，CC BY 4.0。
```

若只截取或组合原图面板，必须在图注中标明节选或组合，并确认许可允许修改。付费墙文章、许可不明图片或仅允许合理使用的图片不得默认嵌入；改为文字总结并提供原文链接。

### 5. 结构与预算

基于证据规划 3 至 7 个主体主题和段落配额。每个主题必须有局部主张、关键证据、边界或反例。讨论处理异质性、矛盾和失败原因；展望提出可验证研究议程。

### 6. Markdown 写作

正文先使用 BibTeX key 占位引用：

```markdown
螺旋结构改变了方向选择性，而不是把全部入射方向等比例放大 [@kuvshinov2016]。
埋地伴随光缆与直接贴纤接收的是不同传播通道 [@paper_a; @paper_b]。
```

引用必须放在对应句子之后。单次通常引用 1 至 3 篇，超过 4 篇需要拆分观点。禁止把整段的所有文献统一堆到段末。

完成正文后运行：

```bash
python scripts/finalize_markdown_citations.py \
  --input {主题}_review_draft.md \
  --bib {主题}_参考文献.bib \
  --output {主题}_review.md
```

脚本必须按每个 key 在正文第一次出现的位置编号，将占位符改为 `[1]` 或 `[2, 3]`，并生成同序、符合 GB/T 7714—2015 的参考文献表。不要人工按评分、年份、作者字母或选文顺序编号。生成后仍须逐条核查 BibTeX 元数据，自动格式化不能替代来源核验。

### 7. 验证

运行计数、结构和 Markdown 引用验证。至少检查：

- 字数与参考文献数量。
- 摘要、引言、主体主题、讨论、展望、结论齐全。
- 文内首次出现的新编号依次为 1、2、3，无跳号和倒置。
- 每个正文编号在参考文献表中存在，且参考文献表无未引条目。
- 每条参考文献以 `[序号]` 起始，含合法文献类型/载体标识，在线资源含访问路径或 DOI，并尽量含 `[YYYY-MM-DD]` 引用日期。
- 不再残留 `[@bibkey]`、LaTeX `\cite{}` 或 Word 文件。
- 每幅原文图存在、可打开、使用相对路径，并有作者、原文图号、DOI/链接和许可证。
- 正文无工作流元叙事。

推荐命令：

```bash
python scripts/validate_review_md.py \
  --md {主题}_review.md \
  --bib {主题}_参考文献.bib \
  --min-refs N --max-refs M
```

若用户明确要求 PDF，再从已经通过验证的 Markdown 导出；不得以 PDF 或 Word 替换 Markdown 主交付物。

## 写作质量

- 以主张组织段落，不按论文逐篇罗列。
- 用证据解释机制、差异来源和适用边界，不只报告性能数字。
- 对冲突结果区分研究对象、测量链、工况、样本、评价指标和耦合条件。
- 关键图之后必须解释图支持什么结论、不能支持什么结论。
- 不确定时明确证据限制，不补造数字、图号、许可或 DOI。

## 关键脚本

- 检索：`multi_query_search.py`、`openalex_search.py`
- 去重：`dedupe_papers.py`
- 选文：`select_references.py`、`build_reference_bib_from_papers.py`
- 证据：`build_evidence_cards.py`
- 引用定序：`finalize_markdown_citations.py`
- Markdown 校验：`validate_review_md.py`
- 字数预算：`plan_word_budget.py`、`validate_word_budget.py`
- 验证报告：`generate_validation_report.py`

## 兼容说明

旧名 `systematic-literature-review` 仅作为触发兼容别名。旧任务中的 LaTeX、PDF 或 Word 文件可以读取以便迁移，但新任务不得默认创建 Word，正式正文以 Markdown 为唯一来源。
