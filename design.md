## Context

本次构建是公务员结构化面试 AI 训练系统（面试AI）的初始全栈实现。当前状态：无已有代码库，从零构建。约束条件：5 名内测用户、低并发（无需分布式）、开发者在 Windows 环境下使用 Vibe Coding 工具（Cursor / Claude Code）。端到端延迟目标：用户提交录音 → 收到报告 ≤ 15 秒。

核心 PRD 参考：`D:\AI_Projects\system-max\AI面试官2026.2.28\mianshiAI.md`（v1.5）

## Goals / Non-Goals

**Goals:**
- 建立从认证、考场模拟、音频采集、ASR、LLM 评分到复盘看板的完整数据闭环
- 所有 AI 相关计算（ASR + LLM + 规则打分）隔离至 FastAPI 后端，Next.js 仅作代理层
- Pydantic 强约束 LLM 输出结构，后端硬钳制规则（apply_rule_caps），消除评分幻觉风险
- 数据模型与 PRD §0《权威数据契约》完全对齐

**Non-Goals:**
- 视频采集与面容分析（MVP 禁止）
- 原生移动端 App（React Native / Flutter）
- 分布式中间件（Kubernetes / Redis / Kafka）
- 笔试题库（行测/申论）
- 商业化接口（支付 / 短信 / 实名认证）
- 真人考官介入系统

## Decisions

### 决策 1：双层架构——Next.js BFF + FastAPI AI 编排层

**选择**：Next.js 14 Route Handlers 仅作代理；FastAPI 承接所有 AI 调用和评分计算。

**理由**：API 密钥安全隔离（不暴露至前端），FastAPI 原生 async/await 适合高延迟 AI 调用，Next.js/Tailwind/Shadcn 对 Vibe Coding 工具训练密度最高。

**对比备选**：Next.js Server Actions 直接调用 AI API → 拒绝，API 密钥无法安全隔离。

---

### 决策 2：Groq whisper-large-v3 作为 ASR 引擎

**选择**：Groq LPU 托管 whisper-large-v3，请求 `word_timestamps=True`。

**理由**：3 分钟音频推理约 3–5 秒，满足 15 秒端到端目标的 ASR 子阶段预算；词级时间戳是副语言流畅度计算和前端高亮同步的数据基础。

**对比备选**：OpenAI Whisper API → 速度较慢（\~8–12 秒/次），成本更高。

**约束**：`prompt` 参数限 Top-20 政策词，禁止全量注入 keyword_dict.json（超 224 tokens 触发 HTTP 400）。

---

### 决策 3：openai-python `beta.chat.completions.parse()` + Pydantic 强约束 LLM 输出

**选择**：以 `LLMEvaluationOutput` Pydantic BaseModel 作为 `response_format`，LLM 仅输出 6 维度评分、结构检查、改进建议、示范答案、规则红线标记；后端独立计算维度 7 和 final_score。

**理由**：Pydantic 自动校验 + 类型强制，消除 LLM 自由发挥空间，解析失败触发最多 2 次重试，彻底失败返回结构化错误。

**对比备选**：LangChain → 拒绝，所有调用为单次线性结构化调用，LangChain 引入不必要抽象。

---

### 决策 4：副语言流畅度（维度 7）纯规则计算，不调用 LLM

**选择**：`calculate_fluency_score()` 基于 Whisper 词级时间戳独立计算停顿、语速、语气词密度。

**理由**：确定性、零 LLM 成本、不受 Prompt 漂移影响；Whisper 词级时间戳已是必需数据，无额外采集成本。

---

### 决策 5：Supabase 作为一体化后端服务（Auth + PostgreSQL + Storage）

**选择**：Supabase Auth（HS256 JWT，3600s 有效期）+ PostgreSQL（RLS）+ Storage（音频 TTL 24h）。

**理由**：一个 SDK 覆盖认证、数据库、文件存储；内置 Row Level Security 满足多用户数据隔离；CLI 生成 TypeScript 类型定义打通前后端类型安全；5 用户规模无需自建 Auth 服务。

---

### 决策 6：IndexedDB 降级为内存保留 Blob + 手动重试

**选择**：弱网时仅在内存保留录音 Blob，展示内联提示 + 手动"重试上传"按钮，不做 IndexedDB 持久化。

**理由**：IndexedDB 跨页面状态机复杂度过高，Blob 存取 + SHA-256 去重 + 断网队列防抖重传极易产生状态死锁；5 用户内测场景可接受"保持页面不刷新"的已知限制。

---

### 决策 7：正则黑名单替代 TF-IDF 反模板化检测

**选择**：`cliche_patterns.json` 硬编码套话正则黑名单，命中数 ≥3 触发警告。

**理由**：TF-IDF 余弦相似度需要 200 条高质量语料库（`corpus.json`），数据来源未解决；AI 编码时极易硬编码无效假数据或引入爬虫库。正则方案零外部依赖，黑名单由产品方逐步维护。

---

### 决策 8：apply_rule_caps 双保险硬钳制

**选择**：LLM 标注（`rule_violations` 枚举）与确定性关键词检测（`_detect_violations_deterministically`）并联，任一命中即触发 RULE_CAPS 分数上限，在入库前执行。

**理由**：Prompt 为软引导，可能因 LLM 漂移而失效；确定性检测提供兜底保障，双保险消除评分上限规则失效的长尾风险。

## Risks / Trade-offs

| 风险 | 缓解方案 |
|------|----------|
| Groq API 限流 / 超时 | 最多 2 次指数退避重试；彻底失败返回 HTTP 503 + ERR_ASR_TIMEOUT |
| LLM 输出 Pydantic 校验失败 | 最多 2 次重试；彻底失败返回 HTTP 503 + ERR_LLM_PARSE_FAILED |
| ffmpeg 未安装于宿主机 | Dockerfile 必须包含 `apt-get install -y ffmpeg`（PRD §6.3 阻断项） |
| OPENAI_MODEL 配置错误 | 环境变量缺失时默认 `gpt-4o-mini`，代码硬编码 fallback |
| gpt-4o-mini 在中国区延迟 | OPENAI_MODEL 可切换为 SiliconFlow / 其他 OpenAI-compatible 端点，改 .env 即生效 |
| Supabase Storage 超额 | TTL ≤ 24h Lifecycle Rule 强制清理，MVP 规模不超配额 |
| 前端计时器漂移 | `performance.now()` + `document.visibilitychange` 校准；Jest 单元测试覆盖 |

## Migration Plan

本次为全新构建，无历史数据迁移。部署顺序：

1. Supabase 项目初始化：执行 SQL Schema（evaluations 表、RLS Policy、Storage Bucket + Lifecycle Rule）
2. 后端 FastAPI：`.env` 注入 API 密钥，构建 Docker 镜像（包含 ffmpeg）
3. 前端 Next.js：`.env.local` 注入 Supabase URL/anon key，NEXT_PUBLIC_ 前缀仅用于公开配置
4. 集成测试：mock 链路端到端耗时断言（不依赖外部 API）

回滚策略：任意阶段失败直接回滚容器；数据库 Schema 变更使用 Supabase CLI migration 版本管理。

## Open Questions

1. **LLM 供应商最终选择**：中国区生产环境是否使用 SiliconFlow / Kimi / 其他兼容 OpenAI API 的供应商？（影响 `OPENAI_API_KEY` + `OPENAI_MODEL` 配置，不影响代码实现）
2. **P2 压力性追问**：MVP 完成后何时进入 P2 开发阶段？追问功能状态机节点 `FOLLOW_UP_INTERVIEW` 是否需要在初始 Schema 中预留字段？
3. **cliche_patterns.json 初始内容**：正式启动前需产品方提供至少 10–20 条套话正则黑名单种子数据。
