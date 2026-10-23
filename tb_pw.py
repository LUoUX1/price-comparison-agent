"""
淘宝/天猫搜索 - Playwright + Stealth 版
"""
import asyncio, json, re, sys
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path(__file__).parent
TB_COOKIE = ROOT / "tb_cookie.json"


async def search_tb(keyword, top_num=5):
    results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()

        # 加载 cookie
        if TB_COOKIE.exists():
            with open(TB_COOKIE) as f:
                cookies = json.load(f)
            await context.add_cookies(cookies)

        page = await context.new_page()

        try:
            url = f"https://main.m.taobao.com/search/index.html?q={keyword}"
            print(f"  访问: {url}")
            await page.goto(url, timeout=30000, wait_until="domcontentloaded")
            await page.wait_for_timeout(5000)

            # 滚动加载
            for _ in range(4):
                await page.evaluate("window.scrollBy(0, 800)")
                await page.wait_for_timeout(2000)

            # 保存 cookie
            cookies = await context.cookies()
            with open(TB_COOKIE, "w", encoding="utf-8") as f:
                json.dump(cookies, f, ensure_ascii=False)

            # 获取页面文本
            text = await page.evaluate("document.body.innerText")
        except Exception as e:
            print(f"  页面加载错误: {e}")
            text = await page.evaluate("document.body.innerText")
        finally:
            await browser.close()

    # 解析商品
    return _parse_tb(text, top_num)


def _parse_tb(text, top_num):
    goods = []
    # 按 ¥ 分割
    parts = text.split("¥")
    for part in parts[1:]:
        lines = [l.strip() for l in part.split("\n") if l.strip()]
        if len(lines) < 2:
            continue

        # 解析价格
        price = 0
        for line in lines[:3]:
            m = re.match(r'([\d,]+)\.?\s*(\d+)?', line)
            if m:
                price = float(m.group(1).replace(',', ''))
                if m.group(2):
                    price += float(m.group(2)) / (10 ** len(m.group(2)))
                break
        if price == 0 or price < 10:
            continue

        # 标题 - 在价格之前的文本中找（放宽过滤条件）
        idx = text.find("¥" + lines[0]) if lines[0] in text else -1
        title = ""
        if idx > 0:
            before = text[max(0, idx - 250):idx].strip().split("\n")
            for l in reversed(before):
                l = l.strip()
                # 放宽：只过滤明显的界面文字，不再过滤含数字的标题
                if len(l) > 6 and not re.search(r'^(商品|搜索|综合|销量|筛选|排序|推荐|价格)$', l):
                    # 过滤纯界面 UI 文字
                    if re.search(r'[a-zA-Z\u4e00-\u9fff]', l):  # 必须含中文或字母
                        title = l[:100]
                        break
        if not title:
            # 尝试从 block 前面几行提取
            for l in lines:
                l = l.strip()
                if len(l) > 10 and re.search(r'[a-zA-Z\u4e00-\u9fff]', l) and not re.match(r'^\d+', l):
                    title = l[:100]
                    break
        if not title:
            title = "未知商品"

        # 销量
        after = " ".join(lines[2:])
        sales = ""
        sm = re.search(r'(\d+[+万]?人?付款|[\d.]+[万+]?已售|\d+\+人付款)', after)
        if sm:
            sales = sm.group(1)

        # 店铺（扩大匹配范围）
        shop = ""
        for l in lines:
            if re.search(r'店|专营|旗舰|官方|数码|科技|商城|专卖|直营|品牌', l) and len(l) < 30:
                shop = l.strip()
                break

        # 判平台
        is_tmall = bool(re.search(r'天猫|tmall|旗舰|专[卖营]', title + after, re.I))

        # 店铺等级
        if '旗舰' in (shop + title):
            level = '旗舰店'
        elif re.search(r'专[卖营]', shop):
            level = '专营店'
        elif is_tmall:
            level = '天猫'
        else:
            level = '淘宝店'

        goods.append({
            "title": title[:60],
            "price": price,
            "sales": sales or "N/A",
            "shop": shop or "未知",
            "shop_level": level,
            "platform": "天猫" if is_tmall else "淘宝",
        })

    # 排序：淘宝低价优先，天猫旗舰优先
    tb_items = [g for g in goods if g["platform"] == "淘宝"]
    tm_items = [g for g in goods if g["platform"] == "天猫"]

    tb_items.sort(key=lambda x: x["price"])
    tm_items.sort(key=lambda x: (
        {"旗舰店": 0, "天猫": 1, "专营店": 2}.get(x["shop_level"], 9),
        x["price"]
    ))

    return tb_items[:top_num], tm_items[:top_num]


if __name__ == "__main__":
    kw = sys.argv[1] if len(sys.argv) > 1 else "Dell电脑充电器"
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 5

    print(f"\n🔍 淘宝+天猫搜索: {kw}\n")
    tb, tm = asyncio.run(search_tb(kw, n))

    print(f"\n{'='*70}")
    print(f"📌 淘宝 (价格升序) TOP{len(tb)}:")
    print(f"{'='*70}")
    for i, g in enumerate(tb, 1):
        print(f"  {i}. [{g['shop_level']}] {g['shop'][:15]} | {g['title'][:40]} ¥{g['price']:.0f} ({g['sales']})")

    print(f"\n{'='*70}")
    print(f"📌 天猫 (旗舰优先) TOP{len(tm)}:")
    print(f"{'='*70}")
    for i, g in enumerate(tm, 1):
        print(f"  {i}. [{g['shop_level']}] {g['shop'][:15]} | {g['title'][:40]} ¥{g['price']:.0f} ({g['sales']})")

    # 最低价
    all_items = tb + tm
    if all_items:
        all_items.sort(key=lambda x: x["price"])
        best = all_items[0]
        print(f"\n{'='*70}")
        print(f"  🏆 淘宝+天猫最低价: [{best['platform']}] {best['shop']} ¥{best['price']:.0f}")
        print(f"     {best['title']}")
        print(f"{'='*70}")
