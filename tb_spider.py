"""
淘宝/天猫爬虫 - 文本提取版
"""

import json, time, re, sys
from pathlib import Path
import undetected_chromedriver as uc

ROOT = Path(__file__).parent
COOKIE_FILE = ROOT / "tb_cookie.json"


def _scrape(keyword):
    """抓取原始文本"""
    driver = uc.Chrome(version_main=150)
    try:
        if COOKIE_FILE.exists():
            driver.get("https://www.taobao.com")
            time.sleep(3)
            with open(COOKIE_FILE) as f:
                for c in json.load(f):
                    try: driver.add_cookie(c)
                    except: pass

        driver.get(f"https://main.m.taobao.com/search/index.html?q={keyword}")
        time.sleep(5)
        for _ in range(4):
            driver.execute_script("window.scrollBy(0, 800)")
            time.sleep(2)

        text = driver.find_element("tag name", "body").text
        
        with open(COOKIE_FILE, "w", encoding="utf-8") as f:
            json.dump(driver.get_cookies(), f, ensure_ascii=False)
        
        return text
    finally:
        try: driver.quit()
        except: pass


def parse_products(text, tmall_only=False):
    """从文本中解析商品"""
    # 按"进店"或"付款"分段
    # 商品块模式: 标题 → 规格 → ¥价格 → 销量 → 店铺 → 进店
    goods = []
    
    # 用正则找商品块
    pattern = re.compile(
        r'([^\n]{10,80}?)\n'           # 标题
        r'(?:.*?\n)*?'                  # 跳过规格
        r'¥\s*\n?\s*([\d,]+)\.?\s*\n?\s*(\d+)?'  # 价格（可能跨行）
        r'.*?'                          # 跳过中间
        r'(\d+[+万]?人?付款|[\d.]+[万+]?人?付款|[\d.]+[万+]?已售)'  # 销量
        r'.*?\n'                        
        r'(?:包邮|运费.*?)?\n?'         # 包邮标签
        r'([^\n]{2,20}(?:店|专营|旗舰|官方|数码|科技).*?)\n'  # 店铺
        r'.*?进店',                     # 进店标记
        re.DOTALL
    )
    
    matches = pattern.findall(text)
    
    for m in matches:
        title, price_int, price_dec, sales, shop = m
        title = title.strip()
        price = float(price_int.replace(',', '')) if price_int else 0
        if price_dec:
            price += float(price_dec) / (10 ** len(price_dec))
        
        # 判断平台
        is_tmall = bool(re.search(r'天猫|旗舰|专[卖营]|tmall', title + shop, re.I))
        
        if tmall_only and not is_tmall:
            continue
        if not tmall_only and is_tmall:
            continue
        
        # 店铺等级
        if re.search(r'天猫|tmall', title + shop, re.I):
            if '旗舰' in shop: level = '旗舰店'
            elif re.search(r'专[卖营]', shop): level = '专营店'
            else: level = '天猫'
        else:
            level = '淘宝店'
        
        goods.append({
            "title": title[:60], "price": price,
            "sales": sales.strip(), "shop": shop.strip(),
            "shop_level": level,
            "platform": "天猫" if is_tmall else "淘宝",
        })
    
    # 如果正则没匹配到，用更简单的方式
    if not goods:
        # 按 ¥ 分割
        parts = text.split("¥")
        for part in parts[1:]:
            lines = [l.strip() for l in part.split("\n") if l.strip()]
            if len(lines) < 3: continue
            
            price = 0
            pm = re.match(r'([\d,]+)\.?\s*(\d+)?', lines[0])
            if not pm and len(lines) > 1:
                pm = re.match(r'([\d,]+)\.?\s*(\d+)?', lines[1])
            if pm:
                price = float(pm.group(1).replace(',', ''))
                if pm.group(2):
                    price += float(pm.group(2)) / (10 ** len(pm.group(2)))
            if price == 0: continue
            
            # 向前找标题
            idx = text.find("¥" + lines[0]) if lines[0] in text else text.find("¥\n" + lines[0])
            before = text[max(0, idx-150):idx].strip().split("\n")
            title = ""
            for l in reversed(before):
                if len(l) > 8 and not re.match(r'\d+mAh|\d+W|商品|搜索|综合|销量', l):
                    title = l.strip()[:60]; break
            
            # 向后找销量和店铺
            after = " ".join(lines[2:8])
            sales = ""
            sm = re.search(r'(\d+[+万]?人?付款|[\d.]+[万+]?已售)', after)
            if sm: sales = sm.group(1)
            
            shop = ""
            for l in lines[3:8]:
                if re.search(r'店|专营|旗舰|官方|数码|科技', l) and len(l) < 20:
                    shop = l.strip(); break
            
            is_tmall = bool(re.search(r'天猫|旗舰|专[卖营]|tmall', title + after, re.I))
            if tmall_only and not is_tmall: continue
            if not tmall_only and is_tmall: continue
            
            level = '旗舰店' if '旗舰' in (shop + title) else ('专营店' if '专营' in shop else ('天猫' if is_tmall else '淘宝店'))
            
            goods.append({
                "title": title or "未知", "price": price,
                "sales": sales or "0", "shop": shop or "未知",
                "shop_level": level,
                "platform": "天猫" if is_tmall else "淘宝",
            })
    
    return goods


def search_tb(keyword, top_num=3):
    text = _scrape(keyword)
    all_goods = parse_products(text, tmall_only=False)
    all_goods.sort(key=lambda x: x["price"])
    return all_goods[:top_num]


def search_tm(keyword, top_num=3):
    text = _scrape(keyword)
    all_goods = parse_products(text, tmall_only=True)
    all_goods.sort(key=lambda x: (
        {"旗舰店": 0, "天猫": 1, "专营店": 2}.get(x["shop_level"], 9),
        x["price"]
    ))
    return all_goods[:top_num]


def search_all(keyword, tb_num=3, tm_num=3):
    """一次抓取，同时返回淘宝和天猫"""
    text = _scrape(keyword)
    tb = parse_products(text, tmall_only=False)
    tb.sort(key=lambda x: x["price"])
    tm = parse_products(text, tmall_only=True)
    tm.sort(key=lambda x: (
        {"旗舰店": 0, "天猫": 1, "专营店": 2}.get(x["shop_level"], 9),
        x["price"]
    ))
    return tb[:tb_num], tm[:tm_num]


if __name__ == "__main__":
    kw = sys.argv[1] if len(sys.argv) > 1 else "iPhone 17"
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    for name, fn in [("淘宝", search_tb), ("天猫", search_tm)]:
        print(f"\n{name} [{kw}] TOP{n}:")
        for i, g in enumerate(fn(kw, n), 1):
            print(f"  {i}. [{g['shop_level']}] {g['shop'][:12]} | {g['title'][:35]} ¥{g['price']:.0f} ({g['sales']})")
