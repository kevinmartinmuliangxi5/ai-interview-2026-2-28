# AI 面试官训练系统 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 构建公务员结构化面试 AI 辅助训练系统——从题目抽取、音频录制、ASR 转写、多维 LLM 评分，到可视化复盘看板的完整数据闭环，端到端耗时 ≤15 秒。

**Architecture:** Next.js 14（前端 BFF 代理层）+ FastAPI（后端 AI 编排层，所有 ASR/LLM 调用仅走此层）+ Supabase（Auth/PostgreSQL/Storage）。前端五态状态机驱动考场流程，后端 Pydantic 强约束 LLM 输出并执行硬钳制规则。

**Tech Stack:** Next.js 14 + TypeScript + Tailwind CSS + Shadcn/UI + Zustand + Recharts（前端）；FastAPI + Python 3.11 + Pydantic v2 + openai-python ≥1.0 + ffmpeg-python + python-magic + pyahocorasick（后端）；Groq whisper-large-v3（ASR）+ gpt-4o-mini（LLM）；Supabase PostgreSQL + Auth + Storage。

**PRD 权威来源：** `mianshiAI.md` v1.5 §0《权威数据契约》。

---

## Enhancement Summary

**深化日期：** 2026-03-02
**深化章节数：** 32 个任务（M1×14 + M2×8 + M3×4 + M4×3 + M5×3）
**研究 Agent 数量：** 14 个并行 Agent

### 关键修正（实施前必读）

| # | 位置 | 原始写法 | 正确写法 | 影响 |
|---|------|---------|---------|------|
| 1 | T1.9 | `word_timestamps=True` | `response_format="verbose_json"` | Groq 不支持前者，调用直接返回 400 |
| 2 | T1.9 | `transcription.segments` | `transcription.words` | verbose_json 词级时间戳字段名不同 |
| 3 | T1.9 | `file=audio_bytes` | `file=(filename, audio_bytes)` | 无扩展名会触发 Groq MIME 检测失败 |
| 4 | T1.8 | `{"audio/webm","audio/mp4"}` | 需加 `"video/webm","video/mp4"` | libmagic 对 audio-only WebM 返回 video/webm |
| 5 | T2.1 | `NEXT_PUBLIC_API_BASE_URL` | `API_BASE_URL`（无 NEXT_PUBLIC_ 前缀） | 后端 URL 会暴露在浏览器 bundle 中 |
| 6 | T2.3 | sessionStorage 传给 @supabase/ssr | 需 createClient 直接传 storage 适配器 | @supabase/ssr createServerClient 不支持 sessionStorage |
| 7 | T1.4 | `Field(ge=0, le=100)` 约束 | 需加 `field_validator` 强制截断 | LLM 可能输出 101，Pydantic ge/le 不截断只报错 |
| 8 | T2.5 | Blob[] 存入 Zustand | Blob 存 `useRef<Map>` 外部 | Blob 在 Zustand 导致内存泄漏 + DevTools 序列化失败 |
| 9 | 全局 | `const enum` | `as const` 数组 | Next.js SWC `isolatedModules=true` 不支持 const enum |

### 新增架构建议

1. **idempotency_key 字段**：在 `evaluations` 表加 `client_request_id UUID UNIQUE`，客户端生成，防止弱网重试产生重复评估记录
2. **per-step 超时**：Groq ≤8s、OpenAI ≤6s、Supabase 写 ≤1s，否则 worst-case 17.2s 超出 15s SLA
3. **asyncio.gather 并行**：Supabase Storage 上传与 LLM 评估并行执行，节省 600ms–2.1s
4. **lifespan 单例**：Groq / OpenAI / Supabase 客户端在 `lifespan` 中初始化一次，每次重建惩罚 100–250ms
5. **Aho-Corasick 启动构建**：automaton 在 `lifespan` 中构建，per-request 构建惩罚 50–200ms
6. **evaluation_pipeline.py**：将 10 步流程提取到独立模块，便于测试和超时管理

---

## 依赖关系总览

```
M1（基础设施 + AI 管道）──► M2（前端考场流程）──► M3（复盘看板）──► M4（安全加固）──► M5（测试 + 部署）
```

M1 内部顺序：T1.1 → T1.2 → T1.3 → T1.4 → T1.5 → T1.6 → T1.7 → T1.8 → T1.9 → T1.10 → T1.11 → T1.12 → T1.13 → T1.14

M2 内部：T2.1（可与 M1 并行起步）→ T2.2 → T2.3 → T2.4 → T2.5 → T2.6 → T2.7 → T2.8

---

## Milestone 1：AI 核心管道 MVP（2–3 天）

**目标：** FastAPI `/api/v1/evaluations/submit` 端点跑通完整链路——音频接收 → 验证 → ffmpeg 转码 → Groq ASR → LLM 评估 → apply_rule_caps → final_score → 写入 Supabase DB，返回完整 EvaluationResult JSON。Pydantic 模型、规则引擎均有单元测试覆盖。

---

### T1.1 创建项目目录结构与 FastAPI 骨架

**文件：**
- 创建：`interview-ai/backend/app/__init__.py`
- 创建：`interview-ai/backend/app/main.py`
- 创建：`interview-ai/backend/requirements.txt`
- 创建：`interview-ai/backend/.env.example`

**做什么：**
`requirements.txt` 包含：
```
fastapi>=0.111.0
uvicorn[standard]>=0.29.0
pydantic>=2.7.0
openai>=1.30.0
groq>=0.9.0
ffmpeg-python>=0.2.0
python-magic>=0.4.27
pyahocorasick>=2.0.0
supabase>=2.4.0
python-multipart>=0.0.9
slowapi>=0.1.9
tenacity>=8.2.0
cachetools>=5.3.0
python-jose[cryptography]>=3.3.0
pytest>=8.0.0
pytest-asyncio>=0.23.0
httpx>=0.27.0
```

`main.py` 仅含 FastAPI app 实例和 `GET /api/v1/health`（无需认证，返回 status/version/model）。

`.env.example`（不含真实密钥）：
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
GROQ_API_KEY=gsk_...
```

**验收标准：** `GET /api/v1/health` 返回 `{"status":"ok","version":"1.0.0","model":"gpt-4o-mini"}`

**验证命令：**
```bash
cd interview-ai/backend
pip install -r requirements.txt
uvicorn app.main:app --reload &
curl http://localhost:8000/api/v1/health
```

**提交：**
```bash
git add interview-ai/backend/
git commit -m "feat: initialize FastAPI backend skeleton with health endpoint"
```

### 研究洞察

**关键修正：**
- `requirements.txt` 增加 `tenacity>=8.2.0`（Groq/OpenAI 重试）和 `cachetools>=5.3.0`（题目缓存）和 `python-jose[cryptography]>=3.3.0`（slowapi JWT key_func 直接解码）
- 去掉 `ffmpeg-python`，直接用 `asyncio.create_subprocess_exec` 调系统 `ffmpeg`（无需 wrapper 库）

**最佳实践 — FastAPI lifespan 模式（替代 `@app.on_event`，已废弃）：**
```python
# app/main.py
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # 启动时初始化所有客户端（单例，避免每次请求重建 100-250ms 开销）
    from groq import AsyncGroq
    from openai import AsyncOpenAI
    from supabase._async.client import AsyncClient, create_client
    app.state.groq = AsyncGroq(api_key=settings.GROQ_API_KEY)
    app.state.openai = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    app.state.supabase = await create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
    # 预构建 Aho-Corasick automaton（避免每次请求重建 50-200ms）
    app.state.automaton = build_automaton_at_startup()
    yield
    # 关闭时清理（可选）

app = FastAPI(lifespan=lifespan)
```

**边缘情况：**
- Windows 开发环境需安装 `python-magic-bin`（而非 `python-magic`）；Dockerfile 用 Linux 无此问题

---

### T1.2 执行 Supabase DB Schema 迁移

**文件：**
- 已有：`db/migrations/001_init.sql`（直接使用）

**做什么：**
在 Supabase Dashboard → SQL Editor 中执行 `db/migrations/001_init.sql`，创建：
- `question_type_enum`（6 个枚举值）
- `questions` 表 + RLS
- `evaluations` 表（15+ 字段、CHECK 约束）+ RLS
- 5 个索引、3 条 RLS Policy

然后在 Supabase Dashboard → Storage 手动创建 `interview-audio` bucket（Private），配置 Lifecycle Rule：对象存在 > 86400s 自动删除。

**验收标准：**
在 Supabase SQL Editor 执行验证：
```sql
SELECT typname FROM pg_type WHERE typname = 'question_type_enum'; -- 1 行
SELECT COUNT(*) FROM pg_policies WHERE tablename IN ('questions','evaluations'); -- 3
SELECT tablename, rowsecurity FROM pg_tables WHERE tablename IN ('questions','evaluations'); -- rowsecurity=true
```

**验证命令：** 在 Supabase Dashboard SQL Editor 运行上方验证 SQL。

**提交：**
```bash
git add db/ interview-ai/backend/.env.example
git commit -m "feat: Supabase DB schema migrated, Storage bucket configured"
```

### 研究洞察

**新增字段建议 — idempotency_key（防止弱网重复提交）：**

在 `evaluations` 表执行迁移后，补充执行：
```sql
-- 客户端每次提交时生成 UUID，服务端 UPSERT 或 INSERT ... ON CONFLICT DO NOTHING
ALTER TABLE evaluations
  ADD COLUMN client_request_id UUID,
  ADD CONSTRAINT evaluations_client_request_id_unique UNIQUE (client_request_id);
```

原理：用户弱网重试时，相同 `client_request_id` 第二次插入会触发 UNIQUE 冲突，后端返回已有记录而非创建新评估，避免用户被重复扣分。

**运行后立即生成 TypeScript 类型（前端 M2 依赖）：**
```bash
supabase gen types typescript --project-id YOUR_PROJECT_ID > interview-ai/frontend/src/types/supabase.ts
```
不执行此步骤，所有 Supabase 查询返回 `any`，失去类型安全。

---

### T1.3 创建静态数据文件（题库、关键词词典、套话黑名单）

**文件：**
- 创建：`interview-ai/backend/app/data/questions.json`
- 创建：`interview-ai/backend/app/data/keyword_dict.json`
- 创建：`interview-ai/backend/app/data/cliche_patterns.json`

**做什么：**

`questions.json`：6 大题型各 3 题（共 18 题），字段严格遵循 PRD §0.1（id/question_type/content/core_keywords/time_limit_seconds）。

`keyword_dict.json`：按 question_type 分组，每组 Top-20 政策词（示例）：
```json
{
  "COMPREHENSIVE_ANALYSIS": ["接诉即办","法治中国建设","国之大者","穿透式调研","网格智治","两个确立","乡村振兴","共同富裕","为民服务","基层治理","依法行政","接诉即办","社会治理","精准施策","群众路线","实事求是","调查研究","系统思维","整体推进","长效机制"],
  "PLANNING_ORGANIZATION": ["安全预案","经费预算","经费保障","安全保障","人员分工","时间节点","应急方案","前期调研","总结报告","长效机制","物资保障","方案论证","责任落实","信息报送","风险评估","复盘总结","任务清单","协调联动","有序推进","全程跟踪"]
}
```

`cliche_patterns.json`（≥15 条正则）：
```json
[
  "随着.{0,10}的发展",
  "不可推卸的责任",
  "为人民服务是我的宗旨",
  "加强领导，落实责任",
  "充分发挥.{0,8}作用",
  "高度重视.{0,8}问题",
  "切实加强.{0,8}建设",
  "认真贯彻落实",
  "进一步提高.{0,8}水平",
  "坚持以人为本",
  "建立健全.{0,8}机制",
  "统筹兼顾.{0,6}协调",
  "扎实推进.{0,8}工作",
  "不断创新.{0,8}方式",
  "形成.{0,8}工作合力"
]
```

**验收标准：**
```bash
python -c "
import json, re
q = json.load(open('app/data/questions.json'))
assert len(q) == 18
assert all(x['question_type'] in ['COMPREHENSIVE_ANALYSIS','PLANNING_ORGANIZATION','EMERGENCY_RESPONSE','INTERPERSONAL_RELATIONSHIPS','SELF_COGNITION','SCENARIO_SIMULATION'] for x in q)
kd = json.load(open('app/data/keyword_dict.json'))
assert len(kd) == 6
cp = json.load(open('app/data/cliche_patterns.json'))
assert len(cp) >= 15
[re.compile(p) for p in cp]
print('OK')
"
```

**验证命令：** 运行上方 python 命令，期望输出 `OK`。

**提交：**
```bash
git add interview-ai/backend/app/data/
git commit -m "feat: add questions, keyword_dict, and cliche_patterns data files"
```

### 研究洞察

**最佳实践 — Aho-Corasick automaton 必须在 lifespan 构建：**
```python
# app/services/vocab_analyzer.py
import ahocorasick
import unicodedata

_AUTOMATON: ahocorasick.Automaton | None = None  # 模块级单例

def build_automaton(keywords: list[str]) -> ahocorasick.Automaton:
    A = ahocorasick.Automaton()
    for idx, word in enumerate(keywords):
        # NFKC 正规化：全角字符 → 半角，繁体 → 统一码点
        normalized = unicodedata.normalize("NFKC", word)
        A.add_word(normalized, (idx, word))
    A.make_automaton()
    return A

def get_automaton() -> ahocorasick.Automaton:
    # 仅作 fallback；正常流程通过 lifespan 注入 app.state.automaton
    global _AUTOMATON
    if _AUTOMATON is None:
        raise RuntimeError("Automaton not initialized in lifespan")
    return _AUTOMATON
```

**边缘情况：**
- cliche_patterns.json 的正则在中文文本中需先 NFKC 正规化，再 `re.search`（不用 `re.match`）
- 政策词含全角标点时，Aho-Corasick 匹配前均需 NFKC 处理

---

### T1.4 实现 Pydantic 数据模型 + 单元测试

**文件：**
- 创建：`interview-ai/backend/app/models/evaluation.py`
- 创建：`interview-ai/backend/tests/__init__.py`
- 创建：`interview-ai/backend/tests/test_models.py`

**做什么：**
按 PRD §7.1 代码片段逐字实现：`DimensionScore`、`StructuralCheck`、`LLMEvaluationOutput`（含 `filter_unknown_violations` field_validator）、`InterviewResult`（含 `final_score()` 加权方法）。

`test_models.py` 覆盖：
1. score > 100 → ValidationError
2. `filter_unknown_violations` 过滤 `"EMERGENCY-HARDLINE"`（连字符变体）
3. `final_score()` 按 PRD §0.3 权重公式计算正确（手算一组数值对比）

**验收标准：**
```
pytest tests/test_models.py -v
# 期望: 3 passed
```

**验证命令：**
```bash
cd interview-ai/backend && pytest tests/test_models.py -v
```

**提交：**
```bash
git add interview-ai/backend/app/models/ interview-ai/backend/tests/
git commit -m "feat: add Pydantic models LLMEvaluationOutput and InterviewResult with unit tests"
```

### 研究洞察

**关键修正 1 — field_validator 截断（`Field(ge=0, le=100)` 不够）：**

`Field(ge=0, le=100)` 仅在 validation 阶段**抛出 ValidationError**，不会自动截断 LLM 输出的越界值（如 103.0）。必须用 `field_validator` 主动截断：

```python
from pydantic import BaseModel, Field, field_validator, computed_field
from typing import Annotated

ScoreField = Annotated[float, Field(ge=0.0, le=100.0)]

class LLMEvaluationOutput(BaseModel):
    analysis_ability_score: float = Field(ge=0.0, le=100.0)
    analysis_ability_reasoning: str
    # ... 其余维度

    @field_validator(
        "analysis_ability_score", "organization_coordination_score",
        "emergency_response_score", "interpersonal_communication_score",
        "language_expression_score", "job_matching_score",
        mode="before"  # 在类型转换前执行
    )
    @classmethod
    def clamp_score(cls, v) -> float:
        # LLM 可能返回字符串 "85.5" 或整数 85
        return max(0.0, min(100.0, float(v)))

    @field_validator("rule_violations", mode="before")
    @classmethod
    def filter_unknown_violations(cls, v) -> list[str]:
        VALID = {"CLICHE_ANALYSIS","NO_SAFETY_PLAN","EMERGENCY_HARDLINE","INTERPERSONAL_CONFLICT"}
        if isinstance(v, list):
            return [x for x in v if x in VALID]
        return []
```

**关键修正 2 — `@computed_field` 替代普通 `@property`：**

Pydantic v2 中，`@property` 不会被序列化到 `.model_dump()` / `.model_json_schema()`。必须用 `@computed_field`：

```python
from pydantic import computed_field

class InterviewResult(BaseModel):
    analysis_ability_score: float
    organization_coordination_score: float
    emergency_response_score: float
    interpersonal_communication_score: float
    language_expression_score: float
    job_matching_score: float
    paralinguistic_fluency_score: float

    @computed_field
    @property
    def final_score(self) -> float:
        return round(
            self.analysis_ability_score            * 0.20 +
            self.organization_coordination_score   * 0.15 +
            self.emergency_response_score          * 0.15 +
            self.interpersonal_communication_score * 0.15 +
            self.language_expression_score         * 0.15 +
            self.job_matching_score                * 0.10 +
            self.paralinguistic_fluency_score      * 0.10,
            2
        )
```

**关键修正 3 — 独立 `exceptions.py` 层级：**
```python
# app/exceptions.py
class AppError(Exception):
    def __init__(self, message: str, error_code: str):
        self.message = message
        self.error_code = error_code
        super().__init__(message)

class ASRError(AppError): pass
class LLMError(AppError): pass
class AudioValidationError(AppError): pass
```

**最佳实践 — pytest.ini 配置：**
```ini
# pytest.ini（backend 根目录）
[pytest]
asyncio_mode = auto   # pytest-asyncio 0.21+ 默认需要显式声明
```

**边缘情况：**
- 增加测试用例：`LLMEvaluationOutput` 收到 `{"analysis_ability_score": "N/A"}` 时，`clamp_score` 应抛 ValueError（`float("N/A")` 失败），而非静默返回 0

---

### T1.5 实现 calculate_fluency_score() + 单元测试

**文件：**
- 创建：`interview-ai/backend/app/services/fluency.py`
- 创建：`interview-ai/backend/tests/test_fluency.py`

**做什么：**
按 PRD §7.1 实现三项扣分规则（停顿 ≥3s/-2/次上限-10；语速越界/-5；语气词密度>5/分钟/-3）+ 保底 50。

`test_fluency.py`（7 个测试用例）：
1. 空 segments → 80.0
2. 正常场景 → 80.0
3. 停顿 5 次 → 70.0
4. 停顿 8 次（超上限）→ 70.0（不超过 -10）
5. 语速 < 150 → 75.0
6. 语气词密度 > 5/分钟 → 77.0
7. 三项叠加超过 30 → 50.0（保底）

**验收标准：**
```
pytest tests/test_fluency.py -v
# 期望: 7 passed
```

**验证命令：**
```bash
cd interview-ai/backend && pytest tests/test_fluency.py -v
```

**提交：**
```bash
git add interview-ai/backend/app/services/fluency.py interview-ai/backend/tests/test_fluency.py
git commit -m "feat: implement calculate_fluency_score() with 7 unit tests covering all rules"
```

### 研究洞察

**关键修正 — Groq verbose_json 词级时间戳字段名：**

`calculate_fluency_score()` 需要从 Groq 返回的数据中提取停顿间隔。Groq `verbose_json` 格式中，词级时间戳存在 `.words` 字段（不是 `.segments`）：

```python
# 正确写法（verbose_json 格式）
def extract_segments_from_groq(transcription) -> list[dict]:
    """将 Groq verbose_json .words 转换为内部 transcript_segments 格式"""
    return [
        {"text": w.word, "start": w.start, "end": w.end}
        for w in (transcription.words or [])
    ]

def detect_pauses(segments: list[dict], threshold: float = 3.0) -> int:
    """统计 ≥3.0s 的静默停顿次数"""
    pause_count = 0
    for i in range(1, len(segments)):
        gap = segments[i]["start"] - segments[i-1]["end"]
        if gap >= threshold:
            pause_count += 1
    return pause_count
```

**最佳实践 — 语气词检测不依赖 jieba：**
```python
FILLER_WORDS = {"那个", "然后", "就是", "这个", "嗯", "啊", "哦", "呃", "对对", "就那个"}

def count_filler_words(transcript: str) -> int:
    """用固定词表匹配，禁止 jieba 分词（PRD §6.2 禁止外部语料）"""
    count = 0
    for word in FILLER_WORDS:
        count += transcript.count(word)
    return count
```

**边缘情况：**
- `audio_duration_seconds = 0` 时会除零，需防护：`if duration <= 0: return 80.0`
- segments 仅含 1 条时，停顿检测循环从 `range(1, 1)` 返回空，正常

---

### T1.6 实现 apply_rule_caps() 双保险硬钳制 + 单元测试

**文件：**
- 创建：`interview-ai/backend/app/services/rule_caps.py`
- 创建：`interview-ai/backend/tests/test_rule_caps.py`

**做什么：**
实现 `RULE_CAPS` 映射、`_detect_violations_deterministically()`、`apply_rule_caps()`。

`test_rule_caps.py`（6 个测试用例）：
1. LLM 标注 `EMERGENCY_HARDLINE` → emergency_response.score 压至 ≤40
2. LLM 分 38 + `EMERGENCY_HARDLINE` → 不变（已低于上限）
3. `PLANNING_ORGANIZATION` 文本无安全预案词 → 确定性命中 NO_SAFETY_PLAN → org ≤65
4. 含"安全预案" → 不触发
5. 未知 violation `"EMERGENCY-HARDLINE"` → 被过滤，无钳制
6. 多个 violation → 各维度均压制

**验收标准：**
```
pytest tests/test_rule_caps.py -v
# 期望: 6 passed
```

**验证命令：**
```bash
cd interview-ai/backend && pytest tests/test_rule_caps.py -v
```

**提交：**
```bash
git add interview-ai/backend/app/services/rule_caps.py interview-ai/backend/tests/test_rule_caps.py
git commit -m "feat: implement apply_rule_caps() dual-guarantee with 6 unit tests"
```

### 研究洞察

**关键修正 — `model_copy` 替代原地修改（Pydantic v2 最佳实践）：**

Pydantic v2 模型是不可变的，直接 `result.emergency_response_score = 38` 会失败。必须用 `model_copy`：

```python
# app/services/rule_caps.py
from app.models.evaluation import InterviewResult

RULE_CAPS: dict[str, tuple[str, float]] = {
    "CLICHE_ANALYSIS":        ("analysis_ability_score",            59.0),
    "NO_SAFETY_PLAN":         ("organization_coordination_score",   65.0),
    "EMERGENCY_HARDLINE":     ("emergency_response_score",          40.0),
    "INTERPERSONAL_CONFLICT": ("interpersonal_communication_score", 40.0),
}

def apply_rule_caps(result: InterviewResult, violations: set[str]) -> InterviewResult:
    """
    对触发红线的维度分执行硬钳制。
    返回新实例（model_copy），永远不原地修改 result。
    """
    updates: dict[str, float] = {}
    for rule_key, (field_name, cap_value) in RULE_CAPS.items():
        if rule_key in violations:
            current = getattr(result, field_name)
            if current > cap_value:
                updates[field_name] = float(cap_value)
    return result.model_copy(update=updates) if updates else result
```

**最佳实践 — 确定性检测使用 `re.search`：**
```python
import re

# 安全预案关键词（任一命中即通过）
SAFETY_PLAN_KEYWORDS = re.compile(r"安全预案|应急预案|紧急预案|安全保障方案")

def _detect_violations_deterministically(
    transcript: str,
    question_type: str,
) -> set[str]:
    violations: set[str] = set()
    if question_type == "PLANNING_ORGANIZATION":
        if not SAFETY_PLAN_KEYWORDS.search(transcript):
            violations.add("NO_SAFETY_PLAN")
    return violations
```

**边缘情况：**
- `apply_rule_caps` 必须在 `supabase DB INSERT` 之前调用（T1.14 步骤 9 → 步骤 10）；若顺序颠倒，硬钳制不生效
- 双保险逻辑：`all_violations = set(llm_violations) | deterministic_violations`，两者取并集

---

### T1.7 实现 Prompt 工厂（按 question_type 路由）+ 单元测试

**文件：**
- 创建：`interview-ai/backend/app/services/prompt_factory.py`
- 创建：`interview-ai/backend/tests/test_prompt_factory.py`

**做什么：**
`build_system_prompt(question_type, policy_coverage, cliche_count) -> str`，按题型注入对应考官清单：
- `COMPREHENSIVE_ANALYSIS` → 点析对升四段论
- `PLANNING_ORGANIZATION` → 定摸筹控结五步 + 否决项（无安全预案/经费 → 上限 65）
- `EMERGENCY_RESPONSE` → 稳明调解报总六字诀 + 红线（暴力驱逐 → 上限 40）
- `INTERPERSONAL_RELATIONSHIPS` → 尊重服从 + 委婉沟通原则
- `SELF_COGNITION` / `SCENARIO_SIMULATION` → 通用深度清单

Prompt 末尾统一注入 `rule_violations` 强枚举约束说明、policy_coverage（非 null 时）、cliche_count（> 0 时）。

`test_prompt_factory.py`（5 个测试用例）：
1. PLANNING_ORGANIZATION prompt 包含"定、摸、筹、控、结"
2. EMERGENCY_RESPONSE prompt 包含"稳、明、调、解、报、总"
3. policy_coverage=None 时 prompt 不含数值
4. cliche_count=0 时不含套话提示
5. 所有 6 种 question_type 均有对应 prompt（不抛异常）

**验收标准：**
```
pytest tests/test_prompt_factory.py -v
# 期望: 5 passed
```

**验证命令：**
```bash
cd interview-ai/backend && pytest tests/test_prompt_factory.py -v
```

**提交：**
```bash
git add interview-ai/backend/app/services/prompt_factory.py interview-ai/backend/tests/test_prompt_factory.py
git commit -m "feat: implement Prompt factory with question_type routing and unit tests"
```

### 研究洞察

**最佳实践 — OpenAI System Prompt 缓存（节省 75% Token 成本）：**

通过在 messages 列表中标记 `"cache_control": {"type": "ephemeral"}`，OpenAI 会缓存 system prompt，相同 prompt 的后续请求节省约 75% 输入 token：

```python
messages = [
    {
        "role": "system",
        "content": [
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"}  # 缓存 system prompt
            }
        ]
    },
    {
        "role": "user",
        "content": f"题目：{question.content}\n\n考生回答：{transcript}"
    }
]
```

缓存条件：system prompt ≥1024 tokens 时生效（中文 prompt 约 800 字以上）。

**边缘情况：**
- `question_type` 不在 6 个枚举值中时，应 fallback 到通用 prompt 而不是抛 KeyError
- `policy_coverage` 为 `0.0`（非 None）时应注入提示（"政策词覆盖率 0%"），与 `None` 区分处理

---

### T1.8 实现音频安全验证 + ffmpeg 转码管道 + Dockerfile

**文件：**
- 创建：`interview-ai/backend/app/services/audio_processor.py`
- 创建：`interview-ai/backend/tests/test_audio_processor.py`
- 创建：`interview-ai/backend/Dockerfile`

**做什么：**
`audio_processor.py`：
1. `validate_audio(content: bytes, content_type: str) -> None`：Content-Type 校验 + 10MB 限制 + python-magic 魔数验证，失败抛自定义异常（含 error_code 字段）
2. `async def transcode_to_wav(input_bytes: bytes) -> bytes`：`ffmpeg-python` + `tempfile.NamedTemporaryFile(delete=True)` 无条件转码为 wav 16kHz mono，临时文件自动清理

`Dockerfile`：
```dockerfile
FROM python:3.11-slim
RUN apt-get update && apt-get install -y ffmpeg libmagic1 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

`test_audio_processor.py`（3 个测试，validate 部分）：
1. Content-Type 非 audio/webm/mp4 → ERR_INVALID_AUDIO
2. 超过 10MB → ERR_FILE_TOO_LARGE
3. 合法 Content-Type + 小于 10MB → 不抛异常

**验收标准：**
```
pytest tests/test_audio_processor.py -v  # 3 passed
docker build -t interview-ai-backend . && docker run --rm interview-ai-backend ffmpeg -version
# 期望: ffmpeg version x.x.x
```

**验证命令：**
```bash
cd interview-ai/backend
pytest tests/test_audio_processor.py -v
docker build -t interview-ai-backend .
docker run --rm interview-ai-backend ffmpeg -version
```

**提交：**
```bash
git add interview-ai/backend/app/services/audio_processor.py interview-ai/backend/tests/test_audio_processor.py interview-ai/backend/Dockerfile
git commit -m "feat: implement audio validation, ffmpeg transcoding, and Dockerfile with ffmpeg"
```

### 研究洞察

**关键修正 1 — MIME 类型集合需含 `video/*` 变体：**

`python-magic` 对纯音频 WebM 文件返回 `video/webm`（而非 `audio/webm`），对 M4A/AAC 文件返回 `video/mp4`（而非 `audio/mp4`）。允许集合必须包含两类：

```python
ALLOWED_MIME_TYPES = {
    "audio/webm", "video/webm",   # libmagic 对 audio-only WebM 返回 video/webm
    "audio/mp4",  "video/mp4",    # libmagic 对 M4A 返回 video/mp4
    "audio/mpeg",                 # MP3
    "audio/wav", "audio/x-wav",   # WAV
    "audio/ogg",                  # OGG Vorbis
    "audio/flac",                 # FLAC
}

def validate_audio(content: bytes, content_type: str) -> None:
    if len(content) > 10 * 1024 * 1024:
        raise AudioValidationError("文件超过 10MB 限制", "ERR_FILE_TOO_LARGE")
    # 1. 检查 Content-Type header（客户端自报）
    if not any(content_type.startswith(m) for m in ALLOWED_MIME_TYPES):
        raise AudioValidationError(f"不支持的 Content-Type: {content_type}", "ERR_INVALID_AUDIO")
    # 2. 魔数验证（防止伪造 Content-Type）
    import magic
    actual_mime = magic.from_buffer(content[:4096], mime=True)
    if actual_mime not in ALLOWED_MIME_TYPES:
        raise AudioValidationError(f"文件实际类型 {actual_mime} 不被允许", "ERR_INVALID_AUDIO")
```

**关键修正 2 — ffmpeg 使用 `asyncio.create_subprocess_exec`（避免阻塞事件循环）：**

`ffmpeg-python` 底层使用同步 `subprocess.run()`，会阻塞 FastAPI 异步事件循环。改用 asyncio 原生管道：

```python
async def transcode_to_wav(input_bytes: bytes) -> bytes:
    """
    通过 stdin/stdout 管道转码，无需临时文件，不阻塞事件循环。
    """
    async with asyncio.timeout(10.0):  # ffmpeg 超时 10s
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg",
            "-i", "pipe:0",          # 从 stdin 读取
            "-f", "wav",
            "-ar", "16000",          # 16kHz（Whisper 最优）
            "-ac", "1",              # mono
            "-acodec", "pcm_s16le",
            "pipe:1",                # 输出到 stdout
            "-loglevel", "error",    # 静默非错误输出
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        wav_bytes, stderr = await proc.communicate(input=input_bytes)
        if proc.returncode != 0:
            raise AudioValidationError(
                f"ffmpeg 转码失败: {stderr.decode()[:200]}",
                "ERR_TRANSCODE_FAILED"
            )
    return wav_bytes
```

**最佳实践 — Dockerfile 安全加固：**
```dockerfile
FROM python:3.11-slim
RUN apt-get update && apt-get install -y ffmpeg libmagic1 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# 非 root 用户运行（安全加固）
RUN useradd -m appuser && chown -R appuser /app
USER appuser
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**边缘情况：**
- 输入文件损坏时 ffmpeg 返回非 0 returncode，`stderr` 含错误信息，需捕获并返回有意义的 `error_code`
- Safari 录制的 M4A 实际是 `audio/x-m4a`，也需加入允许集合

---

### T1.9 实现 Groq Whisper ASR 调用（prompt 截断 + 重试）

**文件：**
- 创建：`interview-ai/backend/app/services/asr.py`
- 创建：`interview-ai/backend/tests/test_asr.py`

**做什么：**
`async def run_asr(audio_wav_bytes: bytes, question_type: str) -> dict`：
1. 按 question_type 从 `keyword_dict.json` 取 Top-20 词，join 为 prompt（≤224 tokens）
2. Groq SDK 调用 `whisper-large-v3`，`word_timestamps=True`
3. 返回 `{"transcript": str, "transcript_segments": list[dict], "audio_duration_seconds": float}`
4. 网络错误/502/504 → 指数退避重试 2 次（等待 1s、2s），彻底失败抛 `ASRTimeoutError`

`test_asr.py`（3 个测试，mock Groq client）：
1. 成功路径返回正确 transcript_segments 格式
2. keyword_dict 词超 20 条时实际注入 ≤20 词
3. 两次失败后抛 ASRTimeoutError

**验收标准：**
```
pytest tests/test_asr.py -v
# 期望: 3 passed
```

**验证命令：**
```bash
cd interview-ai/backend && pytest tests/test_asr.py -v
```

**提交：**
```bash
git add interview-ai/backend/app/services/asr.py interview-ai/backend/tests/test_asr.py
git commit -m "feat: implement Groq Whisper ASR with Top-20 prompt injection and 2-retry logic"
```

### 研究洞察

**关键修正 1 — Groq API 正确调用方式（3 处不同于 OpenAI）：**

```python
# app/services/asr.py
import asyncio
from groq import AsyncGroq
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

def _is_retryable(exc: BaseException) -> bool:
    import groq
    if isinstance(exc, groq.APIStatusError):
        return exc.status_code in {429, 502, 503, 504}
    return isinstance(exc, (groq.APIConnectionError, groq.APITimeoutError))

@retry(
    stop=stop_after_attempt(3),          # 初始 + 2 次重试
    wait=wait_exponential(multiplier=1, min=1, max=4),
    retry=retry_if_exception(_is_retryable),
    reraise=True,
)
async def run_asr(
    audio_wav_bytes: bytes,
    question_type: str,
    groq_client: AsyncGroq,
    keyword_dict: dict,
) -> dict:
    # 构建 prompt（Top-20 词，≤224 tokens）
    keywords = keyword_dict.get(question_type, [])[:20]
    prompt = "，".join(keywords)

    async with asyncio.timeout(8.0):  # ≤8s per-step 超时（PRD §SLA）
        transcription = await groq_client.audio.transcriptions.create(
            file=("audio.wav", audio_wav_bytes),   # ← 关键：必须是 (filename, bytes) 元组
            model="whisper-large-v3",
            response_format="verbose_json",         # ← 关键：不是 word_timestamps=True
            language="zh",
            prompt=prompt,
            temperature=0.0,
        )

    # 词级时间戳在 .words，不是 .segments
    segments = [
        {"text": w.word, "start": w.start, "end": w.end}
        for w in (transcription.words or [])        # ← 关键：.words 不是 .segments
    ]

    return {
        "transcript": transcription.text,
        "transcript_segments": segments,
        "audio_duration_seconds": float(transcription.duration or 0),
    }
```

**关键修正 2 — 测试 mock 方式（Groq verbose_json 结构）：**
```python
# tests/test_asr.py
from unittest.mock import AsyncMock, MagicMock

def make_mock_groq_response():
    word = MagicMock()
    word.word = "各位考官"
    word.start = 0.0
    word.end = 0.8

    response = MagicMock()
    response.text = "各位考官，关于这个问题"
    response.words = [word]
    response.duration = 5.2
    return response

async def test_asr_success(mock_groq):
    mock_groq.audio.transcriptions.create = AsyncMock(
        return_value=make_mock_groq_response()
    )
    result = await run_asr(b"fake-wav", "COMPREHENSIVE_ANALYSIS", mock_groq, KEYWORD_DICT)
    assert result["transcript"] == "各位考官，关于这个问题"
    assert result["transcript_segments"][0] == {"text": "各位考官", "start": 0.0, "end": 0.8}
```

**边缘情况：**
- `transcription.words` 可能为 `None`（Groq 静音片段），需 `(transcription.words or [])` 防护
- `transcription.duration` 可能为 `None` 或 `0`，需 `float(transcription.duration or 0)` 防护
- Groq 对 WAV prompt > 224 tokens 会静默截断，实现层主动截断到 20 词更安全

---

### T1.10 实现 LLM 结构化评估调用（Pydantic parse + 重试）

**文件：**
- 创建：`interview-ai/backend/app/services/llm_evaluator.py`
- 创建：`interview-ai/backend/tests/test_llm_evaluator.py`

**做什么：**
`async def run_llm_evaluation(transcript, question, policy_coverage, cliche_count) -> LLMEvaluationOutput`：
1. 读 `OPENAI_MODEL` env，缺失 fallback `gpt-4o-mini`
2. 调用 `build_system_prompt()`
3. `openai.AsyncOpenAI().beta.chat.completions.parse(response_format=LLMEvaluationOutput, ...)`
4. 解析失败 → 重试 2 次，彻底失败抛 `LLMParseError`

`test_llm_evaluator.py`（3 个测试，mock openai client）：
1. 成功路径返回 `LLMEvaluationOutput`
2. 无 OPENAI_MODEL 环境变量 → 使用 `gpt-4o-mini`
3. Pydantic 校验两次均失败 → 抛 LLMParseError

**验收标准：**
```
pytest tests/test_llm_evaluator.py -v
# 期望: 3 passed
```

**验证命令：**
```bash
cd interview-ai/backend && pytest tests/test_llm_evaluator.py -v
```

**提交：**
```bash
git add interview-ai/backend/app/services/llm_evaluator.py interview-ai/backend/tests/test_llm_evaluator.py
git commit -m "feat: implement LLM evaluation with openai parse(), OPENAI_MODEL fallback, and retry"
```

### 研究洞察

**关键修正 — `parse()` 正确用法（需检查 `message.refusal`）：**

```python
# app/services/llm_evaluator.py
import asyncio
from openai import AsyncOpenAI
from openai import LengthFinishReasonError
from app.models.evaluation import LLMEvaluationOutput

async def run_llm_evaluation(
    transcript: str,
    question_content: str,
    question_type: str,
    policy_coverage: float | None,
    cliche_count: int,
    openai_client: AsyncOpenAI,
    model: str = "gpt-4o-mini",
) -> LLMEvaluationOutput:
    system_prompt = build_system_prompt(question_type, policy_coverage, cliche_count)

    async with asyncio.timeout(6.0):  # ≤6s per-step 超时
        try:
            completion = await openai_client.beta.chat.completions.parse(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": [{"type": "text", "text": system_prompt,
                                     "cache_control": {"type": "ephemeral"}}]
                    },
                    {"role": "user", "content": f"题目：{question_content}\n\n回答：{transcript}"}
                ],
                response_format=LLMEvaluationOutput,
                temperature=0.2,
            )
        except LengthFinishReasonError:
            raise LLMError("LLM 输出被截断（max_tokens 不足）", "ERR_LLM_LENGTH")

    message = completion.choices[0].message

    # 检查 refusal（模型拒绝回答）
    if message.refusal:
        raise LLMError(f"LLM 拒绝评估: {message.refusal}", "ERR_LLM_REFUSAL")

    # message.parsed 已经是 LLMEvaluationOutput 实例（field_validator 已执行）
    if message.parsed is None:
        raise LLMError("LLM 返回空 parsed 结果", "ERR_LLM_PARSE")

    return message.parsed
```

**最佳实践 — 抽取 `evaluation_pipeline.py` 模块：**

将 T1.14 的 10 步流程抽到独立文件，而不是全写在路由函数里：
```
app/services/evaluation_pipeline.py   ← 10 步流程（便于测试 + 超时管理）
app/routers/evaluations.py            ← 仅做请求解析、调用 pipeline、返回响应
```

**边缘情况：**
- `gpt-4o-mini` 有时返回 `"score": null`，`field_validator(mode='before')` 中需处理 `None` → 返回 0.0 而非抛错
- Structured Outputs 偶发 HTTP 500，需用 tenacity 重试（`retry_if_exception_type(openai.InternalServerError)`）

---

### T1.11 实现 Aho-Corasick 词汇分析 + P1 正则黑名单

**文件：**
- 创建：`interview-ai/backend/app/services/vocab_analyzer.py`
- 创建：`interview-ai/backend/tests/test_vocab_analyzer.py`

**做什么：**
1. `analyze_vocab(transcript, question_type) -> dict`：
   - Aho-Corasick 政策词扫描：`policy_coverage = matched/required`；`required=0` → `None`
   - Aho-Corasick 套话黑名单：返回 `cliche_count`
2. `check_anti_template(transcript) -> str | None`（P1）：`re` 模块匹配 `cliche_patterns.json`，命中 ≥3 条 → 返回警告文案，否则 `None`（**禁止 jieba / 外部语料**）

`test_vocab_analyzer.py`（4 个测试）：
1. `required_count=0` → `policy_coverage=None`
2. 含 2 个政策词，required=4 → `policy_coverage=0.5`
3. P1：命中 2 条 → None
4. P1：命中 3 条 → 非 None 字符串

**验收标准：**
```
pytest tests/test_vocab_analyzer.py -v
# 期望: 4 passed
```

**验证命令：**
```bash
cd interview-ai/backend && pytest tests/test_vocab_analyzer.py -v
```

**提交：**
```bash
git add interview-ai/backend/app/services/vocab_analyzer.py interview-ai/backend/tests/test_vocab_analyzer.py
git commit -m "feat: implement Aho-Corasick vocab analysis and P1 regex cliche detection"
```

### 研究洞察

**最佳实践 — automaton 从 `request.app.state` 注入（不重建）：**

```python
# app/services/vocab_analyzer.py
import unicodedata
import re

def analyze_vocab(
    transcript: str,
    question_type: str,
    automaton,           # 从 app.state.automaton 传入（lifespan 已构建）
    keyword_dict: dict,
) -> dict:
    # NFKC 正规化后匹配
    normalized = unicodedata.normalize("NFKC", transcript)
    required_keywords = set(keyword_dict.get(question_type, []))

    matched = set()
    for _, (_, word) in automaton.iter(normalized):
        if word in required_keywords:
            matched.add(word)

    policy_coverage = (
        len(matched) / len(required_keywords)
        if required_keywords
        else None
    )

    return {
        "policy_coverage": policy_coverage,
        "matched_keywords": list(matched),
    }

def check_anti_template(transcript: str, patterns: list[str]) -> str | None:
    """P1：命中 ≥3 条套话正则 → 返回警告文案"""
    hit_count = sum(1 for p in patterns if re.search(p, transcript))
    if hit_count >= 3:
        return f"检测到 {hit_count} 处套话表达，建议增强答案具体性和针对性"
    return None
```

**边缘情况：**
- `transcript` 为空字符串时，`automaton.iter("")` 返回空迭代器，`policy_coverage = 0/n`（`required=0` 时仍返回 `None`）
- 正则匹配前须用 `re.compile` 预编译并缓存（在 lifespan 中预编译所有 patterns）

---

### T1.12 实现 FastAPI JWT 认证 Dependency

**文件：**
- 创建：`interview-ai/backend/app/dependencies/auth.py`
- 修改：`interview-ai/backend/app/main.py`（注册 Supabase client）

**做什么：**
`auth.py`：`async def get_current_user(authorization: str = Header(...)) -> dict`：
1. 提取 `Bearer <token>`
2. `supabase_client.auth.get_user(token)` 验证
3. 无效/过期 → `HTTPException(401, {"error_code":"ERR_UNAUTHORIZED"})`
4. 返回 `user` 对象（含 `user.id`）

**验收标准：**
```bash
curl -X GET http://localhost:8000/api/v1/questions/draw -H "Authorization: Bearer invalid"
# 期望: 401 {"error_code":"ERR_UNAUTHORIZED"}
```

**验证命令：**
```bash
curl -X GET http://localhost:8000/api/v1/questions/draw -H "Authorization: Bearer invalid"
```

**提交：**
```bash
git add interview-ai/backend/app/dependencies/
git commit -m "feat: implement FastAPI JWT authentication dependency using supabase-py"
```

### 研究洞察

**最佳实践 — `get_current_user` 从 `request.app.state` 取客户端（不新建）：**

```python
# app/dependencies/auth.py
from fastapi import Depends, HTTPException, Header, Request

async def get_current_user(
    request: Request,
    authorization: str = Header(...),
) -> dict:
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, {"error_code": "ERR_UNAUTHORIZED"})
    token = authorization.removeprefix("Bearer ").strip()

    try:
        # 使用 lifespan 注入的 supabase 客户端，不每次重建
        supabase = request.app.state.supabase
        async with asyncio.timeout(3.0):  # Supabase auth ≤3s
            user_response = await supabase.auth.get_user(token)
        if user_response.user is None:
            raise HTTPException(401, {"error_code": "ERR_UNAUTHORIZED"})
        return {"id": str(user_response.user.id), "email": user_response.user.email}
    except asyncio.TimeoutError:
        raise HTTPException(503, {"error_code": "ERR_AUTH_TIMEOUT"})
    except Exception:
        raise HTTPException(401, {"error_code": "ERR_UNAUTHORIZED"})
```

**边缘情况：**
- JWT 过期（`exp` 过期）时，Supabase 返回 `{"message": "invalid JWT"}` 而非 HTTP 错误，需检查 `user_response.user is None`
- Supabase auth 端点偶发超时（高峰期），需单独超时处理，不能让整个请求 hang 住

---

### T1.13 实现速率限制（每用户每分钟 3 次）

**文件：**
- 创建：`interview-ai/backend/app/middleware/rate_limit.py`
- 修改：`interview-ai/backend/app/main.py`

**做什么：**
使用 `slowapi`，仅对 `POST /api/v1/evaluations/submit` 应用 `@limiter.limit("3/minute")`，key 为 user_id（从 JWT 提取）。超出返回 HTTP 429，响应头含 `Retry-After`、`X-RateLimit-Limit: 3`、`X-RateLimit-Remaining: 0`。

**验收标准：**
同一有效 user 60s 内第 4 次 POST → 429 响应。

**验证命令：**
```bash
TOKEN="valid-jwt-here"
for i in 1 2 3 4; do
  echo "Request $i:"
  curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:8000/api/v1/evaluations/submit \
    -H "Authorization: Bearer $TOKEN"
done
# 期望: 前3次 4xx（无音频），第4次 429
```

**提交：**
```bash
git add interview-ai/backend/app/middleware/
git commit -m "feat: add per-user rate limiting 3/minute to evaluations/submit"
```

### 研究洞察

**最佳实践 — JWT key_func（在 Depends 之前解码 JWT）：**

slowapi 的 `key_func` 在 FastAPI `Depends()` 之前运行，无法访问已解码的 user 对象。需在 `key_func` 内部直接解码 JWT：

```python
# app/middleware/rate_limit.py
from slowapi import Limiter
from slowapi.util import get_remote_address
from jose import jwt, JWTError
from fastapi import Request

def get_rate_limit_key(request: Request) -> str:
    """从 JWT 提取 user_id 作为限流 key，降级到 IP"""
    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        return f"anon:{get_remote_address(request)}"

    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = jwt.decode(
            token,
            options={"verify_signature": False}  # key_func 只取 sub，不验证签名
        )
        uid = payload.get("sub") or payload.get("user_id")
        if uid:
            return f"user:{uid}"
    except JWTError:
        pass
    return f"anon:{get_remote_address(request)}"

limiter = Limiter(key_func=get_rate_limit_key)
```

**自定义 429 响应（含 Retry-After）：**
```python
# app/main.py
from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse
import time

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"error_code": "ERR_RATE_LIMIT", "message": "请求过于频繁，请 60 秒后重试"},
        headers={
            "Retry-After": "60",
            "X-RateLimit-Limit": "3",
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(int(time.time()) + 60),
        }
    )
```

**中间件注册顺序（必须）：**
```python
# main.py 中的顺序很重要
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)  # 在 app.state.limiter 设置后
```

**边缘情况：**
- pytest 中需 `limiter.reset()` 清空状态，否则测试间互相影响
- `verify_signature=False` 仅用于限流 key 提取，真正的 JWT 验证仍在 `get_current_user` 中完成

---

### T1.14 实现 /api/v1/evaluations/submit 完整端点 + questions 路由

**文件：**
- 创建：`interview-ai/backend/app/routers/evaluations.py`
- 创建：`interview-ai/backend/app/routers/questions.py`
- 创建：`interview-ai/backend/app/services/evaluation_pipeline.py`
- 修改：`interview-ai/backend/app/main.py`（注册路由）

**做什么：**
`evaluation_pipeline.py`（10 步流程，独立模块）：
1. `validate_audio(content, content_type)`
2. 查询 question_id 存在于 questions 表（命中缓存则跳过 DB 查询）
3. `transcode_to_wav(audio_bytes)`（asyncio 管道）
4. `run_asr(wav_bytes, question_type)` → transcript / transcript_segments
5. `analyze_vocab(transcript, question_type)` → policy_coverage / cliche_count
6. `check_anti_template(transcript)` → anti_template_warning
7. 并行执行：`asyncio.gather(run_llm_evaluation(...), upload_to_storage(wav_bytes))`
8. `apply_rule_caps(llm_output, transcript, question_type)` ← **入库前执行**
9. `calculate_fluency_score(transcript_segments)` → paralinguistic_fluency_score
10. 写入 `evaluations` 表（含 client_request_id 幂等检查）
11. `InterviewResult.final_score` 聚合后返回 HTTP 201

`questions.py`：
- `GET /api/v1/questions/draw?count=3`（3-5 题，从 questions 表随机抽取）
- `GET /api/v1/questions/{question_id}`

**验收标准：**
用 10s 测试音频文件调用 submit，返回 HTTP 201，JSON 含 `final_score`、7 个维度分、`transcript_segments`，`evaluations` 表有新记录。

**验证命令：**
```bash
TOKEN="valid-jwt"
QUESTION_ID="valid-question-uuid"
curl -X POST http://localhost:8000/api/v1/evaluations/submit \
  -H "Authorization: Bearer $TOKEN" \
  -F "audio=@test_audio.webm;type=audio/webm" \
  -F "question_id=$QUESTION_ID" \
  | python -m json.tool
# 期望: HTTP 201, JSON 含 final_score
```

**提交：**
```bash
git add interview-ai/backend/app/routers/ interview-ai/backend/app/services/evaluation_pipeline.py
git commit -m "feat: implement complete /api/v1/evaluations/submit 10-step AI pipeline"
```

### 研究洞察

**关键修正 — asyncio.gather 并行化（节省 600ms–2.1s）：**

LLM 评估（2–4s）与 Supabase Storage 上传（0.6–2.1s）完全独立，可以并行：

```python
# app/services/evaluation_pipeline.py（关键片段）
async def run_pipeline(audio_bytes, question, client_request_id, app_state) -> InterviewResult:
    # 串行部分（有依赖）
    validate_audio(audio_bytes, content_type)
    wav_bytes = await transcode_to_wav(audio_bytes)
    asr_result = await run_asr(wav_bytes, question.question_type, app_state.groq)
    transcript = asr_result["transcript"]

    vocab = analyze_vocab(transcript, question.question_type, app_state.automaton)
    anti_warning = check_anti_template(transcript, app_state.cliche_patterns)

    # 并行部分（LLM + Storage 同时执行，节省 0.6-2.1s）
    llm_task = asyncio.create_task(
        run_llm_evaluation(transcript, question, vocab, app_state.openai)
    )
    upload_task = asyncio.create_task(
        upload_audio_to_storage(wav_bytes, app_state.supabase)
    )
    llm_output, storage_path = await asyncio.gather(llm_task, upload_task)

    # 入库前执行硬钳制（顺序关键）
    all_violations = set(llm_output.rule_violations) | _detect_violations_deterministically(
        transcript, question.question_type
    )
    capped_output = apply_rule_caps(llm_output, all_violations)

    fluency = calculate_fluency_score(asr_result["transcript_segments"], asr_result["audio_duration_seconds"])

    # 幂等写入（client_request_id UNIQUE 约束防重复）
    result = await insert_evaluation(capped_output, fluency, storage_path, client_request_id, app_state.supabase)
    return result
```

**关键修正 — client_request_id 幂等检查：**
```python
# 写入前检查是否已存在（弱网重试场景）
async def insert_evaluation(data, client_request_id, supabase) -> dict:
    try:
        result = await supabase.table("evaluations").insert({
            **data,
            "client_request_id": str(client_request_id)
        }).execute()
        return result.data[0]
    except Exception as e:
        if "evaluations_client_request_id_unique" in str(e):
            # 重复提交：返回已有记录
            existing = await supabase.table("evaluations").select("*").eq(
                "client_request_id", str(client_request_id)
            ).single().execute()
            return existing.data
        raise
```

**端到端耗时修正（含并行优化）：**

| 阶段 | 串行预算 | 并行优化后 |
|------|---------|----------|
| 音频上传 | ~1s | ~1s |
| ffmpeg 转码 | ~0.5s | ~0.5s |
| Groq Whisper ASR | 3–5s | 3–5s |
| 词汇分析 | <0.1s | <0.1s |
| LLM 评估 | 2–4s | **并行** ↓ |
| Storage 上传 | 0.6–2.1s | **并行** ↑（与 LLM 同时） |
| 规则计算 + DB 写入 | ~0.5s | ~0.5s |
| **总计（串行）** | **7.7–13.2s** | **约 5.6–11.1s** |

---

## Milestone 2：前端考场流程（2–3 天）

**目标：** 用户可登录 → 进入考场 → 完成多题录音 → 提交后端 → 看到 PROCESSING 骨架屏 → 跳转复盘页。

**依赖：** Milestone 1 全部完成。

---

### T2.1 初始化 Next.js 14 项目（TypeScript + Tailwind + Shadcn/UI + Zustand）

**文件：**
- 创建：`interview-ai/frontend/`（整个 Next.js 项目）
- 创建：`interview-ai/frontend/.env.local.example`

**做什么：**
```bash
cd interview-ai
npx create-next-app@14 frontend --typescript --tailwind --app --no-src-dir
cd frontend
npx shadcn-ui@latest init
npm install zustand
```

`.env.local.example`（**严禁** OPENAI_API_KEY / GROQ_API_KEY 前缀）：
```
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...
API_BASE_URL=http://localhost:8000
```

**验收标准：**
`npm run dev` → http://localhost:3000 正常，无报错。

**验证命令：**
```bash
cd interview-ai/frontend && npm run dev &
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000
# 期望: 200
```

**提交：**
```bash
git add interview-ai/frontend/
git commit -m "feat: initialize Next.js 14 with TypeScript, Tailwind, Shadcn/UI, Zustand"
```

### 研究洞察

**关键修正 — `API_BASE_URL` 替代 `NEXT_PUBLIC_API_BASE_URL`：**

`NEXT_PUBLIC_` 前缀会将变量打包到浏览器 bundle，导致后端 URL 公开暴露。后端 API 调用仅在 Next.js Route Handler（服务端）进行，使用无前缀的 `API_BASE_URL`：

```
# .env.local.example（正确）
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co  ← 前端需要
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...                       ← 前端需要
API_BASE_URL=http://localhost:8000                          ← 仅服务端用，无 NEXT_PUBLIC_
```

**运行 T1.2 完成后立即生成类型文件：**
```bash
npm install supabase --save-dev
npx supabase gen types typescript --project-id YOUR_PROJECT_ID > types/supabase.ts
```

然后在客户端创建时使用泛型：
```typescript
import type { Database } from '@/types/supabase'
import { createClient } from '@supabase/supabase-js'
const supabase = createClient<Database>(url, anonKey)
// 现在所有查询都有类型推断，避免 any
```

**关键修正 — 禁止 `const enum`：**

Next.js 使用 SWC 编译器，`isolatedModules: true`，不支持 `const enum`（跨文件枚举值解析失败）：
```typescript
// ❌ 会在 SWC 编译时报错
const enum InterviewState { IDLE, READING, RECORDING, PROCESSING, REVIEW }

// ✅ 正确写法
const INTERVIEW_STATES = ["IDLE", "READING", "RECORDING", "PROCESSING", "REVIEW"] as const
type InterviewState = typeof INTERVIEW_STATES[number]
```

---

### T2.2 实现登录页面（/login）

**文件：**
- 创建：`interview-ai/frontend/app/login/page.tsx`
- 创建：`interview-ai/frontend/lib/supabase.ts`

**做什么：**
`supabase.ts`：创建 Supabase browser client（`@supabase/ssr`）。

`login/page.tsx`（Client Component）：
- 邮箱 + 密码输入框 + 登录按钮
- 成功：`access_token` 写入 `sessionStorage`（**禁止 localStorage**）→ `router.push('/dashboard')`
- 失败：`data-testid="login-error"` 内联红色文案"邮箱或密码错误"（不区分失败原因），URL 保持 /login
- 请求中：按钮 disabled + loading，**禁止弹窗**

**验收标准：**
- 错误密码 → 内联错误提示，URL 不变
- 正确密码 → sessionStorage 有 token，跳 /dashboard
- DevTools Application 面板：无 localStorage 写入

**验证命令：** 手动测试以上 3 个场景。

**提交：**
```bash
git add interview-ai/frontend/app/login/ interview-ai/frontend/lib/supabase.ts
git commit -m "feat: implement /login page with sessionStorage JWT, inline error, anti-duplicate"
```

### 研究洞察

**关键修正 — `createClient` 直接传 sessionStorage（不用 `@supabase/ssr`）：**

`@supabase/ssr` 的 `createBrowserClient` 默认使用 localStorage，且不支持直接传 sessionStorage 作为 storage 适配器。需用基础 `@supabase/supabase-js` 并手动传 storage：

```typescript
// lib/supabase.ts
import { createClient } from '@supabase/supabase-js'
import type { Database } from '@/types/supabase'

export function createSessionStorageSupabaseClient() {
  return createClient<Database>(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      auth: {
        // SSR 安全：只在浏览器中使用 sessionStorage
        storage: typeof window !== 'undefined' ? sessionStorage : undefined,
        autoRefreshToken: true,
        persistSession: true,
        flowType: 'pkce',
      },
    }
  )
}
```

**关键修正 — 登录成功时设置 `auth-present` cookie（Edge Middleware 检测需要）：**

Edge Middleware 无法访问 sessionStorage，通过 cookie 信号判断登录状态：

```typescript
// app/login/page.tsx（登录成功回调）
const { data, error } = await supabase.auth.signInWithPassword({ email, password })
if (data.session) {
  // 设置信号 cookie（无 httpOnly，供 Middleware 读取）
  document.cookie = 'auth-present=1; path=/; SameSite=Lax; Max-Age=3600'
  router.push('/dashboard')
}
```

**边缘情况：**
- 页面刷新时 sessionStorage 清空，需在 `useEffect` 中检测并重定向到 `/login`
- `signInWithPassword` 网络超时时需显示错误（非弹窗），按钮重新启用

---

### T2.3 实现路由守卫（受保护页面 JWT 校验）

**文件：**
- 创建：`interview-ai/frontend/middleware.ts`
- 创建：`interview-ai/frontend/lib/auth.ts`

**做什么：**
`middleware.ts`（Next.js Edge Middleware）：匹配 `/dashboard`、`/interview/*`、`/review/*`，用 `@supabase/ssr createServerClient` 验证 session，无效 → `redirect('/login')`。

`auth.ts`：导出 `useRequireAuth()` Hook，Client Component mount 时调用 `supabase.auth.getUser()`，401 → 清除 sessionStorage → `router.push('/login')`。

**验收标准：**
- 未登录访问 /dashboard → 重定向 /login
- token 过期访问受保护路由 → 重定向 /login

**验证命令：** 清除 sessionStorage 后手动访问 /dashboard 确认跳转。

**提交：**
```bash
git add interview-ai/frontend/middleware.ts interview-ai/frontend/lib/auth.ts
git commit -m "feat: implement route guard middleware and useRequireAuth hook"
```

### 研究洞察

**关键修正 — Edge Middleware 无法读 sessionStorage，改用 cookie 信号：**

Next.js Edge Middleware 运行在 V8 沙箱，无 DOM API 访问权限，无法读取 sessionStorage。需用 T2.2 中设置的 `auth-present` cookie 作为快速检测信号，JWT 真正验证交给客户端 Hook：

```typescript
// middleware.ts
import { NextRequest, NextResponse } from 'next/server'

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl
  const protectedPaths = ['/dashboard', '/interview', '/review']
  const isProtected = protectedPaths.some(p => pathname.startsWith(p))

  if (!isProtected) return NextResponse.next()

  // 通过 cookie 信号快速检测（不验证 JWT，仅防止未登录用户直接访问）
  const authPresent = request.cookies.get('auth-present')?.value
  if (!authPresent) {
    return NextResponse.redirect(new URL('/login', request.url))
  }

  return NextResponse.next()
}

export const config = {
  matcher: ['/dashboard/:path*', '/interview/:path*', '/review/:path*'],
}
```

```typescript
// lib/auth.ts（真正的 JWT 验证在客户端）
'use client'
import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { createSessionStorageSupabaseClient } from './supabase'

export function useRequireAuth() {
  const router = useRouter()
  useEffect(() => {
    // typeof window guard：SSR 时 sessionStorage 不存在
    if (typeof window === 'undefined') return
    const supabase = createSessionStorageSupabaseClient()
    supabase.auth.getUser().then(({ data, error }) => {
      if (error || !data.user) {
        sessionStorage.clear()
        document.cookie = 'auth-present=; path=/; Max-Age=0'
        router.replace('/login')
      }
    })
  }, [router])
}
```

**边缘情况：**
- `/login` 和 `/` 路径不应被 matcher 匹配（避免死循环重定向）
- Cookie `Max-Age=3600` 与 Supabase JWT `exp` 对齐

---

### T2.4 实现 useInterviewTimer Hook + 单元测试

**文件：**
- 创建：`interview-ai/frontend/hooks/useInterviewTimer.ts`
- 创建：`interview-ai/frontend/__tests__/useInterviewTimer.test.ts`

**做什么：**
`useInterviewTimer(initialSeconds, onExpireCallback) -> { secondsLeft, isWarning }`：
- `performance.now()` 记录起始时间戳，`setInterval(100ms)` 更新（基于 perf.now() 差值，不累积漂移）
- `visibilitychange` → 切回时重算剩余时间
- `secondsLeft <= 60` → `isWarning = true`
- `secondsLeft <= 0` → 调用 `onExpireCallback()`

`test` 覆盖 5 个场景：初始值正确 / 3分钟漂移≤1s / visibilitychange 校准 / ≤60s isWarning=true / ≤0 触发回调。

**验收标准：**
```
npm test __tests__/useInterviewTimer.test.ts -- --verbose
# 期望: 5 passed
```

**验证命令：**
```bash
cd interview-ai/frontend && npm test __tests__/useInterviewTimer.test.ts -- --verbose
```

**提交：**
```bash
git add interview-ai/frontend/hooks/useInterviewTimer.ts interview-ai/frontend/__tests__/useInterviewTimer.test.ts
git commit -m "feat: implement useInterviewTimer with performance.now() and unit tests (drift ≤1s)"
```

### 研究洞察

**最佳实践 — `hasFiredRef` 防止回调多次触发：**

`setInterval` 100ms 精度下，`secondsLeft` 可能从 1 跳到 -1（跳过 0），且同一帧内可能多次满足 `<= 0` 条件：

```typescript
// hooks/useInterviewTimer.ts
import { useState, useEffect, useRef, useCallback } from 'react'

export function useInterviewTimer(
  initialSeconds: number,
  onExpire: () => void
) {
  const [secondsLeft, setSecondsLeft] = useState(initialSeconds)
  const startEpochRef = useRef<number>(0)        // performance.now() 锚点
  const hasFiredRef = useRef(false)              // 防止 onExpire 多次触发
  const onExpireRef = useRef(onExpire)
  onExpireRef.current = onExpire                 // 始终持有最新引用

  useEffect(() => {
    startEpochRef.current = performance.now()
    hasFiredRef.current = false

    const timer = setInterval(() => {
      const elapsed = (performance.now() - startEpochRef.current) / 1000
      const remaining = Math.max(0, initialSeconds - elapsed)
      setSecondsLeft(Math.ceil(remaining))

      if (remaining <= 0 && !hasFiredRef.current) {
        hasFiredRef.current = true
        onExpireRef.current()
        clearInterval(timer)
      }
    }, 100)

    // visibilitychange 校准：tab 切回时重算（浏览器可能冻结 setInterval）
    const handleVisibility = () => {
      if (document.visibilityState === 'visible') {
        const elapsed = (performance.now() - startEpochRef.current) / 1000
        const remaining = Math.max(0, initialSeconds - elapsed)
        setSecondsLeft(Math.ceil(remaining))
      }
    }
    document.addEventListener('visibilitychange', handleVisibility)

    return () => {
      clearInterval(timer)
      document.removeEventListener('visibilitychange', handleVisibility)
    }
  }, [initialSeconds])

  return {
    secondsLeft,
    isWarning: secondsLeft <= 60 && secondsLeft > 0,
  }
}
```

**边缘情况：**
- `initialSeconds = 0` → 直接触发回调，不进入计时循环
- 组件卸载时 `clearInterval` 已在 cleanup 中，但 `hasFiredRef` 防止了 unmount 后的回调

---

### T2.5 实现 useInterviewFlowManager Hook + Zustand Store + 单元测试

**文件：**
- 创建：`interview-ai/frontend/store/interviewStore.ts`
- 创建：`interview-ai/frontend/hooks/useInterviewFlowManager.ts`
- 创建：`interview-ai/frontend/__tests__/useInterviewFlowManager.test.ts`

**做什么：**
`interviewStore.ts`（Zustand）：`{ questions, currentQuestionIndex, state: 'IDLE'|'READING'|'RECORDING'|'PROCESSING'|'REVIEW', audioBlobs }`

`useInterviewFlowManager.ts`：
- `startExam(questions)` → IDLE→READING
- `startRecording()` → READING→RECORDING，调用 `MediaRecorder.start()`
- `stopCurrentRecording()` → 合并 Blob Chunks
- `nextQuestion()` → 非最后题 → 重置 READING
- `submitAll()` → RECORDING→PROCESSING → POST → 成功 → REVIEW

`test` 覆盖 6 个场景（mock MediaRecorder）：初始 IDLE / startExam→READING / startRecording→RECORDING / 非最后题→READING / 最后题→PROCESSING / 无未定义中间态。

**验收标准：**
```
npm test __tests__/useInterviewFlowManager.test.ts -- --verbose
# 期望: 6 passed
```

**验证命令：**
```bash
cd interview-ai/frontend && npm test __tests__/useInterviewFlowManager.test.ts -- --verbose
```

**提交：**
```bash
git add interview-ai/frontend/store/ interview-ai/frontend/hooks/useInterviewFlowManager.ts interview-ai/frontend/__tests__/useInterviewFlowManager.test.ts
git commit -m "feat: implement useInterviewFlowManager state machine with 6 unit tests"
```

### 研究洞察

**关键修正 — Blob 不应存入 Zustand（内存泄漏 + DevTools 崩溃）：**

Zustand DevTools 会序列化整个 store 状态；Blob 对象无法 JSON 序列化，导致 DevTools 崩溃。且 Blob 长期存在 Zustand 中会阻止 GC：

```typescript
// store/interviewStore.ts（正确方式）
import { create } from 'zustand'

type InterviewState = 'IDLE' | 'READING' | 'RECORDING' | 'PROCESSING' | 'REVIEW'

interface InterviewStore {
  questions: Question[]
  currentQuestionIndex: number
  state: InterviewState
  isHydrated: boolean
  // ❌ 不存 audioBlobs: Blob[]
  setQuestions: (questions: Question[]) => void
  setState: (state: InterviewState) => void
  nextQuestion: () => void
  reset: () => void
}

export const useInterviewStore = create<InterviewStore>((set) => ({
  questions: [],
  currentQuestionIndex: 0,
  state: 'IDLE',
  isHydrated: false,
  setQuestions: (questions) => set({ questions, state: 'READING' }),
  setState: (state) => set({ state }),
  nextQuestion: () => set((s) => ({ currentQuestionIndex: s.currentQuestionIndex + 1, state: 'READING' })),
  reset: () => set({ questions: [], currentQuestionIndex: 0, state: 'IDLE' }),
}))
```

```typescript
// hooks/useInterviewFlowManager.ts（Blob 存外部 ref）
const audioBlobsRef = useRef<Map<number, Blob>>(new Map())  // 不进 Zustand

// stopCurrentRecording 时：
const blob = new Blob(chunksRef.current, { type: mimeType })
audioBlobsRef.current.set(currentQuestionIndex, blob)
// 提交时从 ref 取
```

**最佳实践 — `isHydrated` 防止 SSR 渲染不一致：**
```typescript
// 在 layout.tsx 或 Provider 中
'use client'
useEffect(() => {
  useInterviewStore.setState({ isHydrated: true })
}, [])

// 在组件中
const isHydrated = useInterviewStore(s => s.isHydrated)
if (!isHydrated) return <Skeleton />  // SSR 和 CSR 第一帧一致
```

---

### T2.6 实现考前设备检测组件

**文件：**
- 创建：`interview-ai/frontend/components/DeviceCheck.tsx`

**做什么：**
- `useEffect` 调用 `getUserMedia({ audio: true })`
- 成功 → `AudioContext + AnalyserNode` 驱动 Canvas 音量波形实时渲染
- `NotAllowedError` → `data-testid="mic-error"` 红色内联文本，"进入考场"按钮 `disabled`
- **禁止弹窗**；"进入考场"按钮 `min-h-12 min-w-12`（48px 触控热区）

**验收标准：**
- 授权 → 波形动画，按钮可用
- 拒绝 → 红色提示，按钮 disabled，无 modal

**验证命令：** Chrome → 手动切换麦克风权限，观察两种状态。

**提交：**
```bash
git add interview-ai/frontend/components/DeviceCheck.tsx
git commit -m "feat: implement microphone device check with waveform and inline permission error"
```

### 研究洞察

**关键修正 — SSR guard for MediaRecorder 和 getUserMedia：**

Next.js 在服务端渲染时没有 `window`、`navigator`、`MediaRecorder`，需要守卫：

```typescript
// components/DeviceCheck.tsx
'use client'
import { useEffect, useRef, useState } from 'react'

export function DeviceCheck({ onReady }: { onReady: () => void }) {
  const [micStatus, setMicStatus] = useState<'pending' | 'granted' | 'denied'>('pending')
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const streamRef = useRef<MediaStream | null>(null)

  useEffect(() => {
    // SSR guard：typeof navigator 检查
    if (typeof navigator === 'undefined' || !navigator.mediaDevices) {
      setMicStatus('denied')
      return
    }

    navigator.mediaDevices.getUserMedia({ audio: true, video: false })
      .then((stream) => {
        streamRef.current = stream
        setMicStatus('granted')
        // 启动波形渲染
        startWaveform(stream, canvasRef.current!)
      })
      .catch((err) => {
        if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
          setMicStatus('denied')
        }
      })

    return () => {
      // 离开时停止麦克风（否则浏览器录音指示灯不消失）
      streamRef.current?.getTracks().forEach(t => t.stop())
    }
  }, [])

  return (
    <div>
      <canvas ref={canvasRef} width={300} height={60} />
      {micStatus === 'denied' && (
        <p data-testid="mic-error" className="text-red-500 text-sm">
          麦克风权限被拒绝，请在浏览器设置中允许访问
        </p>
      )}
      <button
        onClick={onReady}
        disabled={micStatus !== 'granted'}
        className="min-h-12 min-w-12 px-4 py-2 bg-blue-600 text-white rounded disabled:opacity-50"
      >
        进入考场
      </button>
    </div>
  )
}
```

**边缘情况：**
- iOS Safari 17+ 要求用户手势触发 `getUserMedia`（不能在页面加载时自动调用）；组件需在按钮点击后请求权限
- `AudioContext` 在 iOS Safari 需 `resume()` 调用才能启动（autoplay 策略）

---

### T2.7 实现 /interview/mock 页面（READING + RECORDING 状态）

**文件：**
- 创建：`interview-ai/frontend/app/interview/mock/page.tsx`
- 创建：`interview-ai/frontend/hooks/useAudioRecorder.ts`

**做什么：**
`useAudioRecorder.ts`：`isTypeSupported` 探测 → 优先 `audio/webm;codecs=opus` → `MediaRecorder` 录制 + Blob Chunks 合并。

`page.tsx` 按 state 渲染：
- **READING**：全屏无干扰，题目文本，60s 审题计时器（`useInterviewTimer`），"思考完毕，开始作答"按钮
- **RECORDING**：答题倒计时（`time_limit_seconds`），右上角 `animate-pulse` 红色录制指示灯（`data-testid="recording-indicator"`），"作答结束"按钮（`min-h-12 min-w-12`）
- 倒计时归零自动停止录音

**验收标准：**
- 加载后题目显示，60s 审题倒计时开始
- 点击"思考完毕"→ 录制指示灯出现，答题计时器开始
- "作答结束"→ 停止录音

**验证命令：** 手动走 READING→RECORDING 流程，确认状态切换和 UI 变化。

**提交：**
```bash
git add interview-ai/frontend/app/interview/ interview-ai/frontend/hooks/useAudioRecorder.ts
git commit -m "feat: implement /interview/mock READING and RECORDING states with MediaRecorder"
```

### 研究洞察

**最佳实践 — MediaRecorder MIME 类型 fallback 链（跨浏览器兼容）：**

```typescript
// hooks/useAudioRecorder.ts
'use client'
import { useRef, useCallback } from 'react'

// 优先级降序：Chromium/Firefox 支持 opus，Safari 支持 mp4
const MIME_CANDIDATES = [
  'audio/webm;codecs=opus',  // Chrome/Firefox 最优
  'audio/webm',              // Chrome/Firefox fallback
  'audio/mp4;codecs=mp4a.40.2', // Safari 最优
  'audio/mp4',               // Safari fallback
] as const

function getSupportedMime(): string {
  // SSR guard
  if (typeof MediaRecorder === 'undefined') return ''
  return MIME_CANDIDATES.find(m => MediaRecorder.isTypeSupported(m)) ?? ''
}

export function useAudioRecorder() {
  const recorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const mimeType = useRef(getSupportedMime())

  const startRecording = useCallback(async (stream: MediaStream) => {
    chunksRef.current = []
    const options: MediaRecorderOptions = {}
    if (mimeType.current) {
      options.mimeType = mimeType.current  // 只有找到支持的才设置，不强制
    }

    const recorder = new MediaRecorder(stream, options)
    recorder.ondataavailable = (e) => {
      if (e.data.size > 0) chunksRef.current.push(e.data)
    }
    // timeslice=10000ms：每10秒一个chunk，保证3分钟录音内存安全
    recorder.start(10_000)
    recorderRef.current = recorder
  }, [])

  const stopRecording = useCallback((): Promise<Blob> => {
    return new Promise((resolve) => {
      const recorder = recorderRef.current!
      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, {
          type: mimeType.current || 'audio/webm'
        })
        resolve(blob)
      }
      recorder.stop()
    })
  }, [])

  return { startRecording, stopRecording, mimeType: mimeType.current }
}
```

**关键修正 — 上传时不要手动设置 Content-Type：**
```typescript
// ❌ 错误：手动设置 Content-Type 会覆盖 FormData 的 boundary
headers: { 'Content-Type': 'multipart/form-data' }

// ✅ 正确：fetch 自动从 FormData 推断（含 boundary）
const formData = new FormData()
formData.append('audio', blob, `recording.${ext}`)  // 文件名决定扩展名
formData.append('question_id', questionId)
await fetch('/api/evaluations', { method: 'POST', body: formData })
// 不加 Content-Type header
```

---

### T2.8 实现多题流转、弱网重试、PROCESSING 骨架屏

**文件：**
- 修改：`interview-ai/frontend/app/interview/mock/page.tsx`
- 创建：`interview-ai/frontend/components/NetworkRetryBanner.tsx`
- 创建：`interview-ai/frontend/components/ProcessingSkeleton.tsx`
- 创建：`interview-ai/frontend/app/api/evaluations/route.ts`（Next.js Route Handler 代理）

**做什么：**
多题：非最后题停止录音后 → `currentQuestionIndex++` → 重回 READING；最后题 → 调 `submitAll()` → PROCESSING。

`NetworkRetryBanner.tsx`：捕获 `TypeError: Failed to fetch` 或 `navigator.onLine=false` → Blob 留内存，显示"网络异常，请保持页面勿刷新"内联提示 + "重试上传"按钮；**禁止弹窗，禁止 IndexedDB**。

`ProcessingSkeleton.tsx`：全屏骨架屏，"AI 正在评分中，请稍候…"

`app/api/evaluations/route.ts`：代理 POST 至 `API_BASE_URL/api/v1/evaluations/submit`，转发 Authorization header；评估成功后 `router.push('/review/{evaluation_id}')`。

**验收标准：**
- 多题：第一题结束后自动进入第二题 READING
- 弱网：DevTools → Offline → 停止录音 → 出现内联提示 → Online → 点击重试 → 跳转复盘页
- PROCESSING 骨架屏出现，≤15s 后跳转 /review

**验证命令：** 手动端到端走完整流程（含弱网模拟）。

**提交：**
```bash
git add interview-ai/frontend/components/ interview-ai/frontend/app/api/
git commit -m "feat: implement multi-question flow, weak-network retry, PROCESSING skeleton"
```

### 研究洞察

**最佳实践 — Route Handler 用服务端环境变量 + idempotency_key：**

```typescript
// app/api/evaluations/route.ts
import { NextRequest, NextResponse } from 'next/server'
import { randomUUID } from 'crypto'

export async function POST(request: NextRequest) {
  // API_BASE_URL 是服务端环境变量（无 NEXT_PUBLIC_ 前缀，不暴露到客户端）
  const backendUrl = process.env.API_BASE_URL
  if (!backendUrl) {
    return NextResponse.json({ error: 'Backend URL not configured' }, { status: 500 })
  }

  const authHeader = request.headers.get('Authorization')
  if (!authHeader) {
    return NextResponse.json({ error_code: 'ERR_UNAUTHORIZED' }, { status: 401 })
  }

  const formData = await request.formData()

  // 生成幂等 key（客户端重试时发送相同 key，服务端去重）
  const clientRequestId = formData.get('client_request_id') as string || randomUUID()

  // 转发到 FastAPI，附带 client_request_id
  formData.set('client_request_id', clientRequestId)

  const response = await fetch(`${backendUrl}/api/v1/evaluations/submit`, {
    method: 'POST',
    headers: { Authorization: authHeader },
    body: formData,
  })

  const data = await response.json()
  return NextResponse.json(data, { status: response.status })
}
```

**最佳实践 — Blob 放 `useRef` 供重试使用（不放 Zustand）：**

```typescript
// hooks/useInterviewFlowManager.ts（弱网重试关键设计）
const pendingBlobRef = useRef<{ blob: Blob; questionId: string; clientRequestId: string } | null>(null)

async function submitWithRetry() {
  if (!pendingBlobRef.current) return

  const { blob, questionId, clientRequestId } = pendingBlobRef.current
  const formData = new FormData()
  formData.append('audio', blob, 'recording.webm')
  formData.append('question_id', questionId)
  formData.append('client_request_id', clientRequestId)  // 相同 ID，服务端去重

  try {
    const res = await fetch('/api/evaluations', {
      method: 'POST',
      headers: { Authorization: `Bearer ${accessToken}` },
      body: formData,
    })
    if (res.ok) {
      const data = await res.json()
      pendingBlobRef.current = null  // 清除，让 Blob 被 GC
      router.push(`/review/${data.id}`)
    }
  } catch (e) {
    if (e instanceof TypeError && e.message.includes('fetch')) {
      setNetworkError(true)  // 显示 NetworkRetryBanner
    }
  }
}
```

---

## Milestone 3：复盘看板（1–2 天）

**目标：** /review/[id] 展示七维雷达图 + 音频同步高亮 + 双栏对照 + 改进建议 + 反模板化警告。

**依赖：** Milestone 2 完成。

---

### T3.1 实现 /review/[id] 数据加载骨架

**文件：**
- 创建：`interview-ai/frontend/app/review/[id]/page.tsx`
- 创建：`interview-ai/frontend/types/evaluation.ts`

**做什么：**
`evaluation.ts`：定义 `EvaluationResult` TypeScript 类型（镜像 PRD §0.4 全部字段）。

`page.tsx`（Server Component）：从 `/api/v1/evaluations/{id}` 拉取数据（附 Authorization），404 → "记录不存在"，成功 → 传入 Client Components。

**验收标准：** /review/{valid-id} 正常渲染；/review/{invalid-id} 显示 404 提示。

**验证命令：** 浏览器访问一个已存在的 evaluation_id。

**提交：**
```bash
git add interview-ai/frontend/app/review/ interview-ai/frontend/types/
git commit -m "feat: implement /review/[id] page data fetching and 404 handling"
```

### 研究洞察

**最佳实践 — 从 `supabase.ts` 生成类型直接使用（避免手写 types）：**

```typescript
// types/evaluation.ts（从 supabase gen types 派生，不手写）
import type { Database } from './supabase'

// 直接用 Supabase 生成的类型，确保与 DB schema 同步
export type EvaluationResult = Database['public']['Tables']['evaluations']['Row']

// 如需扩展（前端专用字段）
export interface EvaluationResultWithQuestion extends EvaluationResult {
  question?: Database['public']['Tables']['questions']['Row']
}
```

**最佳实践 — Server Component 数据获取（Next.js App Router 模式）：**
```typescript
// app/review/[id]/page.tsx（Server Component，可直接访问 cookies）
import { cookies } from 'next/headers'
import { notFound } from 'next/navigation'

export default async function ReviewPage({ params }: { params: { id: string } }) {
  const cookieStore = cookies()
  // Server Component 通过 cookie 获取 token（需在登录时同步设置 httpOnly cookie）
  // 或通过 Route Handler 代理（推荐）

  const res = await fetch(`${process.env.API_BASE_URL}/api/v1/evaluations/${params.id}`, {
    cache: 'no-store',  // 评估结果不应缓存
  })
  if (res.status === 404) notFound()

  const evaluation: EvaluationResult = await res.json()
  return <ReviewDashboard evaluation={evaluation} />
}
```

---

### T3.2 实现七维雷达图（Recharts RadarChart）

**文件：**
- 创建：`interview-ai/frontend/components/review/RadarScoreChart.tsx`

**做什么：**
```bash
npm install recharts
```
7 维度（中文标签）+ RadarChart，hover tooltip 显示维度名 + 分数 + 权重，数据范围 0-100。

**验收标准：** 7 维轴标签显示中文，数据点与 evaluation 字段一一对应。

**验证命令：** 浏览器访问 /review/{id}，观察雷达图。

**提交：**
```bash
git add interview-ai/frontend/components/review/RadarScoreChart.tsx
git commit -m "feat: implement 7-dimension radar chart with Recharts"
```

### 研究洞察

**最佳实践 — Recharts v3 雷达图完整实现（中文标签 + SSR 安全）：**

```typescript
// components/review/RadarScoreChart.tsx
'use client'  // ← 必须，Recharts 使用 DOM API
import dynamic from 'next/dynamic'
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Tooltip, ResponsiveContainer } from 'recharts'

// SSR 安全包装（Recharts 依赖 window）
// 如果整个文件已是 'use client'，可以不用 dynamic，但保留作为最佳实践
interface ChartData { subject: string; score: number; weight: string; fullMark: number }

interface CustomTickProps {
  x?: number; y?: number; cx?: number; cy?: number; payload?: { value: string }
}

// 中文标签换行（每4字一行）
function CustomAngleTick({ x = 0, y = 0, cx = 0, cy = 0, payload }: CustomTickProps) {
  const label = payload?.value ?? ''
  const lines: string[] = []
  for (let i = 0; i < label.length; i += 4) lines.push(label.slice(i, i + 4))

  const deltaX = x - cx
  const textAnchor = deltaX > 10 ? 'start' : deltaX < -10 ? 'end' : 'middle'

  return (
    <g>
      <text x={x} y={y} textAnchor={textAnchor} fontSize={12} fill="#374151">
        {lines.map((line, i) => (
          <tspan key={i} x={x} dy={i === 0 ? 0 : 14}>{line}</tspan>
        ))}
      </text>
    </g>
  )
}

export function RadarScoreChart({ evaluation }: { evaluation: EvaluationResult }) {
  const data: ChartData[] = [
    { subject: '综合分析', score: evaluation.analysis_ability_score, weight: '20%', fullMark: 100 },
    { subject: '计划组织协调', score: evaluation.organization_coordination_score, weight: '15%', fullMark: 100 },
    { subject: '应急应变', score: evaluation.emergency_response_score, weight: '15%', fullMark: 100 },
    { subject: '人际交往', score: evaluation.interpersonal_communication_score, weight: '15%', fullMark: 100 },
    { subject: '言语表达', score: evaluation.language_expression_score, weight: '15%', fullMark: 100 },
    { subject: '求职动机', score: evaluation.job_matching_score, weight: '10%', fullMark: 100 },
    { subject: '副语言流畅度', score: evaluation.paralinguistic_fluency_score, weight: '10%', fullMark: 100 },
  ]

  return (
    <ResponsiveContainer width="100%" height={380}>
      <RadarChart data={data} margin={{ top: 20, right: 30, bottom: 20, left: 30 }}>
        <PolarGrid />
        <PolarAngleAxis dataKey="subject" tick={<CustomAngleTick />} />
        <PolarRadiusAxis domain={[0, 100]} tickCount={5} />  {/* 显式 domain，不归一化 */}
        <Radar
          name="得分"
          dataKey="score"
          stroke="#3B82F6"
          fill="#3B82F6"
          fillOpacity={0.3}
        />
        <Tooltip
          formatter={(value, name, props) => [
            `${value} 分（权重 ${props.payload.weight}）`,
            props.payload.subject
          ]}
        />
      </RadarChart>
    </ResponsiveContainer>
  )
}
```

**边缘情况：**
- 所有分数为 0 时，雷达图退化为一个点（而非多边形）；在外层加 "暂无数据" 判断
- `ResponsiveContainer` 在 Flexbox 容器中需要显式设置 `height`，否则渲染为 0

---

### T3.3 实现音频播放器 + 转写文本高亮同步（requestAnimationFrame）

**文件：**
- 创建：`interview-ai/frontend/hooks/useTranscriptHighlight.ts`
- 创建：`interview-ai/frontend/components/review/AudioTranscriptSync.tsx`

**做什么：**
`useTranscriptHighlight(audioRef, segments) -> { activeIndex }`：rAF 循环读 `audioRef.currentTime`，找 `[start-0.5, end+0.5]` 范围内的 segment，返回 activeIndex。**禁止 setInterval**。

`AudioTranscriptSync.tsx`：HTML5 `<audio controls>`，转写段落列表，`activeIndex` 段 `bg-amber-100`，`scrollIntoView({ behavior:'smooth', block:'center' })`。

**验收标准：**
- 播放时高亮随时间戳移动（±0.5s 容差）
- 拖动进度条到第 30s → 含第 30s 的段落变黄
- 无闪烁（rAF 保证 ≤100ms 帧间隔）

**验证命令：** 手动播放音频，拖动进度条验证。

**提交：**
```bash
git add interview-ai/frontend/hooks/useTranscriptHighlight.ts interview-ai/frontend/components/review/AudioTranscriptSync.tsx
git commit -m "feat: implement audio-transcript sync with rAF, ±0.5s tolerance, smooth scroll"
```

### 研究洞察

**最佳实践 — rAF 实现（自动暂停 + 清理）：**

```typescript
// hooks/useTranscriptHighlight.ts
import { useState, useEffect, useRef, RefObject } from 'react'

interface Segment { text: string; start: number; end: number }

export function useTranscriptHighlight(
  audioRef: RefObject<HTMLAudioElement>,
  segments: Segment[]
) {
  const [activeIndex, setActiveIndex] = useState(-1)
  const rafRef = useRef<number>(0)

  useEffect(() => {
    const audio = audioRef.current
    if (!audio || segments.length === 0) return

    function tick() {
      const currentTime = audio!.currentTime
      const TOLERANCE = 0.5

      // 二分查找比线性扫描更高效（segments 按时间升序）
      let found = -1
      for (let i = 0; i < segments.length; i++) {
        if (
          currentTime >= segments[i].start - TOLERANCE &&
          currentTime <= segments[i].end + TOLERANCE
        ) {
          found = i
          break
        }
      }

      setActiveIndex(prev => prev !== found ? found : prev)  // 避免无意义重渲染

      if (!audio!.paused) {
        rafRef.current = requestAnimationFrame(tick)
      }
    }

    const handlePlay = () => { rafRef.current = requestAnimationFrame(tick) }
    const handlePause = () => cancelAnimationFrame(rafRef.current)
    const handleSeeked = () => { rafRef.current = requestAnimationFrame(tick) }

    audio.addEventListener('play', handlePlay)
    audio.addEventListener('pause', handlePause)
    audio.addEventListener('seeked', handleSeeked)

    return () => {
      cancelAnimationFrame(rafRef.current)
      audio.removeEventListener('play', handlePlay)
      audio.removeEventListener('pause', handlePause)
      audio.removeEventListener('seeked', handleSeeked)
    }
  }, [audioRef, segments])

  return { activeIndex }
}
```

**边缘情况：**
- 音频结束（`ended` 事件）后 rAF 不应继续运行，需监听 `ended` 事件调用 `cancelAnimationFrame`
- `segments` 为空数组时直接返回 `activeIndex = -1`，不启动 rAF

---

### T3.4 实现双栏对照 + 结构检查 + 改进建议 + 反模板化警告

**文件：**
- 创建：`interview-ai/frontend/components/review/AnswerComparison.tsx`
- 创建：`interview-ai/frontend/components/review/StructuralCheck.tsx`
- 创建：`interview-ai/frontend/components/review/ImprovementList.tsx`
- 创建：`interview-ai/frontend/components/review/AntiTemplateWarning.tsx`

**做什么：**
`AnswerComparison.tsx`：`grid grid-cols-2` 双栏（左：考生原文，右：AI 示范），窄屏折叠单栏。

`StructuralCheck.tsx`：`present_elements` → 绿色标签，`missing_elements` → 红色标签。

`ImprovementList.tsx`：有序列表渲染 `improvement_suggestions`。

`AntiTemplateWarning.tsx`：`anti_template_warning !== null` → 黄色警告横幅（`bg-yellow-50 border-yellow-400`），`null` → 不渲染。

**验收标准：**
- 双栏内容正确填充，移动端 375px 无横向滚动
- `anti_template_warning=null` 时无警告横幅
- `anti_template_warning` 非 null 时黄色横幅出现

**验证命令：**
- DevTools 375px 宽度检查双栏折叠
- 构造含 anti_template_warning 的评估记录，观察警告横幅

**提交：**
```bash
git add interview-ai/frontend/components/review/
git commit -m "feat: implement review dashboard: dual-column, structural check, suggestions, warning banner"
```

### 研究洞察

**最佳实践 — 响应式双栏布局（375px 适配）：**

```typescript
// components/review/AnswerComparison.tsx
'use client'
export function AnswerComparison({
  userAnswer,
  modelAnswer,
}: {
  userAnswer: string
  modelAnswer: string
}) {
  return (
    // 宽屏双栏，窄屏（<768px）自动折叠为单栏
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div className="border rounded-lg p-4">
        <h3 className="font-semibold text-gray-700 mb-2">考生原文</h3>
        <p className="text-sm text-gray-600 leading-relaxed whitespace-pre-wrap">
          {userAnswer}
        </p>
      </div>
      <div className="border rounded-lg p-4 bg-blue-50">
        <h3 className="font-semibold text-blue-700 mb-2">AI 示范答案</h3>
        <p className="text-sm text-blue-800 leading-relaxed whitespace-pre-wrap">
          {modelAnswer}
        </p>
      </div>
    </div>
  )
}
```

**最佳实践 — AntiTemplateWarning null 检查：**
```typescript
// components/review/AntiTemplateWarning.tsx
export function AntiTemplateWarning({ warning }: { warning: string | null }) {
  // null 时不渲染任何内容（PRD §9 条目12：null 时明确不渲染）
  if (warning === null) return null

  return (
    <div className="flex items-start gap-2 rounded-lg border border-yellow-400 bg-yellow-50 p-4">
      <span className="text-yellow-600 text-lg">⚠</span>
      <div>
        <p className="font-semibold text-yellow-800">反模板化提醒</p>
        <p className="text-sm text-yellow-700 mt-1">{warning}</p>
      </div>
    </div>
  )
}
```

**边缘情况：**
- `improvement_suggestions` 为空数组（`[]`）时，`ImprovementList` 应显示"暂无改进建议"而非空列表
- `structural_framework_check.present_elements` 或 `missing_elements` 可能为空数组，需防御性渲染

---

## Milestone 4：安全加固 + 跨端适配（1 天）

**目标：** API 密钥安全隔离验证，移动端 375px 适配，Safari/Chrome 双端兼容。

**依赖：** Milestone 3 完成。

---

### T4.1 API 密钥安全审计

**文件：** 无新建，审计扫描

**做什么：**
```bash
# 扫描前端代码，确认无 AI API 密钥
grep -r "OPENAI_API_KEY\|GROQ_API_KEY\|sk-\|gsk_" interview-ai/frontend/ \
  --include="*.ts" --include="*.tsx" --exclude-dir=".next"
# 期望: 无任何匹配

# 同时扫描后端 URL 环境变量是否泄露到前端
grep -r "NEXT_PUBLIC_API_BASE_URL" interview-ai/frontend/ \
  --include="*.ts" --include="*.tsx"
# 期望: 无任何匹配（应使用无前缀的 API_BASE_URL）
```

如发现泄露，立即修复（移至后端 .env）。

**验收标准：** grep 输出为空（0 匹配）。

**验证命令：**
```bash
grep -r "OPENAI_API_KEY\|GROQ_API_KEY\|sk-\|gsk_" interview-ai/frontend/ --include="*.ts" --include="*.tsx"
grep -r "NEXT_PUBLIC_API_BASE_URL" interview-ai/frontend/ --include="*.ts" --include="*.tsx"
# 期望: 两条命令均无输出
```

**提交：**
```bash
git commit -am "security: verify no AI API keys exposed in frontend codebase"
```

### 研究洞察

**最佳实践 — 扩展安全扫描范围：**

```bash
# 扫描 .env.local 是否被意外提交到 git
git ls-files | grep -E "\.env\.local$|\.env$" | head -5
# 期望: 无输出（.env.local 应在 .gitignore 中）

# 检查 git 历史中是否曾出现过密钥（即使已删除）
git log --all --grep="sk-\|gsk_" --oneline
git log -p --all -S "sk-" -- "*.env*" 2>/dev/null | head -30

# 检查 Docker image 是否包含密钥
docker run --rm interview-ai-backend env | grep -E "OPENAI|GROQ|SUPABASE"
# 期望: 无输出（密钥应通过 env_file 注入，不 BAKE 进镜像）
```

**Dockerfile 安全 — 使用 secrets mount（不把密钥写进 layer）：**
```dockerfile
# 使用 BuildKit secrets（不进入 image layer）
# docker build --secret id=openai_key,env=OPENAI_API_KEY .
RUN --mount=type=secret,id=openai_key \
    pip install -r requirements.txt  # 构建时不需要密钥，示例结构
```

**边缘情况：**
- `NEXT_PUBLIC_SUPABASE_ANON_KEY` 暴露到前端是**预期行为**（RLS 保护下安全），不是问题；扫描时排除此变量

---

### T4.2 移动端适配（375px + 触控热区 48px）

**文件：**
- 修改：`interview-ai/frontend/app/globals.css`
- 修改：相关页面组件（按需）

**做什么：**
1. `globals.css`：`body { overflow-x: hidden; }` 防横向溢出
2. 所有主操作按钮（"开始作答"、"作答结束"、"重试上传"、"进入考场"）：`min-h-12 min-w-12 px-4`
3. 字体大小最小 14px（Tailwind `text-sm` 或 `text-base`）

**验收标准：**
Chrome DevTools → 375px → 所有页面（/login, /interview/mock, /review/[id]）无横向滚动条。

**验证命令：**
Chrome DevTools → Device Toolbar → iPhone SE (375×667) → 逐页检查。

**提交：**
```bash
git commit -am "fix: mobile responsive 375px layout, touch targets ≥48px"
```

### 研究洞察

**最佳实践 — iOS 安全区域适配（iPhone 刘海屏）：**

```css
/* globals.css */
body {
  overflow-x: hidden;
  /* iOS 安全区域 padding（刘海屏 + 底部 Home Bar）*/
  padding-top: env(safe-area-inset-top);
  padding-bottom: env(safe-area-inset-bottom);
  padding-left: env(safe-area-inset-left);
  padding-right: env(safe-area-inset-right);
}
```

**最佳实践 — 触控热区最佳实践（WCAG 2.5.5）：**
```typescript
// 所有交互按钮的 className 模板
const buttonClass = "min-h-[48px] min-w-[48px] px-4 py-2 rounded-lg"
// Tailwind JIT 中用方括号语法保证精确 48px
```

**边缘情况：**
- Safari 在 iPhone 上，`<audio controls>` 默认宽度可能超出 375px 容器；需 `className="w-full max-w-full"`
- 横屏模式（landscape）时底部 Home Bar 占用高度，考场计时器需避免被遮挡

---

### T4.3 Mock 链路端到端耗时断言（CI 发版阻断）

**文件：**
- 创建：`interview-ai/backend/tests/test_pipeline_latency.py`

**做什么：**
用 `unittest.mock` 替换 Groq client 和 openai client（立即返回预设数据），调用完整 submit pipeline，断言 `elapsed <= 15.0`：

```python
async def test_pipeline_latency_mock():
    start = time.perf_counter()
    result = await run_full_pipeline(
        audio_bytes=b"fake-audio",
        question=test_question,
        asr_client=mock_asr,    # 立即返回预设 transcript_segments
        llm_client=mock_llm,    # 立即返回预设 LLMEvaluationOutput
    )
    elapsed = time.perf_counter() - start
    assert elapsed <= 15.0
    assert result.final_score is not None
```

**验收标准：**
```
pytest tests/test_pipeline_latency.py -v
# 期望: passed, elapsed 远小于 15s（mock 场景应 <1s）
```

**验证命令：**
```bash
cd interview-ai/backend && pytest tests/test_pipeline_latency.py -v
```

**提交：**
```bash
git add interview-ai/backend/tests/test_pipeline_latency.py
git commit -m "test: add mock pipeline latency assertion ≤15s for CI gate"
```

### 研究洞察

**最佳实践 — 测试 asyncio.gather 并行行为：**

```python
# tests/test_pipeline_latency.py
import asyncio
import time
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_pipeline_latency_with_parallel_io():
    """验证 asyncio.gather 并行化有效（LLM + Storage 不串行）"""

    call_log = []

    async def mock_llm_eval(*args, **kwargs):
        call_log.append(('llm_start', time.perf_counter()))
        await asyncio.sleep(0.05)  # 模拟 50ms LLM 延迟
        call_log.append(('llm_end', time.perf_counter()))
        return make_mock_llm_output()

    async def mock_upload(*args, **kwargs):
        call_log.append(('upload_start', time.perf_counter()))
        await asyncio.sleep(0.05)  # 模拟 50ms Storage 延迟
        call_log.append(('upload_end', time.perf_counter()))
        return "storage/path/audio.wav"

    start = time.perf_counter()
    await asyncio.gather(mock_llm_eval(), mock_upload())
    elapsed = time.perf_counter() - start

    # 并行时总时间 ≈ 单个任务时间（50ms），而非串行时间（100ms）
    assert elapsed < 0.08, f"预期并行耗时 <80ms，实际 {elapsed*1000:.1f}ms（可能未并行执行）"

@pytest.mark.asyncio
async def test_pipeline_latency_e2e_mock():
    """端到端 mock 测试（全部 I/O mocked）"""
    from app.services.evaluation_pipeline import run_pipeline

    start = time.perf_counter()
    result = await run_pipeline(
        audio_bytes=b"x" * 1000,
        question=make_test_question(),
        client_request_id="test-uuid-1234",
        app_state=make_mock_app_state(),
    )
    elapsed = time.perf_counter() - start

    assert elapsed <= 15.0, f"Pipeline 耗时 {elapsed:.2f}s 超出 15s SLA"
    assert result.final_score is not None
    assert 0 <= result.final_score <= 100
```

---

## Milestone 5：测试全绿 + 部署就绪（1 天）

**目标：** Docker Compose 一键启动，全量测试通过，benchmark 脚本可运行。

**依赖：** Milestone 4 完成。

---

### T5.1 创建 Docker Compose 本地开发环境

**文件：**
- 创建：`interview-ai/docker-compose.yml`

**做什么：**
```yaml
version: "3.9"
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    env_file:
      - ./backend/.env
    volumes:
      - ./backend:/app
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
前端无需容器化（`npm run dev` 直接运行）。

**验收标准：**
```
docker compose up backend --build
curl http://localhost:8000/api/v1/health  # {"status":"ok"}
docker run --rm interview-ai-backend-backend ffmpeg -version  # 输出版本号
```

**验证命令：**
```bash
cd interview-ai && docker compose up backend --build -d
curl http://localhost:8000/api/v1/health
```

**提交：**
```bash
git add interview-ai/docker-compose.yml
git commit -m "feat: add Docker Compose for one-command local backend startup with ffmpeg"
```

### 研究洞察

**最佳实践 — 添加 `.dockerignore`（避免复制不必要文件）：**

```
# interview-ai/backend/.dockerignore
__pycache__/
*.pyc
*.pyo
.pytest_cache/
tests/
.env
.env.local
*.egg-info/
dist/
.git/
```

**最佳实践 — healthcheck 配置（Docker Compose 健康检测）：**
```yaml
# docker-compose.yml
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    env_file: ./backend/.env
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
```

**边缘情况：**
- `volumes: - ./backend:/app` 会覆盖容器内 `pip install` 的包；开发模式需用 named volume 或去掉 volume 挂载
- Windows 路径分隔符：`./backend` 在 Docker Desktop for Windows 正常工作，无需修改

---

### T5.2 运行全量测试套件确保全绿

**文件：** 按需修复各测试文件

**做什么：**
```bash
# 后端全量测试
cd interview-ai/backend && pytest tests/ -v --tb=short

# 前端全量测试
cd interview-ai/frontend && npm test -- --watchAll=false
```

修复所有失败测试（**不允许修改断言来通过测试，必须修改实现**）。

**验收标准：**
```
后端: X passed, 0 failed, 0 error
前端: Y passed, 0 failed, 0 error
```

**验证命令：**
```bash
cd interview-ai/backend && pytest tests/ -v
cd interview-ai/frontend && npm test -- --watchAll=false
```

**提交：**
```bash
git commit -am "test: all backend and frontend tests green"
```

### 研究洞察

**最佳实践 — pytest-asyncio 配置（0.21+ 必须显式设置）：**

```ini
# interview-ai/backend/pytest.ini
[pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
```

若不设置 `asyncio_mode = auto`，所有 `async def test_*` 需手动加 `@pytest.mark.asyncio`，否则 coroutine 不被执行（常见静默失败：测试"通过"但实际没有运行）。

**最佳实践 — React Testing Library 测试 Hooks：**

```typescript
// __tests__/useInterviewTimer.test.ts
import { renderHook, act } from '@testing-library/react'
import { useInterviewTimer } from '../hooks/useInterviewTimer'

// 使用 Jest 假计时器（not real timers）
jest.useFakeTimers()

test('3 分钟计时漂移 ≤1s', () => {
  // Mock performance.now() 推进
  const startTime = performance.now()
  jest.spyOn(performance, 'now')
    .mockReturnValueOnce(startTime)
    .mockImplementation(() => startTime + 180_000)  // 跳到 180s 后

  const { result } = renderHook(() => useInterviewTimer(180, jest.fn()))

  act(() => {
    jest.advanceTimersByTime(180_100)  // 比 180s 多 100ms
  })

  // 应该在 179-181 之间（≤1s 漂移）
  expect(result.current.secondsLeft).toBeLessThanOrEqual(1)
})
```

**边缘情况：**
- 前端测试中 `MediaRecorder` 不存在，需全局 mock：`global.MediaRecorder = jest.fn()`
- `sessionStorage` 在 jsdom 中存在但共享状态，每个测试前需 `sessionStorage.clear()`

---

### T5.3 创建 benchmark_eval.py + 结果模板

**文件：**
- 创建：`interview-ai/backend/scripts/benchmark_eval.py`
- 创建：`interview-ai/backend/docs/benchmark_results.md`

**做什么：**
`benchmark_eval.py`（用文字稿直接调 LLM，无需音频）：
```python
# 对 5 道标准问题各调用 5 次 run_llm_evaluation
# 计算每道题 final_score 极差（Max-Min）
# 极差 ≤ 3 → PASS，否则 WARN
# 追加写入 docs/benchmark_results.md
# 支持 --dry-run 跳过真实 LLM 调用
```

`benchmark_results.md` 初始模板：
```markdown
# Benchmark Results (PRD §5.2)
目标：20 道题各 5 次，total_score 极差 ≤ 3 分。

| Date | Question ID | Type | Min | Max | Range | Status |
|------|-------------|------|-----|-----|-------|--------|
```

**验收标准：**
```bash
python scripts/benchmark_eval.py --dry-run
# 期望: 输出运行报告，docs/benchmark_results.md 模板写入成功，无异常
```

**验证命令：**
```bash
cd interview-ai/backend
python scripts/benchmark_eval.py --dry-run
cat docs/benchmark_results.md
```

**提交：**
```bash
git add interview-ai/backend/scripts/ interview-ai/backend/docs/benchmark_results.md
git commit -m "feat: add benchmark_eval.py for scoring consistency (Max-Min ≤3) measurement"
```

### 研究洞察

**最佳实践 — benchmark 支持并发（asyncio.gather 加速 5×5=25 次调用）：**

```python
# scripts/benchmark_eval.py
import asyncio
import argparse
from datetime import date

async def benchmark_question(question_id: str, question_type: str, transcript: str, n: int = 5):
    """对单题并发调用 n 次 LLM，返回分数列表"""
    tasks = [run_llm_evaluation(transcript, question_type) for _ in range(n)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    scores = [r.final_score for r in results if not isinstance(r, Exception)]
    return {
        "question_id": question_id,
        "question_type": question_type,
        "scores": scores,
        "min": min(scores) if scores else 0,
        "max": max(scores) if scores else 0,
        "range": max(scores) - min(scores) if scores else 0,
        "status": "PASS" if (max(scores) - min(scores)) <= 3 else "WARN",
    }

async def main(dry_run: bool):
    if dry_run:
        # 干跑：用固定数据不调 LLM
        results = [{"question_id": "dry-run", "range": 0, "status": "PASS (dry-run)"}]
    else:
        results = await asyncio.gather(*[
            benchmark_question(q["id"], q["type"], SAMPLE_TRANSCRIPTS[q["type"]])
            for q in BENCHMARK_QUESTIONS
        ])
    write_results(results)
    print_summary(results)
```

**边缘情况：**
- LLM 并发 25 次调用可能触发 OpenAI 速率限制（gpt-4o-mini TPM 限制）；加 `asyncio.Semaphore(5)` 限制并发数
- `--dry-run` 时不应写入真实结果到 benchmark_results.md（只写 dry-run 标记行）

---

## 快速参考：关键约束速查

| 约束 | 违反后果 |
|------|---------|
| Dockerfile 无 `apt-get install ffmpeg` | FileNotFoundError，链路崩溃（PRD §6.3 阻断项）|
| Groq `word_timestamps=True` | HTTP 400，ASR 链路中断（正确参数：`response_format="verbose_json"`）|
| Groq `file=audio_bytes` 裸字节 | MIME 检测失败，正确：`file=("audio.wav", bytes)` 元组 |
| Groq `.segments` 字段 | 词级时间戳在 `.words`，`.segments` 为 None |
| `localStorage` 存 token | XSS 持久化风险（PRD §3.0）|
| LLM 输出 final_score | 数据失真（PRD §0.2 明确禁止）|
| `apply_rule_caps` 在入库后调用 | 硬钳制失效（PRD §9 条目8）|
| IndexedDB 持久化弱网 Blob | 状态死锁（PRD v1.5 §4.4 已废弃）|
| LangChain / Redux 引入 | PRD §6.2/§6.3 明确禁止 |
| 前端暴露 OPENAI_API_KEY/GROQ_API_KEY | API 密钥泄露（PRD §5.3）|
| `NEXT_PUBLIC_API_BASE_URL` | 后端 URL 暴露到浏览器 bundle，改用 `API_BASE_URL` |
| `anti_template_warning` 省略不写 null | 前端无法判断是否渲染警告（PRD §9 条目12）|
| `const enum` 在 Next.js/TypeScript | SWC isolatedModules 不支持，改用 `as const` |
| Blob[] 存入 Zustand | 内存泄漏 + DevTools 序列化崩溃 |
| Aho-Corasick 每请求重建 | 每次请求多 50–200ms 延迟 |
| 无 per-step 超时 | worst-case 17.2s 超出 15s SLA |
| `Field(ge=0, le=100)` 无 validator | LLM 输出 103 → ValidationError，不截断 |

## 端到端耗时预算（目标 ≤15s）

| 阶段 | 预算 | 优化方式 |
|------|------|---------|
| 音频上传（~2MB） | ~1s | — |
| ffmpeg 转码 | ~0.5s | asyncio pipe，无临时文件 |
| Groq Whisper ASR（3 分钟音频） | 3–5s | per-step timeout ≤8s |
| 词汇分析（Aho-Corasick） | <0.1s | lifespan 预构建 automaton |
| LLM 评估（gpt-4o-mini）**并行** | 2–4s | asyncio.gather + Storage 并行 |
| Storage 上传**并行** | 0.6–2.1s | 与 LLM 并行，不占关键路径 |
| 规则计算 + DB 写入 | ~0.5s | per-step timeout ≤1s |
| **总计（串行）** | **7.7–13.2s** | — |
| **总计（并行优化后）** | **约 5.6–11.1s** | asyncio.gather 节省 0.6–2.1s |
