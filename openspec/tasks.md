## 1. 项目初始化与基础设施

- [ ] 1.1 初始化 Next.js 14 项目（`create-next-app`），配置 Tailwind CSS + Shadcn/UI + Zustand
- [ ] 1.2 初始化 FastAPI 项目，配置 `openai-python >= 1.0`、`pydantic`、`ffmpeg-python`、`python-magic`、`ahocorasick`
- [ ] 1.3 创建 Supabase 项目，执行 `evaluations` 表 SQL Schema（含 PRD §0.4 全部 15+ 字段）
- [ ] 1.4 配置 Supabase RLS：`evaluations` 表策略 `auth.uid() = user_id`
- [ ] 1.5 配置 Supabase Storage Bucket，设置 Lifecycle Rule 音频 TTL ≤ 24 小时
- [ ] 1.6 编写后端 `Dockerfile`，包含 `RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*`
- [ ] 1.7 配置 `.env`（后端）和 `.env.local`（前端），验证 OPENAI_API_KEY、GROQ_API_KEY、Supabase 连接

## 2. 数据文件准备

- [ ] 2.1 创建 `keyword_dict.json`：按 6 大 `question_type` 分组，每组包含必选政策词汇及语料频次排序
- [ ] 2.2 创建 `cliche_patterns.json`：包含 ≥10 条套话正则黑名单种子条目（如 `"随着.{0,10}的发展"`、`"不可推卸的责任"` 等）
- [ ] 2.3 创建题库静态 JSON（或 SQLite），覆盖 6 大题型各 ≥3 题，字段：id、question_type、content、core_keywords、time_limit_seconds

## 3. 用户认证

- [ ] 3.1 实现 `/login` 页面，调用 `supabase.auth.signInWithPassword()`，access_token 存入 sessionStorage
- [ ] 3.2 实现登录错误处理：HTTP 400 时显示 `data-testid="login-error"` 文案"邮箱或密码错误"，URL 不跳转
- [ ] 3.3 实现防重复提交：登录进行中按钮 disabled + loading 态
- [ ] 3.4 实现受保护路由守卫：mount 时校验 JWT，过期/缺失重定向至 /login
- [ ] 3.5 实现 FastAPI JWT 验证中间件：每个受保护路由调用 `supabase-py auth.get_user(token)`
- [ ] 3.6 实现 `/api/v1/evaluations/submit` 速率限制：每用户每分钟最多 3 次，超出返回 HTTP 429

## 4. 模拟考场流程

- [ ] 4.1 实现 `useInterviewTimer(initialSeconds, onExpireCallback)` Hook：`performance.now()` 计时 + `visibilitychange` 校准
- [ ] 4.2 编写 `useInterviewTimer` 单元测试：覆盖正常计时、标签页切换、剩余 60 秒变红、倒计时归零回调
- [ ] 4.3 实现 `useInterviewFlowManager` Hook：管理五态状态机完整生命周期（IDLE/READING/RECORDING/PROCESSING/REVIEW）
- [ ] 4.4 编写 `useInterviewFlowManager` 单元测试：覆盖所有状态跳转路径，验证无未定义中间态
- [ ] 4.5 实现考前设备检测组件：`getUserMedia` 权限检测 + Web Audio API 音量波形 + `NotAllowedError` 内联提示
- [ ] 4.6 实现题库调度逻辑：从 6 大题型随机抽取 3–5 题，加载至 Zustand Store
- [ ] 4.7 实现 `/interview/mock` 页面：全屏无干扰考场 UI，禁止模态弹窗，录制指示灯 animate-pulse

## 5. 音频采集与 ASR 管道

- [ ] 5.1 实现前端 MediaRecorder 录音采集：`isTypeSupported` 能力探测，录音结束合并 Blob Chunks
- [ ] 5.2 实现弱网容错：捕获 NetworkError / onLine=false，Blob 保留内存，显示内联提示 + 手动"重试上传"按钮
- [ ] 5.3 实现后端音频安全验证：Content-Type 校验 + 10MB 大小限制 + python-magic 魔数验证
- [ ] 5.4 实现 ffmpeg 转码管道：所有格式无条件转码为 `wav 16kHz mono`（无格式分支）
- [ ] 5.5 实现 Whisper prompt 截断注入：按 question_type 过滤 keyword_dict.json，取 Top-20，≤224 tokens
- [ ] 5.6 实现 Groq Whisper API 调用：`word_timestamps=True`，返回 transcript_segments 词级时间戳
- [ ] 5.7 实现 ASR 重试逻辑：最多 2 次指数退避，彻底失败返回 HTTP 503 + ERR_ASR_TIMEOUT

## 6. AI 评估引擎

- [ ] 6.1 实现 `LLMEvaluationOutput` Pydantic 模型（含 `filter_unknown_violations` 字段校验器）
- [ ] 6.2 实现 `InterviewResult` Pydantic 模型（含 `final_score()` 加权计算方法）
- [ ] 6.3 实现 Prompt 工厂：按 `question_type` 路由至对应考官评分清单（4 种差异化 System Prompt）
- [ ] 6.4 实现 `openai-python beta.chat.completions.parse()` LLM 调用：2 次重试，彻底失败返回 HTTP 503 + ERR_LLM_PARSE_FAILED
- [ ] 6.5 实现 `calculate_fluency_score(segments)`：停顿（≥3.0s）、语速、语气词三项扣分规则
- [ ] 6.6 实现 `_detect_violations_deterministically(transcript, question_type)`：PLANNING_ORGANIZATION 安全预案确定性检测
- [ ] 6.7 实现 `apply_rule_caps(llm_output, transcript, question_type)`：RULE_CAPS 双保险硬钳制，入库前调用
- [ ] 6.8 实现 `OPENAI_MODEL` 环境变量读取，缺失时 fallback 至 `gpt-4o-mini`

## 7. 词汇分析管道

- [ ] 7.1 实现 Aho-Corasick 政策词汇扫描：计算 policy_coverage，required_count=0 时设为 null
- [ ] 7.2 实现 Aho-Corasick 套话黑名单扫描：统计命中数，作为 LLM Prompt 上下文注入
- [ ] 7.3 实现 P1 正则黑名单反模板化检测：加载 cliche_patterns.json，命中 ≥3 时写入 anti_template_warning（标准库 re 模块，不引入 jieba）

## 8. 数据写入与 API 端点

- [ ] 8.1 实现 `/api/v1/evaluations/submit` 端点完整流程：验证 → 转码 → ASR → 词汇分析 → LLM 评估 → apply_rule_caps → final_score → 写库
- [ ] 8.2 实现 `evaluations` 表写入：所有 PRD §0.4 字段，anti_template_warning 未触发时显式写入 null
- [ ] 8.3 实现 Supabase Storage 音频上传（仅后端操作）
- [ ] 8.4 实现端到端耗时 mock 链路 CI 断言：假 ASR + 假 LLM 响应，验证流程耗时 ≤15s

## 9. 复盘看板

- [ ] 9.1 实现七维雷达图（Recharts RadarChart），7 个维度轴与评分数据绑定
- [ ] 9.2 实现 HTML5 `<audio>` 播放器 + transcript_segments 高亮同步（requestAnimationFrame 驱动，±0.5s 容差）
- [ ] 9.3 实现 `scrollIntoView` 自动滚动：高亮段落 bg-amber-100，帧间隔 ≤100ms
- [ ] 9.4 实现左右双栏对照：左侧考生转写原文（批注），右侧 model_ideal_answer
- [ ] 9.5 实现 anti_template_warning 横幅：字段非 null 时显示警告横幅，null 时不渲染
- [ ] 9.6 实现 structural_framework_check 展示：missing_elements 警告色，present_elements 绿色
- [ ] 9.7 实现 improvement_suggestions 列表渲染

## 10. 跨端适配与安全加固

- [ ] 10.1 验证最小屏幕宽度 375px（iPhone SE）无横向滚动条
- [ ] 10.2 验证"结束录音"按钮点击热区 ≥ 48×48 物理像素
- [ ] 10.3 验证 Safari audio/mp4 + Chrome audio/webm 均可正常录制、上传、转码
- [ ] 10.4 确认 OPENAI_API_KEY 和 GROQ_API_KEY 不出现在任何前端代码或前端环境变量中
- [ ] 10.5 运行 `benchmark_eval.py`：20 道标准答案各 5 次，总分极差 ≤3 分，结果写入 `docs/benchmark_results.md`
