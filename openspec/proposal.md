## Why

公务员结构化面试备考缺乏高质量的 AI 辅助训练工具：人工点评费用高昂（每次 200–500 元）、反馈周期漫长（1–3 天），初期 5 名核心内测用户需要一个端到端的全真模拟 + 即时多维评分系统，在 ≤15 秒内返回完整复盘报告。

## What Changes

- 新增**用户认证**：Supabase Auth 邮箱密码登录，`sessionStorage` 存储 JWT，RLS 数据隔离
- 新增**全真模拟考场流程**：前端五态状态机（IDLE → READING → RECORDING → PROCESSING → REVIEW），`performance.now()` 精准计时，计时漂移 ≤ 1 秒/3 分钟
- 新增**音频采集与 ASR 转写**：`MediaRecorder API` 录制，`ffmpeg-python` 统一转码为 wav 16kHz mono，Groq `whisper-large-v3` 词级时间戳转写
- 新增**结构化 AI 评估引擎**：Pydantic `LLMEvaluationOutput` 强约束 LLM 输出，6 维度评分 + 规则硬钳制 `apply_rule_caps()`，后端独立计算副语言流畅度（维度7）与 `final_score`
- 新增**多维可视化复盘看板**：七维雷达图（Recharts）、音频进度与转写文本高亮同步（`requestAnimationFrame`，±0.5 秒容差）
- 新增**词汇与套话分析**：Aho-Corasick 政策词汇命中率 + 套话黑名单检测（P0）；正则黑名单反模板化警告（P1）

## Capabilities

### New Capabilities

- `user-auth`: 邮箱密码登录、JWT 会话管理（sessionStorage）、Supabase RLS 行级安全、速率限制
- `mock-exam-flow`: 前端五态状态机完整生命周期、题库调度（6 大题型随机抽题）、`useInterviewTimer` 计时 Hook、设备麦克风检测
- `audio-processing`: MediaRecorder 录制与 Blob 组合、ffmpeg 转码管道（统一 wav 16kHz mono）、Groq Whisper ASR 调用、弱网内存保留容错
- `ai-evaluation-engine`: Pydantic LLM 输出约束（`LLMEvaluationOutput`）、`question_type` 动态 Prompt 工厂（6 题型差异化系统提示）、`apply_rule_caps()` 双保险硬钳制、`calculate_fluency_score()` 规则计算、加权总分聚合
- `review-dashboard`: 七维雷达图渲染（Recharts）、音频播放器 + 转写文本高亮同步（transcript_segments 时间戳）、左右双栏对照（考生原文 vs AI 示范答案）、反模板化警告横幅
- `vocab-analysis`: Aho-Corasick 多模式匹配（政策词汇命中率 + 套话黑名单）、keyword_dict.json 词典管理、Whisper prompt Top-20 截断注入、P1 正则黑名单反模板化检测（cliche_patterns.json）

### Modified Capabilities

（无——本次为全新初始化构建，openspec/specs/ 中不存在已有 spec 文件）

## Impact

- **后端**：FastAPI + Pydantic + openai-python SDK + ffmpeg-python；新增 `/api/v1/evaluations/submit` 端点；所有 AI 调用（ASR + LLM）仅走 FastAPI，不穿透至 Next.js
- **前端**：Next.js 14 + Tailwind CSS + Shadcn/UI + Zustand；新增 `useInterviewTimer`、`useInterviewFlowManager` 两个核心 Hook
- **数据库**：Supabase PostgreSQL；新增 `evaluations` 表（含 15+ 字段，见 PRD §0.4）；Storage Lifecycle Rules 录音 TTL ≤ 24 小时
- **外部依赖**：Groq API（ASR）、OpenAI-compatible API（LLM，默认 `gpt-4o-mini`）、Supabase（Auth + DB + Storage）
- **安全约束**：API 密钥仅存服务端 `.env`，严禁暴露前端；每用户每分钟限流 3 次提交
