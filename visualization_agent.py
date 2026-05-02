"""
可视化 Agent - 数据图表生成
解决痛点: 不知道用什么图表 → 自动推荐并生成
"""

import os
import warnings
import matplotlib
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from openai import OpenAI
from config import *

# 忽略 matplotlib 中文字体缺失警告（不影响显示）
warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib')
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False

os.makedirs(CHART_OUTPUT_DIR, exist_ok=True)

# 中国市场配色：红涨绿跌
COLORS_PRIMARY = ['#E53935', '#1E88E5', '#43A047', '#FB8C00', '#8E24AA', '#00ACC1', '#FFB300', '#5E35B1']
COLORS_WARM = ['#E53935', '#FF7043', '#FFA726', '#FFCA28', '#66BB6A', '#42A5F5']


class VisualizationAgent:
    """数据可视化Agent - 自动推荐图表类型并生成高质量图表"""

    def __init__(self, api_key=None, base_url=None, model=None):
        self.api_key = api_key or OPENAI_API_KEY
        self.base_url = base_url or OPENAI_BASE_URL
        self.model = model or LLM_MODEL
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url) if self.api_key else None

    def recommend_chart(self, df: pd.DataFrame, user_query: str, intent: dict = None) -> str:
        """
        根据数据特征、用户问题和意图推荐图表类型
        长链推理：利用上一步的意图信息做出更准确的图表推荐
        """
        if self.client is None:
            return self._rule_based_chart_type(df, user_query, intent)

        try:
            cols_desc = ", ".join([f"{col}({str(dtype)})" for col, dtype in zip(df.columns, df.dtypes)])
            intent_info = ""
            if intent:
                intent_info = f"\n分析类型: {intent.get('analysis_type', '')}"

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": VISUALIZATION_PROMPT},
                    {"role": "user", "content": f"用户问题: {user_query}\n数据列: {cols_desc}\n数据行数: {len(df)}{intent_info}\n\n推荐图表类型:"}
                ],
                temperature=0.1,
                max_tokens=50,
            )
            chart_type = response.choices[0].message.content.strip().lower()
            valid_types = ['bar', 'grouped_bar', 'line', 'pie', 'scatter', 'heatmap']
            return chart_type if chart_type in valid_types else self._rule_based_chart_type(df, user_query, intent)
        except Exception as e:
            return self._rule_based_chart_type(df, user_query, intent)

    def _rule_based_chart_type(self, df: pd.DataFrame, query: str, intent: dict = None) -> str:
        """规则判断图表类型"""
        analysis_type = intent.get('analysis_type', '') if intent else ''
        num_cols = df.select_dtypes(include=['number']).columns.tolist()

        # 意图驱动
        if analysis_type == '趋势分析':
            return "line"
        if analysis_type == '占比分析':
            return "pie"
        if analysis_type == '对比分析' and len(num_cols) >= 2:
            return "grouped_bar"

        # 关键词驱动
        if any(k in query.lower() for k in ["趋势", "月度", "每月", "变化", "增长"]):
            return "line"
        if any(k in query.lower() for k in ["占比", "比例", "份额", "分布"]):
            return "pie"

        return "bar"

    def generate_chart(self, df: pd.DataFrame, chart_type: str, title: str, output_path: str) -> str:
        """生成图表"""
        plt.style.use('seaborn-v0_8-whitegrid')
        fig, ax = plt.subplots(figsize=(11, 6.5))

        try:
            if chart_type == "bar":
                self._plot_bar(df, ax, title)
            elif chart_type == "grouped_bar":
                self._plot_grouped_bar(df, ax, title)
            elif chart_type == "line":
                self._plot_line(df, ax, title)
            elif chart_type == "pie":
                self._plot_pie(df, ax, title)
            elif chart_type == "scatter":
                self._plot_scatter(df, ax, title)
            elif chart_type == "heatmap":
                self._plot_heatmap(df, ax, title)
            else:
                self._plot_bar(df, ax, title)

            plt.tight_layout()
            plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
            plt.close(fig)
            print(f"✅ 图表已生成: {output_path}")
            return output_path
        except Exception as e:
            print(f"❌ 图表生成失败: {e}")
            plt.close(fig)
            # 降级：简单柱状图
            fig2, ax2 = plt.subplots(figsize=(10, 6))
            self._plot_bar(df, ax2, title)
            plt.tight_layout()
            plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
            plt.close(fig2)
            return output_path

    def _plot_bar(self, df, ax, title):
        """柱状图 - 带数值标签"""
        if len(df.columns) >= 2:
            x_col = df.columns[0]
            num_cols = df.select_dtypes(include=['number']).columns.tolist()
            y_col = num_cols[0] if num_cols else df.columns[1]
            data = df.head(12)
            bars = ax.bar(data[x_col].astype(str), data[y_col], color=COLORS_PRIMARY[:len(data)], edgecolor='white', linewidth=0.5)
            # 数值标签
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height, f'{height:,.0f}',
                       ha='center', va='bottom', fontsize=9, fontweight='bold')
            ax.set_xlabel(x_col, fontsize=11)
            ax.set_ylabel(y_col, fontsize=11)
            ax.tick_params(axis='x', rotation=30, labelsize=9)
            ax.tick_params(axis='y', labelsize=9)
            # 千分位格式
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:,.0f}'))
        ax.set_title(title, fontsize=14, pad=15, fontweight='bold')

    def _plot_grouped_bar(self, df, ax, title):
        """分组柱状图 - 多指标对比"""
        num_cols = df.select_dtypes(include=['number']).columns.tolist()
        x_col = df.columns[0]
        data = df.head(12)
        x = np.arange(len(data))
        width = 0.35

        for i, col in enumerate(num_cols[:3]):
            offset = (i - len(num_cols[:3])/2 + 0.5) * width
            bars = ax.bar(x + offset, data[col], width, label=col, color=COLORS_PRIMARY[i], edgecolor='white')
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height, f'{height:,.0f}',
                       ha='center', va='bottom', fontsize=7, fontweight='bold')

        ax.set_xticks(x)
        ax.set_xticklabels(data[x_col].astype(str), rotation=30, ha='right', fontsize=9)
        ax.legend(fontsize=10)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:,.0f}'))
        ax.set_title(title, fontsize=14, pad=15, fontweight='bold')

    def _plot_line(self, df, ax, title):
        """折线图 - 带数据点和标注"""
        x_col = df.columns[0]
        num_cols = df.select_dtypes(include=['number']).columns.tolist()
        y_col = num_cols[0] if num_cols else df.columns[1]

        df_sorted = df.sort_values(by=x_col)
        ax.plot(df_sorted[x_col].astype(str), df_sorted[y_col], marker='o', linewidth=2.5,
                color=COLORS_PRIMARY[0], markersize=7, markerfacecolor='white', markeredgewidth=2)

        # 标注最大最小值
        max_idx = df_sorted[y_col].idxmax()
        min_idx = df_sorted[y_col].idxmin()
        ax.annotate(f'最高: {df_sorted.loc[max_idx, y_col]:,.0f}',
                    xy=(df_sorted.loc[max_idx, x_col], df_sorted.loc[max_idx, y_col]),
                    xytext=(10, 15), textcoords='offset points', fontsize=9,
                    arrowprops=dict(arrowstyle='->', color=COLORS_PRIMARY[0]),
                    color=COLORS_PRIMARY[0], fontweight='bold')
        ax.annotate(f'最低: {df_sorted.loc[min_idx, y_col]:,.0f}',
                    xy=(df_sorted.loc[min_idx, x_col], df_sorted.loc[min_idx, y_col]),
                    xytext=(10, -20), textcoords='offset points', fontsize=9,
                    arrowprops=dict(arrowstyle='->', color=COLORS_PRIMARY[2]),
                    color=COLORS_PRIMARY[2], fontweight='bold')

        ax.set_xlabel(x_col, fontsize=11)
        ax.set_ylabel(y_col, fontsize=11)
        ax.tick_params(axis='x', rotation=30, labelsize=9)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:,.0f}'))
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.set_title(title, fontsize=14, pad=15, fontweight='bold')

        # 填充区域
        ax.fill_between(range(len(df_sorted)), df_sorted[y_col], alpha=0.1, color=COLORS_PRIMARY[0])

    def _plot_pie(self, df, ax, title):
        """饼图 - 带百分比和突出"""
        label_col = df.columns[0]
        num_cols = df.select_dtypes(include=['number']).columns.tolist()
        value_col = num_cols[0] if num_cols else df.columns[1]
        data = df.head(8)

        # 突出最大块
        explode = [0.05] * len(data)
        max_idx = data[value_col].idxmax()
        max_pos = data.index.get_loc(max_idx)
        explode[max_pos] = 0.12

        wedges, texts, autotexts = ax.pie(
            data[value_col], labels=data[label_col], autopct='%1.1f%%',
            startangle=90, colors=COLORS_PRIMARY[:len(data)],
            explode=explode, shadow=True, pctdistance=0.8
        )
        for text in autotexts:
            text.set_fontsize(10)
            text.set_fontweight('bold')
        ax.set_title(title, fontsize=14, pad=15, fontweight='bold')

    def _plot_scatter(self, df, ax, title):
        """散点图"""
        num_cols = df.select_dtypes(include=['number']).columns.tolist()
        if len(num_cols) >= 2:
            ax.scatter(df[num_cols[0]], df[num_cols[1]], alpha=0.7, color=COLORS_PRIMARY[0],
                      s=80, edgecolors='white', linewidth=0.5)
            # 趋势线
            z = np.polyfit(df[num_cols[0]], df[num_cols[1]], 1)
            p = np.poly1d(z)
            x_line = np.linspace(df[num_cols[0]].min(), df[num_cols[0]].max(), 100)
            ax.plot(x_line, p(x_line), '--', color=COLORS_PRIMARY[1], alpha=0.8, linewidth=2)
            ax.set_xlabel(num_cols[0], fontsize=11)
            ax.set_ylabel(num_cols[1], fontsize=11)
        ax.set_title(title, fontsize=14, pad=15, fontweight='bold')

    def _plot_heatmap(self, df, ax, title):
        """热力图"""
        num_cols = df.select_dtypes(include=['number']).columns.tolist()
        cat_cols = df.select_dtypes(include=['object']).columns.tolist()
        if len(cat_cols) >= 2 and len(num_cols) >= 1:
            pivot = df.pivot_table(values=num_cols[0], index=cat_cols[0], columns=cat_cols[1], aggfunc='sum', fill_value=0)
            sns.heatmap(pivot, annot=True, fmt='.0f', cmap='YlOrRd', ax=ax, linewidths=1)
        else:
            corr = df.select_dtypes(include=['number']).corr()
            sns.heatmap(corr, annot=True, cmap='RdBu_r', center=0, ax=ax, linewidths=1)
        ax.set_title(title, fontsize=14, pad=15, fontweight='bold')

    def generate_all_charts(self, df: pd.DataFrame, user_query: str, intent: dict = None, query_id: str = "default") -> list:
        """
        智能生成多张图表
        长链推理：基于意图和数据特征，决定生成哪些图表
        """
        chart_paths = []

        # 图表1: 主分析图
        chart_type = self.recommend_chart(df, user_query, intent)
        path1 = os.path.join(CHART_OUTPUT_DIR, f"{query_id}_main.png")
        self.generate_chart(df, chart_type, f"{user_query}", path1)
        chart_paths.append(path1)

        # 图表2: 辅助对比图（如果数据适合）
        num_cols = df.select_dtypes(include=['number']).columns.tolist()
        cat_cols = df.select_dtypes(include=['object']).columns.tolist()

        if len(num_cols) >= 2 and len(df) <= 20:
            fig, ax = plt.subplots(figsize=(11, 6.5))
            data = df.head(12)
            x = np.arange(len(data))
            width = 0.35
            for i, col in enumerate(num_cols[:2]):
                offset = (i - 0.5) * width
                ax.bar(x + offset, data[col], width, label=col, color=COLORS_PRIMARY[i], edgecolor='white')
            ax.set_xticks(x)
            ax.set_xticklabels(data.iloc[:, 0].astype(str), rotation=30, ha='right', fontsize=9)
            ax.legend(fontsize=10)
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:,.0f}'))
            ax.set_title(f"{user_query} — 多指标对比", fontsize=14, pad=15, fontweight='bold')
            plt.tight_layout()
            path2 = os.path.join(CHART_OUTPUT_DIR, f"{query_id}_compare.png")
            plt.savefig(path2, dpi=150, bbox_inches='tight', facecolor='white')
            plt.close(fig)
            chart_paths.append(path2)

        # 图表3: 趋势图（如果主图不是折线图，但数据有时间维度）
        if chart_type != "line" and len(df) > 3 and len(num_cols) >= 1:
            # 检查是否有时间特征
            first_col = df.columns[0]
            if any(k in str(first_col).lower() for k in ['date', 'month', 'year', '时间', '月份', '日期']):
                fig, ax = plt.subplots(figsize=(11, 6.5))
                self._plot_line(df, ax, f"{user_query} — 趋势变化")
                plt.tight_layout()
                path3 = os.path.join(CHART_OUTPUT_DIR, f"{query_id}_trend.png")
                plt.savefig(path3, dpi=150, bbox_inches='tight', facecolor='white')
                plt.close(fig)
                chart_paths.append(path3)

        return chart_paths
