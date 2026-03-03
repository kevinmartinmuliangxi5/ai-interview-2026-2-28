## ADDED Requirements

### Requirement: Aho-Corasick 政策词汇命中率计算（P0）
后端 MUST 使用 Aho-Corasick 算法对转写文本扫描 `keyword_dict.json` 中的政策词汇，计算命中率：`policy_coverage = matched_count / required_count`（required 集合由 `question_type` 决定）。MUST 处理除零边界：`required_count == 0` 时 `policy_coverage = null`，不注入 LLM Prompt，API 响应显示"该题型无必选政策词"。`required_count > 0` 时将命中率注入 LLM Prompt 上下文。

#### Scenario: 政策词汇命中率计算
- **WHEN** 转写文本包含 3/5 个 required_keywords
- **THEN** policy_coverage = 0.60，注入 LLM Prompt 作为评分上下文

#### Scenario: required_count 为零除法防护
- **WHEN** 当前 question_type 对应的 required_keywords 集合为空
- **THEN** policy_coverage = null，不注入 Prompt，前端展示"该题型无必选政策词"

#### Scenario: keyword_dict.json 词典加载
- **WHEN** 后端初始化
- **THEN** keyword_dict.json 从文件加载，包含政策词汇（如"两个确立"、"法治中国建设"、"接诉即办"等），按 question_type 分组索引

---

### Requirement: Aho-Corasick 套话黑名单命中数统计（P0）
后端 MUST 使用 Aho-Corasick 算法扫描套话黑名单，统计命中数量并注入 LLM Prompt 作为上下文提示（不直接触发规则钳制，作为 LLM 评分参考）。

#### Scenario: 套话命中注入 Prompt
- **WHEN** Aho-Corasick 检测到 5 次套话黑名单命中
- **THEN** Prompt 上下文包含套话命中数量，引导 LLM 在 rule_violations 中标记 CLICHE_ANALYSIS（如适用）

---

### Requirement: Whisper Prompt Top-20 专有名词截断注入
后端 MUST 在调用 Groq Whisper API 时，从 `keyword_dict.json` 按当前 `question_type` 过滤后取高频 Top-20 专有名词（按语料频次倒序），注入 `prompt` 参数，总长度约束在 224 tokens 以内。MUST NOT 全量注入整个词典，否则触发 Groq HTTP 400。

#### Scenario: Top-20 截断注入
- **WHEN** 后端准备 Whisper API 请求
- **THEN** prompt 参数包含 ≤20 个政策专有名词，token 数量 ≤224

#### Scenario: 全量注入拒绝
- **WHEN** keyword_dict.json 包含 200+ 词条
- **THEN** 系统仅取 Top-20 注入，不发送全量词典，Groq API 正常返回 200

---

### Requirement: 正则黑名单反模板化检测（P1 可选增强）
后端 SHALL 对转写文本执行正则匹配，黑名单词组硬编码于 `cliche_patterns.json`。命中条目数 ≥ 3 时写入 `anti_template_warning` 字段（格式："检测到高频套话模式，命中 X 条黑名单词组，建议结合具体情境重组答案结构"）。未触发时 MUST 显式写入 `null`，MUST NOT 省略字段。MUST NOT 引入 `jieba`、外部停用词表或语料库文件。

#### Scenario: 正则命中达阈值触发警告
- **WHEN** 转写文本命中 cliche_patterns.json 中 ≥3 条正则词组
- **THEN** anti_template_warning = "检测到高频套话模式，命中 X 条黑名单词组，建议结合具体情境重组答案结构"

#### Scenario: 命中不足阈值不触发
- **WHEN** 转写文本命中 1–2 条正则词组
- **THEN** anti_template_warning = null（显式写入，不省略字段）

#### Scenario: 无外部依赖实现
- **WHEN** P1 正则检测启用
- **THEN** 实现代码中不导入 jieba、sklearn、或任何 NLP 语料库，仅使用 Python 标准库 re 模块

---

### Requirement: cliche_patterns.json 词典管理
项目 SHALL 维护 `cliche_patterns.json` 文件，存储套话正则黑名单条目（每条为 Python re 兼容的正则字符串）。初始版本 MUST 包含不少于 10 条种子条目，由产品方提供并可持续维护扩充。

#### Scenario: cliche_patterns.json 格式有效
- **WHEN** 后端加载 cliche_patterns.json
- **THEN** 文件为合法 JSON 数组，每个元素为可编译的 Python 正则字符串，无加载错误
