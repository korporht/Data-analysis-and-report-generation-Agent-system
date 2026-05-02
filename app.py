"""
Streamlit Web 界面 - 数据分析Agent系统
运行方式: streamlit run app.py
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import os

# 导入各Agent
from nl2sql_agent import NL2SQLAgent, DataQueryAgent
from visualization_agent import VisualizationAgent
from report_agent import ReportAgent
from config import *

# 页面设置
st.set_page_config(
    page_title="数据分析Agent系统",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 初始化Agent（缓存）
@st.cache_resource
def init_agents():
    nl2sql = NL2SQLAgent()
    query = DataQueryAgent()
    viz = VisualizationAgent()
    report = ReportAgent()
    if not USE_CSV_MODE:
        query.init_db()
    return nl2sql, query, viz, report


def main():
    st.title("📊 数据分析Agent系统")
    st.caption("基于多Agent协作的智能数据分析 · 自然语言提问 → SQL查询 → 可视化 → 报告")

    # 侧边栏：数据预览
    with st.sidebar:
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
            "Alice卖了哪些产品，各卖了多少",
            "各产品类别的销售趋势是怎样的",
            "哪个销售代表业绩最好",
            "企业客户的销售额占比是多少",
        ]
        for ex in examples:
            if st.button(f"💬 {ex}", use_container_width=True, key=ex):
                st.session_state['user_query'] = ex

    # 初始化
    nl2sql_agent, query_agent, viz_agent, report_agent = init_agents()

    # 主界面
    tab1, tab2 = st.tabs(["🔍 智能分析", "📄 批量报告生成"])

    with tab1:
        st.subheader("🔍 输入分析问题")

        # 输入框
        user_query = st.text_input(
            "用自然语言描述您想分析的问题：",
            value=st.session_state.get('user_query', ''),
            placeholder="例如：2024年各地区的销售总额是多少",
            label_visibility="collapsed"
        )

        col1, col2, col3 = st.columns([1, 1, 4])
        with col1:
            analyze_btn = st.button("🚀 开始分析", type="primary", use_container_width=True)
        with col2:
            clear_btn = st.button("🗑️ 清空", use_container_width=True)

        if clear_btn:
            st.session_state['user_query'] = ''
            st.rerun()

        if analyze_btn and user_query:
            with st.spinner("🤖 Agent协作中，请稍候..."):

                # Step 1: NL2SQL
                st.info("🔄 Step 1/4: 理解问题，生成SQL...")
                sql = nl2sql_agent.generate_sql(user_query)
                st.code(sql, language="sql")

                # Step 2: 执行查询
                st.info("🔄 Step 2/4: 执行数据查询...")
                success, data = query_agent.execute_sql(sql)
                if not success:
                    st.error(f"查询失败: {data}")
                    st.stop()
                st.success(f"✅ 查询成功，返回 {len(data)} 条数据")

                # 显示数据
                with st.expander("📋 查看查询结果", expanded=True):
                    st.dataframe(data, use_container_width=True, hide_index=True)
                    st.caption(f"共 {len(data)} 行 × {len(data.columns)} 列")

                # Step 3: 数据解读
                st.info("🔄 Step 3/4: AI分析数据...")
                analysis = report_agent.generate_analysis_text(user_query, data, sql)
                st.markdown("### 📝 数据解读")
                st.markdown(analysis)

                # Step 4: 可视化
                st.info("🔄 Step 4/4: 生成可视化图表...")
                os.makedirs(CHART_OUTPUT_DIR, exist_ok=True)
                query_id = datetime.now().strftime("%Y%m%d_%H%M%S")
                chart_paths = viz_agent.generate_all_charts(data, user_query, query_id)

                st.markdown("### 📊 可视化图表")
                for i, chart_path in enumerate(chart_paths):
                    st.image(chart_path, caption=f"图表 {i+1}", use_container_width=True)

                # 生成报告按钮
                st.divider()
                col_a, col_b, col_c = st.columns(3)
                os.makedirs(REPORT_OUTPUT_DIR, exist_ok=True)

                with col_a:
                    if st.button("📄 下载 Markdown 报告"):
                        path = os.path.join(REPORT_OUTPUT_DIR, f"report_{query_id}.md")
                        report_agent.generate_markdown_report(user_query, sql, data, analysis, chart_paths, path)
                        with open(path, 'r', encoding='utf-8') as f:
                            st.download_button("⬇️ 下载 .md 文件", f.read(), file_name=f"report_{query_id}.md")

                with col_b:
                    if st.button("🌐 下载 HTML 报告"):
                        path = os.path.join(REPORT_OUTPUT_DIR, f"report_{query_id}.html")
                        report_agent.generate_html_report(user_query, sql, data, analysis, chart_paths, path)
                        with open(path, 'r', encoding='utf-8') as f:
                            st.download_button("⬇️ 下载 .html 文件", f.read(), file_name=f"report_{query_id}.html")

                with col_c:
                    if st.button("📃 下载 Word 报告"):
                        path = os.path.join(REPORT_OUTPUT_DIR, f"report_{query_id}.docx")
                        r = report_agent.generate_word_report(user_query, sql, data, analysis, chart_paths, path)
                        if r:
                            with open(path, 'rb') as f:
                                st.download_button("⬇️ 下载 .docx 文件", f.read(), file_name=f"report_{query_id}.docx")
                        else:
                            st.warning("python-docx 未安装，请运行: pip install python-docx")

        elif analyze_btn and not user_query:
            st.warning("⚠️ 请输入分析问题")

    with tab2:
        st.subheader("📄 批量报告生成")
        st.caption("一次性分析多个问题，批量生成报告")

        questions_text = st.text_area(
            "输入多个分析问题（每行一个）：",
            height=150,
            placeholder="2024年各地区的销售总额\n各产品销售对比\n销售代表业绩排名"
        )

        if st.button("🚀 批量分析", type="primary"):
            questions = [q.strip() for q in questions_text.split('\n') if q.strip()]
            if not questions:
                st.warning("⚠️ 请输入至少一个问题")
            else:
                results = []
                progress = st.progress(0)
                for i, q in enumerate(questions):
                    st.info(f"处理问题 {i+1}/{len(questions)}: {q}")
                    sql = nl2sql_agent.generate_sql(q)
                    success, data = query_agent.execute_sql(sql)
                    if success and len(data) > 0:
                        analysis = report_agent.generate_analysis_text(q, data, sql)
                        query_id = datetime.now().strftime("%Y%m%d_%H%M%S") + f"_{i}"
                        chart_paths = viz_agent.generate_all_charts(data, q, query_id)
                        html_path = os.path.join(REPORT_OUTPUT_DIR, f"batch_report_{query_id}.html")
                        report_agent.generate_html_report(q, sql, data, analysis, chart_paths, html_path)
                        results.append({'query': q, 'sql': sql, 'rows': len(data), 'report': html_path})
                    else:
                        results.append({'query': q, 'error': '查询失败或无数据'})
                    progress.progress((i+1)/len(questions))

                st.success(f"✅ 批量分析完成！共处理 {len(questions)} 个问题")
                for r in results:
                    if 'error' in r:
                        st.error(f"❌ {r['query']}: {r['error']}")
                    else:
                        st.success(f"✅ {r['query']}: {r['rows']} 条数据 → {r['report']}")


if __name__ == "__main__":
    main()
