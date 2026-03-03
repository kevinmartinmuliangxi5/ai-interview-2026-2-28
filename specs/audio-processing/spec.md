## ADDED Requirements

### Requirement: 前端 MediaRecorder 录音采集
系统 SHALL 使用 `MediaRecorder API` 采集麦克风音频。前端 MUST 执行 `isTypeSupported` 能力探测，MUST NOT 强制客户端 16kHz，由后端统一转码。录音结束后将所有 Blob Chunks 合并为单一 Blob，以 `multipart/form-data` 一次性 POST 上传（MUST NOT 使用 WebSocket 流式传输）。

#### Scenario: 录音采集与上传
- **WHEN** MediaRecorder.stop() 被调用
- **THEN** Blob Chunks 合并为单一音频文件，发起 multipart/form-data POST 至后端

#### Scenario: 浏览器格式兼容
- **WHEN** Safari 浏览器生成 audio/mp4 格式录音
- **THEN** 前端直接上传原始格式，不做客户端转码

---

### Requirement: 后端音频安全验证
后端 MUST 在进入 ASR 流程前执行以下验证，验证失败立即返回：
- `Content-Type` 须为 `audio/webm` 或 `audio/mp4`，否则 HTTP 400：`{"error_code": "ERR_INVALID_AUDIO"}`
- 文件超过 10MB 返回 HTTP 413：`{"error_code": "ERR_FILE_TOO_LARGE"}`
- 使用 `python-magic` 验证文件头魔数（防 Content-Type 伪造）

#### Scenario: Content-Type 非法拒绝
- **WHEN** 上传文件的 Content-Type 不是 audio/webm 或 audio/mp4
- **THEN** HTTP 400，error_code=ERR_INVALID_AUDIO，不启动 ffmpeg 转码

#### Scenario: 文件大小超限拒绝
- **WHEN** 上传文件大小超过 10MB
- **THEN** HTTP 413，error_code=ERR_FILE_TOO_LARGE

#### Scenario: 魔数验证防伪
- **WHEN** 请求头声称 audio/webm 但文件魔数不符
- **THEN** HTTP 400，拒绝处理

---

### Requirement: ffmpeg 统一转码管道
后端 MUST 使用 `ffmpeg-python` 将所有上传音频**无条件**转码为 `wav 16kHz mono`，命令固定为 `ffmpeg -i input -ar 16000 -ac 1 -f wav output.wav`。MUST NOT 根据原始格式添加分支逻辑。Dockerfile MUST 包含 `RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*`。

#### Scenario: webm 格式转码
- **WHEN** 接收到 audio/webm 文件
- **THEN** ffmpeg 转码为 wav 16kHz mono 后进入 ASR

#### Scenario: mp4 格式转码
- **WHEN** 接收到 audio/mp4 文件（Safari）
- **THEN** 相同 ffmpeg 命令转码为 wav 16kHz mono，无格式分支

#### Scenario: ffmpeg 缺失报错
- **WHEN** 部署环境未安装 ffmpeg 二进制
- **THEN** ffmpeg-python 抛出 FileNotFoundError，后端返回 HTTP 500，Dockerfile 缺失被识别为阻断项

---

### Requirement: Groq Whisper ASR 调用与词级时间戳
后端 MUST 调用 Groq `whisper-large-v3` API，参数 `word_timestamps=True`，返回词级时间戳存储于 `transcript_segments`（格式：`[{"text": "...", "start": 0.0, "end": 1.2}]`）。`prompt` 参数 MUST 按当前 `question_type` 过滤 `keyword_dict.json`，仅注入 Top-20 高频专有名词（MUST NOT 全量注入词典，否则触发 HTTP 400）。API 返回 502/504 或超时 MUST 最多 2 次指数退避重试，彻底失败返回 HTTP 503：`{"error_code": "ERR_ASR_TIMEOUT"}`。

#### Scenario: ASR 成功返回时间戳
- **WHEN** Groq Whisper 成功推理
- **THEN** transcript_segments 包含词级时间戳，结构为 {text, start, end} 数组

#### Scenario: prompt 参数截断注入
- **WHEN** 后端准备调用 Whisper API
- **THEN** prompt 参数为 question_type 对应的 Top-20 关键词，长度控制在 224 tokens 以内

#### Scenario: ASR 服务不可用重试
- **WHEN** Groq API 返回 502/504 或超时
- **THEN** 指数退避重试最多 2 次；2 次均失败返回 HTTP 503 + error_code=ERR_ASR_TIMEOUT

---

### Requirement: 弱网内存保留容错
系统 SHALL 在网络失败时将音频 Blob 保留在前端页面内存中，MUST NOT 写入 IndexedDB。界面显示内联提示："网络异常，请保持页面勿刷新"，提供手动"重试上传"按钮（MUST NOT 弹窗）。用户点击重试时从内存读取 Blob 重新 POST。

#### Scenario: 网络断开录音保留
- **WHEN** 上传时捕获 NetworkError 或 navigator.onLine=false
- **THEN** Blob 保留在内存，内联提示出现，不写入 IndexedDB

#### Scenario: 手动重试上传
- **WHEN** 用户点击"重试上传"且网络已恢复
- **THEN** 从内存读取 Blob，重新 POST，成功后清除内存引用
