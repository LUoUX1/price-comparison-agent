"""
Hermes消息监听主程序
监听微信群/Discord指令 → 调用 browser-use 京东爬虫 → 自动回复
指令格式：帮我列出近期热销前三的xxx
"""

import json
import re
import time
import sys
from pathlib import Path
from jd_spider import get_jd_top_sales

ROOT = Path(__file__).parent
with open(ROOT / "config.json", "r", encoding="utf-8") as f:
    cfg = json.load(f)


def parse_command(text: str):
    m = re.search(r"帮我列出近期热销前三的(.+)", text)
    return m.group(1).strip() if m else None


def poll_stdin():
    """从 stdin 读取指令（供 Hermes 直接调用）"""
    print("🔍 等待指令...")
    for line in sys.stdin:
        content = line.strip()
        keyword = parse_command(content)
        if keyword:
            print(f"📌 正在抓取【{keyword}】热销商品...")
            try:
                goods = get_jd_top_sales(keyword, top_num=3, headless=True)
                if not goods:
                    print("❌ 未抓取到商品")
                    continue
                print(f"✅【{keyword} 热销TOP3】")
                for i, item in enumerate(goods, 1):
                    print(f"{i}. {item['title'][:40]}")
                    print(f"   💰 ¥{item['price']}  💬 {item['comment']}")
                    print(f"   🔗 {item['url']}")
            except Exception as e:
                print(f"❌ 抓取失败: {e}")


if __name__ == "__main__":
    # 命令行测试模式
    if len(sys.argv) > 1:
        kw = sys.argv[1]
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 3
        results = get_jd_top_sales(kw, n, headless=False)
        for i, item in enumerate(results, 1):
            print(f"{i}. {item['title'][:40]}")
            print(f"   💰 ¥{item['price']}  💬 {item['comment']}")
            print(f"   🔗 {item['url']}")
            print()
    else:
        poll_stdin()
