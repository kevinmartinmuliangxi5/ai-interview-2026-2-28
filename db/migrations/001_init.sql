-- =============================================================
-- Migration: 001_init.sql
-- Project:   AI Interview Training System (面试AI)
-- PRD Ref:   v1.5 §0.1 / §0.4 / §5.3 / §6.4 / §7.1
-- Supabase:  PostgreSQL 15 + Row Level Security
-- =============================================================

-- -------------------------------------------------------------
-- Extensions
-- -------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";   -- gen_random_uuid() fallback
CREATE EXTENSION IF NOT EXISTS "pgcrypto";    -- gen_random_bytes(), provided by Supabase by default


-- =============================================================
-- SECTION 1: Custom Types
-- =============================================================

-- PRD §0.1: question_type 枚举（全文统一，禁止使用其他写法）
CREATE TYPE question_type_enum AS ENUM (
    'COMPREHENSIVE_ANALYSIS',       -- 综合分析题
    'PLANNING_ORGANIZATION',        -- 计划组织协调题
    'EMERGENCY_RESPONSE',           -- 应急应变题
    'INTERPERSONAL_RELATIONSHIPS',  -- 人际关系交往题
    'SELF_COGNITION',               -- 自我认知题
    'SCENARIO_SIMULATION'           -- 情景模拟题
);

-- PRD §0.2 / §7.1: rule_violations 强枚举（apply_rule_caps 输入源）
-- 以 TEXT[] + CHECK 实现，便于 Supabase TypeScript 类型生成
-- 合法值集合：
--   CLICHE_ANALYSIS         → analysis_ability.score ≤ 59
--   NO_SAFETY_PLAN          → organization_coordination.score ≤ 65
--   EMERGENCY_HARDLINE      → emergency_response.score ≤ 40
--   INTERPERSONAL_CONFLICT  → interpersonal_communication.score ≤ 40


-- =============================================================
-- SECTION 2: Tables
-- =============================================================

-- -------------------------------------------------------------
-- Table: questions
-- PRD §0.1 — 静态题库（只读）
-- -------------------------------------------------------------
CREATE TABLE questions (
    id                  UUID               PRIMARY KEY DEFAULT gen_random_uuid(),
    question_type       question_type_enum NOT NULL,
    content             TEXT               NOT NULL CHECK (char_length(content) > 0),
    core_keywords       TEXT[]             NOT NULL DEFAULT '{}',
    time_limit_seconds  INTEGER            NOT NULL DEFAULT 180
                                               CHECK (time_limit_seconds BETWEEN 30 AND 600),
    created_at          TIMESTAMPTZ        NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE  questions                     IS '题库：6大题型结构化面试题目，PRD §0.1（只读）';
COMMENT ON COLUMN questions.question_type       IS 'question_type_enum 枚举，全文统一，PRD §0.1';
COMMENT ON COLUMN questions.core_keywords       IS '该题必选政策词汇数组，供 Aho-Corasick required 集合使用';
COMMENT ON COLUMN questions.time_limit_seconds  IS '默认作答时限（秒），前端倒计时基准，PRD §3.2';


-- -------------------------------------------------------------
-- Table: evaluations
-- PRD §0.4 — 每道题一条评估记录（append-only）
-- -------------------------------------------------------------
CREATE TABLE evaluations (

    -- ── 标识 ─────────────────────────────────────────────────
    id                                  UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                             UUID          NOT NULL
                                            REFERENCES auth.users(id) ON DELETE CASCADE,
    question_id                         UUID
                                            REFERENCES questions(id) ON DELETE SET NULL,

    -- ── 音频管道结果 ──────────────────────────────────────────
    transcript                          TEXT          NOT NULL,
    -- JSONB 结构: [{"text": "...", "start": 0.0, "end": 1.2}, ...]
    -- 来源: Groq Whisper word_timestamps=True
    transcript_segments                 JSONB         NOT NULL DEFAULT '[]',
    audio_duration_seconds              NUMERIC(6, 2) NOT NULL CHECK (audio_duration_seconds > 0),
    -- Supabase Storage 路径，音频 TTL 24h 由 Lifecycle Rule 自动删除
    audio_storage_path                  TEXT,

    -- ── 维度 1：综合分析（LLM 生成）────────────────────────────
    analysis_ability_score              NUMERIC(5, 2) NOT NULL
                                            CHECK (analysis_ability_score BETWEEN 0 AND 100),
    analysis_ability_reasoning          TEXT          NOT NULL,

    -- ── 维度 2：计划组织协调（LLM 生成）──────────────────────────
    organization_coordination_score     NUMERIC(5, 2) NOT NULL
                                            CHECK (organization_coordination_score BETWEEN 0 AND 100),
    organization_coordination_reasoning TEXT          NOT NULL,

    -- ── 维度 3：应急应变（LLM 生成）─────────────────────────────
    emergency_response_score            NUMERIC(5, 2) NOT NULL
                                            CHECK (emergency_response_score BETWEEN 0 AND 100),
    emergency_response_reasoning        TEXT          NOT NULL,

    -- ── 维度 4：人际交往（LLM 生成）─────────────────────────────
    interpersonal_communication_score   NUMERIC(5, 2) NOT NULL
                                            CHECK (interpersonal_communication_score BETWEEN 0 AND 100),
    interpersonal_communication_reasoning TEXT        NOT NULL,

    -- ── 维度 5：言语表达（LLM 生成）─────────────────────────────
    language_expression_score           NUMERIC(5, 2) NOT NULL
                                            CHECK (language_expression_score BETWEEN 0 AND 100),
    language_expression_reasoning       TEXT          NOT NULL,

    -- ── 维度 6：求职动机（LLM 生成）─────────────────────────────
    job_matching_score                  NUMERIC(5, 2) NOT NULL
                                            CHECK (job_matching_score BETWEEN 0 AND 100),
    job_matching_reasoning              TEXT          NOT NULL,

    -- ── 维度 7：副语言流畅度（规则计算，非 LLM）─────────────────
    -- calculate_fluency_score() 输出，保底 50 分，PRD §7.1
    paralinguistic_fluency_score        NUMERIC(5, 2) NOT NULL
                                            CHECK (paralinguistic_fluency_score BETWEEN 50 AND 100),

    -- ── P1：副语言原始指标（供趋势分析，PRD §2.2）──────────────
    pause_count                         INTEGER       CHECK (pause_count >= 0),
    speech_rate_cpm                     NUMERIC(6, 2) CHECK (speech_rate_cpm >= 0),
    filler_density_per_min              NUMERIC(5, 2) CHECK (filler_density_per_min >= 0),

    -- ── 结构化分析（LLM 生成，JSONB）───────────────────────────
    -- 必含键: is_complete (bool), missing_elements (array), present_elements (array)
    structural_framework_check          JSONB         NOT NULL DEFAULT '{}'
                                            CHECK (
                                                structural_framework_check ? 'is_complete' AND
                                                structural_framework_check ? 'missing_elements' AND
                                                structural_framework_check ? 'present_elements'
                                            ),
    improvement_suggestions             JSONB         NOT NULL DEFAULT '[]',
    model_ideal_answer                  TEXT          NOT NULL,

    -- ── 规则红线（LLM 标注 + 确定性检测双保险）─────────────────
    -- apply_rule_caps() 的输入；未知值由 Pydantic filter_unknown_violations 丢弃
    rule_violations                     TEXT[]        NOT NULL DEFAULT '{}'
                                            CHECK (
                                                rule_violations <@ ARRAY[
                                                    'CLICHE_ANALYSIS',
                                                    'NO_SAFETY_PLAN',
                                                    'EMERGENCY_HARDLINE',
                                                    'INTERPERSONAL_CONFLICT'
                                                ]::TEXT[]
                                            ),

    -- ── P1：反模板化警告（正则黑名单检测）──────────────────────
    -- NULL 表示未触发或 P1 未启用；前端据此决定是否渲染警告横幅
    anti_template_warning               TEXT,

    -- ── 加权总分（后端计算，非 LLM）─────────────────────────────
    -- final_score = round(Σ score_i × weight_i, 2)，PRD §0.3
    final_score                         NUMERIC(5, 2) NOT NULL
                                            CHECK (final_score BETWEEN 0 AND 100),

    -- ── 元数据 ───────────────────────────────────────────────
    created_at                          TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE  evaluations                               IS '评估记录：每道题一条，append-only，PRD §0.4';
COMMENT ON COLUMN evaluations.transcript                    IS '全文转写文本（Whisper 输出拼接）';
COMMENT ON COLUMN evaluations.transcript_segments           IS 'Whisper 词级时间戳数组：[{text,start,end}]';
COMMENT ON COLUMN evaluations.audio_storage_path            IS 'Supabase Storage 路径；Lifecycle Rule TTL=24h 自动删除';
COMMENT ON COLUMN evaluations.paralinguistic_fluency_score  IS '副语言流畅度维度7，规则计算非LLM，保底50分';
COMMENT ON COLUMN evaluations.pause_count                   IS 'P1：停顿次数（≥3.0s gap），用于趋势分析';
COMMENT ON COLUMN evaluations.speech_rate_cpm               IS 'P1：语速（字/分钟），用于趋势分析';
COMMENT ON COLUMN evaluations.filler_density_per_min        IS 'P1：语气词密度（次/分钟），用于趋势分析';
COMMENT ON COLUMN evaluations.structural_framework_check    IS 'LLM输出：{is_complete,missing_elements,present_elements}';
COMMENT ON COLUMN evaluations.rule_violations               IS 'LLM标注规则红线枚举数组，apply_rule_caps()输入';
COMMENT ON COLUMN evaluations.anti_template_warning         IS 'P1正则黑名单检测结果；NULL=未触发，前端据此渲染警告横幅';
COMMENT ON COLUMN evaluations.final_score                   IS '加权总分，后端硬编码计算，禁止LLM生成';


-- =============================================================
-- SECTION 3: Indexes
-- =============================================================

-- 主访问路径：用户查询自己的历史记录（Dashboard + RLS 过滤）
CREATE INDEX idx_evaluations_user_id
    ON evaluations(user_id);

-- 复合索引：按用户 + 时间倒序（历史列表分页）
CREATE INDEX idx_evaluations_user_created
    ON evaluations(user_id, created_at DESC);

-- 题目维度分析（按题目聚合成绩趋势）
CREATE INDEX idx_evaluations_question_id
    ON evaluations(question_id);

-- 题库按题型筛选（随机抽题调度）
CREATE INDEX idx_questions_type
    ON questions(question_type);

-- JSONB 字段：structural_framework_check.is_complete 快速查询
-- （可选：如需统计"框架完整率"）
CREATE INDEX idx_evaluations_framework_complete
    ON evaluations USING gin (structural_framework_check jsonb_path_ops);


-- =============================================================
-- SECTION 4: Row Level Security
-- =============================================================

ALTER TABLE questions   ENABLE ROW LEVEL SECURITY;
ALTER TABLE evaluations ENABLE ROW LEVEL SECURITY;

-- ── questions：所有已认证用户可读（只读题库）────────────────
CREATE POLICY "questions_select_authenticated"
    ON questions
    FOR SELECT
    TO authenticated
    USING (true);

-- ── evaluations：用户只能读取自己的记录──────────────────────
CREATE POLICY "evaluations_select_own"
    ON evaluations
    FOR SELECT
    TO authenticated
    USING (auth.uid() = user_id);

-- ── evaluations：用户只能插入自己的记录──────────────────────
CREATE POLICY "evaluations_insert_own"
    ON evaluations
    FOR INSERT
    TO authenticated
    WITH CHECK (auth.uid() = user_id);

-- 注意：不设置 UPDATE / DELETE 策略
-- evaluations 表为 append-only，业务层不允许修改或删除评估记录


-- =============================================================
-- SECTION 5: Supabase Storage（SQL 无法直接配置，此处记录预期配置）
-- =============================================================
-- 请在 Supabase Dashboard → Storage 执行以下操作（或通过 CLI）：
--
--   1. 创建 Bucket: 'interview-audio'
--      - 访问控制: Private（仅后端 Service Role 可写）
--
--   2. 配置 Lifecycle Rule:
--      - Bucket: interview-audio
--      - Condition: 对象存在超过 86400 秒（24小时）
--      - Action: 永久删除
--      - 目的: 满足 PRD §5.3 录音 TTL ≤ 24h 数据安全约束
--
--   3. Storage RLS Policy（如需，限制后端 Service Role 写入）:
--      - INSERT: 仅允许 service_role
--      - SELECT: 仅允许匹配 user_id 路径的 authenticated 用户
-- =============================================================
