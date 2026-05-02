"""
主程序 - 数据分析Agent系统入口
串联所有Agent，提供CLI和API两种使用方式
"""

import sys
import os
from datetime import datetime

# 导入各Agent
from nl2sql_agent import NL2SQLAgent, DataQueryAgent
from visualization_agent import VisualizationAgent
from report_agent import ReportAgent
from config import *


class DataAnalysisAgentSystem:
    """
    数据分析Agent系统 - 主协调器
    流程: 用户问题 → NL2SQL → 执行查询 → 生成图表 → 生成报告
    """

    def __init__(self, api_key=None, verbose=True):
        self.verbose = verbose
        self.nl2sql_agent = NL2SQLAgent(api_key=api_key)
        self.query_agent = DataQueryAgent()
        self.viz_agent = VisualizationAgent(api_key=api_key)
        self.report_agent = ReportAgent(api_key=api_key)
        self._init_db()

    def _init_db(self):
        """初始化数据库（如果未使用CSV模式）"""
        if not USE_CSV_MODE:
            self.query_agent.init_db()

    def analyze(self, user_query: str, output_formats=None) -> dict:
        """
        完整分析流程

        参数:
            user_query: 用户的自然语言问题
            output_formats: 输出格式列表，可选 ['markdown', 'html', 'word']

        返回:
            {
                'sql': 生成的SQL,
                'df': 查询结果DataFrame,
                'analysis': LLM生成的分析文本,
                'chart_paths': [图表文件路径列表],
                'report_paths': {格式: 报告路径},
                'summary': 文字摘要
            }
        """
        if output_formats is None:
            output_formats = ['markdown', 'html']

        result = {}
        query_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        os.makedirs(REPORT_OUTPUT_DIR, exist_ok=True)
        os.makedirs(CHART_OUTPUT_DIR, exist_ok=True)

        # Step 1: NL2SQL
        self._log("🔄 Step 1/5: 理解问题，生成SQL...")
        sql = self.nl2sql_agent.generate_sql(user_query)
        self._log(f"   SQL: {sql}")
        result['sql'] = sql

        # Step 2: 执行查询
        self._log("🔄 Step 2/5: 执行数据查询...")
        success, data = self.query_agent.execute_sql(sql)
        if not success:
            self._log(f"❌ 查询失败: {data}")
            result['error'] = data
            return result
        self._log(f"   ✅ 查询成功，返回 {len(data)} 条数据")
        result['df'] = data

        # Step 3: 数据解读
        self._log("🔄 Step 3/5: 分析数据...")
        analysis = self.report_agent.generate_analysis_text(user_query, data, sql)
        result['analysis'] = analysis
        self._log(f"   ✅ 分析完成")

        # Step 4: 生成图表
        self._log("🔄 Step 4/5: 生成可视化图表...")
        chart_paths = self.viz_agent.generate_all_charts(data, user_query, query_id)
        result['chart_paths'] = chart_paths
        self._log(f"   ✅ 生成 {len(chart_paths)} 张图表")

        # Step 5: 生成报告
        self._log("🔄 Step 5/5: 生成分析报告...")
        report_paths = {}
        for fmt in output_formats:
            if fmt == 'markdown':
                path = os.path.join(REPORT_OUTPUT_DIR, f"report_{query_id}.md")
                self.report_agent.generate_markdown_report(user_query, sql, data, analysis, chart_paths, path)
                report_paths['markdown'] = path
            elif fmt == 'html':
                path = os.path.join(REPORT_OUTPUT_DIR, f"report_{query_id}.html")
                self.report_agent.generate_html_report(user_query, sql, data, analysis, chart_paths, path)
                report_paths['html'] = path
            elif fmt == 'word':
                path = os.path.join(REPORT_OUTPUT_DIR, f"report_{query_id}.docx")
                r = self.report_agent.generate_word_report(user_query, sql, data, analysis, chart_paths, path)
                if r:
                    report_paths['word'] = r
        result['report_paths'] = report_paths

        # 生成摘要
        num_cols = data.select_dtypes(include=['number']).columns.tolist()
        total = data[num_cols[0]].sum() if num_cols else 0
        result['summary'] = (
            f"✅ 分析完成！\n"
            f"   SQL: {sql[:80]}{'...' if len(sql) > 80 else ''}\n"
            f"   数据: {len(data)} 条\n"
            f"   总计: {total:,.0f} 元\n"
            f"   图表: {len(chart_paths)} 张\n"
            f"   报告: {list(report_paths.keys())}"
        )
        self._log(result['summary'])

        # 打印分析文本
        print(f"\n{'='*60}")
        print("📊 数据解读")
        print(f"{'='*60}")
        print(analysis)
        print(f"{'='*60}\n")

        return result

    def _log(self, msg):
        if self.verbose:
            print(msg)

    def interactive_mode(self):
        """交互式问答模式"""
        print("=" * 60)
        print("🤖 数据分析Agent系统 - 交互模式")
        print("=" * 60)
        print("提示: 输入问题进行数据分析，输入 'exit' 或 'quit' 退出")
        print(f"数据来源: {CSV_PATH if USE_CSV_MODE else DB_PATH}")
        print("=" * 60)

        while True:
            try:
                query = input("\n🔍 请输入您的分析问题: ").strip()
                if not query:
                    continue
                if query.lower() in ['exit', 'quit', '退出', 'q']:
                    print("👋 再见！")
                    break

                result = self.analyze(query)
                if 'error' in result:
                    print(f"❌ 错误: {result['error']}")
                    print("请尝试更清晰地描述您的问题，例如:")
                    print("  - 2024年各地区的销售总额是多少")
                    print("  - Alice卖了哪些产品")
                    print("  - 各产品类别的销售趋势")

            except KeyboardInterrupt:
                print("\n👋 再见！")
                break
            except Exception as e:
                print(f"❌ 发生错误: {e}")


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description='数据分析Agent系统')
    parser.add_argument('--query', '-q', type=str, help='自然语言分析问题')
    parser.add_argument('--api-key', type=str, help='OpenAI API Key（或使用环境变量）')
    parser.add_argument('--formats', nargs='+', default=['markdown', 'html'],
                        choices=['markdown', 'html', 'word'],
                        help='输出格式（可多选）')
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
        # 默认进入交互模式
        system.interactive_mode()


if __name__ == '__main__':
    main()
