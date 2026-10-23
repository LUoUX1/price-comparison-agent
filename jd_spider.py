"""
京东爬虫 - 含店铺提取 + 优先级过滤
"""

import asyncio, json, os, random, re, sys
from pathlib import Path
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

ROOT = Path(__file__).parent
COOKIE_PATH = ROOT / "jd_cookie.json"

SHOP_PRIORITY = {"自营": 1, "京东自营": 1, "旗舰店": 2, "专卖店": 3, "专营店": 3}


def extract_shop(text):
    """从商品文本提取店铺名和等级"""
    # 自营
    if "京东自营" in text or "自营" in text:
        return "京东自营", "自营"
    # 旗舰店
    m = re.search(r"(.{2,15}旗舰店)", text)
    if m:
        return m.group(1), "旗舰店"
    # 专卖店/专营店
    m = re.search(r"(.{2,15}[专卖专]营店)", text)
    if m:
        return m.group(1), "专营店"
    # 普通店铺
    lines = [l.strip() for l in text.split("\n") if l.strip() and "¥" not in l and len(l) > 2]
    for l in reversed(lines):
        if "进店" in l or "店" in l:
            return l, "普通"
    return "未知店铺", "普通"


def extract_from_text(text):
    price = 0
    m = re.search(r"¥\s*(\d+\.?\d*)", text)
    if m:
        price = float(m.group(1))
    comment = "0条评价"
    for p in [r"(\d+\.?\d*万?\+?条?评价)", r"已售(\d+\.?\d*万?\+?)",
              r"(\d+\.?\d*万?\+?人?评价)", r"(\d+\.?\d*万?\+?条评论)"]:
        m = re.search(p, text)
        if m:
            comment = m.group(1) if m.lastindex else m.group(0)
            break
    return price, comment


async def wait_for_login(page, timeout=90):
    print("🔐 请扫码登录京东...")
    for i in range(timeout):
        await page.wait_for_timeout(1000)
        if i % 5 == 0: print(f"   等待 ({i}s)...")
        if "passport" not in page.url: return True
    return False


async def _scrape(keyword, top_num=3, headless=True):
    async with Stealth().use_async(async_playwright()) as p:
        browser = await p.chromium.launch(
            headless=headless,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0",
            viewport={"width": 1920, "height": 1080},
        )
        if COOKIE_PATH.exists():
            with open(COOKIE_PATH, "r", encoding="utf-8") as f:
                await context.add_cookies(json.load(f))

        page = await context.new_page()
        url = f"https://search.jd.com/Search?keyword={keyword}&enc=utf-8"
        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)

        if "passport" in page.url:
            if not await wait_for_login(page): return []
            page = await context.new_page()
            await page.goto(url, wait_until="load")
            await page.wait_for_timeout(5000)

        for _ in range(3):
            await page.evaluate("window.scrollBy(0, 2800)")
            await page.wait_for_timeout(random.randint(2000, 3500))

        raw = await page.evaluate("""() => {
            const items = document.querySelectorAll('[data-sku]');
            return Array.from(items).map(el => {
                const sku = el.getAttribute('data-sku');
                const tm = el.outerHTML.match(/title="([^"]+)"/);
                return {sku, title: tm ? tm[1] : '', text: el.innerText};
            }).filter(x => x.sku && x.sku !== '0' && x.title);
        }""")

        cookies = await context.cookies()
        with open(COOKIE_PATH, "w", encoding="utf-8") as f:
            json.dump(cookies, f, ensure_ascii=False)
        await browser.close()

        goods = []
        for r in raw:
            price, comment = extract_from_text(r["text"])
            shop_name, shop_level = extract_shop(r["text"])
            title = r["title"]
            if price > 0:
                goods.append({
                    "title": title, "price": price, "comment": comment,
                    "url": f"https://item.jd.com/{r['sku']}.html",
                    "shop": shop_name, "shop_level": shop_level,
                    "priority": SHOP_PRIORITY.get(shop_level, 99),
                })

        # 去重: 相同 title+price 的只保留一个
        seen = set()
        deduped = []
        for g in goods:
            key = (g["title"][:50], g["price"])
            if key not in seen:
                seen.add(key)
                deduped.append(g)

        # 按优先级排序（越小越优先），同优先级按评价数
        deduped.sort(key=lambda x: (x["priority"], -int("".join(c for c in x["comment"] if c.isdigit()) or 0)))
        return deduped[:top_num]


def get_jd_top_sales(keyword, top_num=3, headless=True):
    return asyncio.run(_scrape(keyword, top_num, headless))
