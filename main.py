import requests
from bs4 import BeautifulSoup
import time
import random



names=[
    "coco.lovelock",
    "lexi.lore",
    "kenzie.reeves",
    "eva.elfie",
    "reislin",
    "marica.haze",
    "lulu.chu",
    "lily.larimar",
    "elle.lee"


    
]

for name in names:
    try:
        with open(f'{name}.txt', 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()  # .strip() 去掉换行符
            print(first_line)
    except:
        first_line="AAA"


    links = []
    page = 1
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0 Safari/537.36"
    }

    while True:
        url = f"https://rargb.to/search/{page}/?search={name}"
        print(f"正在爬取第 {page} 页: {url}")

        # ====== 死循环重试机制 ======
        while True:
            try:
                resp = requests.get(url, headers=headers, timeout=15)
                resp.raise_for_status()
                html = resp.text
                break  # 成功则跳出重试循环
            except Exception as e:
                print(f"请求失败，重试中... 错误：{e}")
                time.sleep(random.uniform(3, 6))  # 等几秒再试

        soup = BeautifulSoup(html, "html.parser")

        # 找到所有<tr class="lista2"> 元素
        rows = soup.find_all("tr", class_="lista2")

        # 如果没有找到，说明已经到最后一页，退出循环
        if not rows:
            print("没有找到更多结果，爬取结束。")
            break

        # 从每个<tr>中提取链接
        for row in rows:
            a_tag = row.find("a", href=True, title=True)
            if a_tag:
                link = a_tag["href"]
                full_link = "https://rargb.to" + link
                if full_link == first_line:
                    break
                links.append(full_link)

        print(f"第 {page} 页提取到 {len(rows)} 条链接")

        # 随机延迟防封
        time.sleep(random.uniform(1, 3))

        page += 1  # 翻页继续

    print("\n==== 爬取完成 ====")
    print(f"共提取 {len(links)} 个链接：")



    # =================  以下为新增：逐条解析详情页 =================
    infohashes = []

    for idx, link in enumerate(links, 1):
        print(f"\n[{idx:>3}/{len(links)}] 正在解析：{link}")
        # 过滤低清关键词
        if any(k in link.lower() for k in ('720', '480', '360', '240')):
            print(f"    检测到低清/枪版关键词，跳过")
            continue

        while True:                       # ===== 死循环重试机制 =====
            try:
                resp = requests.get(link, headers=headers, timeout=15)
                resp.raise_for_status()
                html = resp.text
                break                     # 成功拿到 HTML
            except Exception as e:
                print(f"    请求失败，重试中... 错误：{e}")
                time.sleep(random.uniform(3, 6))
                continue                  # 继续重试

        # 解析
        soup = BeautifulSoup(html, "html.parser")
        magnet_tag = soup.select_one('a[href^="magnet:?xt=urn:btih:"]')
        if not magnet_tag:
            print("    未找到 magnet 链接，跳过")
            continue

        magnet = magnet_tag["href"]
        # 正则提取 40 位 info-hash（不区分大小写）
        import re
        m = re.search(r"xt=urn:btih:([0-9A-Fa-f]{40})", magnet)
        if not m:
            print("    未能解析 info-hash，跳过")
            continue

        info_hash = m.group(1).upper()   # 统一大写
        infohashes.append(info_hash)
        print(f"    提取到 info-hash：{info_hash}")

        # 随机延迟，防封
        time.sleep(random.uniform(1, 2.5))

    print("\n==== info-hash 收集完成 ====")
    print(f"共拿到 {len(infohashes)} 条 info-hash：")



    # =================  无条件 w 模式写入 infohash.txt =================
    # 新内容
    new_content = links[0] + "\n" + "\n".join(infohashes) + "\n"

    # 读取原内容（如果文件存在）
    try:
        with open(f"{name}.txt", "r", encoding="utf-8") as f:
            original_content = f.read()
    except FileNotFoundError:
        original_content = ""

    # 写入新内容 + 原内容
    with open(f"{name}.txt", "w", encoding="utf-8") as f:
        f.write(new_content + original_content)

    print(f"\n已前面追加写入txt  共 {len(infohashes)} 条")