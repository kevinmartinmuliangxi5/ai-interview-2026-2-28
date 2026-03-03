## ADDED Requirements

### Requirement: Pydantic 强约束 LLM 结构化输出
后端 MUST 使用 `openai-python >= 1.0` SDK 的 `beta.chat.completions.parse()` 方法，以 `LLMEvaluationOutput` Pydantic BaseModel 作为 `response_format`。LLM 仅输出 6 维度评分（0–100 百分制）、`structural_framework_check`、`improvement_suggestions`、`model_ideal_answer`、`rule_violations`。LLM MUST NOT 输出 `final_score`、`paralinguistic_fluency_score`、`max_score`、`weight`。Pydantic 校验失败 MUST 触发最多 2 次重试，彻底失败返回 HTTP 503：`{"error_code": "ERR_LLM_PARSE_FAILED"}`。

#### Scenario: LLM 输出通过 Pydantic 校验
- **WHEN** LLM 推理返回响应
- **THEN** 通过 LLMEvaluationOutput 校验，6 个维度各含 score（0–100）和 reasoning 字段

#### Scenario: LLM 输出校验失败重试
- **WHEN** LLM 输出不符合 Pydantic 模型（字段缺失或类型错误）
- **THEN** 最多重试 2 次；2 次均失败返回 HTTP 503 + error_code=ERR_LLM_PARSE_FAILED

#### Scenario: 后端计算字段不由 LLM 生成
- **WHEN** 后端调用 LLM
- **THEN** 模型响应中不存在 final_score、paralinguistic_fluency_score 字段，这两个字段由后端独立计算追加

---

### Requirement: 动态 Prompt 工厂（按 question_type 路由）
后端 MUST 实现 Prompt Factory，读取 `question_type` 字段路由至对应考官评分清单。MUST NOT 使用通用一刀切 Prompt。支持的路由：
- `PLANNING_ORGANIZATION` → 注入"定、摸、筹、控、结"五步闭环核对清单
- `EMERGENCY_RESPONSE` → 注入"稳、明、调、解、报、总"六字诀核对清单
- `COMPREHENSIVE_ANALYSIS` → 注入"点、析、对、升"四段论核对清单
- `INTERPERSONAL_RELATIONSHIPS` → 注入"尊重服从、委婉沟通"原则核查

#### Scenario: PLANNING_ORGANIZATION 注入五步法
- **WHEN** 评估请求的 question_type = PLANNING_ORGANIZATION
- **THEN** System Prompt 包含"定、摸、筹、控、结"五步核对清单，structural_framework_check.missing_elements 标注遗漏步骤

#### Scenario: EMERGENCY_RESPONSE 注入六字诀
- **WHEN** 评估请求的 question_type = EMERGENCY_RESPONSE
- **THEN** System Prompt 包含"稳、明、调、解、报、总"六字诀核对清单

---

### Requirement: apply_rule_caps 后端硬钳制（双保险）
后端 MUST 在 LLM 输出经 Pydantic 解析后、写入数据库前，调用 `apply_rule_caps(llm_output, transcript, question_type)` 执行分数上限钳制。机制为双保险：LLM 的 `rule_violations` 枚举标注 OR 确定性关键词检测，任一命中即触发 RULE_CAPS 映射表中的上限。未知 rule_violation 值 MUST 自动丢弃并写入 warning 日志。

RULE_CAPS 映射：
- `CLICHE_ANALYSIS` → `analysis_ability.score` ≤ 59
- `NO_SAFETY_PLAN` → `organization_coordination.score` ≤ 65
- `EMERGENCY_HARDLINE` → `emergency_response.score` ≤ 40
- `INTERPERSONAL_CONFLICT` → `interpersonal_communication.score` ≤ 40

#### Scenario: LLM 标注规则红线触发钳制
- **WHEN** LLM rule_violations 包含 EMERGENCY_HARDLINE
- **THEN** apply_rule_caps 将 emergency_response.score 压制为 ≤ 40，即使 LLM 原始评分更高

#### Scenario: 确定性检测兜底（PLANNING_ORGANIZATION 缺安全预案）
- **WHEN** question_type=PLANNING_ORGANIZATION 且转写文本中不含"安全预案/经费预算/经费保障/安全保障"任一词
- **THEN** 确定性检测命中 NO_SAFETY_PLAN，organization_coordination.score ≤ 65，无论 LLM 是否标注

#### Scenario: 未知 rule_violation 值过滤
- **WHEN** LLM 返回 rule_violations 中包含 "EMERGENCY-HARDLINE"（连字符变体）
- **THEN** 该值被丢弃，写入 warning 日志，不触发硬钳制，不抛出异常

---

### Requirement: 副语言流畅度规则计算（维度 7）
后端 MUST 使用 `calculate_fluency_score(segments)` 纯规则函数基于 Whisper 词级时间戳计算维度 7，MUST NOT 调用 LLM。基础分 80，最低保底 50。扣分规则：
- 停顿 ≥ 3.0 秒（相邻 segment gap）：−2 分/次，上限 −10
- 语速 < 150 或 > 280 字/分钟：−5 分
- 语气词（"那个"/"嗯"/"就是说"/"然后就是"）密度 > 5 次/分钟：−3 分

#### Scenario: 正常流畅答题满分
- **WHEN** 无停顿 ≥3s、语速 200 字/分钟、语气词密度 2 次/分钟
- **THEN** calculate_fluency_score 返回 80.0

#### Scenario: 多次停顿扣分封顶
- **WHEN** 检测到 8 次停顿 ≥ 3.0 秒
- **THEN** 停顿扣分上限 10 分，基础分 80 − 10 = 70

#### Scenario: 保底分数限制
- **WHEN** 各项扣分之和超过 30
- **THEN** 最终得分为 50（max(50, 80−sum)）

---

### Requirement: 加权总分聚合
后端 MUST 按固定权重计算 `final_score`，MUST NOT 允许 LLM 参与计算：
`final_score = round(Σ(dim_score × weight), 2)`，权重：analysis_ability×0.20 + organization_coordination×0.15 + emergency_response×0.15 + interpersonal_communication×0.15 + language_expression×0.15 + job_matching×0.10 + paralinguistic_fluency_score×0.10。

#### Scenario: 权重聚合正确
- **WHEN** 6 维度 LLM 评分和 paralinguistic_fluency_score 均已计算
- **THEN** final_score = round(加权求和, 2)，结果与 PRD §0.3 公式一致

#### Scenario: apply_rule_caps 先于 final_score 计算
- **WHEN** LLM 输出经 Pydantic 解析
- **THEN** 先调用 apply_rule_caps 修正评分，再聚合 final_score，确保钳制后分数用于最终计算
