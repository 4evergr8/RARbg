import requests
from bs4 import BeautifulSoup
import time
import random
import re

names = [




    "coco.lovelock",
    "elle.lee",
    "eva.elfie",
    "kenzie.reeves",
    "lexi.lore",
    "lily.larimar",
    "lulu.chu",
    "marica.haze",
    "molly.redwolf",
    "mollyredwolf",
    "reislin",
    "sola.zola",
    "solazola",
    "vina.sky",








]

# ==================== 清晰度优先级 ====================
RESOLUTION_RANK = {
    '2160p': 6, '4k': 6,
    '1080p': 4,
    '720p': 2, '480p': 1, '360p': 1
}


def get_resolution_score(title: str) -> int:
    t = title.lower()
    for res, score in RESOLUTION_RANK.items():
        if res in t:
            return score
    return 0


def normalize_title(title: str) -> str:
    t = title.lower()

    # Step 1: 把点换成空格（coco.lovelock → coco lovelock）
    t = t.replace('.', ' ')

    # Step 2: 只提取「站点名 + 日期 + 演员 + 片名」这一段，后面的一律砍掉
    # 匹配例子：
    # deeper-25-01-30-coco-lovelock-and-madi-collins-hot-to-go-xxx-1080p...
    # purgatoryx-25-02-28-coco-lovelock-and-savanah-storm-xxx-2160p...
    match = re.search(r'^([^-/]+-\d{2,4}-\d{2}-\d{2}-.+?)-xxx-', t)
    if match:
        key = match.group(1)  # 就是站点-日期-演员-片名 那一段
    else:
        # 万一没有 -xxx-（极少数），就直接砍到第一个清晰度或组名前
        key = re.sub(r'-\d{3,4}p.*$|-(hevc|x265|wrb|nbq|p2p|xc).*', '', t)

    # Step 3: 统一连字符为空格，压缩多余空格
    key = re.sub(r'[-_]+', ' ', key)
    key = re.sub(r'\s+', ' ', key).strip()

    return key


# ============================================================

for name in names:
    # 读取断点
    try:
        with open(f'{name}.txt', 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
    except:
        first_line = "AAA"

    links = []
    page = 1
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    # ====================== 第一步：抓取所有链接 ======================
    # ====================== 第一步：抓取所有链接 ======================
    print(f"\n=== 开始爬取 {name} ===")
    page = 1
    empty_page_count = 0
    MAX_EMPTY_PAGES = 5
    reached_breakpoint = False  # 新增标志位

    while True:
        url = f"https://rargb.to/search/{page}/?search={name} -720p -480p -hevc"
        print(url)

        page_has_content = False

        while True:
            try:
                r = requests.get(url, headers=headers, timeout=15)
                r.raise_for_status()
                soup = BeautifulSoup(r.text, "html.parser")
                rows = soup.find_all("tr", class_="lista2")

                if not rows:
                    print(f"第 {page} 页为空（无 lista2 行）")
                else:
                    print(f"第 {page} 页抓到 {len(rows)} 条")
                    page_has_content = True
                    empty_page_count = 0

                    for row in rows:
                        a = row.find("a", href=True, title=True)
                        if a:
                            full = "https://rargb.to" + a["href"]

                            # 遇到断点 → 立刻停止当前演员
                            if full == first_line:
                                print("检测到断点文件，立即停止当前演员抓取！")
                                if full not in links:  # 防止重复
                                    links.append(full)
                                reached_breakpoint = True
                                break

                            links.append(full)

                    # 这一页解析完了，如果已经触发断点就跳出去
                    if reached_breakpoint:
                        break

                break  # 请求成功，退出重试循环

            except Exception as e:
                print(f"第 {page} 页请求失败，重试... {e}")
                time.sleep(5)

        # ======== 断点优先级最高：一旦触发，立即结束当前演员所有后续页面 ========
        if reached_breakpoint:
            print(f"断点终止，停止翻页（当前已抓 {len(links)} 条）")
            break

        # ======== 正常空页判断 ========
        if not page_has_content:
            empty_page_count += 1
            print(f"连续空页次数: {empty_page_count}/{MAX_EMPTY_PAGES}")
            if empty_page_count >= MAX_EMPTY_PAGES:
                print("连续 5 次空页，判定已到底，正常结束抓取")
                break
        else:
            empty_page_count = 0

        time.sleep(random.uniform(1.5, 3.5))
        page += 1

    print(f"第一步完成，共抓到 {len(links)} 条链接\n")

    # ====================== 第二步：全局分析，选出每部片的最高清版本 ======================
    best_per_movie = {}  # norm_title -> {'link': xxx, 'score': 6, 'raw_title': xxx}

    for link in links:
        raw_title = link.split('/torrent/')[-1].rsplit('.html', 1)[0]
        norm = normalize_title(raw_title)
        score = get_resolution_score(raw_title)

        # 直接过滤垃圾
        if score <= 2:
            continue

        if norm not in best_per_movie or score > best_per_movie[norm]['score']:
            best_per_movie[norm] = {
                'link': link,
                'score': score,
                'raw_title': raw_title
            }

    final_links_to_fetch = [info['link'] for info in best_per_movie.values()]
    print(f"第二步全局筛选完成！")
    print(f"最终胜出（最高清）版本数量：{len(final_links_to_fetch)} 条（每部片只留一个）\n")

    # ====================== 第三步：提取 info-hash（网络错误死循环重试，内容缺失直接跳过） ======================
    final_hashes = []
    skipped_links = []  # 可选：记录被跳过的链接，方便后续分析

    for idx, link in enumerate(final_links_to_fetch, 1):
        raw_title = link.split('/torrent/')[-1].rsplit('.html', 1)[0]
        print(f"[{idx}/{len(final_links_to_fetch)}] 正在提取 → {raw_title[:80]}...")

        while True:  # 死循环，只针对网络问题
            try:
                r = requests.get(link, headers=headers, timeout=20)
                r.raise_for_status()  # 网络成功，进入解析阶段
                soup = BeautifulSoup(r.text, "html.parser")
                magnet_a = soup.select_one('a[href^="magnet:?xt=urn:btih:"]')

                # —— 成功拿到页面，但没有 magnet：说明种子被删或被隐藏 → 跳过，不再重试
                if not magnet_a:
                    print(f"    magnet 不存在，已被删除或隐藏，跳过 → {link}")
                    skipped_links.append(link)
                    break  # 跳出死循环，进入下一个种子

                magnet = magnet_a["href"]
                m = re.search(r"xt=urn:btih:([0-9A-Fa-f]{40})", magnet)
                if not m:
                    print(f"    info-hash 解析失败，页面异常，跳过 → {link}")
                    skipped_links.append(link)
                    break

                info_hash = m.group(1).upper()
                final_hashes.append(info_hash)
                print(f"    成功 → {info_hash}")
                break  # 成功了，跳出死循环

            except Exception as e:
                # —— 所有网络相关问题（超时、502、连接错误、Cloudflare 等）→ 打印并继续重试
                print(f"    网络异常，正在重试... ({e})")
                time.sleep(5)

        time.sleep(random.uniform(1, 2))  # 礼貌间隔

    # ====================== 第四步：写入文件 + 美化打印 ======================
    added_count = len(final_hashes)  # 本轮新增数量

    if links:  # 有抓到任何页面记录就更新断点
        new_breakpoint = links[0]  # 原始最新链接，用于断点续爬
        latest_filename = new_breakpoint.split('/torrent/')[-1].rsplit('.html', 1)[0]

        new_content = new_breakpoint + "\n" + "\n".join(final_hashes) + "\n"

        old_content = ""
        try:
            with open(f"{name}.txt", "r", encoding="utf-8") as f:
                old_content = f.read()
        except:
            pass

        with open(f"{name}.txt", "w", encoding="utf-8") as f:
            f.write(new_content + old_content)

        print("\n" + "=" * 80)
        print(f"          【{name.upper()}】 本轮任务全部完成！")
        print("=" * 80)
        print(f"本次抓取页面       : 第 1～{page - 1} 页（共 {len(links)} 条原始记录）")
        print(f"最高清版本胜出     : {len(final_links_to_fetch)} 部")
        print(f"成功新增 info-hash : {added_count} 条  ←←←←←←←←←←←←←←←←←←←←←")
        if added_count > 0:
            print(f"最新一部作品       : {latest_filename}")
        print(f"断点已更新         : {latest_filename}")
        print(f"文件已保存         : {name}.txt  （历史总量 ≈ {old_content.count('info-hash'):} 条）")
        print("=" * 80 + "\n")

    else:
        print("\n" + "=" * 80)
        print(f"          【{name.upper()}】 本轮无任何新内容")
        print("可能原因：网络波动 / 搜索被临时屏蔽 / 真的没有新片")
        print("断点未更新，下次会从上次位置继续尝试")
        print("=" * 80 + "\n")
