# 混改潜力评分系统 V1 原型

这是一个先跑通界面、后端数据库和核心跳转的演示原型。当前支持两种后端数据库：

- 默认：读取本地 JSON 文件数据库。
- 云端：配置 `MONGODB_URI` 后，读取 MongoDB 云端数据库，不再依赖本地 JSON 作为运行数据源。

后端数据库在：

```text
backend/database/
  companies.json    公司基础信息
  financials.json   财务指标
  equity.json       股权与信用数据
  policies.json     属地适配、政策信号、加减分原因
  policy_documents.json  Markdown 政策/样本研究文档
  source_catalog.json    已导入源文件目录
  raw/*.jsonl            Excel/CSV 原始明细表
```

数据库访问层在 `backend/app/db.py`，提供本地 JSON 与 MongoDB 两套实现，负责集合的新增、查询、更新、删除。业务计算层在 `backend/app/services.py`，负责按公司代码关联各类数据并计算模块分、总分和排名。

## 使用云端 MongoDB

安装 Python 依赖：

```powershell
pip install -r requirements.txt
```

在 PowerShell 中设置 MongoDB 连接信息：

```powershell
$env:MONGODB_URI="mongodb+srv://<username>:<password>@<cluster-url>/?retryWrites=true&w=majority"
$env:MONGODB_DATABASE="mixed_reform"
```

把当前本地数据库迁移到 MongoDB：

```powershell
python -m backend.app.migrate_to_mongo
```

默认会迁移这些可查询集合：

```text
companies
financials
equity
policies
policy_documents
source_catalog
```

如果 MongoDB 空间足够，也要迁移 `backend/database/raw/*.jsonl` 原始明细表，可以额外设置：

```powershell
$env:MONGODB_MIGRATE_RAW="1"
python -m backend.app.migrate_to_mongo
```

注意：raw 原始明细约 532MB，不建议放免费小容量数据库。更合理的长期方案是：MongoDB 存可查询结构化集合，OSS/S3/R2 存原始 Excel、CSV、JSONL 文件。

## 导入数据

把 `.xlsx`、`.csv`、`.md` 原始数据文件放在 `backend/` 目录后，运行：

```powershell
python -m backend.app.import_sources
```

导入器会：

- 将所有 Markdown 政策文件写入 `policy_documents.json`。
- 将所有 Excel/CSV 明细表流式写入 `backend/database/raw/*.jsonl`。
- 生成 `source_catalog.json`，记录每个源文件、sheet、列名、行数和 raw 文件位置。
- 从公司所在地、财务、股权质押、省级财政 GDP 等数据中派生 `companies.json`、`financials.json`、`equity.json`、`policies.json`，供前端 API 查询和评分计算使用。

## 启动

先构建 React 前端：

```powershell
cd china-reform-score-main/china-reform-score-main
npm install
npm run build
cd ../..
```

再启动 Python 统一服务：

```powershell
python run.py
```

如果当前终端已设置 `MONGODB_URI`，后端会自动使用 MongoDB；否则使用本地 `backend/database`。

打开：

```text
http://127.0.0.1:8000
```

## 已实现

- 首页搜索框：输入公司代码、公司名、简称或省份。
- 首页研究简报式首屏：搜索框、样本说明、Top 1 大卡和 Top 2-10 榜单。
- 首页 Top 10 榜单：按后端数据库计算得分降序排列。
- 按省份浏览：从首页或搜索框进入省份榜单。
- 公司详情页：展示总分徽章、全国/省内排名、四大模块分、关键加减分原因和财务快照。
- 省份榜单页：展示该省公司，按评分降序排列。
- 用户搜索公司时，后端会从 JSON 数据库查询公司、读取关联财务/股权/政策数据，再计算指标后返回前端。
- Python 后端统一提供 API 和 React SPA 静态资源。
- API：
  - `GET /api/home/top-companies?limit=10`
  - `GET /api/search?q=江西`
  - `GET /api/companies/600362`
  - `GET /api/provinces`
  - `GET /api/provinces/江西省/companies`
  - `POST /api/import/excel`

## 测试

```powershell
python -m pytest -q
```

前端构建验证：

```powershell
cd china-reform-score-main/china-reform-score-main
npm run build
```

## Python + Streamlit 网页入口

课程展示推荐使用这个入口。React 前端目录仍然保留作为备份，但主展示页面可以完全用 Python 运行：

```powershell
$env:MONGODB_URI="mongodb+srv://<username>:<password>@<cluster-url>/?appName=Cluster0"
$env:MONGODB_DATABASE="mixed_reform"
$env:MIXED_REFORM_SOURCE_ROOT="C:\Users\赖宏\Desktop\公司混改系统"
& "C:\Users\赖宏\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m streamlit run streamlit_app.py
```

打开 Streamlit 输出的本地地址，一般是：

```text
http://localhost:8501
```

Streamlit 页面包含：首页 Top 榜单、公司搜索、公司详情、省份榜单和数据说明。数据仍然来自 MongoDB 云端；如果没有设置 `MONGODB_URI`，会自动回退读取本地 `backend/database` 备份数据。

治理合规资质二级页会从 `MIXED_REFORM_SOURCE_ROOT\企业股权评分\企业股权评分\result\企业股权最终评分.xlsx` 读取 2023-2025 年治理合规趋势；如果文件缺失，页面会显示空态。

可选 Qwen/NVIDIA 亮点生成配置：

```powershell
$env:QWEN_API_KEY="<your-nvidia-api-key>"
$env:QWEN_BASE_URL="https://integrate.api.nvidia.com/v1"
$env:QWEN_MODEL="qwen/qwen3-next-80b-a3b-instruct"
$env:QWEN_HIGHLIGHTS_ENABLED="1"
$env:QWEN_TIMEOUT_SECONDS="4"
```

请只在本机环境变量或 Streamlit secrets 中配置真实 API key，不要写入仓库文件。如果未设置 `QWEN_API_KEY`，关键治理亮点会自动使用规则生成文案，不影响页面展示。
