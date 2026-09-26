import streamlit as st
import googleapiclient.discovery
import re

# -----------------------------------------------------------------------------
# 1. Page Configuration & UI Setup
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Shorts Score Analyzer", page_icon="📊", layout="wide")

st.title("📊 YouTube Shorts 데이터 기반 성과 분석기")
st.caption("쇼츠 URL을 입력하고 내부 수치를 보정하여 알고리즘 점수 및 성과 가능성을 진단하세요.")

# Sidebar - API Key Input
st.sidebar.header("🔑 설정")
api_key = st.sidebar.text_input("YouTube Data API Key 입력", type="password")

# -----------------------------------------------------------------------------
# 2. Helper Functions
# -----------------------------------------------------------------------------
def extract_video_id(url):
    """Extracts YouTube Video ID from standard or shorts URLs."""
    pattern = r"(?:v=|\/shorts\/|youtu\.be\/)([a-zA-Z0-9_-]{11})"
    match = re.search(pattern, url)
    return match.group(1) if match else None

def parse_iso8601_duration(duration_str):
    """Parses ISO 8601 duration string into total seconds."""
    match = re.match(r'PT(?:(\d+)M)?(?:(\d+)S)?', duration_str)
    if not match:
        return 0
    minutes = int(match.group(1)) if match.group(1) else 0
    seconds = int(match.group(2)) if match.group(2) else 0
    return minutes * 60 + seconds

def get_video_data(v_id, key):
    """Fetches video metadata from YouTube Data API v3."""
    youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=key)
    request = youtube.videos().list(part="snippet,statistics,contentDetails", id=v_id)
    response = request.execute()
    
    if not response.get("items"):
        return None
    
    item = response["items"][0]
    stats = item.get("statistics", {})
    snippet = item.get("snippet", {})
    content = item.get("contentDetails", {})
    
    return {
        "title": snippet.get("title", ""),
        "views": int(stats.get("viewCount", 0)),
        "likes": int(stats.get("likeCount", 0)),
        "comments": int(stats.get("commentCount", 0)),
        "duration": parse_iso8601_duration(content.get("duration", "PT0S")),
        "tags": snippet.get("tags", []),
        "thumbnail": snippet.get("thumbnails", {}).get("high", {}).get("url", "")
    }

# -----------------------------------------------------------------------------
# 3. Main Logic
# -----------------------------------------------------------------------------
url_input = st.text_input("분석할 쇼츠 URL을 입력하세요:", placeholder="https://www.youtube.com/shorts/...")

if url_input:
    v_id = extract_video_id(url_input)
    
    if not v_id:
        st.error("올바른 유튜브 쇼츠 URL 형식이 아닙니다.")
    elif not api_key:
        st.warning("왼쪽 사이드바에 YouTube Data API 키를 입력해주세요.")
    else:
        try:
            data = get_video_data(v_id, api_key)
            
            if not data:
                st.error("영상 데이터를 가져올 수 없습니다. URL을 확인해 주세요.")
            else:
                # Top Summary Section
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.image(data["thumbnail"], use_column_width=True)
                with col2:
                    st.subheader(data["title"])
                    st.write(f"⏱️ **영상 길이:** {data['duration']}초")
                    
                    # Metrics Display
                    m1, m2, m3 = st.columns(3)
                    m1.metric("조회수", f"{data['views']:,}회")
                    m2.metric("좋아요", f"{data['likes']:,}개")
                    m3.metric("댓글", f"{data['comments']:,}개")

                st.markdown("---")
                st.subheader("⚙️ 스튜디오 세부 지표 수동 보정 (정밀 분석용)")
                st.info("YouTube API 제한으로 인해 완독률 및 VVSA(피드 선택률)는 YouTube Studio 수치를 입력해주시면 더 정확해집니다.")

                col_a, col_b = st.columns(2)
                with col_a:
                    vvsa_input = st.slider("초반 피드 선택률 (VVSA %)", 0, 100, 65, help="피드에서 넘기지 않고 본 비율")
                    hooking_passed = st.checkbox("첫 3초 내 강렬한 후킹 요소 존재 여부", value=True)
                with col_b:
                    retention_input = st.slider("평균 완독률 (Retention %)", 0, 150, 75, help="100% 이상은 재시청(루핑) 발생")
                    is_looping = st.checkbox("무한 루프(Looping) 연출 적용 여부", value=False)

                # Calculate Scores
                # 1. Hooking Score (Max 30)
                score_hooking = min(30, int((vvsa_input / 70) * 20) + (10 if hooking_passed else 0))
                
                # 2. Retention Score (Max 30)
                score_retention = min(30, int((retention_input / 80) * 25) + (5 if is_looping else 0))
                
                # 3. Engagement Score (Max 20)
                er = ((data['likes'] + data['comments']) / data['views'] * 100) if data['views'] > 0 else 0
                score_er = min(20, int((er / 4.0) * 20))  # ER 4% 이상 시 만점
                
                # 4. Metadata & Pace Score (Max 20)
                score_meta = 0
                if len(data['title']) <= 40: score_meta += 5
                if 15 <= data['duration'] <= 50: score_meta += 10
                if "#shorts" in data['title'].lower() or len(data['tags']) > 0: score_meta += 5

                total_score = score_hooking + score_retention + score_er + score_meta

                # Display Results
                st.markdown("---")
                st.header(f"🎯 최종 종합 성과 점수: {total_score} / 100점")

                # Score Breakdown Progress Bars
                col_s1, col_s2 = st.columns(2)
                with col_s1:
                    st.write(f"**1. 초반 후킹 & VVSA:** {score_hooking}/30점")
                    st.progress(score_hooking / 30)
                    
                    st.write(f"**2. 완독률 & 루핑:** {score_retention}/30점")
                    st.progress(score_retention / 30)

                with col_s2:
                    st.write(f"**3. 참여율 (ER: {er:.2f}%):** {score_er}/20점")
                    st.progress(score_er / 20)
                    
                    st.write(f"**4. 메타데이터 & 구성:** {score_meta}/20점")
                    st.progress(score_meta / 20)

                # Diagnostic Summary
                st.subheader("💡 데이터 기반 진단 리포트")
                if total_score >= 85:
                    st.success("🟢 **대형 바이럴 가능성이 매우 높은 상위 5% 쇼츠입니다.** 알고리즘 추천 피드에 대량 노출될 조건을 갖추었습니다.")
                elif total_score >= 70:
                    st.info("🟡 **무난한 성과(1만~10만 회)가 기대되는 쇼츠입니다.** 참여율(댓글/공유)이나 루프 연출을 보완하면 3차 확산이 가능합니다.")
                else:
                    st.warning("🔴 **노출 정체 구간에 진입할 가능성이 큽니다.** 초반 3초 타이밍의 후킹 요소를 재편집하거나 이탈 구간을 단축하세요.")

        except Exception as e:
            st.error(f"데이터를 처리하는 중 오류가 발생했습니다: {e}")
