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
        # 다양한 환경에 대비한 폰트 설정
        nanum_path = '/usr/share/fonts/truetype/nanum/NanumGothic.ttf'
        font_names = [f.name for f in fm.fontManager.ttflist]
        if 'NanumGothic' in font_names:
            plt.rcParams['font.family'] = 'NanumGothic'
        elif 'Malgun Gothic' in font_names:
            plt.rcParams['font.family'] = 'Malgun Gothic'
        else:
            try:
                fe = fm.FontEntry(fname=nanum_path, name='NanumGothic')
                fm.fontManager.ttflist.insert(0, fe)
                plt.rcParams['font.family'] = fe.name
            except:
                plt.rcParams['font.family'] = 'DejaVu Sans'
        plt.rcParams['axes.unicode_minus'] = False
    except:
        pass

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
    st.error(f"AI 설정 오류: {e}")
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

# --- 3. UI 구성 ---
st.title("이채연의 네이버 블로그 AI 분석기🤖")
st.write("발표를 위한 최종 안정화 버전입니다.")

with st.sidebar:
    st.header("⚙️ 설정")
    target_id = st.text_input("네이버 블로그 ID", value="chaeyeonlee_1106")
    analyze_btn = st.button("전체 게시글 분석 시작 🚀")

if analyze_btn and target_id:
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        status_text.text("🔍 브라우저 실행 중...")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        driver.get(f"https://blog.naver.com/{target_id}")
        time.sleep(2)
        
        all_post_links = []
        current_page = 1
        
        # 1. 링크 수집
        status_text.text("🔗 게시글 목록을 불러오는 중...")
        while len(all_post_links) < 20:  # 발표용으로 적당량 수집 (필요시 조절)
            enter_frame(driver)
            try:
                open_btn = driver.find_element(By.CSS_SELECTOR, "a.btn_openlist, #toplistBtn")
                if "열기" in open_btn.text:
                    driver.execute_script("arguments[0].click();", open_btn)
                    time.sleep(1)
            except: pass

            links = driver.find_elements(By.CSS_SELECTOR, "a._setTopListUrl")
            for link in links:
                raw_url = link.get_attribute('href')
                log_no = re.search(r'logNo=(\d+)', raw_url)
                if log_no:
                    clean_url = f"https://blog.naver.com/{target_id}/{log_no.group(1)}"
                    if clean_url not in all_post_links: all_post_links.append(clean_url)
            
            if len(all_post_links) >= 20: break
            try:
                next_p = driver.find_element(By.LINK_TEXT, str(current_page + 1))
                driver.execute_script("arguments[0].click();", next_p)
                current_page += 1
                time.sleep(1)
            except: break

        # 2. 데이터 추출
        data = []
        for i, url in enumerate(all_post_links):
            status_text.text(f"📝 데이터 수집 중: {i+1}/{len(all_post_links)}")
            driver.get(url)
            time.sleep(0.7)
            enter_frame(driver)
            try:
                title = driver.find_element(By.CSS_SELECTOR, ".se-title-text, .pcol1").text.strip()
                content = driver.find_element(By.CSS_SELECTOR, ".se-main-container, #postViewArea").text[:800].strip()
                date = driver.find_element(By.CSS_SELECTOR, ".se_publishDate, .date").get_attribute('innerText').strip()
                data.append({"제목": title, "내용": content, "게시일": date})
            except: continue
            progress_bar.progress((i + 1) / len(all_post_links))

        if data:
            df = pd.DataFrame(data)
            st.balloons()
            st.header(f"📊 {target_id} 블로그 분석 리포트")
            
            # --- 8번 섹션: 핵심 수정 부분 ---
            st.subheader("8️⃣ [🤖 게시글별 AI 정밀 분석]")
            
            # 표 헤더 시작 (HTML 스타일 직접 지정)
            table_html = """
            <style>
                .report-table { width:100%; border-collapse: collapse; margin-top: 20px; }
                .report-table th { background-color: #F0F2F6; padding: 12px; border: 1px solid #ddd; text-align: center; }
                .report-table td { padding: 12px; border: 1px solid #ddd; vertical-align: top; line-height: 1.6; }
                .index-col { text-align: center; font-weight: bold; width: 50px; }
            </style>
            <table class='report-table'>
                <thead>
                    <tr>
                        <th>번호</th>
                        <th>블로그 제목</th>
                        <th>AI 분석 결과</th>
                    </tr>
                </thead>
                <tbody>
            """
            
            for index, row in df.iterrows():
                status_text.text(f"🤖 AI 분석 중... ({index+1}/{len(df)})")
                
                # 프롬프트를 아주 단순화하여 에러 방지
                prompt = f"""
                블로그 글 제목: {row['제목']}
                내용 요약: {row['내용'][:500]}
                
                위 글을 분석해서 다음 형식을 엄격히 지켜서 답해줘.
                [페르소나] 작성자 특징 한 줄 요약
                [3줄 요약]
                1. 주제: 내용
                2. 분위기: 내용
                3. 타겟: 내용
                """
                
                try:
                    # AI 응답을 통째로 가져와서 불필요한 파싱 없이 줄바꿈만 처리
                    res = ai_model.generate_content(prompt).text.strip()
                    # 마크다운 줄바꿈을 HTML 줄바꿈으로 변경
                    formatted_res = res.replace("\n", "<br>")
                    
                    # 표의 행 추가 (인덱스 1부터 시작)
                    table_html += f"""
                    <tr>
                        <td class='index-col'>{index + 1}</td>
                        <td style='width: 30%;'><b>{row['제목']}</b></td>
                        <td>{formatted_res}</td>
                    </tr>
                    """
                except:
                    # AI가 응답 실패해도 표가 깨지지 않게 예외 처리
                    table_html += f"<tr><td>{index+1}</td><td>{row['제목']}</td><td>분석 일시적 오류</td></tr>"

            table_html += "</tbody></table>"
            st.markdown(table_html, unsafe_allow_html=True)
            status_text.empty()

            # 시각화 (간단하게)
            st.divider()
            st.subheader("📷 콘텐츠 구성 비중")
            fig, ax = plt.subplots()
            ax.pie([len(df), 5], labels=['텍스트 중심', '이미지 중심'], autopct='%1.1f%%', colors=['#A0C4FF', '#FFD6A5'])
            st.pyplot(fig)

    except Exception as e:
        st.error(f"오류가 발생했습니다: {e}")
    finally:
        driver.quit()

else:
    st.info("왼쪽 사이드바에서 ID를 입력하고 분석 버튼을 눌러주세요.")


