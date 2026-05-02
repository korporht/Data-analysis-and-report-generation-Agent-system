"""
NL2SQL Agent - 自然语言转SQL
将用户的自然语言问题转换为可执行的SQL查询
"""

import re
import sqlite3
import pandas as pd
from openai import OpenAI
from config import *


class NL2SQLAgent:
    """自然语言转SQL Agent"""

    def __init__(self, api_key=None, base_url=None, model=None):
        self.api_key = api_key or OPENAI_API_KEY
        self.base_url = base_url or OPENAI_BASE_URL
        self.model = model or LLM_MODEL
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url) if self.api_key else None

    def generate_sql(self, user_query: str, table_schema: str = None) -> str:
        """
        将自然语言问题转换为SQL
        """
        if self.client is None:
            # 无API key时使用规则匹配（降级模式）
            return self._rule_based_sql(user_query)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": NL2SQL_PROMPT},
                    {"role": "user", "content": f"用户问题: {user_query}\n\n请生成SQL查询语句:"}
                ],
                temperature=0.1,
                max_tokens=500,
            )
            sql = response.choices[0].message.content.strip()
            # 清理可能的代码块标记
            sql = re.sub(r'```sql|```', '', sql).strip()
            return sql
        except Exception as e:
            print(f"⚠️ LLM调用失败，使用规则匹配: {e}")
            return self._rule_based_sql(user_query)

    def _rule_based_sql(self, query: str) -> str:
        """
        规则匹配的降级方案（无需API）
        """
        query_lower = query.lower()

        # 各地区销售额
        if any(k in query_lower for k in ["地区", "区域", "region"]) and any(k in query_lower for k in ["销售", "金额", "总额"]):
            year = self._extract_year(query)
            where = f" WHERE Date LIKE '{year}%'" if year else ""
            return f"SELECT Region, SUM(Sales_Amount) as Total_Sales, SUM(Quantity) as Total_Qty FROM sales_data{where} GROUP BY Region ORDER BY Total_Sales DESC;"

        # 各产品销售
        if any(k in query_lower for k in ["产品", "product"]) and any(k in query_lower for k in ["销售", "金额"]):
            year = self._extract_year(query)
            where = f" WHERE Date LIKE '{year}%'" if year else ""
            return f"SELECT Product, Category, SUM(Sales_Amount) as Total_Sales, SUM(Quantity) as Total_Qty FROM sales_data{where} GROUP BY Product ORDER BY Total_Sales DESC;"

        # 销售代表业绩
        if any(k in query_lower for k in ["销售", "代表", "alice", "bob", "charlie", "rep"]):
            year = self._extract_year(query)
            where = f" WHERE Date LIKE '{year}%'" if year else ""
            return f"SELECT Sales_Rep, SUM(Sales_Amount) as Total_Sales, SUM(Quantity) as Total_Qty, COUNT(*) as Order_Count FROM sales_data{where} GROUP BY Sales_Rep ORDER BY Total_Sales DESC;"

        # 时间趋势
        if any(k in query_lower for k in ["趋势", "月度", "每月", "月份", "trend", "monthly"]):
            return "SELECT SUBSTR(Date, 1, 7) as Month, SUM(Sales_Amount) as Total_Sales, SUM(Quantity) as Total_Qty FROM sales_data GROUP BY SUBSTR(Date, 1, 7) ORDER BY Month;"

        # 客户类型
        if any(k in query_lower for k in ["客户", "customer", "企业", "个体"]):
            year = self._extract_year(query)
            where = f" WHERE Date LIKE '{year}%'" if year else ""
            return f"SELECT Customer_Type, SUM(Sales_Amount) as Total_Sales, COUNT(*) as Order_Count FROM sales_data{where} GROUP BY Customer_Type ORDER BY Total_Sales DESC;"

        # 默认：全部销售记录
        return "SELECT Date, Region, Product, Sales_Rep, Sales_Amount, Quantity FROM sales_data ORDER BY Date DESC LIMIT 20;"

    def _extract_year(self, query: str) -> str:
        """从问题中提取年份"""
        import re
        match = re.search(r'20\d{2}', query)
        if match:
            return match.group()
        if "2024" in query or "去年" in query:
            return "2024"
        if "2025" in query or "今年" in query:
            return "2025"
        return ""


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
            # CSV模式：每次查询时将CSV加载为临时SQLite
            conn = sqlite3.connect(":memory:")
            df = pd.read_csv(self.csv_path)
            df.to_sql('sales_data', conn, if_exists='replace', index=False)
            return conn
        else:
            if self.conn is None:
                self.conn = sqlite3.connect(self.db_path)
            return self.conn

    def execute_sql(self, sql: str) -> tuple:
        """
        执行SQL查询，返回 (成功?, 结果DataFrame/错误信息)
        """
        try:
            conn = self.get_connection()
            df = pd.read_sql_query(sql, conn)
            return True, df
        except Exception as e:
            return False, str(e)

    def get_schema(self) -> str:
        """获取数据库表结构描述"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(sales_data)")
        columns = cursor.fetchall()
        schema = "表名: sales_data\n"
        for col in columns:
            schema += f"- {col[1]}: {col[2]}\n"
        return schema

    def get_summary_stats(self) -> dict:
        """获取数据的概要统计"""
        conn = self.get_connection()
        stats = {}
        stats['total_sales'] = pd.read_sql_query("SELECT SUM(Sales_Amount) as v FROM sales_data", conn)['v'].iloc[0]
        stats['total_orders'] = pd.read_sql_query("SELECT COUNT(*) as v FROM sales_data", conn)['v'].iloc[0]
        stats['avg_order'] = pd.read_sql_query("SELECT AVG(Sales_Amount) as v FROM sales_data", conn)['v'].iloc[0]
        stats['top_product'] = pd.read_sql_query("SELECT Product, SUM(Sales_Amount) as v FROM sales_data GROUP BY Product ORDER BY v DESC LIMIT 1", conn).iloc[0]
        stats['top_region'] = pd.read_sql_query("SELECT Region, SUM(Sales_Amount) as v FROM sales_data GROUP BY Region ORDER BY v DESC LIMIT 1", conn).iloc[0]
        return stats
