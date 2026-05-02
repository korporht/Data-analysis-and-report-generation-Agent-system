"""
报告生成 Agent - 自动生成数据分析报告
支持 Markdown、HTML、Word 格式
"""

import os
import json
from datetime import datetime
from openai import OpenAI
import pandas as pd
from config import *

os.makedirs(REPORT_OUTPUT_DIR, exist_ok=True)


class ReportAgent:
    """报告生成Agent"""

    def __init__(self, api_key=None, base_url=None, model=None):
        self.api_key = api_key or OPENAI_API_KEY
        self.base_url = base_url or OPENAI_BASE_URL
        self.model = model or LLM_MODEL
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url) if self.api_key else None

    def generate_analysis_text(self, user_query: str, df: pd.DataFrame, sql: str) -> str:
        """用LLM生成数据解读文本"""
        if self.client is None:
            return self._rule_based_analysis(user_query, df)

        try:
            # 准备数据摘要
            data_summary = f"查询结果行数: {len(df)}\n"
            data_summary += f"列名: {', '.join(df.columns.tolist())}\n"
            data_summary += f"数据预览:\n{df.head(10).to_string()}\n"
            if len(df) > 10:
                data_summary += f"\n（共{len(df)}行，仅显示前10行）\n"
            # 添加统计信息
            num_cols = df.select_dtypes(include=['number']).columns.tolist()
            if num_cols:
                data_summary += f"\n数值列统计:\n{df[num_cols].describe().to_string()}\n"

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": QUERY_ANALYSIS_PROMPT},
                    {"role": "user", "content": f"用户问题: {user_query}\n\n{data_summary}"}
                ],
                temperature=0.3,
                max_tokens=1000,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"⚠️ LLM分析失败，使用规则分析: {e}")
            return self._rule_based_analysis(user_query, df)

    def _rule_based_analysis(self, user_query: str, df: pd.DataFrame) -> str:
        """规则式数据解读（降级方案）"""
        lines = ["## 关键发现\n"]
        num_cols = df.select_dtypes(include=['number']).columns.tolist()

        if len(num_cols) > 0:
            # 找出最大的数值列
            main_col = num_cols[0]
            total = df[main_col].sum()
            avg = df[main_col].mean()
            max_row = df.loc[df[main_col].idxmax()] if len(df) > 0 else None

            lines.append(f"- 总计: {total:,.0f} 元")
            lines.append(f"- 平均值: {avg:,.0f} 元")
            if max_row is not None:
                lines.append(f"- 最高值: {max_row.iloc[0] if len(max_row) > 0 else 'N/A'} -> {max_row[main_col]:,.0f} 元")

        lines.append(f"- 数据条数: {len(df)} 条")
        lines.append("")
        lines.append("## 数据解读")
        lines.append(f"根据查询条件「{user_query}」，共返回 {len(df)} 条数据。")
        if len(df) > 0:
            lines.append(f"主要统计维度包括: {', '.join(df.columns[:5].tolist())}。")
            lines.append("建议结合图表进一步分析数据趋势和异常值。")
        lines.append("")
        lines.append("## 建议")
        lines.append("- 建议对相关异常数据进行进一步核查")
        lines.append("- 可将结果按时间/地区等维度做深入对比分析")

        return "\n".join(lines)

    def generate_markdown_report(self, user_query: str, sql: str,
                                 df: pd.DataFrame, analysis: str,
                                 chart_paths: list, output_path: str) -> str:
        """生成Markdown格式报告"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        lines = []
        lines.append(f"# 数据分析报告")
        lines.append(f"")
        lines.append(f"**生成时间**: {now}  ")
        lines.append(f"**分析问题**: {user_query}  ")
        lines.append(f"**数据来源**: sales_data  ")
        lines.append(f"**数据条数**: {len(df)} 条  ")
        lines.append(f"")
        lines.append(f"---\n")
        lines.append(f"## 执行的SQL查询\n")
        lines.append(f"```sql\n{sql}\n```\n")
        lines.append(f"---\n")
        lines.append(f"## 数据解读\n")
        lines.append(analysis)
        lines.append(f"")
        lines.append(f"---\n")
        lines.append(f"## 原始数据\n")
        lines.append(df.head(20).to_markdown(index=False))
        lines.append(f"")
        lines.append(f"（共 {len(df)} 行，显示前 20 行）")
        lines.append(f"")
        lines.append(f"---\n")
        lines.append(f"## 图表\n")

        for i, chart_path in enumerate(chart_paths, 1):
            chart_name = os.path.basename(chart_path)
            lines.append(f"### 图表 {i}")
            lines.append(f"![图表{i}]({chart_path})")
            lines.append("")

        lines.append(f"---\n")
        lines.append(f"*报告由 WorkBuddy 数据分析Agent自动生成*")

        content = "\n".join(lines)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ Markdown报告已生成: {output_path}")
        return output_path

    def generate_html_report(self, user_query: str, sql: str,
                             df: pd.DataFrame, analysis: str,
                             chart_paths: list, output_path: str) -> str:
        """生成HTML格式报告（带样式，可直接分享）"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        # 将图表转为base64嵌入
        import base64
        chart_imgs = []
        for chart_path in chart_paths:
            try:
                with open(chart_path, 'rb') as f:
                    b64 = base64.b64encode(f.read()).decode()
                    chart_imgs.append(f"data:image/png;base64,{b64}")
            except:
                chart_imgs.append("")

        # 数据表格HTML
        table_html = df.head(50).to_html(index=False, classes='data-table')

        html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>数据分析报告</title>
    <style>
        body {{ font-family: 'Microsoft YaHei', Arial, sans-serif; margin: 40px; color: #333; }}
        h1 {{ color: #1a73e8; border-bottom: 2px solid #1a73e8; padding-bottom: 10px; }}
        h2 {{ color: #333; margin-top: 30px; }}
        .meta {{ background: #f5f5f5; padding: 15px; border-radius: 8px; margin: 20px 0; }}
        .meta span {{ margin-right: 30px; }}
        pre {{ background: #f0f0f0; padding: 15px; border-radius: 5px; overflow-x: auto; }}
        .chart {{ text-align: center; margin: 30px 0; }}
        .chart img {{ max-width: 100%; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        .data-table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        .data-table th {{ background: #1a73e8; color: white; padding: 10px; text-align: left; }}
        .data-table td {{ padding: 8px 10px; border-bottom: 1px solid #eee; }}
        .data-table tr:hover {{ background: #f5f5f5; }}
        .analysis {{ background: #fffde7; padding: 20px; border-left: 4px solid #fbc02d; margin: 20px 0; }}
        .footer {{ text-align: center; color: #999; margin-top: 50px; font-size: 12px; }}
    </style>
</head>
<body>
    <h1>📊 数据分析报告</h1>
    <div class="meta">
        <span><strong>生成时间:</strong> {now}</span>
        <span><strong>数据条数:</strong> {len(df)} 条</span>
    </div>
    <div class="meta">
        <strong>分析问题:</strong> {user_query}
    </div>

    <h2>📝 执行的SQL查询</h2>
    <pre>{sql}</pre>

    <h2>🔍 数据解读</h2>
    <div class="analysis">
{analysis.replace(chr(10), '<br>')}
    </div>

    <h2>📊 可视化图表</h2>
"""

        for i, img_data in enumerate(chart_imgs, 1):
            if img_data:
                html += f'    <div class="chart"><h3>图表 {i}</h3><img src="{img_data}"></div>\n'

        html += f"""
    <h2>📋 原始数据（前50行）</h2>
    {table_html}

    <div class="footer">
        * 本报告由 WorkBuddy 数据分析Agent自动生成 | {now} *
    </div>
</body>
</html>
"""

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"✅ HTML报告已生成: {output_path}")
        return output_path

    def generate_word_report(self, user_query: str, sql: str,
                             df: pd.DataFrame, analysis: str,
                             chart_paths: list, output_path: str) -> str:
        """生成Word格式报告"""
        try:
            from docx import Document
            from docx.shared import Inches, Pt, RGBColor
            from docx.enum.text import WD_ALIGN_PARAGRAPH
        except ImportError:
            print("⚠️ python-docx 未安装，跳过Word报告生成")
            print("   请运行: pip install python-docx")
            return None

        doc = Document()

        # 标题
        title = doc.add_heading('数据分析报告', 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER

        # 元信息
        doc.add_paragraph(f'生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M")}')
        doc.add_paragraph(f'分析问题: {user_query}')
        doc.add_paragraph(f'数据条数: {len(df)} 条')

        doc.add_heading('执行的SQL查询', 2)
        doc.add_paragraph(sql, style='Intense Quote')

        doc.add_heading('数据解读', 2)
        # 将analysis按行分割添加
        for line in analysis.split('\n'):
            if line.strip():
                doc.add_paragraph(line)

        # 添加图表
        doc.add_heading('可视化图表', 2)
        for chart_path in chart_paths:
            try:
                doc.add_picture(chart_path, width=Inches(5.5))
            except Exception as e:
                doc.add_paragraph(f"[图表: {os.path.basename(chart_path)}]")

        # 添加数据表（前20行）
        doc.add_heading('原始数据（前20行）', 2)
        table = doc.add_table(rows=min(21, len(df)+1), cols=len(df.columns))
        table.style = 'Light Grid Accent 1'
        # 表头
        for i, col in enumerate(df.columns):
            table.rows[0].cells[i].text = col
        # 数据
        for r in range(min(20, len(df))):
            for c, col in enumerate(df.columns):
                table.rows[r+1].cells[c].text = str(df.iloc[r][col])

        doc.add_paragraph('\n*报告由 WorkBuddy 数据分析Agent自动生成*')

        doc.save(output_path)
        print(f"✅ Word报告已生成: {output_path}")
        return output_path
