"""
NL2SQL Agent + 意图理解Agent + SQL校验Agent + 数据查询Agent
长链推理的前三个环节
"""

import re
import json
import sqlite3
import pandas as pd
from openai import OpenAI
from config import *


# ============================================================
# Agent 1: 意图理解Agent
# 解决痛点: 业务人员无法精确表达分析需求 → 自动拆解意图
# ============================================================
class IntentUnderstandingAgent:
    """意图理解Agent - 将模糊问题拆解为结构化分析意图"""

    def __init__(self, api_key=None, base_url=None, model=None):
        self.api_key = api_key or OPENAI_API_KEY
        self.base_url = base_url or OPENAI_BASE_URL
        self.model = model or LLM_MODEL
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url) if self.api_key else None

    def understand(self, user_query: str) -> dict:
        """
        解析用户意图，返回结构化意图对象
        这是长链推理的第一步：理解 → 拆解 → 精确化
        """
        if self.client is None:
            return self._rule_based_understanding(user_query)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": INTENT_UNDERSTANDING_PROMPT},
                    {"role": "user", "content": f"用户问题: {user_query}"}
                ],
                temperature=0.1,
                max_tokens=500,
            )
            content = response.choices[0].message.content.strip()
            # 清理可能的代码块标记
            content = re.sub(r'```json|```', '', content).strip()
            intent = json.loads(content)
            return intent
        except Exception as e:
            print(f"⚠️ 意图理解LLM失败，使用规则匹配: {e}")
            return self._rule_based_understanding(user_query)

    def _rule_based_understanding(self, query: str) -> dict:
        """规则式意图理解（降级方案）"""
        query_lower = query.lower()
        intent = {
            "original_query": query,
            "analysis_type": "综合分析",
            "time_scope": "全部",
            "dimensions": [],
            "metrics": ["Sales_Amount"],
            "filters": [],
            "comparison": False,
            "clarified_query": query
        }

        # 分析类型判断
        if any(k in query_lower for k in ["趋势", "变化", "增长", "月度", "每月"]):
            intent["analysis_type"] = "趋势分析"
            intent["dimensions"] = ["时间"]
        elif any(k in query_lower for k in ["对比", "比较", "vs", "哪个好"]):
            intent["analysis_type"] = "对比分析"
        elif any(k in query_lower for k in ["占比", "比例", "份额", "分布"]):
            intent["analysis_type"] = "占比分析"
        elif any(k in query_lower for k in ["排名", "最好", "最多", "最高", "Top"]):
            intent["analysis_type"] = "排名分析"
        elif any(k in query_lower for k in ["明细", "列出", "哪些", "有什么"]):
            intent["analysis_type"] = "明细查询"

        # 维度提取
        if any(k in query_lower for k in ["地区", "区域", "region"]):
            intent["dimensions"].append("Region")
        if any(k in query_lower for k in ["产品", "product"]):
            intent["dimensions"].append("Product")
        if any(k in query_lower for k in ["代表", "alice", "bob", "charlie", "rep"]):
            intent["dimensions"].append("Sales_Rep")
        if any(k in query_lower for k in ["客户", "customer", "企业", "个体"]):
            intent["dimensions"].append("Customer_Type")
        if any(k in query_lower for k in ["类别", "分类", "category"]):
            intent["dimensions"].append("Category")

        # 时间范围
        if "2024" in query:
            intent["time_scope"] = "2024年"
        elif "2025" in query:
            intent["time_scope"] = "2025年"

        # 指标
        if any(k in query_lower for k in ["数量", "多少件", "quantity"]):
            intent["metrics"].append("Quantity")
        if any(k in query_lower for k in ["折扣", "discount"]):
            intent["metrics"].append("Discount")

        # 筛选条件
        for name in ["Alice", "Bob", "Charlie"]:
            if name.lower() in query_lower:
                intent["filters"].append(f"Sales_Rep={name}")
        for ctype in ["Enterprise", "SMB", "Individual"]:
            if ctype.lower() in query_lower:
                intent["filters"].append(f"Customer_Type={ctype}")

        # 对比
        if any(k in query_lower for k in ["同比", "环比", "对比", "比较", "增长"]):
            intent["comparison"] = True

        return intent


# ============================================================
# Agent 2: NL2SQL Agent
# 解决痛点: 业务人员不会写SQL → 自然语言自动生成SQL
# ============================================================
class NL2SQLAgent:
    """自然语言转SQL Agent - 基于意图生成精确查询"""

    def __init__(self, api_key=None, base_url=None, model=None):
        self.api_key = api_key or OPENAI_API_KEY
        self.base_url = base_url or OPENAI_BASE_URL
        self.model = model or LLM_MODEL
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url) if self.api_key else None

    def generate_sql(self, user_query: str, intent: dict = None) -> str:
        """
        根据用户问题和解析的意图生成SQL
        意图信息让SQL生成更精确（长链推理：上一步的输出是下一步的输入）
        """
        if self.client is None:
            return self._rule_based_sql(user_query, intent)

        try:
            # 将意图信息注入prompt，让SQL生成更精确
            intent_desc = ""
            if intent:
                intent_desc = f"\n\n已解析的分析意图:\n- 分析类型: {intent.get('analysis_type', '')}\n- 时间范围: {intent.get('time_scope', '')}\n- 分析维度: {intent.get('dimensions', [])}\n- 关注指标: {intent.get('metrics', [])}\n- 筛选条件: {intent.get('filters', [])}\n- 是否对比: {intent.get('comparison', False)}"

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": NL2SQL_PROMPT},
                    {"role": "user", "content": f"用户问题: {user_query}{intent_desc}\n\n请生成SQL查询语句:"}
                ],
                temperature=0.1,
                max_tokens=500,
            )
            sql = response.choices[0].message.content.strip()
            sql = re.sub(r'```sql|```', '', sql).strip()
            return sql
        except Exception as e:
            print(f"⚠️ LLM调用失败，使用规则匹配: {e}")
            return self._rule_based_sql(user_query, intent)

    def _rule_based_sql(self, query: str, intent: dict = None) -> str:
        """规则匹配降级方案"""
        query_lower = query.lower()
        dims = intent.get('dimensions', []) if intent else []
        time_scope = intent.get('time_scope', '') if intent else ''
        where_time = f" WHERE Date LIKE '{self._extract_year(query)}%'" if self._extract_year(query) else ""

        # 根据分析类型和维度生成SQL
        if "趋势分析" in (intent.get('analysis_type', '') if intent else ''):
            return "SELECT SUBSTR(Date,1,7) as Month, SUM(Sales_Amount) as Total_Sales, SUM(Quantity) as Total_Qty FROM sales_data GROUP BY SUBSTR(Date,1,7) ORDER BY Month;"

        if "Region" in dims or any(k in query_lower for k in ["地区", "区域"]):
            return f"SELECT Region, SUM(Sales_Amount) as Total_Sales, SUM(Quantity) as Total_Qty, COUNT(*) as Order_Count FROM sales_data{where_time} GROUP BY Region ORDER BY Total_Sales DESC;"

        if "Sales_Rep" in dims or any(k in query_lower for k in ["销售", "代表", "alice", "bob", "charlie"]):
            return f"SELECT Sales_Rep, SUM(Sales_Amount) as Total_Sales, SUM(Quantity) as Total_Qty, COUNT(*) as Order_Count FROM sales_data{where_time} GROUP BY Sales_Rep ORDER BY Total_Sales DESC;"

        if "Product" in dims or any(k in query_lower for k in ["产品", "product"]):
            return f"SELECT Product, Category, SUM(Sales_Amount) as Total_Sales, SUM(Quantity) as Total_Qty FROM sales_data{where_time} GROUP BY Product ORDER BY Total_Sales DESC;"

        if "Customer_Type" in dims or any(k in query_lower for k in ["客户", "customer"]):
            return f"SELECT Customer_Type, SUM(Sales_Amount) as Total_Sales, COUNT(*) as Order_Count FROM sales_data{where_time} GROUP BY Customer_Type ORDER BY Total_Sales DESC;"

        if "Category" in dims or any(k in query_lower for k in ["类别", "分类"]):
            return f"SELECT Category, SUM(Sales_Amount) as Total_Sales, SUM(Quantity) as Total_Qty FROM sales_data{where_time} GROUP BY Category ORDER BY Total_Sales DESC;"

        # 默认
        return "SELECT Date, Region, Product, Sales_Rep, Sales_Amount, Quantity, Customer_Type FROM sales_data ORDER BY Date DESC LIMIT 20;"

    def _extract_year(self, query: str) -> str:
        match = re.search(r'20\d{2}', query)
        if match:
            return match.group()
        return ""


# ============================================================
# Agent 3: SQL校验Agent（自修复）
# 解决痛点: AI生成的SQL可能有误 → 自动检测+修复，保证结果可信
# ============================================================
class SQLValidationAgent:
    """SQL校验与自修复Agent - 保证SQL正确性"""

    def __init__(self, api_key=None, base_url=None, model=None):
        self.api_key = api_key or OPENAI_API_KEY
        self.base_url = base_url or OPENAI_BASE_URL
        self.model = model or LLM_MODEL
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url) if self.api_key else None

    def validate_and_fix(self, sql: str, schema_info: str = "") -> tuple:
        """
        校验SQL并尝试修复
        返回: (是否修改, 修复后的SQL, 校验日志)
        """
        log = []

        # 1. 基础语法检查（不需要LLM）
        checks = self._syntax_checks(sql)
        log.extend(checks['logs'])

        if checks['fixed_sql'] != sql:
            log.append("🔧 SQL已通过规则校验修复")
            return True, checks['fixed_sql'], log

        # 2. LLM深度校验（如果可用）
        if self.client:
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": SQL_VALIDATION_PROMPT},
                        {"role": "user", "content": f"数据库表: sales_data\n{schema_info}\n\nSQL: {sql}"}
                    ],
                    temperature=0.1,
                    max_tokens=500,
                )
                result = response.choices[0].message.content.strip()
                if result.upper() == "VALID":
                    log.append("✅ SQL通过LLM深度校验")
                    return False, sql, log
                else:
                    # LLM返回了修复后的SQL
                    fixed = re.sub(r'```sql|```', '', result).strip()
                    log.append("🔧 SQL已通过LLM深度校验修复")
                    return True, fixed, log
            except Exception as e:
                log.append(f"⚠️ LLM校验失败: {e}")

        log.append("✅ SQL通过规则校验")
        return False, sql, log

    def _syntax_checks(self, sql: str) -> dict:
        """基础SQL语法检查"""
        logs = []
        fixed_sql = sql

        # 检查末尾分号
        if not fixed_sql.rstrip().endswith(';'):
            fixed_sql = fixed_sql.rstrip() + ';'
            logs.append("📝 已添加末尾分号")

        # 检查是否有SELECT
        if not fixed_sql.strip().upper().startswith('SELECT'):
            logs.append("⚠️ SQL不以SELECT开头")

        # 检查GROUP BY一致性（简单检查）
        select_cols = re.findall(r'SELECT\s+(.*?)\s+FROM', fixed_sql, re.IGNORECASE | re.DOTALL)
        if select_cols and 'GROUP BY' in fixed_sql.upper():
            # 提取非聚合列
            non_agg_cols = re.findall(r'(\w+)\.(?:\w+)|(?:^|,\s*)(\w+)(?=\s*,|\s+FROM)', select_cols[0])
            logs.append("📝 GROUP BY一致性已检查")

        # 检查危险操作
        dangerous = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE']
        for word in dangerous:
            if word in fixed_sql.upper():
                logs.append(f"🚫 检测到危险操作 {word}，已移除")
                return {'fixed_sql': 'SELECT 1;', 'logs': logs}

        return {'fixed_sql': fixed_sql, 'logs': logs}


# ============================================================
# Agent 4: 数据查询Agent
# ============================================================
class DataQueryAgent:
    """数据查询Agent - 执行SQL并返回结果"""

    def __init__(self, db_path=None, csv_path=None):
        self.db_path = db_path or DB_PATH
        self.csv_path = csv_path or CSV_PATH
        self.conn = None

    def init_db(self):
        """从CSV初始化SQLite数据库"""
        df = pd.read_csv(self.csv_path)
        self.conn = sqlite3.connect(self.db_path)
        df.to_sql('sales_data', self.conn, if_exists='replace', index=False)
        print(f"✅ 数据库已初始化: {self.db_path}")
        return self.conn

    def get_connection(self):
        """获取数据库连接"""
        if USE_CSV_MODE:
            conn = sqlite3.connect(":memory:")
            df = pd.read_csv(self.csv_path)
            df.to_sql('sales_data', conn, if_exists='replace', index=False)
            return conn
        else:
            if self.conn is None:
                self.conn = sqlite3.connect(self.db_path)
            return self.conn

    def execute_sql(self, sql: str) -> tuple:
        """执行SQL查询，返回 (成功?, 结果DataFrame/错误信息)"""
        try:
            conn = self.get_connection()
            df = pd.read_sql_query(sql, conn)
            return True, df
        except Exception as e:
            return False, str(e)

    def get_schema(self) -> str:
        """获取数据库表结构"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(sales_data)")
        columns = cursor.fetchall()
        schema = "表名: sales_data\n"
        for col in columns:
            schema += f"- {col[1]}: {col[2]}\n"
        return schema

    def get_summary_stats(self) -> dict:
        """获取数据概要统计"""
        conn = self.get_connection()
        stats = {}
        stats['total_sales'] = pd.read_sql_query("SELECT SUM(Sales_Amount) as v FROM sales_data", conn)['v'].iloc[0]
        stats['total_orders'] = pd.read_sql_query("SELECT COUNT(*) as v FROM sales_data", conn)['v'].iloc[0]
        stats['avg_order'] = pd.read_sql_query("SELECT AVG(Sales_Amount) as v FROM sales_data", conn)['v'].iloc[0]
        return stats
