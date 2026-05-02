"""
可视化 Agent - 数据图表生成
根据数据自动生成合适的图表
"""

import os
import matplotlib.pyplot as plt
import matplotlib
import seaborn as sns
import pandas as pd
from openai import OpenAI
from config import *

# 设置中文字体
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
matplotlib.rcParams['axes.unicode_minus'] = False

# 确保输出目录存在
os.makedirs(CHART_OUTPUT_DIR, exist_ok=True)


class VisualizationAgent:
    """数据可视化Agent"""

    def __init__(self, api_key=None, base_url=None, model=None):
        self.api_key = api_key or OPENAI_API_KEY
        self.base_url = base_url or OPENAI_BASE_URL
        self.model = model or LLM_MODEL
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url) if self.api_key else None

    def recommend_chart(self, df: pd.DataFrame, user_query: str) -> str:
        """根据数据和问题推荐图表类型"""
        if self.client is None:
            return self._rule_based_chart_type(df, user_query)

        try:
            cols_desc = ", ".join([f"{col}({str(dtype)})" for col, dtype in zip(df.columns, df.dtypes)])
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": VISUALIZATION_PROMPT},
                    {"role": "user", "content": f"用户问题: {user_query}\n数据列: {cols_desc}\n数据行数: {len(df)}\n\n推荐图表类型:"}
                ],
                temperature=0.1,
                max_tokens=50,
            )
            chart_type = response.choices[0].message.content.strip().lower()
            # 验证返回值
            if chart_type in ['bar', 'line', 'pie', 'scatter', 'heatmap']:
                return chart_type
            return self._rule_based_chart_type(df, user_query)
        except Exception as e:
            print(f"⚠️ 图表推荐失败，使用规则判断: {e}")
            return self._rule_based_chart_type(df, user_query)

    def _rule_based_chart_type(self, df: pd.DataFrame, query: str) -> str:
        """根据规则判断图表类型"""
        query_lower = query.lower()
        cols = df.columns.tolist()
        n_rows = len(df)

        # 时间趋势 → 折线图
        if any(k in query_lower for k in ["趋势", "月度", "每月", "时间", "trend", "month"]):
            return "line"
        # 占比 → 饼图
        if any(k in query_lower for k in ["占比", "比例", "份额", "pie", "比例"]):
            return "pie"
        # 两列数值 → 散点图
        num_cols = df.select_dtypes(include=['number']).columns.tolist()
        if len(num_cols) >= 2 and n_rows > 3:
            return "bar"  # 默认柱状图，更清晰
        # 默认
        return "bar"

    def generate_chart(self, df: pd.DataFrame, chart_type: str, title: str, output_path: str) -> str:
        """
        生成图表并保存
        返回: 图表文件路径
        """
        plt.style.use('seaborn-v0_8')
        fig, ax = plt.subplots(figsize=(10, 6))

        try:
            if chart_type == "bar":
                self._plot_bar(df, ax, title)
            elif chart_type == "line":
                self._plot_line(df, ax, title)
            elif chart_type == "pie":
                self._plot_pie(df, ax, title)
            elif chart_type == "scatter":
                self._plot_scatter(df, ax, title)
            elif chart_type == "heatmap":
                self._plot_heatmap(df, ax, title)
            else:
                self._plot_bar(df, ax, title)  # 默认

            plt.tight_layout()
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            plt.close(fig)
            print(f"✅ 图表已生成: {output_path}")
            return output_path

        except Exception as e:
            print(f"❌ 图表生成失败: {e}")
            # 生成简化版图表
            fig2, ax2 = plt.subplots(figsize=(10, 6))
            self._plot_bar(df, ax2, title)
            plt.tight_layout()
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            plt.close(fig2)
            return output_path

    def _plot_bar(self, df, ax, title):
        """柱状图"""
        if len(df.columns) >= 2:
            x_col = df.columns[0]
            y_col = df.select_dtypes(include=['number']).columns[0] if df.select_dtypes(include=['number']).columns.any() else df.columns[1]
            data = df.head(10)  # 最多显示10条
            ax.bar(data[x_col].astype(str), data[y_col], color='steelblue')
            ax.set_xlabel(x_col)
            ax.set_ylabel(y_col)
            ax.tick_params(axis='x', rotation=45)
        else:
            ax.bar(range(len(df)), df.iloc[:, 0], color='steelblue')
        ax.set_title(title, fontsize=14, pad=15)

    def _plot_line(self, df, ax, title):
        """折线图"""
        x_col = df.columns[0]
        num_cols = df.select_dtypes(include=['number']).columns.tolist()
        y_col = num_cols[0] if num_cols else df.columns[1]

        # 按x轴排序
        df = df.sort_values(by=x_col)
        ax.plot(df[x_col].astype(str), df[y_col], marker='o', linewidth=2, color='steelblue')
        ax.set_xlabel(x_col)
        ax.set_ylabel(y_col)
        ax.tick_params(axis='x', rotation=45)
        ax.grid(True, alpha=0.3)
        ax.set_title(title, fontsize=14, pad=15)

    def _plot_pie(self, df, ax, title):
        """饼图"""
        label_col = df.columns[0]
        num_cols = df.select_dtypes(include=['number']).columns.tolist()
        value_col = num_cols[0] if num_cols else df.columns[1]

        data = df.head(8)  # 饼图最多8块
        ax.pie(data[value_col], labels=data[label_col], autopct='%1.1f%%', startangle=90)
        ax.set_title(title, fontsize=14, pad=15)
        ax.axis('equal')

    def _plot_scatter(self, df, ax, title):
        """散点图"""
        num_cols = df.select_dtypes(include=['number']).columns.tolist()
        if len(num_cols) >= 2:
            ax.scatter(df[num_cols[0]], df[num_cols[1]], alpha=0.6, color='steelblue')
            ax.set_xlabel(num_cols[0])
            ax.set_ylabel(num_cols[1])
        ax.set_title(title, fontsize=14, pad=15)

    def _plot_heatmap(self, df, ax, title):
        """热力图（需要透视表）"""
        num_cols = df.select_dtypes(include=['number']).columns.tolist()
        cat_cols = df.select_dtypes(include=['object']).columns.tolist()
        if len(cat_cols) >= 2 and len(num_cols) >= 1:
            pivot = df.pivot_table(values=num_cols[0], index=cat_cols[0], columns=cat_cols[1], aggfunc='sum', fill_value=0)
            sns.heatmap(pivot, annot=True, fmt='.0f', cmap='Blues', ax=ax)
        else:
            sns.heatmap(df.corr(numeric_only=True), annot=True, cmap='Blues', ax=ax)
        ax.set_title(title, fontsize=14, pad=15)

    def generate_all_charts(self, df: pd.DataFrame, user_query: str, query_id: str = "default") -> list:
        """
        智能生成多个图表（适合报告）
        返回: 图表文件路径列表
        """
        chart_paths = []

        # 图表1：主要对比（推荐类型）
        chart_type = self.recommend_chart(df, user_query)
        path1 = os.path.join(CHART_OUTPUT_DIR, f"{query_id}_main.png")
        self.generate_chart(df, chart_type, f"{user_query} - 主要分析", path1)
        chart_paths.append(path1)

        # 图表2：如果数据有多列数值，生成对比图
        num_cols = df.select_dtypes(include=['number']).columns.tolist()
        if len(num_cols) >= 2 and len(df) <= 20:
            # 横向对比柱状图
            fig, ax = plt.subplots(figsize=(10, 6))
            df_head = df.head(10)
            x = range(len(df_head))
            width = 0.35
            ax.bar([i - width/2 for i in x], df_head[num_cols[0]], width, label=num_cols[0], color='steelblue')
            if len(num_cols) > 1:
                ax.bar([i + width/2 for i in x], df_head[num_cols[1]], width, label=num_cols[1], color='orange')
            ax.set_xticks(x)
            ax.set_xticklabels(df_head.iloc[:, 0].astype(str), rotation=45, ha='right')
            ax.legend()
            ax.set_title(f"{user_query} - 多指标对比", fontsize=14, pad=15)
            plt.tight_layout()
            path2 = os.path.join(CHART_OUTPUT_DIR, f"{query_id}_compare.png")
            plt.savefig(path2, dpi=150, bbox_inches='tight')
            plt.close(fig)
            chart_paths.append(path2)

        return chart_paths
