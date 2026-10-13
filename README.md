# Podcast Studio

Podcast Studio 是一个本地运行的长音频处理工作台，支持：

- 音频上传与批量任务处理
- ASR 转录（默认 faster-whisper）
- 说话人分离 / Speaker diarization
- 语音转文本结果的时间轴整理
- 可选 LLM 翻译（DeepSeek / Qwen 等）
- 输出 Markdown / TXT / SRT / JSON
- 前端 Web 界面，支持任务状态、播放、查看和导出

它适合 podcast、会议纪要、音频内容转文字、长录音整理等场景，且尽量保持本地部署、低耦合和可扩展。

## 功能特性

- 本地音频处理，不强依赖 Docker / Redis / PostgreSQL
- 支持批量上传和任务列表管理
- 任务状态追踪：queued / running / done / failed / cancelled
- ASR 与 diarization 结果按时间轴展示
- 支持播放音频并精准定位到对应语句
- 支持文本和翻译结果导出
- 可扩展多种 ASR / Speaker / LLM provider

## 项目结构

```text
.
├── backend/
│   ├── app/
│   ├── requirements.txt
│   └── requirements-optional.txt
├── frontend/
│   ├── src/
│   └── package.json
├── data/
├── .env.example
├── .gitignore
├── LICENSE
├── README.md
├── run.sh
└── scripts/
```

## 技术栈

- Backend: FastAPI + SQLite + Python Worker
- Frontend: Vue 3 + Vite
- ASR: faster-whisper（默认），FunASR 可选
- Speaker: pyannote（默认）
- LLM: OpenAI-compatible providers（Qwen / DeepSeek / 自定义）
- Audio: FFmpeg

## 运行环境要求

- Python 3.10+（推荐 3.11）
- Node.js 18+（仅前端构建/开发需要）
- FFmpeg
- Conda / venv 可选

Ubuntu 20.04 示例：

```bash
sudo apt update
sudo apt install -y ffmpeg git curl build-essential python3.10 python3.10-venv python3.10-dev
```

## 快速开始

### 1. 克隆项目

```bash
git clone <your-repo-url>
cd podcast_studio_v1
```

### 2. 配置环境

```bash
cp .env.example .env
```

可编辑的核心配置如下：

```env
HOST=0.0.0.0
PORT=8765
DATA_DIR=./data

ASR_PROVIDER=faster_whisper
ASR_MODEL=large-v3-turbo
DIARIZATION_PROVIDER=none
LLM_ENABLED=false
```

### 3. 创建 Python 环境并安装依赖

推荐使用 Conda：

```bash
source ~/anaconda3/etc/profile.d/conda.sh
conda create -n podenv311 python=3.11 -y
conda activate podenv311
python -m pip install -U pip wheel setuptools
pip install -r backend/requirements.txt
```

### 4. 启动应用

```bash
source ~/anaconda3/etc/profile.d/conda.sh
conda activate podenv311
./run.sh
```

访问：

```text
http://127.0.0.1:8765
```

如果需要局域网访问，可将 `.env` 配置为：

```env
HOST=0.0.0.0
PORT=8765
```

## 前端构建

在项目根目录执行：

```bash
cd frontend
npm install
npm run build
```

随后启动后端即可访问静态前端页面。

## 输出结果

每个任务会生成以下文件：

```text
data/jobs/<job_id>/
  source/
  audio/
  asr/transcript.json
  diarization/speakers.json
  merged/timeline.json
  llm/translated.json
  output/<name>.md
  output/<name>.txt
  output/<name>.srt
  output/<name>.json
```

## 可选配置

### pyannote（说话人分离）

```env
DIARIZATION_PROVIDER=pyannote
HF_TOKEN=hf_xxx
DIARIZATION_MODEL=pyannote/speaker-diarization-community-1
```

### DeepSeek / Qwen LLM

```env
LLM_ENABLED=true
LLM_PROVIDER=deepseek
LLM_BASE_URL=https://api.deepseek.com
LLM_API_KEY=your_key
LLM_MODEL=deepseek-chat
```

或：

```env
LLM_ENABLED=true
LLM_PROVIDER=qwen
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_API_KEY=your_key
LLM_MODEL=qwen-plus
```

## API

- `POST /api/jobs` 上传文件并创建任务
- `GET /api/jobs` 获取任务列表
- `GET /api/jobs/{id}` 获取任务详情
- `POST /api/jobs/{id}/retry` 重试失败任务
- `POST /api/jobs/{id}/cancel` 取消任务
- `GET /api/jobs/{id}/timeline` 获取时间轴 JSON
- `GET /api/jobs/{id}/audio` 获取音频
- `GET /api/jobs/{id}/files/{name}` 下载输出文件
- `POST /api/jobs/{id}/export-json-global` 导出最终 JSON 到全局目录
- `GET /api/config` 获取运行配置

## 开发建议

后续可以继续扩展：

1. Speaker 人物名编辑器
2. ASR/A/B 对照测试
3. 单击时间轴跳转播放
4. 批量导入目录
5. 低置信度片段质量告警
6. RSS / Apple Podcasts 下载器集成

## 贡献

欢迎提交 issue、PR 和改进建议。请保持代码和文档清晰，尽量保持本地化部署优先。

## 许可证

本项目采用 MIT License。详细内容见 [LICENSE](LICENSE)。

## 免责声明

本项目仅用于研究、开发与本地音频处理场景。使用前请遵守相关模型/服务提供商的许可协议与使用条款。
