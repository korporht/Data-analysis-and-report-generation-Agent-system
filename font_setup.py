"""
matplotlib 中文字体配置工具
自动检测 Windows 可用的中文字体，避免 Glyph missing 警告
"""

import matplotlib
import os
import warnings


def setup_chinese_font():
    """
    配置 matplotlib 中文字体
    返回可用的中文字体名称
    """
    # Windows 常见中文字体路径
    font_candidates = [
        ('SimHei', 'C:\\Windows\\Fonts\\simhei.ttf'),
        ('Microsoft YaHei', 'C:\\Windows\\Fonts\\msyh.ttc'),
        ('SimSun', 'C:\\Windows\\Fonts\\simsun.ttc'),
        ('FangSong', 'C:\\Windows\\Fonts\\simfang.ttf'),
        ('KaiTi', 'C:\\Windows\\Fonts\\simkai.ttf'),
        ('Arial Unicode MS', 'C:\\Windows\\Fonts\\arialuni.ttf'),
    ]

    available_fonts = []
    for name, path in font_candidates:
        if os.path.exists(path):
            available_fonts.append(name)

    if available_fonts:
        # 使用找到的第一个字体
        font_name = available_fonts[0]
        matplotlib.rcParams['font.sans-serif'] = [font_name, 'DejaVu Sans', 'Arial']
        matplotlib.rcParams['axes.unicode_minus'] = False
        return font_name
    else:
        # 没有中文字体，使用默认配置并忽略警告
        warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib')
        matplotlib.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial']
        matplotlib.rcParams['axes.unicode_minus'] = False
        return None


def apply_font_fix():
    """在 import matplotlib 后调用此函数"""
    try:
        import matplotlib.font_manager as fm
        # 重建字体缓存（首次运行可能需要）
        # fm._load_fontmanager(try_read_cache=False)
    except:
        pass
    return setup_chinese_font()
