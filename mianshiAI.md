# 针对中国公务员结构化面试的AI辅助训练系统：面向Vibe Coding的产品需求文档 (PRD v1.5)

> **版本说明**：本文档为 v1.5，在 v1.4 基础上根据 AI 代码落地性审查意见裁剪两项"过度工程"隐患：①§4.4 废弃 IndexedDB 持久化方案，改为内存保留 Blob + 手动重试按钮的轻量弱网策略，消除断网状态机死锁风险；②§7.2.5 废弃 TF-IDF 余弦相似度 + 200条样本库的反模板化方案，改为高频套话正则黑名单命中计数，消除外部语料依赖与 AI 编码时引入爬虫库的风险；同步更新 §0.3、§1.1（用户E）、§2.2 P1 及 §9 条目12 的一致性描述。全文以§0《权威数据契约》为唯一真理来源，其他章节不得重复定义 Schema。

---

## §0. 权威数据契约（单一真理来源）

> **所有代码实现必须以本节定义为准。其他章节中的 JSON 示例仅为说明，不得覆盖本节定义。**

### §0.1 题目数据结构

```json
{
  "id": "uuid-string",
  "question_type": "COMPREHENSIVE_ANALYSIS",
  "content": "题目全文...",
  "core_keywords": ["接诉即办", "法治中国建设"],
  "time_limit_seconds": 180
}
```

**`question_type` 枚举（全文统一，禁止使用其他写法）**：

| 枚举值 | 中文题型 |
|--------|----------|
| `COMPREHENSIVE_ANALYSIS` | 综合分析题 |
| `PLANNING_ORGANIZATION` | 计划组织协调题 |
| `EMERGENCY_RESPONSE` | 应急应变题 |
| `INTERPERSONAL_RELATIONSHIPS` | 人际关系交往题 |
| `SELF_COGNITION` | 自我认知题 |
| `SCENARIO_SIMULATION` | 情景模拟题 |

### §0.2 LLM 输出字段（LLM 仅负责这些字段，其余由后端计算）

```json
{
  "analysis_ability":            {"score": 82.0, "reasoning": "..."},
  "organization_coordination":   {"score": 75.0, "reasoning": "..."},
  "emergency_response":          {"score": 78.0, "reasoning": "..."},
  "interpersonal_communication": {"score": 80.0, "reasoning": "..."},
  "language_expression":         {"score": 77.0, "reasoning": "..."},
  "job_matching":                {"score": 85.0, "reasoning": "..."},
  "structural_framework_check": {
    "is_complete": false,
    "missing_elements": ["长效机制"],
    "present_elements": ["表明态度", "分析原因", "提出对策"]
  },
  "improvement_suggestions": ["建议结尾结合乡村振兴政策进行拔高..."],
  "model_ideal_answer": "各位考官，关于这个问题，我的看法如下...",
  "rule_violations": []
}
```

**说明**：
- `score` 为 **0–100 百分制**，LLM 不输出 `max_score`、`weight`、`final_score`，这三者均为后端字段
- `paralinguistic_fluency_score`（维度7）**不进入 LLM Prompt**，由后端 `calculate_fluency_score()` 基于 Whisper 时间戳独立计算
- `rule_violations` 为 LLM 标记的规则红线列表（可选值：`CLICHE_ANALYSIS` / `NO_SAFETY_PLAN` / `EMERGENCY_HARDLINE` / `INTERPERSONAL_CONFLICT`），后端 `apply_rule_caps()` 读取后执行分数硬钳制（见 §7.1）

### §0.3 后端计算字段（不由 LLM 生成）

| 字段 | 类型 | 说明 |
|------|------|------|
| `paralinguistic_fluency_score` | float (0–100) | 基于 Whisper 时间戳规则计算，见 §7.1 |
| `anti_template_warning` | str \| None | P1 套话正则黑名单检测结果；命中正则条目 ≥3 时后端写入警告文案（如"检测到高频套话模式，命中 X 条黑名单词组，建议结合具体情境重组答案结构"），未触发或 P1 未启用时为 `null` |
| `final_score` | float | `Σ(score_i × weight_i)`，保留2位小数 |

**加权公式（后端硬编码，不允许 LLM 参与）**：

```
final_score = round(
  analysis_ability.score            × 0.20 +
  organization_coordination.score   × 0.15 +
  emergency_response.score          × 0.15 +
  interpersonal_communication.score × 0.15 +
  language_expression.score         × 0.15 +
  job_matching.score                × 0.10 +
  paralinguistic_fluency_score      × 0.10,
  2
)
```

### §0.4 数据库完整记录结构（写入 `evaluations` 表）

```json
{
  "id": "uuid",
  "user_id": "uuid",
  "question_id": "uuid",
  "transcript": "全文转写文本",
  "transcript_segments": [{"text": "...", "start": 0.0, "end": 1.2}],
  "audio_duration_seconds": 173.5,
  "analysis_ability_score": 82.0,
  "analysis_ability_reasoning": "...",
  "organization_coordination_score": 75.0,
  "organization_coordination_reasoning": "...",
  "emergency_response_score": 78.0,
  "emergency_response_reasoning": "...",
  "interpersonal_communication_score": 80.0,
  "interpersonal_communication_reasoning": "...",
  "language_expression_score": 77.0,
  "language_expression_reasoning": "...",
  "job_matching_score": 85.0,
  "job_matching_reasoning": "...",
  "paralinguistic_fluency_score": 74.0,
  "structural_framework_check": {"is_complete": false, "missing_elements": ["长效机制"]},
  "improvement_suggestions": ["..."],
  "model_ideal_answer": "...",
  "anti_template_warning": null,
  "final_score": 79.35,
  "created_at": "2026-02-28T10:00:00Z"
}
```

---

## 1. 产品概述与核心业务逻辑

本系统旨在解决中国公务员考试结构化面试备考阶段的核心痛点：考生缺乏高质量的模拟练习场景，且人工点评费用高昂、反馈周期漫长。本产品被定义为一款高度垂直的 AI 面试辅助训练工具，**初期服务约 5 名核心内测用户，定位为低并发、高实时性场景**（非高并发，不需要分布式中间件）。

系统以"全真模拟环境构建、语音转文本、基于 LLM 的多维深度评估"为核心业务逻辑，建立从题目随机调度、标准化倒计时录答、后端音频解析到生成多维可视化复盘报告的完整数据闭环。

**端到端处理目标**：用户提交录音 → 收到完整评估报告的总耗时目标值 ≤ 15 秒（含音频上传、ASR、LLM 推理三阶段）。

本 PRD 摒弃模糊语义（如"良好体验"），将所有业务逻辑解构为具备确定性、可测试性、可直接转化为代码与 API 契约的绝对指令。

### 1.1 核心目标用户画像与工程约束

系统初期部署规模严格限制在约 5 名核心测试用户。以下是用户特征提取及其对底层系统架构的工程约束：

| **用户** | **背景与岗位** | **核心缺陷** | **对系统的工程约束** |
|---|---|---|---|
| **用户A** | 应届生，报考市直机关文秘岗 | 答题陷入"学生思维"，缺乏政策敏感度 | 后端 Aho-Corasick 模块检测政策词汇命中率；政策词覆盖率 = `matched_count / required_count`（required 集合来自 `keyword_dict.json`）；`required_count == 0` 时值为 `null`，前端显示"该题型无必选政策词"，不注入 LLM Prompt；非零时此指标注入 LLM Prompt |
| **用户B** | 在职人员，报考基层综合执法岗 | 套用企业管理思维，忽视"依法行政"铁律 | LLM Prompt 强制包含"三大铁律"校验逻辑；违反原则（推脱责任/对抗上级）时，对应维度得分上限压制为 59 分 |
| **用户C** | 全职备考者，报考乡镇统筹协调岗 | 高压下思维短路，答题卡顿频繁 | 前端计时器漂移误差须 ≤ 1 秒/3 分钟（详见 §3.2）；后端基于 Whisper 时间戳统计停顿次数（间隔 **≥ 3.0 秒**）与语速，量化为副语言流畅度扣分项 |
| **用户D** | 跨专业备考者，报考财务审计岗 | 计划组织题遗漏"经费预算"、"安全预案"等闭环节点 | `question_type=PLANNING_ORGANIZATION` 时，LLM Prompt 强制注入"定、摸、筹、控、结"五步核对清单；`structural_framework_check.missing_elements` 高亮展示 |
| **用户E** | 多次进面"老考生"，报考党群机关 | 答题高度套路化，缺乏真情实感 | 后端 Aho-Corasick 检测套话黑名单命中率（P0）；正则黑名单命中计数作为 **P1 可选增强**，命中 ≥3 条时注入反模板化警告（黑名单词组如"随着…的发展"、"不可推卸的责任"、"为人民服务是我的宗旨"等） |

---

## 2. 核心功能清单与优先级排序

### 2.1 P0 级功能：核心数据闭环（不可妥协）

| **模块** | **工程约束** | **优先级** |
|---|---|---|
| **沉浸式考场 UI** | 全屏无干扰测试页面。前端状态机单向流转：`IDLE` → `READING`（审题60s）→ `RECORDING`（作答，默认180s）→ `PROCESSING`（骨架屏）→ `REVIEW`（报告）。**严禁模态弹窗**。音频采集使用 `MediaRecorder API`，**前端负责能力探测**（`isTypeSupported`），不强制 16kHz——后端统一转码保证提交给 Whisper 的格式为 `wav 16kHz mono`。 | P0 |
| **静态题库调度** | 从 6 大题型中随机抽取 3–5 题生成试卷。题目使用静态 JSON 文件或轻量 SQLite 只读加载。数据结构字段：`id`、**`question_type`**（见 §0.1 枚举）、`content`、`core_keywords`、`time_limit_seconds`。 | P0 |
| **ASR 转写引擎** | 后端将接收到的音频**统一转码**为 `wav 16kHz mono`（使用 `ffmpeg-python`），再调用 Groq `whisper-large-v3` API。前端采用"录音结束后一次性 POST 上传"策略，禁止 WebSocket 流式传输。Groq API 返回**词级时间戳**（`word_timestamps=True`），存储于 `transcript_segments`。 | P0 |
| **结构化 AI 评估引擎** | 后端使用 `openai-python >= 1.0` SDK，调用 `beta.chat.completions.parse()` 方法，以 §0.2 定义的 `LLMEvaluationOutput` Pydantic 模型作为 `response_format`。模型读取环境变量 `OPENAI_MODEL`（默认 `gpt-4o-mini`）。任何解析失败触发最多 2 次指数退避重试。 | P0 |
| **多维可视化复盘看板** | 根据 §0.3 后端完整结果渲染报告：七维雷达图（Recharts）、原音重放播放器（HTML5 `<audio>`）、音频进度与转写文本高亮同步（基于 `transcript_segments` 时间戳，详见 §4.5）。 | P0 |

### 2.2 P1 级功能：专业性增强

| **模块** | **工程约束** | **优先级** |
|---|---|---|
| **词汇审查与套话检测** | 后端 Aho-Corasick 多模式匹配：①高频政策词汇命中率；②套话黑名单命中数。两项指标作为上下文注入 LLM Prompt，提高评分准确性。**正则黑名单命中计数**（反模板化检测）作为本 P1 的可选增强：对照硬编码套话正则黑名单（如 `"随着.{0,10}的发展"`、`"不可推卸的责任"` 等条目，存于 `cliche_patterns.json`），命中数 ≥3 时在报告注入"反模板化警告"，无需外部语料库。 | P1 |
| **副语言特征持久化** | 将 `calculate_fluency_score()` 计算的停顿次数、语速、语气词密度原始数据一并写入 `evaluations` 数据库记录，供未来趋势分析使用。 | P1 |

### 2.3 P2 级功能：高阶模拟

| **模块** | **工程约束** | **优先级** |
|---|---|---|
| **压力性追问生成** | 完成试卷后，系统根据 LLM 识别的最大逻辑漏洞即时生成追问题。状态机拓展 `FOLLOW_UP_INTERVIEW` 节点，追问限时 60 秒，复用主评估引擎。 | P2 |

---

## 3. 用户故事 (User Stories — BDD 格式)

### 3.0 用户认证：登录与会话管理

- **作为** 受邀内测考生，**我想要** 通过邮箱密码登录，**以便** 我的记录与报告安全绑定账号。

- **Vibe Coding 约束**：路由 `/login`，调用 `supabase.auth.signInWithPassword()`，成功后 `access_token` 存入 **`sessionStorage`**（**严禁 `localStorage`**，防 XSS 持久化），重定向 `/dashboard`。所有鉴权页面 mount 时校验 token，过期则跳 `/login`。

- **验收标准（可自动化）**：
  - **Given** 输入错误密码点击登录 → **Then** HTTP 400，`data-testid="login-error"` 出现，文案固定"邮箱或密码错误"（不区分两种失败原因，防账号枚举），URL 保持 `/login`
  - **Given** 请求进行中 → **Then** 按钮 disabled + loading 态，防重复提交

### 3.1 考前设备检验

- **作为** 即将进入模拟流程的考生，**我想要** 在正式计秒前强制通过麦克风测试，**以便** 避免硬件问题导致采集失败。

- **Vibe Coding 约束**：组件初始化调用 `navigator.mediaDevices.getUserMedia({ audio: true })`，用 Web Audio API `AnalyserNode` 渲染实时音量波形。捕获 `NotAllowedError` 时，红色 inline 提示文本锁定"进入考场"按钮，**禁止弹窗**。

### 3.2 高压考场时间管理

- **作为** 容易超时的考生，**我想要** 看到极度醒目的倒计时，剩余 60 秒时颜色变红并有脉冲动效，**以便** 培养时间感知。

- **Vibe Coding 约束**：自定义 Hook `useInterviewTimer(initialSeconds, onExpireCallback)`。计时器用 `performance.now()` 基准替代纯 `setInterval`，结合 `document.visibilitychange` 事件在标签页切回时校准，确保**计时漂移绝对误差 ≤ 1 秒/3 分钟**。UI 使用 Tailwind `animate-pulse text-red-600`。

### 3.3 专项题型差异化评分

- **作为** 在计划组织题上经常丢分的考生，**我想要** AI 明确指出"定、摸、筹、控、结"中哪一步缺失，**以便** 针对性修补逻辑链。

- **Vibe Coding 约束**：后端 Prompt 工厂（Prompt Factory）读取 **`question_type`** 字段进行路由。`question_type === 'PLANNING_ORGANIZATION'` → 注入五步法核对清单；`question_type === 'EMERGENCY_RESPONSE'` → 注入六字诀核对清单。**禁止一刀切通用 Prompt**。

### 3.4 高分对照学习

- **作为** 语言口语化的应届生，**我想要** 看到 AI 生成的官方话语体系高分示范答案，**以便** 逐字比对模仿。

- **Vibe Coding 约束**：LLM 输出的 `model_ideal_answer` 字段（见 §0.2）在复盘看板中用左右双栏布局渲染：左侧考生原文高亮批注，右侧 AI 高分示范。

---

## 4. 验收标准 (Acceptance Criteria — Given/When/Then)

### 4.1 核心状态机：全真模拟生命周期

- **Given** 用户完成设备测试，路由推至 `/interview/mock`，题目数据加载至前端 Store
- **When** 页面完成首次内容绘制（FCP）
- **Then** 题目文本立即渲染，审题倒计时从 60 秒开始，录音引擎挂起

- **When** 审题倒计时归零 **或** 用户点击"思考完毕，开始作答"
- **Then** 自动调用 `MediaRecorder.start()`，答题倒计时（题目 `time_limit_seconds` 或默认 180 秒）显现，界面右上角出现带 `animate-pulse` 的红色录制指示灯

- **When** 用户点击"作答结束"按钮
- **Then** 调用 `MediaRecorder.stop()`，将音频 Chunks 合并为 Blob。非最后一题 → 状态重置加载下一题；最后一题 → POST 至 `/api/v1/evaluations/submit`，跳转 `PROCESSING` 骨架屏

### 4.2 数据流韧性：音频上传与 ASR 容错

- **Given** 录音结束，生成约 2MB 的音频 Blob（约 3 分钟）
- **When** 前端发起 `multipart/form-data` POST 请求
- **Then** 后端执行以下安全验证（验证失败立即返回，不进入 ASR 流程）：
  - `Content-Type` 须为 `audio/webm` 或 `audio/mp4`，否则返回 HTTP 400：`{"error_code": "ERR_INVALID_AUDIO"}`
  - 文件超过 **10MB** 返回 HTTP 413：`{"error_code": "ERR_FILE_TOO_LARGE"}`
  - 使用 `python-magic` 验证文件头魔数（防 Content-Type 伪造）

- **And** 通过验证后，后端用 `ffmpeg-python` **无条件转码**所有音频为 `wav 16kHz mono`（命令：`ffmpeg -i input -ar 16000 -ac 1 -f wav output.wav`，适用于 `audio/webm` 与 `audio/mp4` 等全部格式，策略统一，无分支），再调用 Groq Whisper API（单文件请求，非"并行"）

- **And** Groq API 返回 HTTP 502/504 或超时 → 最多 2 次指数退避重试；彻底失败返回 HTTP 503：`{"error_code": "ERR_ASR_TIMEOUT", "message": "语音转写服务当前不可用，请重试。"}`

- **And** 正常情况下，从前端提交到后端返回完整评估报告的**端到端耗时目标值 ≤ 15 秒**

### 4.3 AI 引擎结构化输出：大模型解析强约束

- **Given** 后端获取 ASR 转写文本，准备调用 `OPENAI_MODEL`（默认 `gpt-4o-mini`）发起评估
- **When** LLM 完成推理返回响应
- **Then** 返回内容须通过 `LLMEvaluationOutput` Pydantic 模型校验（见 §7.1 代码）

- **And** LLM 输出字段严格遵循 §0.2 定义：**仅包含** 6 个维度得分（0–100 百分制）、`structural_framework_check`、`improvement_suggestions`、`model_ideal_answer`、`rule_violations`

- **And** LLM **不输出** `final_score`、`paralinguistic_fluency_score`、`max_score`、`weight`——这三者由后端计算后追加

- **And** Pydantic 校验失败 → 触发最多 2 次重试，彻底失败返回 HTTP 503：`{"error_code": "ERR_LLM_PARSE_FAILED"}`

### 4.4 弱网络容错

- **Given** 用户正在录制（`RECORDING` 状态），网络物理断开
- **When** 答题倒计时结束，系统尝试上传
- **Then** 前端监听 `navigator.onLine` 或捕获 `fetch` 抛出的 `NetworkError`，立即阻断上传；音频 Blob 保留在当前页面内存中（**不写入 IndexedDB**，不做持久化）

- **And** 界面显示内联提示："**网络异常，请保持页面勿刷新**。网络恢复后点击'重试上传'按钮继续。"，**禁止弹窗**

- **And** 用户点击"重试上传" → 直接从内存中读取 Blob，重新 POST 至 `/api/v1/evaluations/submit`；上传成功后清除内存引用

> **降级说明（v1.5）**：MVP 阶段不引入 IndexedDB 持久化（跨页面状态机复杂度过高，极易产生状态死锁与竞争条件）。用户须保持页面不刷新，刷新后录音不可恢复属已知限制，验收时需明确告知内测用户。

### 4.5 复盘看板：音频与文本高亮同步

- **Given** 用户进入复盘看板，音频播放器与转写文本均已加载
- **When** 用户拖动进度条至第 30 秒
- **Then** 包含第 30 秒（±0.5 秒容差）内容的段落背景色变为 `#FEF3C7`（Tailwind `bg-amber-100`），调用 `scrollIntoView({ behavior: 'smooth', block: 'center' })`，其余段落恢复白色

- **When** 音频自然播放至下一段落起始时间戳
- **Then** 高亮平滑切换，无闪烁，帧间隔 ≤ 100ms（使用 `requestAnimationFrame` 驱动，**禁止 `setInterval` 轮询**）

- **And** 时间戳来源：`transcript_segments` 字段，每项结构：`{"text": "...", "start": 0.0, "end": 1.2}`

---

## 5. 量化非功能需求 (NFR)

> **重要**：以下指标分为两类。**「发版阻断」**：必须满足才能上线；**「监控目标」**：未达到时触发告警但不阻断发版。

### 5.1 性能指标

| 指标 | 目标值 | 类别 | 测试方式 |
|------|--------|------|----------|
| 端到端处理耗时（mock 链路，提交→报告） | ≤ 15 秒 | **发版阻断** | CI 内 mock 链路断言（假 ASR/假 LLM，不依赖外部网络，消除上游抖动干扰） |
| 端到端处理耗时（真实上游 P95） | ≤ 15 秒 | **监控目标** | 预发环境统计告警，不阻断合并 |
| ASR 子阶段耗时（P95，仅 Groq 推理） | ≤ 5 秒 | **监控目标** | 后端日志 + 告警阈值 |
| LLM TTFB（首字节响应） | ≤ 3.5 秒 | **监控目标** | 后端日志 |
| 考场界面 FCP | ≤ 2 秒 | **监控目标** | Lighthouse CI |
| 录制期间主线程 TBT | ≤ 50ms | **本地参考**（非 CI 指标） | 本地性能剖析（Web Vitals + 自定义性能埋点）；Lighthouse 对真实 `MediaRecorder` 场景覆盖有限、波动大，不作为自动化检测指标 |
| 计时器漂移 | ≤ 1 秒/3 分钟 | **发版阻断** | Jest 单元测试（模拟 visibility change） |

### 5.2 准确性与一致性（手动 Benchmark，不纳入 CI）

- **WER（字错率）**：标准普通话测试集（底噪 < 40dB），基础 WER ≤ 5%；调用 Whisper 时注入政策专有名词 `prompt` 参数，专有名词识别率 ≥ 95%。**注入截断约束（阻断项）**：Groq Whisper API 对 `prompt` 参数有约 224 tokens 上限，后端必须按当前 `question_type` 过滤 `keyword_dict.json`，仅取高频 Top 20 专有名词（按语料频次倒序）注入，超出部分截断；**禁止全量注入整个词典**，否则 Groq 返回 HTTP 400。

- **AI 评分一致性**【**手动 Benchmark，非 CI 阻断**】：
  - 发版前运行 `benchmark_eval.py`，对 20 道标准答案各调用 5 次，总分极差（Max-Min）≤ 3 分，结果记录于 `docs/benchmark_results.md`
  - 产品验收阶段：3 名经验考官独立打分，与系统分数 RMSE ≤ 8 分（属产品验收，非开发 CI）

### 5.3 数据安全与合规

- **录音 TTL**：音频上传至 Supabase Storage 后，Lifecycle Rules 硬性限制存活时间 ≤ 24 小时，到期物理删除

- **身份验证**：使用 Supabase Auth 内置 JWT（HS256 算法）。FastAPI 每个受保护路由通过 `supabase-py` 的 `auth.get_user(token)` 验证，令牌有效期 3600 秒

- **API 密钥安全**：`OPENAI_API_KEY`、`GROQ_API_KEY` 须写入服务端 `.env` 文件，**严禁暴露至前端任何环境变量**

- **数据隔离（RLS）**：数据库表级启用 Row Level Security，`evaluations` 表查询策略：`auth.uid() = user_id`

- **速率限制**：`/api/v1/evaluations/submit` 每用户每分钟最多 3 次请求，超出返回 HTTP 429

### 5.4 跨端兼容性

- **屏幕适配**：最小屏幕宽度 375px（iPhone SE）无横向滚动条。"结束录音"按钮点击热区 ≥ 48×48 物理像素

- **音频兼容**：前端 `isTypeSupported` 能力探测，**不强制客户端 16kHz**。后端统一用 `ffmpeg-python` 转码（命令：`ffmpeg -i input -ar 16000 -ac 1 -f wav output.wav`），Safari `audio/mp4` 与 Chrome `audio/webm` 均支持。回放使用 `URL.createObjectURL()` 原始 Blob，Safari 可原生解码

---

## 6. 技术栈选型与系统边界定义

### 6.1 系统边界（必须遵守，禁止混用）

```
┌─────────────────────────────────────────────────┐
│  Next.js 14（前端 / BFF 层）                     │
│  ✅ 负责：UI 渲染、状态管理、Supabase Auth 登录  │
│  ✅ 负责：Route Handlers（代理转发至 FastAPI）   │
│  ❌ 禁止：Server Actions 直接调用 OpenAI/Groq   │
│  ❌ 禁止：在前端代码暴露任何 AI API 密钥        │
└──────────────────┬──────────────────────────────┘
                   │ HTTP（内网）
┌──────────────────▼──────────────────────────────┐
│  FastAPI（Python 后端，AI 编排层）               │
│  ✅ 负责：音频接收、ffmpeg 转码、Groq ASR 调用  │
│  ✅ 负责：Prompt 工厂、openai-python LLM 调用   │
│  ✅ 负责：副语言流畅度计算、final_score 聚合    │
│  ✅ 负责：Supabase 数据库写入、Storage 上传     │
└─────────────────────────────────────────────────┘
```

**所有 ASR + LLM + 评分计算只走 FastAPI，Next.js 不直接接触 AI API。**

### 6.2 前端：Next.js 14 + Tailwind CSS + Shadcn/UI + Zustand

- **Vibe Coding 最佳宿主**：Cursor/v0.dev 对 React/Next.js/Tailwind 组合训练密度最高，AI 直接输出可运行代码
- **状态管理**：使用 `Zustand` 维护面试状态机（题目队列、倒计时、录音授权）。**禁止 Redux**
- **严禁使用 Gradio/Streamlit**：无法满足跨页面状态流转、精细录音 API 控制和复盘雷达图渲染

### 6.3 后端：FastAPI + Pydantic + openai-python SDK

- **异步非阻塞**：FastAPI 原生 `async/await`，避免高延迟 AI 调用阻塞线程池
- **结构化输出**：`openai-python >= 1.0` 的 `beta.chat.completions.parse()` + Pydantic `BaseModel` 作为 `response_format`，自动反序列化并抛出清晰校验错误
- **严禁引入 LangChain**：所有 LLM 调用均为单次线性结构化调用，LangChain 的抽象层引入不必要复杂度
- **ffmpeg 宿主依赖（阻断项）**：`ffmpeg-python` 仅为 Python wrapper，自身不包含可执行文件。部署 `Dockerfile` 必须包含以下指令，否则云端运行时直接抛出 `FileNotFoundError: [Errno 2] No such file or directory: 'ffmpeg'`：
  ```dockerfile
  RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*
  ```

### 6.4 数据库与鉴权：Supabase

- PostgreSQL + RLS 行级安全 + Supabase Auth（HS256 JWT）+ Supabase Storage
- Supabase CLI 生成 TypeScript 类型定义，打通前后端类型安全

### 6.5 核心 AI 模型

- **ASR**：Groq 托管的 `whisper-large-v3`（`word_timestamps=True`）。Groq LPU 可将 3 分钟音频推理控制在约 3–5 秒。
- **LLM**：默认 `gpt-4o-mini`（结构化 JSON 输出稳定，每次评估成本约 ¥0.05）

  ```
  # .env（不得提交至 Git）
  OPENAI_API_KEY=sk-...
  OPENAI_MODEL=gpt-4o-mini    # 升级改此变量，无需改代码
  GROQ_API_KEY=gsk_...
  ```

---

## 7. 评估引擎架构：评分逻辑与动态 Prompt 设计

### 7.1 七大评分维度与后端计算实现

**维度定义（全部使用 0–100 百分制，后端按权重聚合）**：

| # | 维度字段名 | 权重 | 考察重点 |
|---|-----------|------|----------|
| 1 | `analysis_ability` | 20% | 综合分析：透过现象看本质的宏观视野 |
| 2 | `organization_coordination` | 15% | 计划组织：从立项到落实的全流程把控 |
| 3 | `emergency_response` | 15% | 应急应变：危机处置"快、准、稳" |
| 4 | `interpersonal_communication` | 15% | 人际交往：情商与原则纪律平衡 |
| 5 | `language_expression` | 15% | 言语表达：流畅清晰、逻辑严密 |
| 6 | `job_matching` | 10% | 求职动机：忠诚度与岗位匹配度 |
| 7 | `paralinguistic_fluency_score` | 10% | **副语言流畅度**（不调用 LLM，规则计算） |

**维度7（副语言流畅度）扣分规则**：

| 扣分规则 | 扣分值 | 上限 |
|----------|--------|------|
| 停顿 **≥ 3.0 秒**（Whisper 词级时间戳相邻 gap） | −2 分/次 | −10 分 |
| 语速 <150 字/分钟 或 >280 字/分钟 | −5 分 | — |
| 语气词（"那个"/"嗯"/"就是说"/"然后就是"）密度 >5 次/分钟 | −3 分 | — |

基础分 80 分，最低保底 50 分。最终得分 = `max(50, 80 − 各项扣分之和)`

**Python 后端实现约束（For AI Agent）**：

```python
from typing import Literal
import logging

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


class DimensionScore(BaseModel):
    score: float = Field(..., ge=0, le=100, description="0-100百分制得分")
    reasoning: str = Field(..., description="针对性扣分依据")

class StructuralCheck(BaseModel):
    is_complete: bool
    missing_elements: list[str]
    present_elements: list[str]

# LLM 只输出这 6 个维度 + 结构检查 + 改进建议 + 示范答案 + 规则红线标记
class LLMEvaluationOutput(BaseModel):
    analysis_ability: DimensionScore
    organization_coordination: DimensionScore
    emergency_response: DimensionScore
    interpersonal_communication: DimensionScore
    language_expression: DimensionScore
    job_matching: DimensionScore
    structural_framework_check: StructuralCheck
    improvement_suggestions: list[str]
    model_ideal_answer: str
    rule_violations: list[Literal[
        "CLICHE_ANALYSIS",
        "NO_SAFETY_PLAN",
        "EMERGENCY_HARDLINE",
        "INTERPERSONAL_CONFLICT",
    ]] = Field(
        default_factory=list,
        description="LLM 标记的规则红线（强枚举）。后端 apply_rule_caps() 据此执行硬钳制。"
    )

    @field_validator("rule_violations", mode="before")
    @classmethod
    def filter_unknown_violations(cls, v: list) -> list:
        """过滤未知违规标识并记录日志，防止 LLM 拼写变体（如 EMERGENCY-HARDLINE）绕过硬钳制。"""
        VALID = {"CLICHE_ANALYSIS", "NO_SAFETY_PLAN", "EMERGENCY_HARDLINE", "INTERPERSONAL_CONFLICT"}
        filtered, unknown = [], []
        for item in v:
            (filtered if item in VALID else unknown).append(item)
        if unknown:
            logger.warning("未知 rule_violation 值已丢弃：%s", unknown)
        return filtered

# 后端完整结果（含规则计算的维度7与加权总分，不由 LLM 生成）
class InterviewResult(BaseModel):
    llm_output: LLMEvaluationOutput
    paralinguistic_fluency_score: float
    anti_template_warning: str | None = None  # P1 TF-IDF 反模板化警告；>60% 相似度时后端赋值，None 表示未触发或 P1 未启用

    def final_score(self) -> float:
        d = self.llm_output
        return round(
            d.analysis_ability.score            * 0.20 +
            d.organization_coordination.score   * 0.15 +
            d.emergency_response.score          * 0.15 +
            d.interpersonal_communication.score * 0.15 +
            d.language_expression.score         * 0.15 +
            d.job_matching.score                * 0.10 +
            self.paralinguistic_fluency_score   * 0.10,
            2
        )

def calculate_fluency_score(segments: list[dict]) -> float:
    """基于 Whisper 词级时间戳计算副语言流畅度，不调用 LLM。
    segments: [{"text": "...", "start": 0.0, "end": 1.2}, ...]
    """
    if not segments:
        return 80.0
    base = 80.0
    deduction = 0.0
    # 停顿检测（间隔 >= 3.0 秒）
    pauses = sum(
        1 for i in range(len(segments) - 1)
        if segments[i + 1]["start"] - segments[i]["end"] >= 3.0
    )
    deduction += min(pauses * 2, 10)
    # 语速检测
    total_chars = sum(len(s["text"]) for s in segments)
    duration_min = (segments[-1]["end"] - segments[0]["start"]) / 60
    if duration_min > 0:
        speed = total_chars / duration_min
        if speed < 150 or speed > 280:
            deduction += 5
    # 语气词检测
    fillers = ["那个", "嗯", "就是说", "然后就是"]
    full_text = "".join(s["text"] for s in segments)
    filler_count = sum(full_text.count(w) for w in fillers)
    if duration_min > 0 and filler_count / duration_min > 5:
        deduction += 3
    return max(50.0, base - deduction)


# ─── 后端硬钳制：防止 Prompt 漂移导致分数上限规则失效 ───────────────────────────

# 规则上限映射表（LLM 违规标识 → 受影响维度字段 & 分数上限）
RULE_CAPS: dict[str, tuple[str, float]] = {
    "CLICHE_ANALYSIS":        ("analysis_ability",            59.0),  # 综合分析-套话堆砌
    "NO_SAFETY_PLAN":         ("organization_coordination",   65.0),  # 计划-缺安全预案/经费
    "EMERGENCY_HARDLINE":     ("emergency_response",          40.0),  # 应急-暴力驱逐/违规变通
    "INTERPERSONAL_CONFLICT": ("interpersonal_communication", 40.0),  # 人际-顶撞/消极/越级
}

# ─── 确定性规则检测（与 LLM 标注并联，形成"双保险"）──────────────────────────────

# 仅用于 PLANNING_ORGANIZATION：若转写文本中无安全预案/经费相关词，直接命中 NO_SAFETY_PLAN
_SAFETY_KEYWORDS = {"安全预案", "经费预算", "经费保障", "安全保障"}


def _detect_violations_deterministically(transcript: str, question_type: str) -> set[str]:
    """对可结构化判定的规则执行确定性关键词检测。
    仅限 PLANNING_ORGANIZATION 题型的 NO_SAFETY_PLAN 检测；其他题型返回空集合。
    """
    violations: set[str] = set()
    if question_type == "PLANNING_ORGANIZATION":
        if not any(kw in transcript for kw in _SAFETY_KEYWORDS):
            violations.add("NO_SAFETY_PLAN")
    return violations


def apply_rule_caps(
    llm_output: LLMEvaluationOutput,
    transcript: str = "",
    question_type: str = "",
) -> LLMEvaluationOutput:
    """后端硬钳制：LLM 标注 OR 确定性检测命中即触发分数上限（双保险）。
    Prompt 约束为软引导，本函数为最终判定，优先级高于 LLM 原始输出。
    调用时机：LLM 输出经 Pydantic 解析后、写入数据库前。
    """
    output = llm_output.model_copy(deep=True)
    # 合并 LLM 标注 + 确定性检测结果，任一命中即触发钳制
    all_violations = set(output.rule_violations)
    all_violations |= _detect_violations_deterministically(transcript, question_type)
    for violation in all_violations:
        if violation in RULE_CAPS:
            field_name, cap = RULE_CAPS[violation]
            dimension: DimensionScore = getattr(output, field_name)
            if dimension.score > cap:
                dimension.score = cap
    return output
```

### 7.2 动态 Prompt 工厂（按 `question_type` 路由）

后端读取 `question_type` 字段，动态注入对应考官阅卷清单作为 `system` 角色指令。**禁止使用通用 Prompt。**

#### 7.2.1 `COMPREHENSIVE_ANALYSIS`（综合分析题）

System Prompt 强制约束 LLM 检查"点、析、对、升"四段论：
1. **点**：开篇前两句是否干脆抛出官方视角观点
2. **析**：是否多维度透视根源（政治/经济/社会/监督）
3. **对**：对策是否具体可操作，是否强调"长效治理机制"
4. **升**：结尾是否牵引至国家宏观战略（共同富裕/乡村振兴）

**硬性扣分**：全文套话堆砌或回避矛盾 → `analysis_ability.score` 上限 59 分

#### 7.2.2 `PLANNING_ORGANIZATION`（计划组织协调题）

System Prompt 强制检查"定、摸、筹、控、结"五步闭环：
1. **定**：目标定位精准不跑题
2. **摸**：是否有前期调研摸底
3. **筹**：人员分工、物资、时间节点是否细致
4. **控**：现场秩序把控，是否预设突发干预方案
5. **结**：是否有总结报告，是否沉淀为长效机制

**否决项**：未提及"安全预案"或"经费预算" → `organization_coordination.score` 强制 ≤ 65 分

#### 7.2.3 `EMERGENCY_RESPONSE`（应急应变题）

System Prompt 校验"稳、明、调、解、报、总"六字诀时序：
1. **稳**：第一反应安抚情绪、隔离危险源
2. **明**：了解事件真实原因与诉求
3. **调**：调动联动部门资源（电力/公安/医疗）
4. **解**：给出化解危机的具体手段
5. **报**：危机解除后第一时间上报领导
6. **总**：复盘反思，修缮防范预案

**红线**：提出暴力驱逐/违规变通/推诿责任 → `emergency_response.score` 上限 40 分

#### 7.2.4 `INTERPERSONAL_RELATIONSHIPS`（人际关系交往题）

- **涉领导矛盾**：先体现"尊重服从"，再"委婉沟通、以大局为重执行"。出现顶撞/消极怠工/越级上访 → `interpersonal_communication.score` ≤ 40 分
- **涉同事冲突**：克制情绪，私下真诚沟通，共探双赢。

#### 7.2.5 政策词汇与套话分析（预处理注入 LLM）

在调用 LLM 前，后端先运行：

1. **Aho-Corasick 政策词汇扫描**（P0 必须实现）：词典来自 `keyword_dict.json`（含"两个确立"、"法治中国建设"、"网格智治"、"接诉即办"、"穿透式调研"、"国之大者"等）。公式：`policy_coverage = matched_count / required_count`（required 集合由 `question_type` 决定）。**除零边界**：`required_count == 0` 时，`policy_coverage = null`，不注入 Prompt，前端展示固定文案"该题型无必选政策词"。

2. **Aho-Corasick 套话黑名单扫描**（P0）：统计套话命中数量，注入 Prompt 作为上下文提示。

3. **正则黑名单反模板化检测**（**P1 可选增强**）：对转写文本执行正则匹配，黑名单词组硬编码于 `cliche_patterns.json`（示例条目：`"随着.{0,10}的发展"`、`"不可推卸的责任"`、`"为人民服务是我的宗旨"`、`"加强领导，落实责任"`）。命中条目数 ≥3 时在报告注入反模板化警告；后端将结果写入 `anti_template_warning` 字段（格式："检测到高频套话模式，命中 X 条黑名单词组，建议结合具体情境重组答案结构"）。**无外部语料依赖，黑名单由产品方在 `cliche_patterns.json` 中逐步维护扩充。**

---

## 8. 明确排除范围 (Explicit Out of Scope)

以下功能**绝对禁止**出现在 MVP 任何代码分支、接口设计或数据库 Schema 中：

1. **笔试题库（行测/申论）**：本系统只处理结构化面试论述题，题目表 Schema 不允许有选择题/填空题字段。

2. **真人考官介入系统**：禁止开发"考官阅卷端"、"管理员后台"、"申诉审核流"、"师生连麦"等功能，一切评判由 AI 引擎独立完成。

3. **视频流面容分析**：MVP 禁止向后端传输视频流。摄像头**仅允许在本地开启作为镜像预览**（不采集、不保存、不上传）。**禁止"本地保存录像"功能**（增加存储权限复杂度，MVP 无实际价值）。

4. **原生移动端 App**：交付产物为响应式 Web App，禁止使用 React Native/Flutter/Swift。

5. **分布式中间件**：5 名用户场景不需要 Kubernetes、Redis、RabbitMQ/Kafka。FastAPI 异步 + 单 Postgres 实例足够。

6. **商业化接口**：禁止集成微信支付/支付宝/短信验证码/公安网实名认证。用户体系仅靠 Supabase Auth 邮箱密码登录或硬编码邀请码白名单。

---

## 9. 致 AI 编码执行智能体（To the Agentic Coder）

进入代码构建阶段时，请严格遵守以下执行指令：

1. **§0《权威数据契约》是唯一真理来源**。当代码与其他章节描述发生冲突时，以 §0 为准。

2. **系统边界绝对遵守**：所有 ASR + LLM + 评分计算只走 FastAPI。Next.js Route Handler 仅作代理层，禁止在 Server Actions 中直接调用 AI API。

3. **前端实现 `useInterviewFlowManager` 自定义 Hook**，封装状态机完整生命周期，必须编写单元测试覆盖所有状态跳转，禁止存在未定义中间态。

4. **后端调用 LLM 时使用 `LLMEvaluationOutput` Pydantic 模型**（见 §7.1）作为 `response_format`，解析失败触发最多 2 次重试，彻底失败返回结构化错误。

5. **`question_type` 枚举全文统一**（见 §0.1），禁止在任何地方使用 `category`、`type`、`ORGANIZATION`（不带 PLANNING_ 前缀）等旧写法。

6. **停顿阈值全文统一为 ≥ 3.0 秒**，基于 Whisper 词级时间戳相邻 gap 计算。

7. **不引入 LangChain**，不引入 Kubernetes/Redis/RabbitMQ，不在前端暴露 AI API 密钥，不保存本地录像文件。

8. **后端硬钳制必须在入库前执行**：LLM 输出经 Pydantic 解析后，必须调用 `apply_rule_caps(llm_output, transcript, question_type)` 再写入数据库并计算 `final_score`。`rule_violations` 字段由 LLM 根据 Prompt 中的红线描述填写（强枚举，未知值自动丢弃并写入 warning 日志）；`apply_rule_caps` 同时执行 LLM 标注检测与确定性关键词检测（双保险：任一命中即钳制），按 `RULE_CAPS` 映射表执行强制上限（见 §7.1）。

9. **`policy_coverage` 除零防护**：Aho-Corasick 扫描前检查 `required_count`；为零时将 `policy_coverage` 记为 `null`，不注入 Prompt 上下文，API 响应及前端复盘看板统一显示"该题型无必选政策词"，不输出数值。

10. **`ffmpeg` 部署依赖（阻断项）**：后端 `Dockerfile` 必须包含 `RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*`，禁止仅安装 `ffmpeg-python` wrapper 而忽略宿主二进制依赖，否则 `ffmpeg-python` 在运行时抛出 `FileNotFoundError`，整个音频处理管道崩溃。

11. **Whisper Prompt 截断（阻断项）**：调用 Groq Whisper API 时，`prompt` 参数注入必须按 `question_type` 过滤后取高频 Top 20 政策关键词，约束在 224 tokens 以内；**禁止全量注入 `keyword_dict.json`**，否则 Groq 返回 HTTP 400，ASR 链路中断。

12. **`anti_template_warning` 写入（P1）**：P1 正则黑名单检测完成后，后端须将检测结果赋值给 `InterviewResult.anti_template_warning`，并写入 `evaluations` 表的 `anti_template_warning` 列；未触发时必须显式写入 `null`，禁止省略字段——前端复盘看板根据该字段是否为 `null` 决定是否渲染警告横幅。**禁止引入 `jieba`、外部停用词表或语料库文件**。
