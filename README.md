# 数据分析与报告生成 Agent 系统

> 基于多 Agent 协作的智能数据分析系统：一句话提问 → 自动生成 SQL → 执行查询 → 可视化图表 → 完整报告

## 系统架构

```
用户问题（自然语言）
    ↓
[NL2SQL Agent]  →  生成SQL查询
    ↓
[DataQuery Agent]  →  执行查询，返回数据
    ↓
[Report Agent]  →  生成数据解读文本
    ↓
[Visualization Agent]  →  生成图表
    ↓
[Report Agent]  →  组装完整报告（Markdown/HTML/Word）
```

## 文件说明

| 文件 | 说明 |
|------|------|
| `config.py` | 配置文件（LLM API、数据库、报告格式） |
| `nl2sql_agent.py` | NL2SQL Agent（自然语言转SQL）+ DataQuery Agent（执行查询） |
| `visualization_agent.py` | 可视化 Agent（自动推荐图表类型并生成） |
| `report_agent.py` | 报告生成 Agent（Markdown/HTML/Word） |
| `main.py` | CLI 主入口（命令行/交互模式） |
| `app.py` | Streamlit Web 界面 |
| `sample_data.csv` | 示例销售数据 |
| `requirements.txt` | Python 依赖 |

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 API Key（可选）

使用 OpenAI API（推荐）：
```bash
export OPENAI_API_KEY="sk-your-key"
export OPENAI_BASE_URL="https://api.openai.com/v1"  # 可选：改其他兼容接口
```

**无需 API Key 也能运行**：系统内置规则匹配降级方案，无 API 时可正常工作（只是智能程度略低）。

使用本地模型（Ollama）：
```bash
# 安装 Ollama 后运行
ollama serve
ollama pull qwen2.5:7b
```
然后在 `config.py` 中修改配置：
```python
OPENAI_API_KEY = "ollama"
OPENAI_BASE_URL = "http://localhost:11434/v1"
LLM_MODEL = "qwen2.5:7b"
```

### 3. 运行方式

**方式一：命令行交互模式（推荐）**
```bash
python main.py --interactive
```

**方式二：单次提问**
```bash
python main.py --query "2024年各地区的销售总额是多少"
python main.py --query "Alice卖了哪些产品" --formats html word
```

**方式三：Web 界面（最直观）**
```bash
streamlit run app.py
```
然后在浏览器打开 `http://localhost:8501`

## 示例问题

系统支持自然语言提问，例如：

- `2024年各地区的销售总额是多少`
- `Alice 卖了哪些产品，各卖了多少`
- `各产品类别的销售趋势是怎样的`
- `哪个销售代表业绩最好`
- `企业客户的销售额占比是多少`
- `2024年每月的销售趋势`
- `折扣对销售金额的影响`

## 输出说明

每次分析生成：

- **SQL 查询语句**（可查看和复用）
- **查询结果表格**（在终端/网页展示）
- **AI 数据解读**（关键发现 + 趋势分析 + 建议）
- **可视化图表**（自动推荐柱状图/折线图/饼图等，PNG 格式）
- **完整报告**（支持 Markdown / HTML / Word 三格式，可下载）

输出目录：
- 图表：`charts/` 目录
- 报告：`reports/` 目录

## 接入自己的数据

1. 将数据保存为 CSV 文件（第一行是列名）
2. 修改 `config.py` 中的 `CSV_PATH` 指向你的文件
3. 修改 `config.py` 中的 `NL2SQL_PROMPT`，更新为你数据的表结构说明
4. 重新运行即可

## 技术亮点

- **多 Agent 协作**：NL2SQL、查询、可视化、报告各司其职
- **降级方案**：无 LLM API 时自动切换规则匹配，保证可用性
- **智能图表推荐**：根据数据特征自动选择最合适的图表类型
- **多格式报告**：Markdown（轻量）、HTML（精美可分享）、Word（正式文档）
- **Web 界面**：基于 Streamlit，开箱即用

## Token 申请用项目描述

> 我构建了一个多 Agent 协作的数据分析与报告生成系统。用户用自然语言提问（如"2024年各地区的销售总额"），系统通过 NL2SQL Agent 自动生成 SQL 查询，DataQuery Agent 执行查询获取结果，Visualization Agent 智能推荐并生成可视化图表，Report Agent 自动撰写数据解读并组装成完整报告（支持 Markdown/HTML/Word 三格式输出）。系统具备降级能力（无 API 时也能运行），已用销售数据完整测试通过。长链推理体现在：自然语言理解 → SQL 生成 → 数据验证 → 图表选择 → 解读生成，全过程无需人工干预。
