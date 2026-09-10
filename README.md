# 电商数据分析 AI 应用

基于 **LangGraph + LangChain + RAG + FastAPI** 的企业级电商数据分析应用。核心能力：

- **对话式数据分析助手（NL2SQL）**：用中文提问 → 自动生成 SQL 取数 → 出图 → 中文解读。
- **RAG 知识库问答**：上传商品手册 / 售后政策等文档，问答带引用来源。
- **用户自助上传数据**：上传 CSV/Excel 立即可对话查询；上传文档立即进 RAG。
- **异常预警 Agent**：扫描核心指标，发现异常自动归因。

默认用 **Mock 数据**（本地 SQLite）开箱即跑，无需真实数据。大模型默认接 **DeepSeek**（OpenAI 兼容）；未填 API Key 时自动回退 MockLLM，界面与流程仍可演示。

> **关于数据**：服务启动后数据库为空，需在界面「数据管理」上传 CSV/Excel 即自动建表，之后即可对话查询；或实现 `data/warehouse_source.py` 接真实数仓。

## 环境要求
- Python 3.12（已验证 3.12.10）
- Windows/macOS/Linux

## 快速开始

### 1. 创建虚拟环境并安装依赖
```bash
# 在项目根目录下执行
py -3.12 -m ensurepip --upgrade
py -3.12 -m venv .venv

# Windows
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m pip install -e .

# macOS / Linux
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e .
```
> 如需中文高质量向量（会额外安装 torch，约 1.5GB）：激活虚拟环境后执行 `pip install -e ".[bge]"`，并在 `.env` 设 `EMBEDDING_PROVIDER=local_bge`。

### 2. 配置
复制 `.env.example` 为 `.env`，填入你的 DeepSeek API Key：
```
DEEPSEEK_API_KEY=sk-xxxxxxxx
```
不填也能跑（MockLLM 回退）。

> 公网 / 企业部署建议：在 `.env` 设置 `API_KEY=你的密钥`（启用 `X-API-Key` 头校验）与 `CORS_ORIGINS=https://你的前端域名`，避免默认的全开 CORS 与免鉴权。

### 3. 启动服务
```bash
# Windows
.venv\Scripts\python.exe run.py

# macOS / Linux（激活虚拟环境后）
python run.py
```
浏览器打开 http://127.0.0.1:8000

## 用 PyCharm 打开运行
1. `File → Open` 选择项目根目录。
2. PyCharm 通常会自动识别 `.venv`；若没有，`Settings → Project → Python Interpreter` 选择 `.venv\Scripts\python.exe`（macOS / Linux 为 `.venv/bin/python`）。
3. 右键 `run.py` → `Run 'run'`；或在终端执行上方命令。
4. 在 `.env` 填 `DEEPSEEK_API_KEY` 切换真实模型。

## 目录结构
```
src/ecommerce_ai/
├── core/        配置、日志、数据模型
├── llm/         DeepSeek / MockLLM 工厂
├── data/        数据源适配器、上传落库
├── rag/         文档加载、嵌入、检索、索引
├── tools/       LangChain Tool 封装
├── agents/      LangGraph 编排与各节点
└── api/         FastAPI 路由 + 前端
```

## 接真实数据
- 结构化数据：实现 `data/warehouse_source.py`，在 `.env` 设 `DATA_SOURCE=warehouse`，业务代码零改动。
- 或直接在界面"数据管理"上传 CSV/Excel。
- 文档：在界面或 `POST /api/v1/knowledge/upload` 上传，自动进 RAG。

## 主要 API
| 方法 | 路径 | 说明 |
|---|---|---|
| POST | /api/v1/chat | 对话（流式 SSE） |
| POST | /api/v1/query | 单轮分析，返回 SQL/结果/图表/解读 |
| GET  | /api/v1/knowledge/search | RAG 检索 |
| POST | /api/v1/data/upload | 上传结构化数据 |
| POST | /api/v1/knowledge/upload | 上传文档 |
| GET  | /api/v1/datasets | 数据集列表 |
| POST | /api/v1/alerts/scan | 触发预警扫描 |
| GET  | /api/v1/health | 健康检查 |
