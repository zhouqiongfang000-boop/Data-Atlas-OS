# AI 分析助手设计说明

## 设计目标

这套 AI 接入不是把现有的数据分析逻辑交给模型重算，而是在现有系统之上增加一个“理解问题 + 调用分析模块 + 组织结果”的智能层。

核心目标有两个：

1. 先接入阿里云百炼（DashScope / Qwen）
2. 后续如果更换模型提供商，尽量只改配置或新增 provider，不改前端和业务接口

## 整体结构

系统现在分成三层：

### 1. 前端 AI 面板

前端只调用两个接口：

- `GET /ai/status`
- `POST /ai/assistant/{filename}`

前端不直接接触任何模型厂商，也不持有 API Key。

### 2. 后端 AI 编排层

后端入口在：

- `backend/main.py`

主要职责：

- 校验当前用户是否能访问文件
- 读取当前文件的精简上下文
- 组合成发给模型的 prompt
- 调用统一的 provider
- 把模型返回结果整理成前端稳定可用的结构

### 3. Provider 适配层

Provider 抽象放在：

- `backend/ai_provider.py`

当前默认 provider：

- `AI_PROVIDER=alibaba`

当前默认模型：

- `AI_MODEL=qwen-plus`

这层的职责是：

- 读取环境变量
- 调用上游模型 API
- 统一返回 JSON 结果

## 为什么要做 Provider 抽象

如果把阿里、OpenAI、Gemini 的请求逻辑直接写在 `main.py` 里，以后每次换模型都要改业务代码，前端和后端容易一起受影响。

现在改成 provider 抽象后：

- 前端永远只认 `/ai/status` 和 `/ai/assistant`
- 后端业务层永远只认 `get_active_ai_provider()`
- 真正和厂商 API 打交道的只有 `ai_provider.py`

这样以后换模型时，优先只需要改：

- `AI_PROVIDER`
- `AI_MODEL`
- `AI_BASE_URL`
- `AI_API_KEY`

如果是同类兼容接口，甚至只要改 `.env`。

## 当前为什么选阿里云百炼

当前项目默认接入阿里，是因为：

- 国内访问更稳
- 对中文问答更友好
- DashScope 提供 OpenAI 兼容模式，方便做统一封装

当前默认地址：

- `https://dashscope.aliyuncs.com/compatible-mode/v1`

## 当前 AI 的职责边界

AI 负责：

- 理解用户问题
- 基于数据上下文给解释
- 推荐下一步分析模块
- 输出结构化建议动作

AI 不负责：

- 替代 pandas 做真实统计计算
- 编造字段或结果
- 改写数据库或文件

也就是说，AI 是“分析助手”，不是“计算真相来源”。

## 模型实际看到的数据

为了控制成本和稳定性，后端不会把整份大文件原样塞给模型，而是只发送精简上下文，包括：

- 当前文件名
- 行数、列数
- 字段列表
- 数值列 / 类别列
- 预览前几行
- 数据质量摘要
- 精简后的字段画像
- 当前工作区状态
- 最近几轮对话

这样做的好处：

- 更稳定
- 响应更快
- 成本更低
- 降低大文件直接喂模型的失败风险

## 返回给前端的结构

AI 返回的是稳定 JSON，核心字段包括：

- `answer`
- `insights`
- `cautions`
- `suggested_actions`

其中 `suggested_actions` 会被前端直接转成按钮，用户点击后可以跳转或执行：

- 图表分析
- 频数分布
- 分组统计
- 质量检查
- 字段画像
- 相关性分析

## 当前可切换方式

### 方式一：仅换兼容接口

如果新模型也支持 OpenAI 兼容风格接口，通常只需要改：

```env
AI_PROVIDER=openai_compatible
AI_BASE_URL=https://your-provider.example/v1
AI_MODEL=your-model-name
AI_API_KEY=your-api-key
```

### 方式二：新增专用 Provider

如果新模型不兼容当前请求格式，可以在 `backend/ai_provider.py` 新增一个 provider 类，然后在 `_build_provider_config()` 里接入。

这样仍然不需要改前端接口。

## 当前环境变量

后端示例配置见：

- `backend/.env.example`

阿里云百炼推荐这样配：

```env
AI_PROVIDER=alibaba
AI_MODEL=qwen-plus
DASHSCOPE_API_KEY=你的密钥
AI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
AI_TIMEOUT_SECONDS=45
```

## 后续扩展建议

下一步如果继续扩展 AI，可以考虑：

1. 让 AI 自动总结图表与统计结果
2. 支持“把 AI 建议保存为分析方案”
3. 给图片工作流复用同一套 provider 抽象
4. 增加多 provider 自动切换或降级策略

## 一句话总结

现在这套设计的核心是：

**前端固定、业务接口固定、模型提供商可切换。**

这样当前可以先用阿里，后面如果你觉得这个 API 不合适，只需要切换 provider 配置或新增 provider，而不需要重做整个系统。
