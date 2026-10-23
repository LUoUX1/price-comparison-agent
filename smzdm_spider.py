"""
SMZDM 多平台比价爬虫
"""

import time, re, sys, subprocess
import undetected_chromedriver as uc


def search_smzdm(keyword, top_num=5):
    subprocess.run("taskkill /F /IM chrome.exe 2>nul", shell=True, capture_output=True)
    time.sleep(1)
    driver = uc.Chrome(version_main=150)
    try:
        driver.get(f"https://search.smzdm.com/?c=home&s={keyword}&order=score")
        time.sleep(5)
        for _ in range(3):
            driver.execute_script("window.scrollBy(0, 600)")
            time.sleep(1.5)

        text = driver.find_element("tag name", "body").text
    finally:
        try: driver.quit()
        except: pass

    # 按"好价"分块解析
    blocks = text.split("好价")
    goods = []
    seen = set()

    for block in blocks[1:]:
        lines = [l.strip() for l in block.split("\n") if l.strip()]
        if len(lines) < 3: continue

        title = ""
        for line in lines:
            if len(line) > 8 and "¥" not in line and "元" not in line and not line[0].isdigit():
                title = line[:80]; break
        if not title or title in seen: continue
        seen.add(title)

        price = 0
        for line in lines:
            m = re.search(r"(\d+\.?\d*)\s*元", line)
            if m: price = float(m.group(1)); break
        if price == 0: continue

        platform = ""
        for kw in ["京东", "天猫", "淘宝", "拼多多", "苏宁", "抖音", "考拉"]:
            if kw in block: platform = kw; break

        shop = ""
        m = re.search(r"(自营|.{2,12}(?:旗舰|专卖|专营)店)", block)
        if m: shop = m.group(1)
        if not shop: shop = platform

        goods.append({
            "title": title, "price": price,
            "platform": platform or "多平台",
            "shop": shop, "shop_level": "好价",
            "source": "SMZDM",
        })
        if len(goods) >= top_num: break

    return goods


if __name__ == "__main__":
    kw = sys.argv[1] if len(sys.argv) > 1 else "键盘"
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    for i, g in enumerate(search_smzdm(kw, n), 1):
        print(f"{i}. [{g['platform']}] {g['shop']} | {g['title'][:45]}")
        print(f"   💰 ¥{g['price']}")
        print()
