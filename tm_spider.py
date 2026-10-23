"""天猫搜索 - 复用淘宝爬虫过滤天猫"""
from tb_spider import search_tm  # noqa

if __name__ == "__main__":
    import sys
    kw = sys.argv[1] if len(sys.argv) > 1 else "iPhone 17"
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    for i, g in enumerate(search_tm(kw, n), 1):
        print(f"{i}. [{g['shopLevel']}] {g['shop']} | {g['title'][:40]} ¥{g['price']} {g['sales']}")
