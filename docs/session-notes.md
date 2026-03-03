# Session Notes

## 2026-03-02 AI 面试官 UI A/B 视觉方案

- 目标：基于既有 PRD 与风格参考图，产出两套可落地的 Dashboard UI（Style A / Style B）。
- 结构统一：顶部导航 + 左侧导航 + 主内容区 + 右侧信息栏。
- Style A：冷淡极简（蓝灰系），按钮圆角 12，卡片圆角 16-20，输入框圆角 12。
- Style B：暖色插画感（橙杏系），按钮圆角 16（渐变），卡片圆角 18-22，输入框圆角 14。
- 每套均包含：
  - 配色方案区块（主色/辅色/背景/文字色）
  - 组件风格区块（按钮、卡片、输入框规格）
- 验证：Pencil MCP 对两套方案均执行了截图检查与布局问题检查（No layout problems）。
- 交付文件：
  - designs/style-a.pen
  - designs/style-b.pen


## 2026-03-02 style-a 深化与精简

- 将 style-a.pen 重构为四页完整流程：总览、登录、模拟、复盘。
- 全量文案改为简体中文；自动扫描结果：文本中无英文与问号。
- 删除与 PRD 无关的展示型模块：配色方案、组件风格、快捷操作等。
- 保留 PRD 关键可视模块：登录错误提示、状态机阶段、弱网重试、复盘预警、转写同步、对照答案、改进建议、结构检查。



## 2026-03-02 ??????? CLAUDE.md ????

- ???`AI???2026.2.28` ???????????PRD/OpenSpec/API/DB/??????????? `package.json`?
- ??????????????`user-auth`?`mock-exam-flow`?`audio-processing`?`ai-evaluation-engine`?`vocab-analysis`?`review-dashboard`?
- ????? API ????????????? RLS?rule_violations ???final_score ????
- ??????? Next.js/FastAPI/Supabase ????? 3 ? GitHub ?????vercel/ai-chatbot?fastapi/full-stack-fastapi-template?supabase/supabase ????
- ????? `CLAUDE.md`????????????????????API ????????? DoD?

## 2026-03-03 Milestone 3 复盘看板实现要点

- 新增后端接口：`GET /api/v1/evaluations/{evaluation_id}`，支持 Supabase 查询与本地内存回退，统一 404 错误码 `ERR_NOT_FOUND`。
- 新增前端类型：`frontend/types/evaluation.ts`，与 OpenAPI `EvaluationResult` 字段对齐，避免复盘页使用 `any`。
- `/review/[id]` 改为真实数据加载：服务端读取短期 cookie `access-token`，按状态分流（成功/404/401/错误）。
- 复盘页组件化拆分：
  - `RadarScoreChart`（七维雷达图，权重提示）
  - `AudioTranscriptSync` + `useTranscriptHighlight`（rAF 同步高亮，含 ±0.5s 容差）
  - `AnswerComparison` / `StructuralCheck` / `ImprovementList` / `AntiTemplateWarning`
- TDD 覆盖新增能力：
  - `reviewDataLoader.test.ts`
  - `radarScoreChart.test.ts`
  - `transcriptHighlight.test.ts`
  - `reviewPanels.test.tsx`
- Windows 下运行后端 pytest 时，如遇 `.env` 编码问题，可在当前 shell 设置：`$env:PYTHONUTF8='1'` 后再执行测试。
