"""
配置模块 - 数据分析Agent系统
支持 OpenAI API 或本地模型
"""

import os
from pathlib import Path

# ============ LLM 配置 ============
# 使用 OpenAI API（推荐）
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
LLM_MODEL = "gpt-4o-mini"  # 或 "gpt-4", "gpt-3.5-turbo"

# 使用本地模型（无需API key，使用 ollama 等）
# 取消注释以下配置使用本地模型
# OPENAI_API_KEY = "ollama"
# OPENAI_BASE_URL = "http://localhost:11434/v1"
# LLM_MODEL = "qwen2.5:7b"

# ============ 数据库配置 ============
# 使用 SQLite（无需安装数据库服务）
DB_PATH = "sales.db"

# 或使用 CSV 模式（无需数据库）
USE_CSV_MODE = True   # True: 直接读CSV  False: 导入SQLite后用SQL查询
CSV_PATH = "sample_data.csv"

# ============ 报告配置 ============
REPORT_OUTPUT_DIR = "reports"
CHART_OUTPUT_DIR = "charts"

# ============ Agent 角色 Prompt ============
NL2SQL_PROMPT = """
你是一个专业的自然语言转SQL助手。
根据用户的自然语言问题，生成准确的SQL查询语句。

数据库表结构（表名: sales_data）:
- Date: 日期 (TEXT, 格式 YYYY-MM-DD)
- Region: 地区 (TEXT, 值: North/South/East/West)
- Product: 产品名称 (TEXT)
- Category: 产品类别 (TEXT, 值: Electronics/Accessories)
- Sales_Rep: 销售代表 (TEXT, 值: Alice/Bob/Charlie)
- Sales_Amount: 销售金额 (REAL, 单位: 元)
- Quantity: 销售数量 (INTEGER)
- Unit_Price: 单价 (REAL, 单位: 元)
- Discount: 折扣率 (REAL, 0.00-0.20)
- Customer_Type: 客户类型 (TEXT, 值: Enterprise/SMB/Individual)

规则:
1. 只输出SQL语句，不要有任何解释或标记
2. 使用标准SQL语法（SQLite兼容）
3. 金额单位：元（已有数据）
4. 日期格式: YYYY-MM-DD
5. 如果需要计算同比增长，使用子查询或CTE
6. 结果按需要排序（金额降序、日期升序等）
7. 限制结果数量时使用 LIMIT

示例:
Q: 2024年各地区的销售总额是多少
A: SELECT Region, SUM(Sales_Amount) as Total_Sales FROM sales_data WHERE Date LIKE '2024%' GROUP BY Region ORDER BY Total_Sales DESC;

Q: Alice在2024年卖了哪些产品，各卖了多少钱
A: SELECT Product, SUM(Sales_Amount) as Total_Sales, SUM(Quantity) as Total_Qty FROM sales_data WHERE Sales_Rep='Alice' AND Date LIKE '2024%' GROUP BY Product ORDER BY Total_Sales DESC;
"""

QUERY_ANALYSIS_PROMPT = """
你是一个数据分析助手。
根据用户的问题和查询结果，用中文给出专业的数据解读。

要求:
1. 先总结关键发现（3-5个要点）
2. 指出数据中的趋势、异常或亮点
3. 如果有对比维度（地区/产品/时间），指出差异原因
4. 用自然语言描述，不要只罗列数字
5. 如果有异常值，特别提醒

输出格式:
## 关键发现
- 要点1
- 要点2

## 数据解读
（2-3段分析文字）

## 建议
（1-2条行动建议）
"""

VISUALIZATION_PROMPT = """
你是一个数据可视化专家。
根据用户问题和数据特征，推荐最合适的图表类型。

可选图表:
- bar: 柱状图（类别对比）
- line: 折线图（时间趋势）
- pie: 饼图（占比分布）
- scatter: 散点图（相关性）
- heatmap: 热力图（多维对比）

只输出图表类型名称（如: bar），不要有其他内容。
"""

REPORT_PROMPT = """
你是一个商业报告撰写专家。
根据分析结果和图表描述，撰写一份专业的数据分析报告。

报告结构:
1. 执行摘要（3句话）
2. 分析背景（用户问题）
3. 数据分析（关键发现+解读）
4. 结论与建议

用中文输出，语气专业但易读，适合发送给管理层。
"""
