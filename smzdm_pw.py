"""
SMZDM搜索 - Playwright版 (v5.1 - 修复验证码绕过)
关键：清理僵尸Chrome进程 + wait_until='load' + 长等待
"""
import asyncio, re, sys
from playwright.async_api import async_playwright


async def search_smzdm(keyword, top_num=5):
    goods = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0",
            viewport={"width": 1920, "height": 1080},
        )
        page = await context.new_page()

        try:
            url = f"https://search.smzdm.com/?c=faxian&s={keyword}&order=score"
            print(f"  访问: {url}")
            await page.goto(url, timeout=30000, wait_until="load")
            print("  页面加载完成，等待渲染...")
            await page.wait_for_timeout(8000)

            # 多次滚动触发懒加载
            for _ in range(5):
                await page.evaluate("window.scrollBy(0, 800)")
                await page.wait_for_timeout(2000)

            text = await page.evaluate("document.body.innerText")
        except Exception as e:
            print(f"  错误: {e}")
            text = ""
        finally:
            await browser.close()

    if not text:
        print("  ⚠️ body.innerText 为空（可能是验证码拦截）")
        return goods

    # ====== 解析 ======
    # 按 "好价" 分割（发现频道以"好价频道"/"国内优惠"为块头）
    seen = set()
    blocks = text.split("好价")
    
    for block in blocks[1:]:
        lines = [l.strip() for l in block.split("\n") if l.strip()]
        if len(lines) < 3:
            continue

        # 找标题（第一个有意义的长文本行，跳过"好价频道"等标签）
        title = ""
        for line in lines:
            if len(line) > 10 and "元" not in line and "¥" not in line and "去购买" not in line:
                # 跳过头标签
                if line in ("好价频道", "国内优惠", "海淘优惠", "扫码购"):
                    continue
                title = line[:80]
                break
        if not title or title in seen:
            continue
        seen.add(title)

        # 找价格
        price = 0
        for line in lines:
            # 匹配 "6334元" 或 "6334元（需用券）"
            m = re.search(r"(\d+\.?\d*)\s*元", line)
            if m:
                price = float(m.group(1))
                break
        if price == 0 or price < 100:
            continue

        # 找平台
        platform = ""
        for kw in ["京东全球购", "京东自营", "京东", "天猫精选", "天猫国际", "天猫", 
                    "淘宝", "拼多多", "苏宁易购", "抖音商城", "快手电商", "美团"]:
            if kw in " ".join(lines):
                platform = kw
                break

        # 找店铺/来源
        shop = ""
        m = re.search(r"(?:京东|天猫|淘宝|抖音).{0,8}((?:自营|旗舰|专卖|专营|国际)店?)", block)
        if m:
            shop = m.group(1) if m.group(1) else ""

        goods.append({
            "title": title,
            "price": price,
            "platform": platform or "多平台",
            "shop": shop or platform,
            "source": "SMZDM",
        })
        if len(goods) >= top_num:
            break

    return goods


if __name__ == "__main__":
    kw = sys.argv[1] if len(sys.argv) > 1 else "Dell电脑充电器"
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 5

    print(f"\n🔍 SMZDM搜索: {kw}")
    results = asyncio.run(search_smzdm(kw, n))

    print(f"\n{'='*70}")
    for i, item in enumerate(results, 1):
        print(f"  {i}. [{item['platform']}] {item['title'][:55]}")
        print(f"     💰 ¥{item['price']:.0f} | {item.get('shop', 'N/A')}")
        print()

    if not results:
        print("  ⚠️ 未获取到SMZDM结果")
