"""
四平台比价系统：京东 + 淘宝 + 天猫 + SMZDM
优先级：JD自营>旗舰>专营 | 淘宝最低价 | 天猫旗舰>专营>普通
"""
import sys, time, subprocess
from jd_spider import get_jd_top_sales
from tb_spider import search_all
from smzdm_spider import search_smzdm


def kill_zombies():
    """清理僵尸Chrome进程，防止tab crash"""
    subprocess.run("taskkill /F /IM chrome.exe 2>nul", shell=True, capture_output=True)
    subprocess.run("taskkill /F /IM chromedriver.exe 2>nul", shell=True, capture_output=True)
    time.sleep(2)


def compare(keyword, top_num=3, headless=True):
    results = {}

    kill_zombies()
    print("📦 [京东] 优先自营 > 旗舰店 > 专营店...")
    try:
        results["京东"] = get_jd_top_sales(keyword, top_num, headless)
    except Exception as e:
        print(f"  ❌ {e}")
        results["京东"] = []

    kill_zombies()
    print("📦 [淘宝+天猫] 一次抓取，内存过滤...")
    try:
        tb, tm = search_all(keyword, top_num, top_num)
        results["淘宝"] = tb
        results["天猫"] = tm
    except Exception as e:
        print(f"  ❌ {e}")
        results["淘宝"] = results["天猫"] = []

    kill_zombies()
    print("📦 [SMZDM] 聚合...")
    try:
        results["SMZDM"] = search_smzdm(keyword, top_num)
    except Exception as e:
        print(f"  ❌ {e}")
        results["SMZDM"] = []

    return results


def print_report(results):
    w = 65
    lines = [f"\n{'='*w}", f"{'🛒 四平台比价报告':^{w}}", f"{'='*w}"]
    all_items = []

    for platform, items in results.items():
        lines.append(f"\n{'─'*w}")
        lines.append(f"  📌 {platform} ({len(items)} 条)")
        lines.append(f"  {'商品':<28} {'店铺':<14} {'价格':>8} {'销量':<10}")
        lines.append(f"  {'─'*28} {'─'*14} {'─'*8} {'─'*10}")
        for item in items:
            title = item.get("title", "")[:26]
            shop = item.get("shop", item.get("shop_level", ""))[:12]
            price = item.get("price", 0)
            extra = item.get("sales", item.get("comment", ""))[:8]
            lines.append(f"  {title:<28} {shop:<14} ¥{price:>7.0f} {extra:<10}")
            all_items.append({"platform": platform, "title": title, "price": price, "shop": shop})

    if all_items:
        all_items.sort(key=lambda x: x["price"])
        best = all_items[0]
        lines.append(f"\n{'='*w}")
        lines.append(f"  🏆 最低价: [{best['platform']}] {best['shop']} — ¥{best['price']:.0f}")
        lines.append(f"{'='*w}")

    return "\n".join(lines)


if __name__ == "__main__":
    kw = sys.argv[1] if len(sys.argv) > 1 else "iPhone 17 白色 256G"
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    report = compare(kw, n, headless=False)
    print(print_report(report))
