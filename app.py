"""
Streamlit Web 界面 - 数据分析Agent系统 v2
运行: streamlit run app.py
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import os

from nl2sql_agent import IntentUnderstandingAgent, NL2SQLAgent, SQLValidationAgent, DataQueryAgent
from visualization_agent import VisualizationAgent
from report_agent import ReportAgent
from config import *

st.set_page_config(
    page_title="数据分析Agent系统",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

@st.cache_resource
def init_agents():
    intent = IntentUnderstandingAgent()
    nl2sql = NL2SQLAgent()
    validation = SQLValidationAgent()
    query = DataQueryAgent()
    viz = VisualizationAgent()
    report = ReportAgent()
    if not USE_CSV_MODE:
        query.init_db()
    return intent, nl2sql, validation, query, viz, report


def main():
    st.title("📊 数据分析Agent系统")
    st.caption("长链推理 · 多Agent协作 · 一句话生成完整分析报告")

    # 痛点展示
    with st.sidebar:
        st.header("🎯 解决的痛点")
        pain_points = [
            ("🤷 需求模糊", "意图理解Agent自动拆解"),
            ("📝 不会SQL", "NL2SQL Agent自动生成"),
            ("⚠️ SQL出错", "校验Agent自检测+修复"),
            ("🤔 有数据看不懂", "解读Agent提炼洞察"),
            ("📈 不会做图表", "可视化Agent智能推荐"),
            ("📄 报告耗时", "一键生成多格式报告"),
        ]
        for title, desc in pain_points:
            st.caption(f"**{title}** → {desc}")

        st.divider()
        st.header("📁 数据预览")
        try:
            df_preview = pd.read_csv(CSV_PATH)
            st.success(f"✅ 数据加载成功")
            st.metric("总记录数", len(df_preview))
            st.metric("销售总额", f"¥{df_preview['Sales_Amount'].sum():,.0f}")
            if st.checkbox("预览原始数据"):
                st.dataframe(df_preview.head(10), use_container_width=True)
        except Exception as e:
            st.error(f"数据加载失败: {e}")

        st.divider()
        st.caption("💡 示例问题")
        examples = [
            "2024年各地区的销售总额是多少",
            "对比分析各销售代表的业绩",
            "各产品类别的月度销售趋势",
            "企业客户和个体客户的销售额对比",
            "折扣对销售金额的影响分析",
        ]
        for ex in examples:
            if st.button(f"💬 {ex}", use_container_width=True, key=ex):
                st.session_state['user_query'] = ex

    # 初始化Agent
    intent_agent, nl2sql_agent, validation_agent, query_agent, viz_agent, report_agent = init_agents()

    tab1, tab2, tab3 = st.tabs(["🔍 智能分析", "🧠 推理链展示", "📄 批量报告"])

    with tab1:
        user_query = st.text_input(
            "用自然语言描述分析需求：",
            value=st.session_state.get('user_query', ''),
            placeholder="例如：2024年各地区的销售总额是多少",
            label_visibility="collapsed"
        )

        col1, col2, col3 = st.columns([1, 1, 4])
        with col1:
            analyze_btn = st.button("🚀 开始分析", type="primary", use_container_width=True)
        with col2:
            if st.button("🗑️ 清空", use_container_width=True):
                st.session_state['user_query'] = ''
                st.rerun()

        if analyze_btn and user_query:
            with st.spinner("🤖 6个Agent协作推理中..."):

                # Step 1: 意图理解
                st.info("🧠 Step 1/6: 意图理解Agent — 拆解分析意图...")
                intent = intent_agent.understand(user_query)
                col_a, col_b, col_c = st.columns(3)
                col_a.metric("分析类型", intent.get('analysis_type', ''))
                col_b.metric("分析维度", ', '.join(intent.get('dimensions', [])))
                col_c.metric("时间范围", intent.get('time_scope', ''))

                # Step 2: NL2SQL
                st.info("📝 Step 2/6: NL2SQL Agent — 生成SQL...")
                sql = nl2sql_agent.generate_sql(user_query, intent=intent)
                st.code(sql, language="sql")

                # Step 3: SQL校验
                st.info("🔍 Step 3/6: SQL校验Agent — 检测+修复...")
                schema_info = query_agent.get_schema()
                fixed, validated_sql, validation_logs = validation_agent.validate_and_fix(sql, schema_info)
                if fixed:
                    st.warning(f"🔧 SQL已自动修复")
                    st.code(validated_sql, language="sql")
                    sql = validated_sql
                else:
                    st.success("✅ SQL校验通过")
                for log in validation_logs:
                    st.caption(log)

                # Step 4: 查询
                st.info("📊 Step 4/6: 数据查询Agent — 执行查询...")
                success, data = query_agent.execute_sql(sql)
                if not success:
                    st.error(f"查询失败: {data}")
                    st.stop()
                st.success(f"✅ 返回 {len(data)} 条数据")

                with st.expander("📋 查看查询结果", expanded=True):
                    st.dataframe(data, use_container_width=True, hide_index=True)

                # Step 5: 解读
                st.info("💡 Step 5/6: 数据解读Agent — 提炼洞察...")
                analysis = report_agent.generate_analysis_text(user_query, data, sql, intent=intent)
                st.markdown("### 📝 数据解读")
                st.markdown(analysis)

                # Step 6: 可视化
                st.info("📈 Step 6/6: 可视化Agent — 生成图表...")
                os.makedirs(CHART_OUTPUT_DIR, exist_ok=True)
                query_id = datetime.now().strftime("%Y%m%d_%H%M%S")
                chart_paths = viz_agent.generate_all_charts(data, user_query, intent=intent, query_id=query_id)

                st.markdown("### 📊 可视化图表")
                for i, chart_path in enumerate(chart_paths):
                    st.image(chart_path, caption=f"图表 {i+1}", use_container_width=True)

                # 下载报告
                st.divider()
                col_x, col_y, col_z = st.columns(3)
                os.makedirs(REPORT_OUTPUT_DIR, exist_ok=True)

                # 构建推理链
                reasoning_chain = [
                    {'icon': '🧠', 'agent': '意图理解Agent', 'action': f'解析「{user_query}」', 'result': f'类型={intent.get("analysis_type", "")}'},
                    {'icon': '📝', 'agent': 'NL2SQL Agent', 'action': '基于意图生成SQL', 'result': sql[:80]},
                    {'icon': '🔍', 'agent': 'SQL校验Agent', 'action': '检测SQL正确性', 'result': '已修复' if fixed else '通过'},
                    {'icon': '📊', 'agent': '数据查询Agent', 'action': '执行查询', 'result': f'{len(data)}条数据'},
                    {'icon': '💡', 'agent': '数据解读Agent', 'action': '提炼洞察', 'result': f'{len(analysis)}字'},
                    {'icon': '📈', 'agent': '可视化Agent', 'action': '生成图表', 'result': f'{len(chart_paths)}张'},
                ]

                with col_x:
                    if st.button("📄 Markdown", key="md"):
                        path = os.path.join(REPORT_OUTPUT_DIR, f"report_{query_id}.md")
                        report_agent.generate_markdown_report(user_query, sql, data, analysis, chart_paths, path, intent=intent, reasoning_chain=reasoning_chain)
                        with open(path, 'r', encoding='utf-8') as f:
                            st.download_button("⬇️ 下载 .md", f.read(), file_name=f"report_{query_id}.md")

                with col_y:
                    if st.button("🌐 HTML", key="html"):
                        path = os.path.join(REPORT_OUTPUT_DIR, f"report_{query_id}.html")
                        report_agent.generate_html_report(user_query, sql, data, analysis, chart_paths, path, intent=intent, reasoning_chain=reasoning_chain)
                        with open(path, 'r', encoding='utf-8') as f:
                            st.download_button("⬇️ 下载 .html", f.read(), file_name=f"report_{query_id}.html")

                with col_z:
                    if st.button("📃 Word", key="word"):
                        path = os.path.join(REPORT_OUTPUT_DIR, f"report_{query_id}.docx")
                        r = report_agent.generate_word_report(user_query, sql, data, analysis, chart_paths, path, intent=intent, reasoning_chain=reasoning_chain)
                        if r:
                            with open(path, 'rb') as f:
                                st.download_button("⬇️ 下载 .docx", f.read(), file_name=f"report_{query_id}.docx")

    with tab2:
        st.subheader("🧠 长链推理过程展示")
        st.caption("以下是6个Agent的协作链路，每一步的输出是下一步的输入")

        st.markdown("""
```
用户问题（自然语言）
    │
    ▼
[意图理解Agent] ──→ 拆解分析意图（类型/维度/指标/时间）
    │                    ↑ 痛点：业务人员表达模糊
    ▼
[NL2SQL Agent] ───→ 基于意图生成SQL（更精确）
    │                    ↑ 痛点：业务人员不会SQL
    ▼
[SQL校验Agent] ───→ 自检测+自修复（保证正确性）
    │                    ↑ 痛点：AI生成的SQL可能出错
    ▼
[数据查询Agent] ──→ 执行SQL获取数据
    │                    ↑ 痛点：数据源接入复杂
    ▼
[数据解读Agent] ──→ 提炼关键发现和业务洞察
    │                    ↑ 痛点：有数据看不懂
    ▼
[可视化Agent] ────→ 智能推荐图表类型+生成
    │                    ↑ 痛点：不知道用什么图表
    ▼
[报告Agent] ──────→ 整合所有输出组装报告
                         ↑ 痛点：报告制作耗时长
```
        """)

        st.info("💡 核心逻辑：**长链推理** = 每一步的输出是下一步的输入，逐步精化，而非单次调用。")

    with tab3:
        st.subheader("📄 批量报告生成")
        questions_text = st.text_area("输入多个分析问题（每行一个）：", height=150,
            placeholder="2024年各地区的销售总额\n对比各销售代表业绩\n月度销售趋势")

        if st.button("🚀 批量分析", type="primary"):
            questions = [q.strip() for q in questions_text.split('\n') if q.strip()]
            if not questions:
                st.warning("⚠️ 请输入至少一个问题")
            else:
                progress = st.progress(0)
                for i, q in enumerate(questions):
                    st.info(f"处理 {i+1}/{len(questions)}: {q}")
                    sql = nl2sql_agent.generate_sql(q)
                    success, data = query_agent.execute_sql(sql)
                    if success and len(data) > 0:
                        analysis = report_agent.generate_analysis_text(q, data, sql)
                        query_id = datetime.now().strftime("%Y%m%d_%H%M%S") + f"_{i}"
                        chart_paths = viz_agent.generate_all_charts(data, q, query_id=query_id)
                        html_path = os.path.join(REPORT_OUTPUT_DIR, f"batch_report_{query_id}.html")
                        report_agent.generate_html_report(q, sql, data, analysis, chart_paths, html_path)
                        st.success(f"✅ {q}: {len(data)}条 → {html_path}")
                    else:
                        st.error(f"❌ {q}: 查询失败")
                    progress.progress((i+1)/len(questions))


if __name__ == "__main__":
    main()
