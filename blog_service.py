#pip install selenium pandas matplotlib google-generativeai webdriver-manager openpyxl
#pip install streamlit
#파일 탐색기에 해당 폴더를 오른쪽 클릭 '통합 터미널에서 열기'->터미널에서 streamlit run blog_service.py
#https://nblog-analyzer-by-chaeyeon.streamlit.app/
#Streamlit Cloud 대시보드 -> Settings -> Secrets 메뉴에 아래 내용을 정확히 입력하고 저장(Save)
# GEMINI_API_KEY = "AIzaSyBPIVefQONoPg1bIWxBjP97b3OBhRnsYho"

import streamlit as st
import pandas as pd
import google.generativeai as genai
import matplotlib.pyplot as plt
import re
import time
import matplotlib.font_manager as fm 
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from collections import Counter

# --- 1. 페이지 및 폰트 설정 ---
st.set_page_config(page_title="이채연의 네이버 블로그 AI 분석기", layout="wide")

def set_korean_font():
    try:
        nanum_path = '/usr/share/fonts/truetype/nanum/NanumGothic.ttf'
        font_names = [f.name for f in fm.fontManager.ttflist]
        if 'NanumGothic' in font_names:
            plt.rcParams['font.family'] = 'NanumGothic'
        elif 'Malgun Gothic' in font_names:
            plt.rcParams['font.family'] = 'Malgun Gothic'
        else:
            fe = fm.FontEntry(fname=nanum_path, name='NanumGothic')
            fm.fontManager.ttflist.insert(0, fe)
            plt.rcParams['font.family'] = fe.name
        plt.rcParams['axes.unicode_minus'] = False
    except:
        plt.rcParams['font.family'] = 'DejaVu Sans'

set_korean_font()

# --- 2. AI 모델 설정 ---
try:
    if "GEMINI_API_KEY" in st.secrets:
        GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
        genai.configure(api_key=GEMINI_API_KEY)
        ai_model = genai.GenerativeModel('models/gemini-flash-latest')
    else:
        st.error("API 키가 Secrets에 설정되지 않았습니다.")
        st.stop()
except Exception as e:
    st.error(f"API 설정 중 오류: {e}")
    st.stop()

def enter_frame(driver):
    driver.switch_to.default_content()
    try:
        WebDriverWait(driver, 10).until(
            EC.frame_to_be_available_and_switch_to_it((By.NAME, "mainFrame"))
        )
        return True
    except:
        return False

# --- 3. 웹 화면 UI ---
st.title("이채연의 네이버 블로그 AI 분석기🤖")
st.write("아이디를 입력하면 각 게시글을 AI가 분석하여 인물 특징과 요약 리포트를 표로 작성합니다.")

with st.sidebar:
    st.header("⚙️ 설정")
    target_id = st.text_input("네이버 블로그 ID", placeholder="예: chaeyeonlee_1106")
    analyze_btn = st.button("전체 게시글 분석 시작 🚀")
    st.info("글 개수가 많으면 분석에 시간이 다소 소요됩니다.")

if analyze_btn and target_id:
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.binary_location = "/usr/bin/chromium" 

        status_text.text("🔍 서버 브라우저 엔진 설정 중...")
        
        try:
            service = Service("/usr/bin/chromedriver")
            driver = webdriver.Chrome(service=service, options=chrome_options)
        except:
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        
        driver.get(f"https://blog.naver.com/{target_id}")
        time.sleep(2)
        all_post_links = []
        current_page = 1
        
        status_text.text("🔗 모든 게시글 링크를 수집하는 중...")
        while True:
            enter_frame(driver)
            try:
                open_btn = WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "a.btn_openlist, #toplistBtn"))
                )
                if "열기" in open_btn.text:
                    driver.execute_script("arguments[0].click();", open_btn)
                    time.sleep(0.8)
            except:
                pass

            links = driver.find_elements(By.CSS_SELECTOR, "a._setTopListUrl")
            for link in links:
                raw_url = link.get_attribute('href')
                log_no_match = re.search(r'logNo=(\d+)', raw_url)
                if log_no_match:
                    clean_url = f"https://blog.naver.com/{target_id}/{log_no_match.group(1)}"
                    if clean_url not in all_post_links:
                        all_post_links.append(clean_url)
            
            status_text.text(f"🔗 링크 수집 중: {current_page}페이지 (누적 {len(all_post_links)}개)")
            
            if current_page >= 3: break # 너무 많은 양을 방지하기 위해 3페이지로 제한 (조절 가능)
            
            next_p = current_page + 1
            try:
                page_btn = driver.find_element(By.LINK_TEXT, str(next_p))
                driver.execute_script("arguments[0].click();", page_btn)
                time.sleep(1)
                current_page = next_p
            except:
                break 

        data = []
        total_links = len(all_post_links)
        
        if total_links == 0:
            st.error("수집된 게시글이 없습니다.")
            st.stop()

        # 게시글 상세 데이터 수집
        for i, url in enumerate(all_post_links):
            status_text.text(f"📝 데이터 수집 중: {i+1}/{total_links}")
            driver.get(url)
            time.sleep(0.7)
            enter_frame(driver)
            
            try:
                title = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".se-title-text, .pcol1"))
                ).text.strip()
                content = driver.find_element(By.CSS_SELECTOR, ".se-main-container, #postViewArea").text.strip()[:1000] # 분석을 위해 앞부분 1000자만 사용
                
                data.append({"제목": title, "내용": content})
            except:
                continue
            progress_bar.progress(int((i + 1) / total_links * 100))

        if data:
            status_text.text("🤖 AI가 게시글별로 심층 분석 중입니다...")
            analysis_results = []
            
            for item in data:
                # --- AI 프롬프트: 개별 글 분석 및 3열 구성 ---
                prompt = (
                    f"블로그 제목: {item['제목']}\n내용 요약: {item['내용']}\n\n"
                    "위 내용을 분석해서 다음 두 항목을 작성해줘:\n"
                    "1. 인물 특징: 이 글에서 나타나는 작성자의 성격이나 특징을 1문장으로 써줘.\n"
                    "2. 3줄 요약: 글의 '주제', '분위기', '타겟'을 각각 명시해서 3문장으로 요약해줘.\n"
                    "결과에 HTML 태그(<br> 등)는 절대 쓰지 마."
                )
                
                try:
                    res = ai_model.generate_content(prompt).text.strip()
                    # 응답에서 인물 특징과 요약 부분을 분리 (AI 응답 형식에 맞게 파싱)
                    parts = res.split('\n')
                    persona = next((p for p in parts if "인물 특징" in p), "분석 중").replace("1. 인물 특징:", "").strip()
                    summary = "\n".join([p for p in parts if "주제" in p or "분위" in p or "타겟" in p or "요약" in p])
                    
                    analysis_results.append({
                        "블로그 제목": item['제목'],
                        "인물 특징": persona,
                        "3줄 요약 (주제/분위기/타겟)": summary
                    })
                except:
                    continue

            st.balloons()
            st.header(f"📊 {target_id} 블로그 게시글별 AI 분석 리포트")
            st.divider()

            # --- 결과 표 출력 ---
            result_df = pd.DataFrame(analysis_results)
            st.table(result_df) # 3열 표로 모든 글 내용 출력

    except Exception as e:
        st.error(f"⚠️ 오류 발생: {e}")
    finally:
        driver.quit()
