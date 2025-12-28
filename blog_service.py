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

# --- 2. AI 모델 설정 (보안 적용 완료) ---
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
st.write("아이디를 입력하면 당신의 블로그(전체공개)를 기반으로 AI가 리포트를 작성합니다.")

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
        
        status_text.text("🔗 모든 게시글 링크를 확보하는 중입니다...")
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
            
            status_text.text(f"🔗 링크 수집 중: {current_page}페이지 완료 (누적 {len(all_post_links)}개)")
            
            next_p = current_page + 1
            try:
                page_btn = driver.find_element(By.LINK_TEXT, str(next_p))
                driver.execute_script("arguments[0].click();", page_btn)
                time.sleep(1)
                current_page = next_p
            except:
                try:
                    next_btn = driver.find_element(By.CSS_SELECTOR, "a.pg_next")
                    driver.execute_script("arguments[0].click();", next_btn)
                    time.sleep(1)
                    current_page = next_p
                except:
                    break 

        data = []
        total_links = len(all_post_links)
        
        if total_links == 0:
            st.error("수집된 게시글이 없습니다. 아이디를 확인해주세요.")
            st.stop()

        for i, url in enumerate(all_post_links):
            status_text.text(f"📝 데이터 정밀 분석 중: {i+1}/{total_links} 완료")
            driver.get(url)
            time.sleep(0.8)
            enter_frame(driver)
            
            try:
                date_text = ""
                for s in ["span.se_publishDate.pcol2", "span.se_publishDate", ".date"]:
                    try:
                        date_text = driver.find_element(By.CSS_SELECTOR, s).get_attribute('innerText').strip()
                        if date_text: break
                    except: continue

                title = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".se-title-text, .pcol1, .itemSubjectBoldfont"))
                ).text.strip()
                
                content_el = driver.find_element(By.CSS_SELECTOR, ".se-main-container, #postViewArea")
                content = content_el.text.strip()
                img_count = len(content_el.find_elements(By.TAG_NAME, "img"))
                
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(0.2)
                l_count = 0
                try:
                    l_count = int(re.sub(r'[^0-9]', '', driver.find_element(By.CSS_SELECTOR, "span.u_likeit_text._count.num").get_attribute('innerText')))
                except: pass
                c_count = 0
                try:
                    c_count = int(re.sub(r'[^0-9]', '', driver.find_element(By.ID, "commentCount").get_attribute('innerText')))
                except: pass

                data.append({
                    "제목": title, "내용": content, "게시일": date_text, 
                    "좋아요": l_count, "댓글": c_count, "글자수": len(content), "이미지수": img_count
                })
            except:
                continue
            
            progress_bar.progress(int((i + 1) / total_links * 100))

        if data:
            df = pd.DataFrame(data)
            
            def parse_dt(text):
                nums = re.findall(r'\d+', str(text))
                return nums if len(nums) >= 5 else None
            df['dt_list'] = df['게시일'].apply(parse_dt)
            df = df.dropna(subset=['dt_list'])
            df['hour'] = df['dt_list'].apply(lambda x: int(x[3]))
            df['month'] = df['dt_list'].apply(lambda x: int(x[1]))
            
            def get_season(m):
                if m in [3, 4, 5]: return "봄 🌱"
                elif m in [6, 7, 8]: return "여름 ☀️"
                elif m in [9, 10, 11]: return "가을 🍂"
                else: return "겨울 ❄️"
            df['계절'] = df['month'].apply(get_season)

            status_text.text("🤖 AI가 페르소나 리포트를 최종 생성하고 있습니다...")
            
            # --- AI 프롬프트 수정 파트 ---
            titles_summary = "\n".join(df['제목'].tolist()[:30])
            prompt = (
                f"다음 블로그 제목들을 분석해줘:\n{titles_summary}\n\n"
                "분석 결과는 아래 형식으로만 작성해줘:\n"
                "1. 글 분석: 작성자의 이름, 현재 상태(예: 휴학생), 성격적 특징을 포함하여 설명해줘.\n"
                "2. 3줄 요약: 블로그의 핵심 내용과 톤앤매너를 3문장으로 정리해줘.\n"
                "(주의: '주제 분석', '목표', '특징' 섹션은 제외해줘. HTML 태그인 <br>은 절대 쓰지 말고 줄바꿈으로만 구분해줘.)"
            )
            ai_res = ai_model.generate_content(prompt).text

            st.balloons()
            st.header(f"📊 {target_id} 블로그 최종 분석 리포트")
            st.divider()

            col1, col2 = st.columns([1, 1.2])
            with col1:
                st.subheader("📌 핵심 지표")
                st.write(f"1️⃣ 총 게시물 수: **{len(df)}개**")
                st.write(f"2️⃣ 가장 활발한 계절: **{df['계절'].mode()[0]}**")
                st.write(f"3️⃣ 주요 활동 시간대: **{df['hour'].mode()[0]}시**")
                st.write(f"4️⃣ 콘텐츠 구성: **✍️{df['글자수'].sum():,}자 / 📷{df['이미지수'].sum()}장**")
                
                best_l = df.loc[df['좋아요'].idxmax()]
                best_c = df.loc[df['댓글'].idxmax()]
                
                st.info(f"5️⃣ **🏆 인기왕: 공감을 가장 많이 받은 포스트** \n\n **{best_l['제목']}** (❤️ {best_l['좋아요']}개)")
                st.success(f"6️⃣ **💬 소통왕: 댓글을 가장 많이 받은 포스트** \n\n **{best_c['제목']}** (💬 {best_c['댓글']}개)")

            with col2:
                st.subheader("7️⃣ 최다 사용 단어 TOP 5")
                words = re.findall(r'[가-힣]{2,}', " ".join(df['내용'].tolist()))
                stop_w = ['진짜', '너무', '오늘', '정말', '생각', '있는', '하고', '것은', '나의', '많이']
                top_words = Counter([w for w in words if w not in stop_w]).most_common(5)
                
                fig_bar, ax_bar = plt.subplots()
                w_labels, w_counts = zip(*top_words)
                ax_bar.bar(w_labels, w_counts, color='#A0C4FF')
                st.pyplot(fig_bar)

            st.divider()
            st.subheader("8️⃣ [🤖 AI 심층 리포트]")
            # <br> 제거 및 텍스트 정제 출력
            clean_ai_res = ai_res.replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n")
            st.info(clean_ai_res)
            
            st.subheader("📷 글/사진 구성 비중")
            fig_pie, ax_pie = plt.subplots()
            ax_pie.pie([df['글자수'].sum(), df['이미지수'].sum()*100], labels=['글', '사진'], autopct='%1.1f%%', colors=['#BDB2FF', '#FFD6A5'])
            st.pyplot(fig_pie)

    except Exception as e:
        st.error(f"⚠️ 분석 중 오류 발생: {e}")
    
else:
    if analyze_btn and not target_id:
        st.warning("분석할 네이버 ID를 입력해주세요.")







