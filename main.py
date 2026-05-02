"""
主程序 - 数据分析Agent系统 v2
核心：长链推理 + 多Agent协作 + 痛点驱动

================================================================
  解决的核心痛点：
  1. 业务人员不会SQL → NL2SQL Agent 自动生成
  2. 需求表达模糊 → 意图理解Agent 拆解结构化意图
  3. AI生成的SQL可能出错 → SQL校验Agent 自动检测+修复
  4. 有数据但看不懂 → 数据解读Agent 提炼洞察
  5. 不知道用什么图表 → 可视化Agent 智能推荐
  6. 报告制作耗时长 → 报告Agent 一键生成多格式报告

  核心逻辑流（长链推理 + 多Agent协作）：
  用户问题
    → [意图理解Agent] 拆解分析意图
    → [NL2SQL Agent] 基于意图生成SQL
    → [SQL校验Agent] 自检测+自修复
    → [数据查询Agent] 执行SQL获取数据
    → [数据解读Agent] 提炼关键发现与洞察
    → [可视化Agent] 智能推荐图表+生成
    → [报告Agent] 整合所有输出组装报告
================================================================
"""

import sys
import os
import json
from datetime import datetime

from nl2sql_agent import IntentUnderstandingAgent, NL2SQLAgent, SQLValidationAgent, DataQueryAgent
from visualization_agent import VisualizationAgent
from report_agent import ReportAgent
from config import *


class DataAnalysisAgentSystem:
    """
    数据分析Agent系统 - 主协调器
    实现6个Agent的长链协作，每一步的输出是下一步的输入
    """

    def __init__(self, api_key=None, verbose=True):
        self.verbose = verbose
        # 6个Agent，各司其职
        self.intent_agent = IntentUnderstandingAgent(api_key=api_key)
        self.nl2sql_agent = NL2SQLAgent(api_key=api_key)
        self.validation_agent = SQLValidationAgent(api_key=api_key)
        self.query_agent = DataQueryAgent()
        self.viz_agent = VisualizationAgent(api_key=api_key)
        self.report_agent = ReportAgent(api_key=api_key)
        self._init_db()

    def _init_db(self):
        if not USE_CSV_MODE:
            self.query_agent.init_db()

    def analyze(self, user_query: str, output_formats=None) -> dict:
        """
        完整分析流程 —— 长链推理的6步

        每一步都记录推理链（reasoning_chain），用于：
        1. 调试和可解释性
        2. 在报告中展示Agent协作过程
        3. 证明这不是简单的单次调用，而是多步推理
        """
        if output_formats is None:
            output_formats = ['markdown', 'html']

        result = {}
        reasoning_chain = []  # 推理链：记录每一步的Agent、动作、结果
        query_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        os.makedirs(REPORT_OUTPUT_DIR, exist_ok=True)
        os.makedirs(CHART_OUTPUT_DIR, exist_ok=True)

        # ==========================================
        # Step 1: 意图理解 Agent
        # 痛点: 业务人员表达模糊，如"帮我看看销售情况"
        # 输出: 结构化意图（分析类型、维度、指标、时间范围等）
        # ==========================================
        self._log("🧠 Step 1/6: 意图理解Agent — 拆解分析意图...")
        intent = self.intent_agent.understand(user_query)
        self._log(f"   分析类型: {intent.get('analysis_type', '')}")
        self._log(f"   分析维度: {intent.get('dimensions', [])}")
        self._log(f"   时间范围: {intent.get('time_scope', '')}")
        reasoning_chain.append({
            'icon': '🧠',
            'agent': '意图理解Agent',
            'action': f'解析用户问题「{user_query}」',
            'result': f'类型={intent.get("analysis_type", "")} | 维度={intent.get("dimensions", [])} | 时间={intent.get("time_scope", "")}'
        })
        result['intent'] = intent

        # ==========================================
        # Step 2: NL2SQL Agent
        # 痛点: 业务人员不会写SQL
        # 输入: 用户问题 + Step1的结构化意图（让SQL更精确）
        # 输出: SQL查询语句
        # ==========================================
        self._log("📝 Step 2/6: NL2SQL Agent — 基于意图生成SQL...")
        sql = self.nl2sql_agent.generate_sql(user_query, intent=intent)
        self._log(f"   SQL: {sql}")
        reasoning_chain.append({
            'icon': '📝',
            'agent': 'NL2SQL Agent',
            'action': '基于意图生成SQL查询',
            'result': sql[:100] + ('...' if len(sql) > 100 else '')
        })
        result['sql'] = sql

        # ==========================================
        # Step 3: SQL校验 Agent（自修复）
        # 痛点: AI生成的SQL可能有语法错误或逻辑问题
        # 输入: Step2生成的SQL
        # 输出: 校验通过的SQL（如有问题自动修复）
        # ==========================================
        self._log("🔍 Step 3/6: SQL校验Agent — 检测并修复SQL...")
        schema_info = self.query_agent.get_schema()
        fixed, validated_sql, validation_logs = self.validation_agent.validate_and_fix(sql, schema_info)
        if fixed:
            self._log(f"   🔧 SQL已修复: {validated_sql}")
            sql = validated_sql
            result['sql'] = sql
        else:
            self._log(f"   ✅ SQL校验通过")
        for log in validation_logs:
            self._log(f"   {log}")
        reasoning_chain.append({
            'icon': '🔍',
            'agent': 'SQL校验Agent',
            'action': '检测SQL语法与逻辑正确性',
            'result': '已修复' if fixed else '校验通过'
        })

        # ==========================================
        # Step 4: 数据查询 Agent
        # 痛点: 不同数据源接入复杂
        # 输入: 校验后的SQL
        # 输出: 查询结果DataFrame
        # ==========================================
        self._log("📊 Step 4/6: 数据查询Agent — 执行查询...")
        success, data = self.query_agent.execute_sql(sql)
        if not success:
            self._log(f"❌ 查询失败: {data}")
            reasoning_chain.append({
                'icon': '❌',
                'agent': '数据查询Agent',
                'action': '执行SQL查询',
                'result': f'失败: {data}'
            })
            result['error'] = data
            result['reasoning_chain'] = reasoning_chain
            return result
        self._log(f"   ✅ 查询成功，返回 {len(data)} 条数据")
        reasoning_chain.append({
            'icon': '📊',
            'agent': '数据查询Agent',
            'action': '执行SQL查询获取数据',
            'result': f'返回 {len(data)} 条数据 × {len(data.columns)} 列'
        })
        result['df'] = data

        # ==========================================
        # Step 5: 数据解读 Agent
        # 痛点: 有数据但看不懂，找不到业务洞察
        # 输入: 用户问题 + 意图 + 查询结果 + SQL
        # 输出: 结构化分析文本（关键发现+趋势+建议）
        # ==========================================
        self._log("💡 Step 5/6: 数据解读Agent — 提炼洞察...")
        analysis = self.report_agent.generate_analysis_text(user_query, data, sql, intent=intent)
        reasoning_chain.append({
            'icon': '💡',
            'agent': '数据解读Agent',
            'action': '分析数据、提炼关键发现和业务洞察',
            'result': f'已生成结构化分析（{len(analysis)}字）'
        })
        result['analysis'] = analysis

        # ==========================================
        # Step 6: 可视化 Agent
        # 痛点: 不知道用什么图表，不会做图
        # 输入: 数据 + 用户问题 + 意图（用于推荐图表类型）
        # 输出: 多张图表
        # ==========================================
        self._log("📈 Step 6/6: 可视化Agent — 生成图表...")
        chart_paths = self.viz_agent.generate_all_charts(data, user_query, intent=intent, query_id=query_id)
        reasoning_chain.append({
            'icon': '📈',
            'agent': '可视化Agent',
            'action': '基于意图推荐图表类型并生成可视化',
            'result': f'生成 {len(chart_paths)} 张图表'
        })
        result['chart_paths'] = chart_paths

        # ==========================================
        # Step 7: 报告组装
        # 痛点: 报告制作耗时长、格式不统一
        # 输入: 以上所有Agent的输出 + 推理链
        # 输出: Markdown/HTML/Word 报告
        # ==========================================
        self._log("📄 生成分析报告...")
        report_paths = {}
        for fmt in output_formats:
            if fmt == 'markdown':
                path = os.path.join(REPORT_OUTPUT_DIR, f"report_{query_id}.md")
                self.report_agent.generate_markdown_report(user_query, sql, data, analysis, chart_paths, path, intent=intent, reasoning_chain=reasoning_chain)
                report_paths['markdown'] = path
            elif fmt == 'html':
                path = os.path.join(REPORT_OUTPUT_DIR, f"report_{query_id}.html")
                self.report_agent.generate_html_report(user_query, sql, data, analysis, chart_paths, path, intent=intent, reasoning_chain=reasoning_chain)
                report_paths['html'] = path
            elif fmt == 'word':
                path = os.path.join(REPORT_OUTPUT_DIR, f"report_{query_id}.docx")
                r = self.report_agent.generate_word_report(user_query, sql, data, analysis, chart_paths, path, intent=intent, reasoning_chain=reasoning_chain)
                if r:
                    report_paths['word'] = r
        result['report_paths'] = report_paths

        # 汇总
        num_cols = data.select_dtypes(include=['number']).columns.tolist()
        total = data[num_cols[0]].sum() if num_cols else 0
        result['reasoning_chain'] = reasoning_chain
        result['summary'] = (
            f"✅ 分析完成！\n"
            f"   🧠 意图: {intent.get('analysis_type', '')}\n"
            f"   📝 SQL: {sql[:80]}{'...' if len(sql) > 80 else ''}\n"
            f"   📊 数据: {len(data)} 条\n"
            f"   💰 总计: {total:,.0f} 元\n"
            f"   📈 图表: {len(chart_paths)} 张\n"
            f"   📄 报告: {list(report_paths.keys())}\n"
            f"   🧠 推理步骤: {len(reasoning_chain)} 步"
        )
        self._log(result['summary'])

        # 打印分析
        print(f"\n{'='*60}")
        print("📊 数据解读")
        print(f"{'='*60}")
        print(analysis)
        print(f"{'='*60}")
        print("\n🧠 推理链:")
        for step in reasoning_chain:
            print(f"  {step['icon']} {step['agent']}: {step['action']}")
            print(f"     → {step['result']}")
        print(f"{'='*60}\n")

        return result

    def _log(self, msg):
        if self.verbose:
            print(msg)

    def interactive_mode(self):
        """交互式问答模式"""
        print("=" * 60)
        print("🤖 数据分析Agent系统 v2")
        print("=" * 60)
        print("📌 解决核心痛点:")
        print("   1. 业务人员不会SQL → 自然语言提问即可")
        print("   2. 需求表达模糊 → 自动拆解分析意图")
        print("   3. SQL可能出错 → 自动校验+修复")
        print("   4. 有数据看不懂 → 自动提炼洞察")
        print("   5. 不会做图表 → 智能推荐+自动生成")
        print("   6. 报告耗时长 → 一键多格式输出")
        print("=" * 60)
        print("💡 输入问题进行分析，输入 'exit' 退出\n")

        while True:
            try:
                query = input("🔍 请输入分析问题: ").strip()
                if not query:
                    continue
                if query.lower() in ['exit', 'quit', '退出', 'q']:
                    print("👋 再见！")
                    break

                result = self.analyze(query)
                if 'error' in result:
                    print(f"❌ 错误: {result['error']}")
                    print("请尝试更清晰地描述，例如:")
                    print("  - 2024年各地区的销售总额是多少")
                    print("  - 对比分析各销售代表的业绩")
                    print("  - 月度销售趋势如何")
            except KeyboardInterrupt:
                print("\n👋 再见！")
                break
            except Exception as e:
                print(f"❌ 发生错误: {e}")


def main():
    """命令行入口"""
    import argparse
    parser = argparse.ArgumentParser(description='数据分析Agent系统 v2 - 长链推理+多Agent协作')
    parser.add_argument('--query', '-q', type=str, help='自然语言分析问题')
    parser.add_argument('--api-key', type=str, help='OpenAI API Key')
    parser.add_argument('--formats', nargs='+', default=['markdown', 'html'],
                        choices=['markdown', 'html', 'word'], help='输出格式')
    parser.add_argument('--interactive', '-i', action='store_true', help='交互模式')
    args = parser.parse_args()

    system = DataAnalysisAgentSystem(api_key=args.api_key)

    if args.interactive:
        system.interactive_mode()
    elif args.query:
        result = system.analyze(args.query, output_formats=args.formats)
        if 'report_paths' in result:
            print("\n📄 生成的报告:")
            for fmt, path in result['report_paths'].items():
                print(f"   [{fmt}] {path}")
    else:
        system.interactive_mode()


if __name__ == '__main__':
    main()
