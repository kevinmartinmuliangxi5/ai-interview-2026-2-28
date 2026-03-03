# 技术栈决策文档

**项目**：公务员结构化面试 AI 训练系统（面试AI）
**基准文档**：PRD v1.5（`AI面试官2026.2.28/mianshiAI.md`）+ openspec 规格
**约束前提**：5 名内测用户、单开发者 Vibe Coding、端到端 ≤15s、Windows 开发环境

---

## 速览表

| 层 | 选定技术 | 关键理由 |
|----|---------|---------|
| 前端框架 | Next.js 14 (App Router) | Vibe Coding 工具训练密度最高；BFF 代理隔离 AI 密钥 |
| 类型系统 | TypeScript 5 | Supabase CLI 生成类型定义，打通前后端类型安全 |
| 样式 | Tailwind CSS v3 | Shadcn/UI 依赖项；AI 生成代码的首选 utility 体系 |
| 组件库 | Shadcn/UI | 可复制源码、无黑盒依赖、Radix 无障碍基础 |
| 状态管理 | Zustand | 五态状态机轻量管理；PRD 明确禁止 Redux |
| 图表 | Recharts | 七维雷达图原生支持，React 组件化，无额外打包体积 |
| 后端框架 | FastAPI | 原生 async/await 适配高延迟 AI 调用；Pydantic 内置 |
| Python 版本 | Python 3.11 | `str \| None` 语法、更快启动速度、Pydantic v2 最优支持 |
| AI 数据验证 | Pydantic v2 | `beta.chat.completions.parse()` 的 response_format 基础 |
| LLM 调用 | openai-python ≥ 1.0 | 结构化输出 API（parse()）+ 指数退避重试内置 |
| 音频转码 | ffmpeg-python | 唯一满足"统一转码 wav 16kHz mono 无格式分支"要求的方案 |
| 文件验证 | python-magic | 魔数验证防 Content-Type 伪造；PRD 安全约束 |
| 多模式匹配 | pyahocorasick | 政策词汇 + 套话黑名单 O(n) 线性扫描 |
| ASGI 服务器 | Uvicorn | FastAPI 官方推荐；async worker 不阻塞 AI 调用 |
| ASR 服务 | Groq whisper-large-v3 | LPU 推理 3–5s/3 分钟音频；词级时间戳必需 |
| LLM 服务 | OpenAI-compatible（默认 gpt-4o-mini） | OPENAI_MODEL 环境变量热切换；结构化 JSON 输出稳定 |
| 数据库 | Supabase PostgreSQL + RLS | 一套 SDK 覆盖 Auth + DB + Storage；RLS 数据隔离 |
| 认证 | Supabase Auth (HS256 JWT) | 与数据库 RLS 深度集成；无需独立 Auth 服务 |
| 文件存储 | Supabase Storage | 原生 Lifecycle Rule 支持音频 TTL ≤ 24h |
| 前端单测 | Jest + React Testing Library | PRD 要求 useInterviewTimer + 状态机单元测试 |
| 后端单测 | Pytest | Python 生态事实标准；Pydantic 模型验证测试首选 |
| 前端部署 | Vercel | Next.js 原生宿主；零配置 Edge Network |
| 后端部署 | Railway（Docker） | 无 Kubernetes 托管容器；含 ffmpeg 镜像直接 push |
| 本地开发 | Docker Compose | 前后端隔离；复现 CI 环境；与 Dockerfile 一致 |

---

## 1. 前端层

### 1.1 Next.js 14（App Router）

**选定理由**：
- Cursor / Claude Code 等 Vibe Coding 工具对 Next.js/React/Tailwind 组合的训练数据密度最高，AI 直接输出可运行代码的概率最大
- Route Handler 作为代理层，将 AI API 密钥隔离在服务端，OPENAI_API_KEY 和 GROQ_API_KEY 不暴露于前端（PRD §5.3 强制约束）
- App Router 的 Server Components + Client Components 分层使状态机逻辑（Client-only）和页面路由清晰分离

**淘汰备选**：

| 方案 | 淘汰原因 |
|------|---------|
| Vite + React SPA | 无 BFF 代理层，API 密钥无法安全隔离于前端 |
| Remix | Vibe Coding 工具对 Remix 代码生成质量远低于 Next.js；loader/action 范式学习曲线高 |
| Nuxt.js (Vue) | Shadcn/UI、Recharts 生态均为 React 专属；切换框架无收益 |
| Gradio / Streamlit | PRD 明确禁止：无法满足跨页面状态流转、精细 MediaRecorder 控制和雷达图渲染 |

---

### 1.2 TypeScript 5

**选定理由**：
- Supabase CLI (`supabase gen types typescript`) 自动生成数据库 Schema 类型定义，打通前后端类型安全
- `LLMEvaluationOutput` Pydantic 模型在后端定义，TypeScript 类型在前端镜像，减少数据断层
- `transcript_segments` 时间戳数组的类型约束防止高亮同步逻辑出现运行时错误

**淘汰备选**：

| 方案 | 淘汰原因 |
|------|---------|
| JavaScript | Supabase 类型生成收益丢失；复杂状态机（5 态 + useInterviewFlowManager）无类型保障，AI 生成代码更易引入 undefined 错误 |

---

### 1.3 Tailwind CSS v3

**选定理由**：
- Shadcn/UI 的必选依赖，不可替换
- `animate-pulse text-red-600`、`bg-amber-100` 等 PRD 中直接指定的 Tailwind 类名需直接使用
- utility-first 方案让 AI 生成的内联样式代码可直接运行，无需额外 CSS 文件

**淘汰备选**：

| 方案 | 淘汰原因 |
|------|---------|
| CSS Modules | 不兼容 Shadcn/UI；AI 生成 CSS Module 代码质量不稳定 |
| Styled Components / Emotion | 运行时 CSS-in-JS，增加打包体积；与 Shadcn/UI 的 class-based 方案冲突 |
| Material UI (MUI) | 设计系统与 Shadcn/UI 冲突，引入两套 Design Token |

---

### 1.4 Shadcn/UI

**选定理由**：
- 组件源码直接复制到项目中，无黑盒依赖，AI 可直接修改组件内部逻辑
- 基于 Radix UI 原语，无障碍（a11y）开箱即用，麦克风检测 disabled 状态正确传递
- 与 Tailwind CSS + Next.js 的集成质量在 AI 代码生成场景下最优

**淘汰备选**：

| 方案 | 淘汰原因 |
|------|---------|
| Ant Design | React 18 兼容性问题频发；中文文档友好但过度设计，与 Tailwind 体系摩擦大 |
| Radix UI（直接使用） | 无样式基础，需手动编写所有视觉层，Vibe Coding 效率低 |
| Headless UI | 仅支持 Tailwind Labs 生态，组件数量远少于 Shadcn/UI |

---

### 1.5 Zustand

**选定理由**：
- PRD §6.2 明确禁止 Redux
- 五态面试状态机（IDLE/READING/RECORDING/PROCESSING/REVIEW）用 Zustand slice 表达简洁，无 Redux 的 action/reducer 样板代码
- 与 `useInterviewFlowManager` Hook 的组合使用在 AI 代码生成场景下错误率极低

**淘汰备选**：

| 方案 | 淘汰原因 |
|------|---------|
| Redux Toolkit | PRD 明确禁止；5 用户 MVP 的状态复杂度不需要 Redux 的完整能力 |
| Jotai / Recoil | 原子化状态模型对面试状态机的顺序流转不友好；Jotai 的 AI 代码生成质量低于 Zustand |
| React Context + useReducer | 状态变更需穿透多层组件，性能隐患；跨组件音频 Blob 引用管理复杂 |

---

### 1.6 Recharts

**选定理由**：
- PRD §2.1 明确指定 Recharts
- `RadarChart` 组件原生支持七维雷达图，与 React 状态系统直接绑定
- 打包体积合理（\~100KB gzip），无 Canvas 依赖，SSR 兼容

**淘汰备选**：

| 方案 | 淘汰原因 |
|------|---------|
| Chart.js + react-chartjs-2 | 配置对象式 API 与 React 状态同步需额外 ref 管理，AI 代码生成更易出错 |
| ECharts + echarts-for-react | 打包体积过大（\~800KB）；七维雷达图配置复杂度高 |
| D3.js | 直接操作 DOM，与 React 声明式模型冲突；Vibe Coding 场景下代码生成质量差 |
| Victory | 雷达图支持不完整；社区活跃度低于 Recharts |

---

## 2. 后端层

### 2.1 FastAPI

**选定理由**：
- PRD §6.3 明确选定
- 原生 `async/await`：Groq ASR（3–5s）和 LLM（2–4s）调用不阻塞主线程池
- Pydantic 内置作为 `response_format` 的基础，`beta.chat.completions.parse()` 直接消费 Pydantic BaseModel
- `/docs` 自动生成 OpenAPI 文档，便于前后端接口对齐

**淘汰备选**：

| 方案 | 淘汰原因 |
|------|---------|
| Django + DRF | 同步优先架构，AI 调用期间阻塞 worker 线程；ORM 对 Supabase 的 RLS 透明支持差 |
| Flask | 无原生 async 支持；需额外集成 asyncio，代码复杂度高 |
| Node.js (Express/Fastify) | Python 生态（openai-python、ffmpeg-python、pyahocorasick、python-magic）全部依赖 Python；语言切换无收益 |

---

### 2.2 Python 3.11

**选定理由**：
- `str | None` 联合类型语法（PRD §7.1 代码直接使用）在 3.10+ 原生支持
- Python 3.11 启动速度比 3.10 快 10–60%，冷启动对 ≤15s 目标有意义
- Pydantic v2 的 Rust 核心在 3.11 性能最优

**淘汰备选**：

| 方案 | 淘汰原因 |
|------|---------|
| Python 3.9 / 3.10 | 需用 `Optional[str]` 替代 `str \| None`，与 PRD 代码片段不兼容 |
| Python 3.12 | 部分依赖库（pyahocorasick）在 3.12 的 wheel 尚不完整，CI 风险高 |

---

### 2.3 Pydantic v2

**选定理由**：
- `openai-python >= 1.0` 的 `beta.chat.completions.parse()` 要求 Pydantic BaseModel 作为 `response_format`，是实现结构化 LLM 输出的核心依赖
- PRD §7.1 代码片段（`LLMEvaluationOutput`、`DimensionScore`、`@field_validator`）直接基于 Pydantic v2 API
- v2 的 Rust 核心比 v1 快 5–50 倍，对高频 schema 验证有意义

**淘汰备选**：

| 方案 | 淘汰原因 |
|------|---------|
| Pydantic v1 | `openai-python >= 1.0` 的结构化输出 API 要求 v2；`@field_validator` 装饰器为 v2 专有 |
| marshmallow | 不支持 openai-python `response_format` 参数；无类型推导 |
| attrs | 同上；与 FastAPI 集成需额外适配层 |

---

### 2.4 openai-python ≥ 1.0

**选定理由**：
- PRD §6.3 明确要求
- `beta.chat.completions.parse()` 是消除 LLM 输出幻觉的关键 API——将 Pydantic 模型直接作为 response_format，自动反序列化并抛出清晰校验错误
- 内置指数退避重试（`max_retries`），PRD 要求的 2 次重试可零代码实现
- `OPENAI_MODEL` 环境变量热切换无需改代码（SiliconFlow、Kimi 等兼容端点均可接入）

**淘汰备选**：

| 方案 | 淘汰原因 |
|------|---------|
| LangChain | PRD §6.3 明确禁止：所有 LLM 调用为单次线性结构化调用，LangChain 的链式抽象引入不必要复杂度和不可预测的 Prompt 注入 |
| httpx 直接调用 | 需手动实现 response_format 参数、Pydantic 解析、重试逻辑，等于重造 openai-python 轮子 |
| anthropic-sdk | Claude API 不支持 openai-python 的 `parse()` 模式；需额外适配 Pydantic 绑定 |

---

### 2.5 ffmpeg-python

**选定理由**：
- PRD §4.2、§6.3 明确要求：`ffmpeg -i input -ar 16000 -ac 1 -f wav output.wav`
- 唯一能无分支统一处理 `audio/webm`（Chrome）和 `audio/mp4`（Safari）的方案
- Python wrapper 调用系统 ffmpeg，转码质量与原生 ffmpeg 一致

**淘汰备选**：

| 方案 | 淘汰原因 |
|------|---------|
| pydub | 依赖 ffmpeg 但封装不完整，16kHz 降采样 + 单声道的精确控制在 pydub API 层不稳定 |
| soundfile + librosa | 仅支持 WAV/FLAC，无法处理 webm/mp4 输入格式 |
| moviepy | 视频处理库，音频处理为附带功能，依赖体积大 |

**注意**：ffmpeg-python 自身不含可执行文件，Dockerfile 必须包含：
```dockerfile
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*
```

---

### 2.6 python-magic

**选定理由**：
- PRD §4.2 要求魔数验证防 Content-Type 伪造（安全硬性约束）
- 直接读取文件头二进制签名，不依赖 HTTP 请求头声明

**淘汰备选**：

| 方案 | 淘汰原因 |
|------|---------|
| mimetypes（stdlib） | 仅根据文件扩展名判断类型，无法检测实际文件内容，可被伪造绕过 |
| filetype | 功能等效但社区维护活跃度低；python-magic 在安全场景下文档更完整 |
| 不做验证 | 违反 PRD §4.2 安全约束，直接进入 ffmpeg 处理可能导致任意文件处理漏洞 |

---

### 2.7 pyahocorasick

**选定理由**：
- PRD §7.2.5 要求 Aho-Corasick 算法实现政策词汇命中率 + 套话黑名单统计
- O(n) 线性时间复杂度，单次扫描同时匹配所有模式词，适合转写文本长度（\~1000–2000 字）
- C 扩展实现，性能远超纯 Python 多模式匹配

**淘汰备选**：

| 方案 | 淘汰原因 |
|------|---------|
| flashtext | 仅支持精确词匹配，不支持部分匹配和重叠模式 |
| re.findall 循环 | O(n×m) 复杂度，每个词一次扫描，词典 200+ 条目时性能下降明显 |
| 自实现 Aho-Corasick | 无必要：pyahocorasick 为成熟库，Bug 风险远低于自实现 |

---

### 2.8 Uvicorn

**选定理由**：
- FastAPI 官方推荐的 ASGI 服务器
- 原生 asyncio event loop，不阻塞 Groq/OpenAI 异步调用
- Docker 生产环境使用 `uvicorn --workers 1`（5 用户无需多 worker）

**淘汰备选**：

| 方案 | 淘汰原因 |
|------|---------|
| Gunicorn（同步） | WSGI 服务器，无原生 async 支持，AI 调用期间阻塞整个 worker |
| Hypercorn | 功能等效但社区规模和文档质量低于 uvicorn |
| Daphne | Django Channels 专用，与 FastAPI 无关联 |

---

## 3. AI 服务层

### 3.1 Groq API（whisper-large-v3）

**选定理由**：
- PRD §6.5 明确选定
- LPU 推理速度：3 分钟音频 \~3–5 秒，是 15s 端到端目标的 ASR 子阶段预算内唯一可靠选项
- `word_timestamps=True` 返回词级时间戳，是副语言流畅度计算和前端高亮同步的数据基础
- 免费额度对 5 用户内测完全覆盖

**淘汰备选**：

| 方案 | 淘汰原因 |
|------|---------|
| OpenAI Whisper API | 速度较慢（\~8–12s/3 分钟），不满足 15s 端到端目标 |
| Azure Speech Services | 实时流式 API，与 PRD"录音结束后一次性 POST"策略不兼容；配置复杂度高 |
| iFlytek（讯飞） | docs/讯飞语音识别Python集成指南.md 已在项目中调研，但词级时间戳支持不完整，无法满足转写高亮同步 |
| 本地 Whisper（faster-whisper） | 需 GPU 或显著延长推理时间；开发者 Windows 本机无专用 GPU，Docker 容器部署复杂 |

---

### 3.2 OpenAI-compatible LLM（默认 gpt-4o-mini）

**选定理由**：
- PRD §6.5 明确：`gpt-4o-mini` 结构化 JSON 输出稳定，每次评估成本约 ¥0.05
- `OPENAI_MODEL` 环境变量设计：无需改代码即可切换 SiliconFlow / Kimi / 零一万物 等国产兼容端点（中国区生产部署）
- `beta.chat.completions.parse()` 对 gpt-4o-mini 的 response_format 支持经过充分验证

**淘汰备选**：

| 方案 | 淘汰原因 |
|------|---------|
| GPT-4o | 成本约 ¥0.5/次，5 用户内测阶段 10× 超预算；结构化输出质量与 gpt-4o-mini 差距不足以覆盖成本差 |
| Claude API (anthropic-sdk) | 不兼容 openai-python 的 `parse()` 模式，需独立适配 Pydantic 绑定，增加代码分支 |
| Gemini API | 结构化输出 API 与 openai-python SDK 不完全兼容；需额外客户端适配 |
| 本地 LLM（Ollama/vLLM） | 推理速度无法满足 ≤15s 目标；开发者本机硬件不支持 |

---

## 4. 数据与基础设施层

### 4.1 Supabase（PostgreSQL + Auth + Storage）

**选定理由**：
- PRD §6.4 明确选定
- **一套 SDK 覆盖三个核心需求**：认证（HS256 JWT）+ 数据库（PostgreSQL + RLS）+ 文件存储（Storage Lifecycle Rule）
- Row Level Security 直接在数据库层实现 `auth.uid() = user_id` 策略，无需应用层逻辑
- `supabase-py` 在 FastAPI 后端验证 JWT（`auth.get_user(token)`）原生支持
- Supabase Storage Lifecycle Rule 配置 TTL ≤ 24h 音频自动删除，满足 PRD §5.3 数据安全要求

**淘汰备选**：

| 方案 | 淘汰原因 |
|------|---------|
| Firebase | NoSQL（Firestore）不支持 PostgreSQL RLS；Storage 无原生 Lifecycle Rule；关系型数据模型（evaluations 表）在 Firestore 表达复杂 |
| PlanetScale | 无 RLS；无内置 Auth 和 Storage；需额外集成 Auth0/Clerk + S3 = 三套服务 |
| 自托管 PostgreSQL + Auth0 | 运维负担与 5 用户规模不匹配；Auth0 免费额度限制严格 |
| Neon (Serverless PG) | 无内置 Auth + Storage；与 Supabase 相比缺少完整的 RLS + CLI 工具链 |

---

## 5. 测试层

### 5.1 Jest + React Testing Library（前端）

**选定理由**：
- PRD §9 条目 3 明确要求 `useInterviewFlowManager` 单元测试，条目 6 要求计时器漂移单元测试（Jest 模拟 `visibilitychange` 事件）
- React Testing Library 的"行为驱动"测试风格与状态机的"给定状态 → 触发事件 → 验证状态"模式高度吻合
- Next.js 14 内置 Jest 配置，零额外配置

**淘汰备选**：

| 方案 | 淘汰原因 |
|------|---------|
| Vitest | 需额外配置 Vite 适配 Next.js App Router；对 `performance.now()` 的 mock 支持与 Jest 相比文档不完整 |
| Mocha + Chai | 无 DOM 环境集成；React 组件测试需额外配置 jsdom |

---

### 5.2 Pytest（后端）

**选定理由**：
- Python 生态事实标准测试框架
- `apply_rule_caps`、`calculate_fluency_score`、`filter_unknown_violations` 等纯函数用 Pytest 参数化测试可覆盖所有边界条件
- Pydantic v2 模型校验测试（`pytest.raises(ValidationError)`）语法简洁

**淘汰备选**：

| 方案 | 淘汰原因 |
|------|---------|
| unittest（stdlib） | 类继承式 API 样板代码多；fixture 机制远不如 Pytest 灵活 |
| nose2 | 已进入维护模式，不推荐新项目使用 |

---

## 6. 部署层

### 6.1 Vercel（前端）

**选定理由**：
- Next.js 由 Vercel 团队开发，App Router / Route Handler 的冷启动优化最佳
- 零配置部署：连接 Git 仓库即自动 CI/CD
- Edge Network 全球 CDN，中国区访问可接受

**淘汰备选**：

| 方案 | 淘汰原因 |
|------|---------|
| Netlify | 对 Next.js App Router 的支持滞后于 Vercel；Route Handler 边缘场景有已知 Bug |
| AWS Amplify | 配置复杂度与 5 用户规模不匹配 |
| 自托管（nginx） | 运维负担过高；失去 Vercel 的自动 HTTPS + CDN |

---

### 6.2 Railway（后端 Docker 容器）

**选定理由**：
- 支持直接 push Docker 镜像，含 ffmpeg 的自定义 Dockerfile 无需额外配置
- PRD §6.4 明确禁止 Kubernetes；Railway 的托管容器模式与"无分布式中间件"约束完全吻合
- 按使用量计费，5 用户内测月成本 \~$5–10

**淘汰备选**：

| 方案 | 淘汰原因 |
|------|---------|
| Fly.io | 功能等效，但 ffmpeg 镜像冷启动偶发超时；Railway 的国内访问稳定性略优 |
| Render | 免费套餐有 15 分钟冷启动限制；付费套餐与 Railway 相比无明显优势 |
| AWS ECS / GCP Cloud Run | 配置复杂度高；IAM 权限管理对单开发者项目是负担 |
| Heroku | Container Registry 已停止支持 Heroku-20 stack；迁移 Docker 方案成本高 |

---

### 6.3 Docker Compose（本地开发）

**选定理由**：
- 在 Windows 开发环境下统一 FastAPI + ffmpeg + python-magic 的 Linux 依赖
- `docker-compose up` 一键启动后端，与生产 Dockerfile 保持一致，消除"本地能跑线上挂"问题
- Next.js 前端无需容器化（`npm run dev` 直接运行），只有 Python 后端需要隔离环境

**淘汰备选**：

| 方案 | 淘汰原因 |
|------|---------|
| 直接本机 Python 环境 | Windows 下 `python-magic` 需要 libmagic DLL，`ffmpeg` 需手动添加 PATH；环境搭建步骤多，Vibe Coding 场景容易出错 |
| WSL2 直接运行 | 与 Windows Claude Code 终端的路径和权限切换增加认知负担 |

---

## 7. PRD 明确禁止项速查

以下技术不得出现在任何代码分支、依赖配置或架构设计中：

| 禁止项 | 禁止来源 | 原因 |
|--------|---------|------|
| Redux | PRD §6.2 | 5 用户 MVP 过度工程；Zustand 已充分满足 |
| LangChain | PRD §6.3 | 所有 LLM 调用为单次线性调用，LangChain 引入不必要抽象 |
| WebSocket（音频流） | PRD §2.1 | 录音结束后一次性 POST，不做流式传输 |
| IndexedDB（持久化） | PRD §4.4 v1.5 | 状态死锁风险；改为内存 Blob + 手动重试 |
| Kubernetes / Redis / RabbitMQ / Kafka | PRD §6.4 | 5 用户场景无需分布式中间件 |
| React Native / Flutter / Swift | PRD §8 | 交付物为响应式 Web App |
| Gradio / Streamlit | PRD §6.2 | 无法满足精细 UI 控制需求 |
| jieba / 外部停用词表 / 语料库 | PRD §9 条目12 v1.5 | TF-IDF 方案已废弃；改用正则黑名单 |
| 前端暴露 OPENAI_API_KEY / GROQ_API_KEY | PRD §5.3 | 安全硬性约束 |
| localStorage 存储 access_token | PRD §3.0 | XSS 持久化风险；必须用 sessionStorage |
