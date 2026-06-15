# 📊 DataPlatform — 智能数据分析平台

一个功能完整的全栈数据分析平台，支持 CSV 数据上传、数据清洗、探索性分析、可视化图表、智能预测、报告生成以及图像处理（含 OCR），并集成 AI 大模型辅助生成分析报告和对话式数据问答。

## ✨ 功能特性

### 🔍 数据分析
- **文件上传**：支持 CSV 文件上传（最大 50MB），自动检测多种编码（UTF-8、GBK、GB2312 等）
- **数据质量报告**：自动评估缺失值、重复值、异常值（IQR + Log-IQR 方法），推断字段类型
- **字段画像**：自动识别列类型（数值型、分类型、日期型、空列），推荐用法，生成自然语言描述
- **数据清洗**：
  - 缺失值处理（删除行 / 中位数填充 / 众数填充 / 固定值填充）
  - 异常值移除（IQR 方法）
  - 重复行删除
  - 列类型转换
  - 版本化清洗历史，支持回滚
- **查询 / 筛选 / 排序**：支持复杂条件过滤（等于、不等、大于、小于、包含、区间、空值判断等），分页查询
- **分组聚合**：多列分组，支持计数、求和、均值、最大值、最小值、中位数等统计指标
- **频次分布**：数值型 / 分类型字段的自动分布分析，含累计计数
- **相关性分析**：Pearson 相关系数矩阵，Top-N 相关对分析

### 📈 可视化图表
基于 ECharts 6，支持以下图表类型：
- **数值型**：直方图、折线图、面积图、柱状图、散点图、箱线图
- **分类型**：柱状图、横向柱状图、饼图、环形图、玫瑰图、矩形树图、词云图

### 🤖 智能预测
- 时间序列预测（季节性趋势、线性趋势、移动平均）
- 回归预测（线性回归、多元线性回归）
- 分类预测（最近质心分类）
- 自动检测数据集可用的预测能力

### 📝 报告生成
- 自动整合质量报告、字段画像、统计摘要、相关性分析、图表推荐和预测结果
- **AI 智能摘要**：集成阿里云 DashScope（通义千问 Qwen-Plus），生成执行摘要、关键发现、风险提示和后续建议
- **HTML 报告导出**：生成独立网页文件，支持打印与展示

### 🖼️ 图像处理
- 支持上传 PNG、JPG、JPEG、WebP、BMP 格式（最大 20MB）
- 图像操作：灰度化、二值化、旋转、翻转、亮度/对比度调整、锐化、降噪、裁剪、缩放
- **OCR 文字识别**：基于 RapidOCR 的轻量级光学字符识别
- 处理历史追踪，支持回滚

### 💬 AI 对话助手
- 基于大模型的对话式数据分析
- 可自动触发数据导航、图表生成、分组分析、分布分析、质量卡片展示、相关性热力图等操作

### 👤 用户与权限
- 用户注册 / 登录（JWT 认证）
- 角色系统：普通用户 / 管理员
- 管理员面板：用户列表管理、角色更新、账号启停、密码重置
- 用户中心：账户概览、活动历史、密码修改
- 文件按用户隔离

### 📋 分析计划与工作流
- **分析计划**：保存和恢复分析配置（查询、分组、分布、相关性、图表状态）
- **分析工作流**：多步骤流水线（清洗 → 查询 → 分组 → 分布 → 图表 → 预测 → AI 摘要），支持保存并一键重跑

---

## 🛠️ 技术栈

| 层级 | 技术 |
|------|------|
| **后端框架** | FastAPI (Python) |
| **服务器** | Uvicorn (ASGI) |
| **数据库 ORM** | SQLAlchemy + MySQL (PyMySQL) |
| **认证** | JWT (python-jose) + passlib[bcrypt] |
| **数据处理** | pandas、numpy |
| **图像处理** | Pillow (PIL)、RapidOCR (ONNX Runtime) |
| **AI / LLM** | 阿里云 DashScope (Qwen-Plus)，OpenAI 兼容接口 |
| **测试** | pytest |
| **前端框架** | Vue 3 (Composition API + `<script setup>`) |
| **构建工具** | Vite 8 |
| **UI 组件库** | Naive UI、Arco Design Web Vue |
| **图表** | ECharts 6 |
| **路由** | Vue Router 5 |
| **HTTP 客户端** | Axios |
| **动画** | GSAP |

---

## 📁 项目结构

```
├── backend/                        # 后端 FastAPI 应用
│   ├── main.py                     # 主应用（54+ API 路由）
│   ├── models.py                   # SQLAlchemy ORM 模型
│   ├── database.py                 # 数据库连接与会话管理
│   ├── config.py                   # 环境变量配置
│   ├── auth.py                     # JWT 认证模块
│   ├── ai_provider.py              # AI 服务抽象层（DashScope）
│   ├── prediction_service.py       # 机器学习预测服务
│   ├── image_service.py            # 图像处理与 OCR 服务
│   ├── requirements.txt            # Python 依赖
│   ├── .env.example                # 环境变量模板
│   └── tests/                      # 测试用例
├── frontend/                       # 前端 Vue 3 SPA
│   ├── src/
│   │   ├── router/index.js         # Vue Router 路由（含权限守卫）
│   │   ├── plugins/ui-libraries.js # Naive UI + Arco Design 插件
│   │   ├── views/                  # 页面组件
│   │   │   ├── DataWorkspace.vue   # 数据分析工作区
│   │   │   ├── ImageWorkspace.vue  # 图像处理工作区
│   │   │   ├── Home.vue            # 仪表盘首页
│   │   │   ├── Login.vue           # 登录页
│   │   │   ├── Register.vue        # 注册页
│   │   │   ├── UserCenter.vue      # 用户中心
│   │   │   └── Admin.vue           # 管理员面板
│   │   ├── components/             # 可复用组件
│   │   └── api/                    # API 请求封装
│   ├── package.json
│   └── vite.config.js
├── .omx/                           # 开发工具配置
└── MEMORY.md                       # 项目记忆文件
```

---

## 🚀 快速开始

### 环境要求

- **Python** 3.10+
- **Node.js** 18+
- **MySQL** 8.0+（运行于 localhost:3306）

### 1. 后端配置

```bash
cd backend

# 创建并激活虚拟环境
python -m venv venv

# Windows
venv\Scripts\activate
# Linux / macOS
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，设置数据库连接、密钥和 API Key
```

### 2. 环境变量说明

编辑 `backend/.env`：

```env
# 运行环境: development / production
APP_ENV=development

# JWT 签名密钥（请修改为随机字符串）
APP_SECRET_KEY=your-secret-key-here

# MySQL 数据库连接
DATABASE_URL=mysql+pymysql://root:password@127.0.0.1:3306/dataplatform

# 阿里云 DashScope API Key（可选，用于 AI 功能）
DASHSCOPE_API_KEY=sk-your-api-key

# AI 服务提供商: alibaba / openai
AI_PROVIDER=alibaba

# CORS 允许的前端地址
CORS_ALLOW_ORIGINS=http://127.0.0.1:5173,http://localhost:5173

# 允许的 Host
ALLOWED_HOSTS=127.0.0.1,localhost

# 最大上传文件大小（MB）
MAX_UPLOAD_SIZE_MB=50
```

> **注意**：AI 功能（智能报告摘要、对话助手）需要配置 `DASHSCOPE_API_KEY`。未配置时系统会自动降级为基于规则的摘要。

### 3. 启动后端

```bash
cd backend
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

后端启动后：
- API 服务：http://127.0.0.1:8000
- 自动生成 API 文档：http://127.0.0.1:8000/docs
- 数据库表将在首次启动时自动创建

### 4. 启动前端

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端启动后访问：http://127.0.0.1:5173

---

## 🔌 API 概览

| 分类 | 主要端点 |
|------|---------|
| **认证** | `POST /register`、`POST /login`、`GET /me` |
| **文件管理** | `POST /upload`、`GET /files`、`DELETE /files/{filename}` |
| **数据质量** | `GET /quality/{filename}`、`GET /field-profiles/{filename}` |
| **数据预览** | `GET /preview/{filename}` |
| **数据清洗** | `POST /clean/preview/{filename}`、`POST /clean/apply/{filename}`、`POST /cleaning/rollback/{filename}` |
| **查询** | `POST /query/preview/{filename}` |
| **分组聚合** | `POST /groupby/analyze/{filename}` |
| **频次分布** | `POST /distribution/analyze/{filename}` |
| **图表** | `GET /chart/{filename}` |
| **统计分析** | `GET /analyze/{filename}`、`GET /export/statistics/{filename}`、`GET /export/correlation/{filename}` |
| **预测** | `GET /predict/{filename}/capabilities`、`POST /predict/{filename}` |
| **报告** | `GET /report/{filename}`、`GET /report/{filename}/html` |
| **图像处理** | `POST /images/upload`、`POST /images/process/preview/{filename}`、`POST /images/ocr/{filename}` |
| **AI 助手** | `GET /ai/status`、`POST /ai/assistant/{filename}` |
| **分析计划** | `GET /plans`、`POST /plans/{filename}`、`DELETE /plans/{plan_id}` |
| **工作流** | `GET /workflows`、`POST /workflows/{filename}`、`POST /workflows/{workflow_id}/run` |
| **管理员** | `GET /admin/summary`、`GET /admin/users`、`PATCH /admin/users/{user_id}` |

完整的 API 文档可在服务启动后访问 http://127.0.0.1:8000/docs 查看 Swagger UI。

---

## 🗺️ 前端路由

| 路径 | 页面 | 权限 |
|------|------|------|
| `/login` | 登录页 | 游客 |
| `/register` | 注册页 | 游客 |
| `/home` | 仪表盘首页 | 需登录 |
| `/workspace/data` | 数据分析工作区 | 需登录 |
| `/workspace/image` | 图像处理工作区 | 需登录 |
| `/account` | 用户中心 | 需登录 |
| `/admin` | 管理员面板 | 管理员 |

---

## 🧪 运行测试

```bash
cd backend
pytest tests/ -v
```

---

## 📄 License

本项目仅供学习交流使用。

---

## 🙏 致谢

- [FastAPI](https://fastapi.tiangolo.com/) — 现代化的 Python Web 框架
- [Vue 3](https://vuejs.org/) — 渐进式 JavaScript 框架
- [Naive UI](https://www.naiveui.com/) — Vue 3 组件库
- [ECharts](https://echarts.apache.org/) — 数据可视化图表库
- [RapidOCR](https://github.com/RapidAI/RapidOCR) — 轻量级 OCR 引擎
- [阿里云 DashScope](https://dashscope.aliyun.com/) — 大模型 API 服务
