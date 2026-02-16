import os
import io
import time
import random
import urllib.parse
import requests
import numpy as np
import re
import textwrap
from collections import Counter
from pathlib import Path
from django.conf import settings

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import matplotlib.image as mpimg
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import matplotlib as mpl

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

import glob

def get_pie_chart(game_name, code):
    game_title = str(game_name)
    deck_codes = code

    # 強化瀏覽器設定
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')

    # 自動安裝並使用正確架構的 ChromeDriver
    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    def handle_cookie_consent(driver):
        try:
            consent_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, '//button[text()="Allow all"]'))
            )
            consent_button.click()
            print("✅ 已自動點擊 Allow all 按鈕")
            time.sleep(2)
            return True
        except Exception as e:
            print(f"ℹ️ 沒有發現 Cookie 彈窗或已自動關閉: {str(e)}")
            return False

    results = []

    try:
        # 特殊處理第一筆資料，先處理 Cookie 再重載
        if deck_codes:
            first_code = deck_codes[0]
            print(f"🔍 處理第一筆資料 (Cookie 處理): {first_code}")

            url = f'https://decklog-en.bushiroad.com/ja/view/{first_code}'
            driver.get(url)

            # 處理 Cookie 同意彈窗
            cookie_handled = handle_cookie_consent(driver)

            # 如果處理了 Cookie，重新載入頁面
            if cookie_handled:
                print("🔄 重新載入頁面以獲取資料...")
                time.sleep(2)
                driver.get(url)

            # 開始抓取資料
            try:
                element = WebDriverWait(driver, 15).until(
                    EC.visibility_of_element_located(
                        (By.XPATH, '//p[contains(@class,"preview-top-label-right")]/span')
                    )
                )
                title = driver.execute_script(
                    'return arguments[0].textContent.trim();', element
                )
                if title and len(title) > 0:
                    results.append(title)
                    print(f"✅ 成功抓取 {first_code}: {title}")
                else:
                    print(f"⚠️ 空值內容 {first_code}")
                    results.append(None)
            except Exception as e:
                print(f"❌ 抓取失敗 {first_code}: {str(e)}")
                results.append(None)

        # 處理其餘牌組代碼
        for code in deck_codes[1:]:
            try:
                time.sleep(random.uniform(2, 5))
                url = f'https://decklog-en.bushiroad.com/ja/view/{code}'
                driver.get(url)
                element = WebDriverWait(driver, 15).until(
                    EC.visibility_of_element_located(
                        (By.XPATH, '//p[contains(@class,"preview-top-label-right")]/span')
                    )
                )
                title = driver.execute_script(
                    'return arguments[0].textContent.trim();', element
                )
                if title and len(title) > 0:
                    results.append(title)
                    print(f"✅ 成功抓取 {code}: {title}")
                else:
                    print(f"⚠️ 空值內容 {code}")
                    results.append(None)
            except Exception as e:
                print(f"❌ 抓取失敗 {code}: {str(e)}")
                results.append(None)
    finally:
        driver.quit()

    # 清理並輸出結果
    final_results = [x for x in results if x]
    print("\n最終有效結果：")
    print(final_results)

    # 統計並排序系列
    series_count = Counter(final_results)
    unique_series = sorted(series_count.keys())

    # 建立系列名→英文檔名對應字典
    def safe_english_filename(s):
        s_ascii = re.sub(r'[^\w]', '_', s)
        return s_ascii.lower()

    series_to_filename = {}
    for i, series in enumerate(unique_series):
        safe_name = f"series_{i+1}"
        series_to_filename[series] = safe_name

    # 建立資料夾
    os.makedirs('series_images', exist_ok=True)

    # 下載圖片（只針對不重複系列，且跳過預組商品）
    chrome_options_img = Options()
    chrome_options_img.add_argument('--headless')
    chrome_options_img.add_argument('--disable-gpu')
    chrome_options_img.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options_img.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')
    service_img = ChromeService(ChromeDriverManager().install())
    driver_img = webdriver.Chrome(service=service_img, options=chrome_options_img)
    try:
        for series_name in unique_series:
            try:
                encoded_name = urllib.parse.quote(series_name)
                url = f"https://ws-tcg.com/products/?title={encoded_name}"
                print(f"處理中: {series_name}")
                driver_img.get(url)
                wait = WebDriverWait(driver_img, 10)
                product_list = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "ul.product-list"))
                )
                img_src = None
                for item in product_list.find_elements(By.CSS_SELECTOR, "li"):
                    try:
                        category_label = item.find_element(By.CSS_SELECTOR, "p.category-label span").text
                        if "トライアルデッキ" in category_label:
                            continue
                        img = item.find_element(By.CSS_SELECTOR, "img")
                        img_src = img.get_attribute("src")
                        break
                    except Exception:
                        continue
                if img_src:
                    english_filename = series_to_filename[series_name]
                    file_path = os.path.join('series_images', f"{english_filename}.jpg")
                    if not os.path.exists(file_path):
                        response = requests.get(img_src)
                        if response.status_code == 200:
                            with open(file_path, 'wb') as file:
                                file.write(response.content)
                            print(f"✅ 成功儲存圖片: {file_path}")
                        else:
                            print(f"❌ 圖片下載失敗: HTTP {response.status_code}")
                    else:
                        print(f"✓ 圖片已存在，略過：{file_path}")
                else:
                    print(f"⚠️ 找不到非預組商品圖片: {series_name}")
            except Exception as e:
                print(f"❌ 處理失敗 ({series_name}): {str(e)}")
            time.sleep(random.uniform(1, 3))
    finally:
        driver_img.quit()
        print("圖片爬取完成")

    # 畫圓餅圖
    mpl.rcParams['font.family'] = 'sans-serif'
    mpl.rcParams['font.sans-serif'] = ['Noto Sans CJK TC', 'Noto Sans CJK JP']
    mpl.rcParams['axes.unicode_minus'] = False
    font_path = (
        Path(__file__).resolve().parent
        / 'datasets'
        / 'font'
        / 'NotoSansCJKtc-Bold.otf'
    )
    font_prop = fm.FontProperties(fname=font_path)

    sizes = [series_count[s] for s in unique_series]
    labels = unique_series

    # --- 系列名稱自動換行（8字一行） ---
    def wrap_label(label, width=10):
        return textwrap.fill(label, width=width)

    wrapped_labels = [wrap_label(label, 10) for label in labels]
    percent_labels = [f"{label}\n{size / sum(sizes) * 100:.1f}%" for label, size in zip(labels, sizes)]

    base_colors = ['#57c1c7', '#c9b95e', '#7dd4b1', '#2f7f8e', '#cb8262']
    colors = [base_colors[i % len(base_colors)] for i in range(len(labels))]
    if len(labels) > 1:
        colors[-1] = '#88D7B4'

    explode = [0.1 if count == max(sizes) else 0 for count in sizes]

    fig, ax = plt.subplots(figsize=(14, 12))
    wedges, texts, autotexts = ax.pie(
        sizes,
        labels=wrapped_labels,
        autopct='%1.1f%%',
        startangle=90,
        colors=colors,
        explode=explode,
        shadow={'ox': -0.004, 'oy': -0.004, 'shade': 0.4},
        textprops={'fontsize': 50, 'fontweight': 'bold', 'fontproperties': font_prop},
        labeldistance=1.3,
        pctdistance=0.6  # 讓百分比更靠近圓心
    )

    # --- 百分比標籤永遠在最上層 ---
    for autotext in autotexts:
        autotext.set_zorder(10)
        autotext.set_bbox(dict(facecolor='white', edgecolor='none', boxstyle='round,pad=0.3', alpha=0.7))

    plt.title(game_title, fontweight='bold', fontproperties=font_prop, fontsize=40, pad=80)
    plt.axis('equal')

    legend = plt.legend(
        wedges, percent_labels,
        title="系列名稱",
        loc='upper center',
        bbox_to_anchor=(0.5, -0.12),
        ncol=2,
        prop=font_prop,
        borderaxespad=0.,
        title_fontsize=18
    )
    legend.get_title().set_fontproperties(font_prop)

    # 計算 wedge 角度
    wedge_angles = []
    for wedge in wedges:
        theta1, theta2 = wedge.theta1, wedge.theta2
        mid_angle = np.radians((theta1 + theta2)/2)
        wedge_angles.append(mid_angle)

    max_zoom = 0.45
    min_zoom = 0.25
    size_arr = np.array(sizes)
    zoom_arr = min_zoom + (max_zoom - min_zoom) * (size_arr - size_arr.min()) / (size_arr.max() - size_arr.min() + 1e-8)

    # --- 產品圖放在圓餅外圍 ---
    for i, (series, angle, zoom) in enumerate(zip(labels, wedge_angles, zoom_arr)):
        percentage = (sizes[i] / sum(sizes)) * 100
        if percentage < 5:
            print(f"⏩ 跳過 {series} (佔比 {percentage:.1f}% < 5%)")
            continue

        english_filename = series_to_filename[series]
        img_path = os.path.join('series_images', f"{english_filename}.jpg")
        if os.path.exists(img_path):
            img_radius = 0.95  
            x = img_radius * np.cos(angle)
            y = img_radius * np.sin(angle)
            try:
                img = mpimg.imread(img_path)
                imagebox = OffsetImage(img, zoom=zoom)
                ab = AnnotationBbox(
                    imagebox, (x, y),
                    frameon=False,
                    pad=0,
                    zorder=5  # zorder低於autotext
                )
                ax.add_artist(ab)
            except Exception as e:
                print(f"❌ 無法添加 {series} 的圖片: {str(e)}")

    plt.tight_layout()

    # 儲存到 media/charts
    media_dir = Path(settings.MEDIA_ROOT) / 'charts'
    os.makedirs(media_dir, exist_ok=True)

    filename = f"{game_name}.png"
    save_path = media_dir / filename
    plt.savefig(save_path, dpi=300, bbox_inches='tight', pad_inches=0.4)
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()

    # 清理暫存圖片
    def delete_all_files_in_directory(directory_path):
        files = glob.glob(os.path.join(directory_path, '*'))
        for file in files:
            if os.path.isfile(file):
                os.remove(file)
        print(f"已刪除資料夾 {directory_path} 中所有檔案")
    delete_all_files_in_directory('series_images')

    return buf
