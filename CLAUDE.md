# CLAUDE.md

## 1. 适用范围
本规范适用于 `AI面试官2026.2.28` 项目的后续实现阶段（前端、后端、数据库、测试）。

当前仓库是“规格先行”状态：已有 PRD/OpenSpec/API/DB/设计稿，但尚未落地业务源码（根目录无 `package.json`）。

---

## 2. 当前项目结构结论（本地分析）

### 2.1 核心目录
- `docs/`：技术栈、API 规范、架构图、数据库说明
- `specs/`：按业务能力拆分的 OpenSpec
  - `user-auth`
  - `mock-exam-flow`
  - `audio-processing`
  - `ai-evaluation-engine`
  - `vocab-analysis`
  - `review-dashboard`
- `db/migrations/001_init.sql`：数据库基线（枚举、RLS、索引、约束）
- `designs/`：`style-a.pen`、`style-b.pen`

### 2.2 API 域（来自 `docs/api-spec.yaml`）
- `/api/v1/health`
- `/api/v1/questions/draw`
- `/api/v1/questions/{question_id}`
- `/api/v1/evaluations/submit`
- `/api/v1/evaluations`
- `/api/v1/evaluations/{evaluation_id}`

### 2.3 错误码全集（当前契约）
- `ERR_ASR_TIMEOUT`
- `ERR_FILE_TOO_LARGE`
- `ERR_FORBIDDEN`
- `ERR_INTERNAL`
- `ERR_INVALID_AUDIO`
- `ERR_LLM_PARSE_FAILED`
- `ERR_MISSING_QUESTION_ID`
- `ERR_NOT_FOUND`
- `ERR_QUESTION_NOT_FOUND`
- `ERR_RATE_LIMIT_EXCEEDED`
- `ERR_UNAUTHORIZED`
- `ERR_VALIDATION`

---

## 3. 技术栈基线（必须对齐）
依据 `docs/tech-stack.md`：
- 前端：Next.js（App Router）+ TypeScript + Tailwind + shadcn/ui + Zustand + Recharts
- 后端：FastAPI + Python 3.11 + Pydantic v2 + openai-python + ffmpeg-python + pyahocorasick
- 数据层：Supabase（PostgreSQL + Auth + Storage + RLS）
- 测试：Jest + React Testing Library（前端），Pytest（后端）

---

## 4. 命名规范

### 4.1 前端
- React 组件：`PascalCase`（例：`InterviewStatusPanel.tsx`）
- Hook：`useXxx`（例：`useInterviewFlowManager.ts`）
- Zustand Store：`xxx.store.ts`（例：`interviewFlow.store.ts`）
- Route Handler：`app/api/v1/<resource>/route.ts`
- 变量/函数：`camelCase`
- 常量：`SCREAMING_SNAKE_CASE`

### 4.2 后端
- Python 模块文件：`snake_case.py`
- Pydantic 模型：`PascalCase`
- 函数/变量：`snake_case`
- 数据库字段：`snake_case`，禁止驼峰混用

### 4.3 领域关键字（禁止改名）
- `question_type`：
  - `COMPREHENSIVE_ANALYSIS`
  - `PLANNING_ORGANIZATION`
  - `EMERGENCY_RESPONSE`
  - `INTERPERSONAL_RELATIONSHIPS`
  - `SELF_COGNITION`
  - `SCENARIO_SIMULATION`
- `rule_violations`：
  - `CLICHE_ANALYSIS`
  - `NO_SAFETY_PLAN`
  - `EMERGENCY_HARDLINE`
  - `INTERPERSONAL_CONFLICT`

---

## 5. 错误处理模式

### 5.1 通用原则
- 对外仅返回结构化错误：`{ error_code, message }`
- 不向前端透出栈信息、SQL 细节、上游供应商原始报错
- 日志保留完整上下文（含 `request_id`）

### 5.2 HTTP 状态码映射
- `400`：请求参数/格式非法（`ERR_VALIDATION`、`ERR_INVALID_AUDIO`）
- `401`：未认证（`ERR_UNAUTHORIZED`）
- `403`：无权限（`ERR_FORBIDDEN`）
- `404`：资源不存在（`ERR_NOT_FOUND`、`ERR_QUESTION_NOT_FOUND`）
- `413`：文件过大（`ERR_FILE_TOO_LARGE`）
- `429`：限流（`ERR_RATE_LIMIT_EXCEEDED`）
- `503`：上游不可用/解析失败（`ERR_ASR_TIMEOUT`、`ERR_LLM_PARSE_FAILED`）
- `500`：内部错误（`ERR_INTERNAL`）

### 5.3 BFF 与后端职责
- Next.js BFF：统一鉴权、错误转换、响应整形
- FastAPI：业务错误显式抛出，不可预期错误统一兜底
- Supabase：RLS 负责数据边界，不在前端绕过

---

## 6. 测试策略

### 6.1 测试分层
- 单元测试：状态机、评分函数、规则上限函数
- 集成测试：API + 鉴权 + RLS + DB
- 端到端：登录 → 模拟录音提交 → 复盘看板

### 6.2 前端（Jest + RTL）
必须覆盖：
- `useInterviewFlowManager` 五态流转：`IDLE -> READING -> RECORDING -> PROCESSING -> REVIEW`
- 计时器漂移校准（`performance.now` + `visibilitychange`）
- 上传失败重试与错误提示展示

### 6.3 后端（Pytest）
必须覆盖：
- `apply_rule_caps`
- `calculate_fluency_score`
- `filter_unknown_violations`
- 音频校验（Content-Type、magic number、大小限制）
- 鉴权与访问控制边界（401/403/404）

### 6.4 CI 最小门禁
每次合并前必须通过：
- `lint`
- `typecheck`
- `test`
- `build`

---

## 7. API 设计模式

### 7.1 版本化与契约优先
- 统一前缀：`/api/v1`
- `docs/api-spec.yaml` 是接口真相源
- 改接口顺序：先改 OpenAPI，再改实现，再改测试

### 7.2 认证与会话
- 受保护接口统一 `Authorization: Bearer <token>`
- 浏览器只允许 `sessionStorage` 保存会话令牌
- `service_role` 仅后端可用，禁止进入前端代码

### 7.3 可观测性
- 每个请求打 `request_id`
- 关键阶段记录耗时：上传校验、转码、ASR、LLM、评分聚合、入库

---

## 8. 参考项目最佳实践（GitHub）

### 8.1 `vercel/ai-chatbot`
- 会话前置拦截（边缘层/代理层）
- 统一错误类型与用户可见消息映射
- 脚本化质量门禁（lint、类型、单测、e2e）

### 8.2 `fastapi/full-stack-fastapi-template`
- `APIRouter` 分域组织，主入口统一注册
- 依赖注入统一鉴权/权限检查
- 健康检查不仅看存活，还检查依赖（如数据库）

### 8.3 `supabase/supabase`（`nextjs-user-management` 示例）
- 使用 RLS + `auth.uid()` 做用户数据隔离
- 明确区分 `anon key` 与 `service_role key`
- 认证后的用户初始化逻辑尽量放在数据库侧（触发器/函数）

---

## 9. 禁止项（硬约束）
- 禁止 Redux（本项目明确选 Zustand）
- 禁止 LangChain（本项目是线性结构化调用）
- 禁止前端 `localStorage` 持久化 `access_token`
- 禁止前端暴露 `OPENAI_API_KEY`、`GROQ_API_KEY`、`service_role`
- 禁止跳过音频安全校验直接进入 ASR

---

## 10. 开发完成定义（DoD）
每次任务结束必须满足：
- 与 `specs/*` 和 `docs/api-spec.yaml` 一致
- 受影响测试通过
- lint/typecheck/build 通过
- 关键路径手工验证一次并留证据
- 输出：变更说明 + 验证证据 + 剩余风险

---

## 11. 规范来源

### 11.1 本地文件
- `docs/tech-stack.md`
- `docs/api-spec.yaml`
- `db/migrations/001_init.sql`
- `specs/*/spec.md`

### 11.2 官方文档
- Next.js Project Structure  
  https://nextjs.org/docs/app/getting-started/project-structure
- Next.js Route Handlers  
  https://nextjs.org/docs/app/building-your-application/routing/route-handlers
- Next.js Error Handling  
  https://nextjs.org/docs/app/getting-started/error-handling
- Next.js Backend-for-Frontend Guide  
  https://nextjs.org/docs/app/guides/backend-for-frontend
- Next.js Testing Guide  
  https://nextjs.org/docs/app/guides/testing
- FastAPI Bigger Applications  
  https://fastapi.tiangolo.com/tutorial/bigger-applications/
- FastAPI Handling Errors  
  https://fastapi.tiangolo.com/tutorial/handling-errors/
- FastAPI Testing  
  https://fastapi.tiangolo.com/tutorial/testing/
- Supabase RLS Guide  
  https://supabase.com/docs/guides/database/postgres/row-level-security

### 11.3 参考仓库
- https://github.com/vercel/ai-chatbot
- https://github.com/fastapi/full-stack-fastapi-template
- https://github.com/supabase/supabase/tree/master/examples/user-management/nextjs-user-management
