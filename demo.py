"""
端到端演示脚本 - 无需API Key即可运行
展示完整的长链推理 + 多Agent协作流程
输出写入 demo_result.txt，避免Windows控制台编码问题
"""

import os
import sys

# 确保UTF-8输出（Windows兼容）
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

os.chdir(os.path.dirname(os.path.abspath(__file__)))

from nl2sql_agent import IntentUnderstandingAgent, NL2SQLAgent, SQLValidationAgent, DataQueryAgent
from visualization_agent import VisualizationAgent
from report_agent import ReportAgent


def demo():
    output_lines = []
    add = lambda s: (output_lines.append(s), sys.stdout.write(s + '\n'))[0]

    add('=' * 70)
    add('  数据分析Agent系统 v2 - 长链推理 + 多Agent协作')
    add('=' * 70)
    add('')
    add('[核心痛点]')
    add('  1. 业务人员不会SQL  -> 自然语言提问即可')
    add('  2. 需求表达模糊      -> 意图理解Agent自动拆解')
    add('  3. AI生成SQL可能出错 -> SQL校验Agent自动检测+修复')
    add('  4. 有数据但看不懂    -> 数据解读Agent提炼洞察')
    add('  5. 不知道用什么图表  -> 可视化Agent智能推荐')
    add('  6. 报告制作耗时长    -> 报告Agent一键生成多格式')
    add('')
    add('[核心逻辑流] (长链推理: 每一步输出是下一步输入)')
    add('  用户问题')
    add('    -> [意图理解Agent] 拆解分析意图')
    add('    -> [NL2SQL Agent]  基于意图生成SQL')
    add('    -> [SQL校验Agent]  自检测+自修复')
    add('    -> [数据查询Agent]  执行SQL获取数据')
    add('    -> [数据解读Agent]  提炼关键发现与洞察')
    add('    -> [可视化Agent]    智能推荐图表+生成')
    add('    -> [报告Agent]      整合输出组装报告')
    add('=' * 70)
    add('')

    # 初始化6个Agent
    intent_agent = IntentUnderstandingAgent()
    nl2sql_agent = NL2SQLAgent()
    validation_agent = SQLValidationAgent()
    query_agent = DataQueryAgent()
    viz_agent = VisualizationAgent()
    report_agent = ReportAgent()

    queries = [
        '2024年各地区的销售总额是多少',
        '对比分析各销售代表的业绩',
        '各产品类别的销售趋势',
    ]

    for idx, user_query in enumerate(queries, 1):
        add('')
        add('=' * 70)
        add(f'  分析 {idx}/{len(queries)}: {user_query}')
        add('=' * 70)
        add('')

        # Step 1: 意图理解
        add('[Step 1/7] 意图理解Agent - 拆解分析意图...')
        intent = intent_agent.understand(user_query)
        add(f'  分析类型: {intent.get("analysis_type", "")}')
        add(f'  分析维度: {intent.get("dimensions", [])}')
        add(f'  关注指标: {intent.get("metrics", [])}')
        add(f'  时间范围: {intent.get("time_scope", "")}')
        add(f'  是否对比: {intent.get("comparison", False)}')
        add('')

        # Step 2: NL2SQL
        add('[Step 2/7] NL2SQL Agent - 基于意图生成SQL...')
        sql = nl2sql_agent.generate_sql(user_query, intent=intent)
        add(f'  SQL: {sql}')
        add('')

        # Step 3: SQL校验
        add('[Step 3/7] SQL校验Agent - 检测+修复SQL...')
        schema_info = query_agent.get_schema()
        fixed, validated_sql, validation_logs = validation_agent.validate_and_fix(sql, schema_info)
        for log in validation_logs:
            add(f'  {log}')
        if fixed:
            add(f'  修复后SQL: {validated_sql}')
            sql = validated_sql
        else:
            add('  SQL校验通过')
        add('')

        # Step 4: 数据查询
        add('[Step 4/7] 数据查询Agent - 执行查询...')
        success, data = query_agent.execute_sql(sql)
        if not success:
            add(f'  查询失败: {data}')
            add('')
            continue
        add(f'  返回 {len(data)} 条数据, {len(data.columns)} 列')
        add(f'  列名: {list(data.columns)}')
        add('  数据预览:')
        # 格式化预览
        preview = data.head(5).to_string(index=False)
        for line in preview.split('\n'):
            add(f'    {line}')
        add('')

        # Step 5: 数据解读
        add('[Step 5/7] 数据解读Agent - 提炼洞察...')
        analysis = report_agent.generate_analysis_text(user_query, data, sql, intent=intent)
        # 只打印前500字
        add(f'  分析文本 ({len(analysis)}字):')
        for line in analysis[:500].split('\n'):
            if line.strip():
                add(f'    {line}')
        add('  ...')
        add('')

        # Step 6: 可视化
        add('[Step 6/7] 可视化Agent - 生成图表...')
        from datetime import datetime
        query_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        chart_paths = viz_agent.generate_all_charts(data, user_query, intent=intent, query_id=query_id)
        for p in chart_paths:
            add(f'  图表: {p}')
        add('')

        # Step 7: 报告
        add('[Step 7/7] 报告Agent - 生成分析报告...')
        import os
        os.makedirs('reports', exist_ok=True)

        reasoning_chain = [
            {'icon': '>>', 'agent': '意图理解Agent', 'action': f'解析问题', 'result': f'类型={intent.get("analysis_type", "")}'},
            {'icon': 'SQL', 'agent': 'NL2SQL Agent', 'action': '生成SQL', 'result': sql[:80]},
            {'icon': 'OK', 'agent': 'SQL校验Agent', 'action': '校验SQL', 'result': '已修复' if fixed else '通过'},
            {'icon': 'DAT', 'agent': '数据查询Agent', 'action': '执行查询', 'result': f'{len(data)}条数据'},
            {'icon': 'ANA', 'agent': '数据解读Agent', 'action': '提炼洞察', 'result': f'{len(analysis)}字'},
            {'icon': 'VIS', 'agent': '可视化Agent', 'action': '生成图表', 'result': f'{len(chart_paths)}张'},
        ]

        md_path = f'reports/demo_report_{query_id}.md'
        report_agent.generate_markdown_report(user_query, sql, data, analysis, chart_paths, md_path, intent=intent, reasoning_chain=reasoning_chain)
        add(f'  Markdown: {md_path}')

        html_path = f'reports/demo_report_{query_id}.html'
        report_agent.generate_html_report(user_query, sql, data, analysis, chart_paths, html_path, intent=intent, reasoning_chain=reasoning_chain)
        add(f'  HTML:     {html_path}')
        add('')

    add('')
    add('=' * 70)
    add('  演示完成!')
    add('=' * 70)
    add('')
    add('[生成文件]')
    add('  charts/    - 可视化图表(PNG)')
    add('  reports/   - 分析报告(Markdown + HTML)')
    add('')
    add('[使用说明]')
    add('  1. 安装依赖: pip install pandas matplotlib seaborn openai python-docx')
    add('  2. 运行Streamlit: streamlit run app.py')
    add('  3. 设置OPENAI_API_KEY后运行可获得LLM增强版')
    add('')

    # 写入文件
    with open('demo_result.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(output_lines))
    print('\n'.join(output_lines))
    print('\n结果已写入 demo_result.txt')


if __name__ == '__main__':
    demo()
