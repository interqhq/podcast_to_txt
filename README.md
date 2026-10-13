# Podcast Studio V1

本地 Podcast 长音频处理工作站：30 分钟级音频、批量、断点续跑、本地 ASR/说话人识别，可选 Qwen/DeepSeek 云端翻译与剧本整理。

## 架构

- FastAPI + SQLite + 本地 Worker
- Vue 3 + Vite 前端
- ASR：faster-whisper 默认，FunASR 可选
- Speaker：pyannote 默认，FunASR CAM++ 可扩展
- LLM：OpenAI-compatible，Qwen / DeepSeek 可选
- FFmpeg 音频预处理
- 中间结果 JSON 持久化，步骤完成后不重复计算
- 输出 Markdown / TXT / SRT / JSON
- 不需要 Docker / Redis / PostgreSQL

## Ubuntu 20.04 推荐环境

Ubuntu 20.04 自带 Python 3.8，而当前 faster-whisper 要求 Python >= 3.9，所以建议使用 Python 3.10 独立环境，不升级系统。

### 1. 安装系统依赖

```bash
sudo apt update
sudo apt install -y ffmpeg git curl build-essential python3.10 python3.10-venv python3.10-dev
```

如果你的 Ubuntu 20.04 仓库没有 python3.10，请使用 deadsnakes PPA（不会执行 dist-upgrade）：

```bash
sudo apt install -y software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.10 python3.10-venv python3.10-dev
```

### 2. 创建环境（Anaconda / Conda）

如果你本来就是用 Anaconda，优先在 `podenv311` 中安装依赖，而不是项目内的 `.venv`：

```bash
cd podcast_studio_v1
source ~/anaconda3/etc/profile.d/conda.sh
conda activate podenv311
python -m pip install -U pip wheel setuptools
pip install -r backend/requirements.txt
```

如果你还没有这个环境：

```bash
source ~/anaconda3/etc/profile.d/conda.sh
conda create -n podenv311 python=3.11 -y
conda activate podenv311
python -m pip install -U pip wheel setuptools
pip install -r backend/requirements.txt
```

### 3. 配置

```bash
cp .env.example .env
```

默认：

- ASR=faster_whisper
- model=large-v3-turbo
- device=auto
- diarization=none（先跑通 ASR）
- LLM=disabled

第一次启动后模型会按需下载并缓存。

### 4. 启动

```bash
source ~/anaconda3/etc/profile.d/conda.sh
conda activate podenv311
./run.sh
```

如果你走的是项目脚本，`run.sh` 会自动切到 `podenv311` 环境。

打开 http://127.0.0.1:8765

### 5. 推荐第一轮验证

先在 `.env`：

```env
ASR_PROVIDER=faster_whisper
ASR_MODEL=large-v3-turbo
DIARIZATION_PROVIDER=none
LLM_ENABLED=false
```

上传一个 5~10 分钟样本。确认 ASR 正常后再开启 pyannote。

前端任务完成后，可直接点击“下载 JSON 到本机”按钮，浏览器会弹出保存文件对话框，选择本地任意目录保存最终 JSON 文件。若浏览器不支持文件保存器，则自动回退为标准下载。

## NVIDIA

当前 faster-whisper 新版 GPU 路径需要 CUDA 12 + cuDNN 9。若机器是较旧的 CUDA 11 / 旧 NVIDIA 卡，不要盲目升级系统；可以先用 CPU 跑通 V1，再根据 `nvidia-smi` 单独选择兼容的 CTranslate2 版本。

旧 CUDA 11 兼容方式示例：

```bash
pip install --force-reinstall 'ctranslate2==3.24.0'
```

具体 CUDA/cuDNN/驱动组合以你的 `nvidia-smi` 为准。

## pyannote

pyannote 的预训练模型通常需要 Hugging Face 账号/token 和相应模型许可。配置：

```env
DIARIZATION_PROVIDER=pyannote
HF_TOKEN=hf_xxx
DIARIZATION_MODEL=pyannote/speaker-diarization-community-1
```

如果不想现在配置，保持 `none` 即可。

## FunASR

FunASR 是可选后端。当前官方安装方式是先安装匹配的 PyTorch/torchaudio，再安装 `funasr`。建议单独验证 FunASR 后再打开：

```bash
pip install funasr
```

然后：

```env
ASR_PROVIDER=funasr
ASR_MODEL=FunAudioLLM/Fun-ASR-Nano-2512
```

不同 FunASR 模型的依赖和输出契约不同，因此 V1 将 FunASR 放在独立 provider，不让它污染主 pipeline。

## 云端 LLM

不开启也不影响本地 ASR/说话人结果。开启后只发送 transcript 文本，不上传原始音频。

### DeepSeek

```env
LLM_ENABLED=true
LLM_PROVIDER=deepseek
LLM_BASE_URL=https://api.deepseek.com
LLM_API_KEY=你的key
LLM_MODEL=deepseek-chat
```

### Qwen / DashScope

```env
LLM_ENABLED=true
LLM_PROVIDER=qwen
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_API_KEY=你的key
LLM_MODEL=qwen-plus
```

## 输出目录

每个任务：

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

## API

- `POST /api/jobs` 上传并创建任务
- `GET /api/jobs` 任务列表
- `GET /api/jobs/{id}` 任务详情
- `POST /api/jobs/{id}/retry` 从失败步骤继续
- `POST /api/jobs/{id}/cancel` 取消
- `GET /api/jobs/{id}/timeline` 时间轴
- `GET /api/jobs/{id}/audio` 音频播放
- `GET /api/jobs/{id}/files/{name}` 下载结果
- `POST /api/jobs/{id}/export-json-global` 复制最终 JSON 到全局目录
- `GET /api/config` 当前运行配置（隐藏 API key）

## V1 后续建议

1. 加 Speaker 人物名编辑器
2. 加 ASR/FunASR A/B 测试
3. 加音频时间轴点击跳转
4. 加全文搜索
5. 加批量导入目录
6. 加质量告警和低置信度片段
7. 加 RSS/Apple Podcasts 下载器，但保持下载器与 pipeline 解耦

### 可选组件安装

pyannote：

```bash
source .venv/bin/activate
pip install -r backend/requirements-optional.txt
```

如果你只需要 FunASR，也可以：

```bash
pip install 'funasr>=1.4,<2'
```

注意：FunASR 当前官方文档要求先安装与你的 Python/CPU/GPU 匹配的 PyTorch 与 torchaudio，再安装 FunASR；不要为了 FunASR 随意覆盖已有 PyTorch 环境。citeturn0search0turn0search3

### 前端构建

服务器如果已经有 Node.js/npm：

```bash
./scripts/build_frontend.sh
./run.sh
```

如果暂时不构建前端，后端 API 仍然可用，访问 `/docs` 查看 Swagger。

<!-- conda install -y pytorch torchvision torchaudio pytorch-cuda=12.1 -c pytorch -c nvidia
pip install pyannote.audio -->
<!-- pip install --no-cache-dir torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu121 -->