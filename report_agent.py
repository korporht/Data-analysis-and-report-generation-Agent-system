"""
报告生成 Agent - 自动生成数据分析报告
解决痛点: 报告制作耗时长、格式不统一 → 一键生成专业报告
"""

import os
import base64
import warnings
from datetime import datetime
from openai import OpenAI
import pandas as pd
from config import *

# 忽略 matplotlib 字体警告
warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib')

os.makedirs(REPORT_OUTPUT_DIR, exist_ok=True)


class ReportAgent:
    """报告生成Agent - 长链推理的最后环节，整合所有Agent输出"""

    def __init__(self, api_key=None, base_url=None, model=None):
        self.api_key = api_key or OPENAI_API_KEY
        self.base_url = base_url or OPENAI_BASE_URL
        self.model = model or LLM_MODEL
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url) if self.api_key else None

    def generate_analysis_text(self, user_query: str, df: pd.DataFrame, sql: str, intent: dict = None) -> str:
        """
        生成数据解读文本
        长链推理：利用意图信息 + 查询结果 + SQL，生成更有针对性的分析
        """
        if self.client is None:
            return self._rule_based_analysis(user_query, df, intent)

        try:
            # 准备数据摘要
            data_summary = f"查询结果行数: {len(df)}\n"
            data_summary += f"列名: {', '.join(df.columns.tolist())}\n"
            data_summary += f"数据预览:\n{df.head(10).to_string()}\n"
            if len(df) > 10:
                data_summary += f"\n（共{len(df)}行，仅显示前10行）\n"
            num_cols = df.select_dtypes(include=['number']).columns.tolist()
            if num_cols:
                data_summary += f"\n数值列统计:\n{df[num_cols].describe().to_string()}\n"

            intent_info = ""
            if intent:
                intent_info = f"\n分析意图: {intent.get('analysis_type', '')} | 维度: {intent.get('dimensions', [])} | 时间: {intent.get('time_scope', '')}"

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": QUERY_ANALYSIS_PROMPT},
                    {"role": "user", "content": f"用户问题: {user_query}\n{intent_info}\n\n{data_summary}"}
                ],
                temperature=0.3,
                max_tokens=1200,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"⚠️ LLM分析失败，使用规则分析: {e}")
            return self._rule_based_analysis(user_query, df, intent)

    def _rule_based_analysis(self, user_query: str, df: pd.DataFrame, intent: dict = None) -> str:
        """规则式数据解读（降级方案）"""
        lines = []
        lines.append("## 🔑 关键发现\n")
        num_cols = df.select_dtypes(include=['number']).columns.tolist()

        if len(num_cols) > 0:
            main_col = num_cols[0]
            total = df[main_col].sum()
            avg = df[main_col].mean()
            max_row = df.loc[df[main_col].idxmax()] if len(df) > 0 else None
            min_row = df.loc[df[main_col].idxmin()] if len(df) > 0 else None

            lines.append(f"- 总计: **{total:,.0f} 元**")
            lines.append(f"- 平均值: **{avg:,.0f} 元**")
            if max_row is not None:
                lines.append(f"- 最高: {max_row.iloc[0]} → **{max_row[main_col]:,.0f} 元**")
            if min_row is not None and len(df) > 1:
                lines.append(f"- 最低: {min_row.iloc[0]} → **{min_row[main_col]:,.0f} 元**")

            # 排名差异分析
            if len(df) > 1:
                max_val = df[main_col].max()
                min_val = df[main_col].min()
                if min_val > 0:
                    ratio = max_val / min_val
                    lines.append(f"- 最大值是最小值的 **{ratio:.1f} 倍**")

        lines.append(f"- 数据条数: {len(df)} 条")
        lines.append("")

        lines.append("## 📈 趋势与异常\n")
        lines.append(f"根据查询「{user_query}」，共返回 {len(df)} 条数据。")
        if len(df) > 0 and len(num_cols) > 0:
            main_col = num_cols[0]
            if len(df) > 2:
                top3 = df.nlargest(3, main_col)
                lines.append(f"\n排名前3: {', '.join([f'{row.iloc[0]}({row[main_col]:,.0f})' for _, row in top3.iterrows()])}")
        lines.append("")

        lines.append("## 💡 行动建议\n")
        lines.append("- 建议对数据差异较大的维度进行深入归因分析")
        lines.append("- 可结合时间维度观察趋势变化，判断是否为季节性波动")
        lines.append("")

        lines.append("## ⚠️ 数据局限\n")
        lines.append("- 本次分析基于当前查询结果，可能未覆盖全部相关数据")
        lines.append("- 建议结合业务上下文综合判断，避免仅依赖单一维度得出结论")

        return "\n".join(lines)

    def generate_markdown_report(self, user_query: str, sql: str,
                                 df: pd.DataFrame, analysis: str,
                                 chart_paths: list, output_path: str,
                                 intent: dict = None, reasoning_chain: list = None) -> str:
        """生成Markdown格式报告（含推理链）"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        lines = []
        lines.append("# 📊 数据分析报告\n")
        lines.append(f"**生成时间**: {now}  ")
        lines.append(f"**分析问题**: {user_query}  ")
        if intent:
            lines.append(f"**分析类型**: {intent.get('analysis_type', '')}  ")
            lines.append(f"**分析维度**: {', '.join(intent.get('dimensions', []))}  ")
            lines.append(f"**时间范围**: {intent.get('time_scope', '')}  ")
        lines.append(f"**数据条数**: {len(df)} 条  ")
        lines.append("")

        # 推理链（展示长链推理过程）
        if reasoning_chain:
            lines.append("---\n")
            lines.append("## 🧠 推理链（Agent协作过程）\n")
            for step in reasoning_chain:
                icon = step.get('icon', '→')
                agent = step.get('agent', '')
                action = step.get('action', '')
                result = step.get('result', '')
                lines.append(f"**{icon} {agent}**: {action}")
                if result:
                    lines.append(f"> {result}")
                lines.append("")
            lines.append("---\n")

        lines.append("## 📝 SQL查询\n")
        lines.append(f"```sql\n{sql}\n```\n")
        lines.append("---\n")
        lines.append("## 🔍 数据解读\n")
        lines.append(analysis)
        lines.append("")
        lines.append("---\n")
        lines.append("## 📊 图表\n")
        for i, chart_path in enumerate(chart_paths, 1):
            lines.append(f"### 图表 {i}")
            lines.append(f"![图表{i}]({chart_path})")
            lines.append("")
        lines.append("---\n")
        lines.append("## 📋 原始数据\n")
        lines.append(df.head(20).to_markdown(index=False))
        lines.append(f"\n（共 {len(df)} 行，显示前 20 行）")
        lines.append(f"\n---\n*报告由数据分析Agent系统自动生成 | {now}*")

        content = "\n".join(lines)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ Markdown报告已生成: {output_path}")
        return output_path

    def generate_html_report(self, user_query: str, sql: str,
                             df: pd.DataFrame, analysis: str,
                             chart_paths: list, output_path: str,
                             intent: dict = None, reasoning_chain: list = None) -> str:
        """生成HTML格式报告（精美，可直接分享）"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        # 图表转base64
        chart_imgs = []
        for chart_path in chart_paths:
            try:
                with open(chart_path, 'rb') as f:
                    b64 = base64.b64encode(f.read()).decode()
                    chart_imgs.append(f"data:image/png;base64,{b64}")
            except:
                chart_imgs.append("")

        table_html = df.head(50).to_html(index=False, classes='data-table')

        # 推理链HTML
        reasoning_html = ""
        if reasoning_chain:
            reasoning_html = '<h2>🧠 推理链（Agent协作过程）</h2><div class="reasoning-chain">'
            for step in reasoning_chain:
                icon = step.get('icon', '→')
                agent = step.get('agent', '')
                action = step.get('action', '')
                result = step.get('result', '')
                reasoning_html += f'''
                <div class="reasoning-step">
                    <div class="step-header"><span class="step-icon">{icon}</span> <strong>{agent}</strong>: {action}</div>
                    <div class="step-result">{result}</div>
                </div>'''
            reasoning_html += '</div>'

        intent_html = ""
        if intent:
            intent_html = f'''
            <div class="meta">
                <span><strong>分析类型:</strong> {intent.get('analysis_type', '')}</span>
                <span><strong>维度:</strong> {', '.join(intent.get('dimensions', []))}</span>
                <span><strong>时间:</strong> {intent.get('time_scope', '')}</span>
            </div>'''

        chart_section = ""
        for i, img_data in enumerate(chart_imgs, 1):
            if img_data:
                chart_section += f'<div class="chart"><h3>图表 {i}</h3><img src="{img_data}"></div>\n'

        html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>数据分析报告 - {user_query}</title>
    <style>
        * {{ box-sizing: border-box; }}
        body {{ font-family: 'Microsoft YaHei', -apple-system, Arial, sans-serif; margin: 0; padding: 40px; color: #333; background: #fafafa; }}
        .container {{ max-width: 1000px; margin: 0 auto; background: white; padding: 40px 50px; border-radius: 12px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); }}
        h1 {{ color: #1a73e8; border-bottom: 3px solid #1a73e8; padding-bottom: 12px; font-size: 24px; }}
        h2 {{ color: #333; margin-top: 35px; font-size: 18px; border-left: 4px solid #1a73e8; padding-left: 12px; }}
        .meta {{ background: #f0f4ff; padding: 15px 20px; border-radius: 8px; margin: 12px 0; }}
        .meta span {{ margin-right: 25px; }}
        pre {{ background: #f5f5f5; padding: 18px; border-radius: 8px; overflow-x: auto; font-size: 13px; border: 1px solid #e0e0e0; }}
        .chart {{ text-align: center; margin: 30px 0; }}
        .chart img {{ max-width: 100%; border-radius: 8px; box-shadow: 0 2px 12px rgba(0,0,0,0.1); }}
        .chart h3 {{ color: #555; margin-bottom: 10px; }}
        .data-table {{ border-collapse: collapse; width: 100%; margin: 20px 0; font-size: 13px; }}
        .data-table th {{ background: #1a73e8; color: white; padding: 10px 14px; text-align: left; }}
        .data-table td {{ padding: 8px 14px; border-bottom: 1px solid #eee; }}
        .data-table tr:hover {{ background: #f5f5f5; }}
        .analysis {{ background: #fffde7; padding: 24px; border-left: 4px solid #fbc02d; margin: 20px 0; border-radius: 0 8px 8px 0; line-height: 1.8; }}
        .reasoning-chain {{ margin: 20px 0; }}
        .reasoning-step {{ background: #f0f4ff; padding: 12px 18px; border-radius: 8px; margin: 8px 0; border-left: 3px solid #1a73e8; }}
        .step-header {{ font-size: 14px; margin-bottom: 4px; }}
        .step-icon {{ font-size: 16px; }}
        .step-result {{ color: #666; font-size: 13px; padding-left: 20px; border-left: 2px solid #e0e0e0; margin-top: 6px; padding-top: 4px; }}
        .footer {{ text-align: center; color: #999; margin-top: 50px; font-size: 12px; padding-top: 20px; border-top: 1px solid #eee; }}
        .pain-point {{ background: #fff3e0; padding: 16px 20px; border-radius: 8px; margin: 15px 0; border-left: 4px solid #ff9800; }}
    </style>
</head>
<body>
<div class="container">
    <h1>📊 数据分析报告</h1>
    <div class="meta">
        <span><strong>生成时间:</strong> {now}</span>
        <span><strong>数据条数:</strong> {len(df)} 条</span>
    </div>
    <div class="meta">
        <strong>分析问题:</strong> {user_query}
    </div>
    {intent_html}

    {reasoning_html}

    <h2>📝 SQL查询语句</h2>
    <pre>{sql}</pre>

    <h2>🔍 数据解读</h2>
    <div class="analysis">
{analysis.replace(chr(10), '<br>')}
    </div>

    <h2>📊 可视化图表</h2>
    {chart_section}

    <h2>📋 原始数据</h2>
    {table_html}

    <div class="footer">
        * 本报告由数据分析Agent系统自动生成 | 多Agent协作 · 长链推理 · {now} *
    </div>
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
                             chart_paths: list, output_path: str,
                             intent: dict = None, reasoning_chain: list = None) -> str:
        """生成Word格式报告"""
        try:
            from docx import Document
            from docx.shared import Inches, Pt, RGBColor
            from docx.enum.text import WD_ALIGN_PARAGRAPH
        except ImportError:
            print("⚠️ python-docx 未安装，跳过Word报告")
            return None

        doc = Document()

        title = doc.add_heading('📊 数据分析报告', 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER

        doc.add_paragraph(f'生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M")}')
        doc.add_paragraph(f'分析问题: {user_query}')
        if intent:
            doc.add_paragraph(f'分析类型: {intent.get("analysis_type", "")} | 维度: {", ".join(intent.get("dimensions", []))}')
        doc.add_paragraph(f'数据条数: {len(df)} 条')

        # 推理链
        if reasoning_chain:
            doc.add_heading('🧠 推理链（Agent协作过程）', 2)
            for step in reasoning_chain:
                agent = step.get('agent', '')
                action = step.get('action', '')
                result = step.get('result', '')
                p = doc.add_paragraph()
                p.add_run(f'{step.get("icon", "→")} {agent}: ').bold = True
                p.add_run(action)
                if result:
                    doc.add_paragraph(f'  → {result}', style='List Bullet')

        doc.add_heading('SQL查询', 2)
        doc.add_paragraph(sql, style='Intense Quote')

        doc.add_heading('数据解读', 2)
        for line in analysis.split('\n'):
            if line.strip():
                doc.add_paragraph(line)

        doc.add_heading('可视化图表', 2)
        for chart_path in chart_paths:
            try:
                doc.add_picture(chart_path, width=Inches(5.5))
            except:
                doc.add_paragraph(f"[图表: {os.path.basename(chart_path)}]")

        doc.add_heading('原始数据（前20行）', 2)
        table = doc.add_table(rows=min(21, len(df)+1), cols=len(df.columns))
        table.style = 'Light Grid Accent 1'
        for i, col in enumerate(df.columns):
            table.rows[0].cells[i].text = col
        for r in range(min(20, len(df))):
            for c, col in enumerate(df.columns):
                table.rows[r+1].cells[c].text = str(df.iloc[r][col])

        doc.add_paragraph('\n*报告由数据分析Agent系统自动生成*')
        doc.save(output_path)
        print(f"✅ Word报告已生成: {output_path}")
        return output_path
