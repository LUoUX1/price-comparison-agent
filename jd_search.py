"""京东搜索命令行入口"""
import sys
from jd_spider import get_jd_top_sales

kw = sys.argv[1] if len(sys.argv) > 1 else "键盘"
n = int(sys.argv[2]) if len(sys.argv) > 2 else 3
headless = "--headless" in sys.argv

print(f"🔍 搜索: {kw} | TOP {n} | headless={headless}\n")
results = get_jd_top_sales(kw, n, headless=headless)

# 标记商品状态
def classify_condition(title):
    """分类：全新/二手/资源机/翻新"""
    if '95新' in title or '99新' in title or '二手' in title or '准新' in title:
        return '⚠️二手'
    if '资源机' in title or '官换' in title or '翻新' in title:
        return '🔄翻新/资源机'
    if 'Pro' in title and 'Pro Max' not in title and 'iPhone 16 Pro' in title:
        return '📱Pro版'
    return '✅全新'

print(f"{'':<3} {'状态':<8} {'店铺':<18} {'等级':<6} {'价格':>8} {'评价':<12}")
print("-" * 78)
for i, item in enumerate(results, 1):
    cond = classify_condition(item.get('title', ''))
    shop = item.get('shop', 'N/A')[:16]
    level = item.get('shop_level', 'N/A')
    price = item.get('price', 0)
    comment = item.get('comment', 'N/A')
    title = item.get('title', 'N/A')[:40]
    print(f"{i:<3} {cond:<8} {shop:<18} {level:<6} ¥{price:>7.0f} {comment:<12}")
    print(f"    {title}")
    print()

# 筛选全新
new_items = [i for i in results if classify_condition(i.get('title','')) == '✅全新']
if new_items:
    print("📌 全新商品汇总:")
    for i, item in enumerate(new_items, 1):
        print(f"  {i}. [{item['shop_level']}] {item['shop']} ¥{item['price']:.0f} | {item['title'][:50]}")
elif results:
    print("⚠️ 未找到全新商品，以上结果含二手/资源机或Pro型号")
