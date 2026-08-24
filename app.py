import os
import re
import html
from datetime import datetime, timedelta, date, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus, urlparse
from difflib import SequenceMatcher

import feedparser
import requests
import streamlit as st
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
from dotenv import load_dotenv


# =========================================================
# 1. 기본 설정
# =========================================================

load_dotenv()

NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")

KST = timezone(timedelta(hours=9))

st.set_page_config(
    page_title="업무 뉴스 모니터링",
    page_icon="📰",
    layout="wide"
)


# =========================================================
# 2. 화면 스타일
# =========================================================

st.markdown(
    """
    <style>

    .block-container {
        max-width: 1280px;
        padding-top: 2.5rem;
        padding-bottom: 5rem;
    }

    h1 {
        font-size: 32px !important;
        font-weight: 800 !important;
        line-height: 1.2 !important;
        margin-bottom: 14px !important;
    }

    h2 {
        font-size: 23px !important;
        font-weight: 750 !important;
        line-height: 1.4 !important;
    }

    h3 {
        font-size: 17px !important;
        font-weight: 700 !important;
        line-height: 1.5 !important;
    }

    p {
        font-size: 15px !important;
        line-height: 1.75 !important;
    }

    label {
        font-size: 15px !important;
        font-weight: 600 !important;
    }

    div[data-testid="stRadio"] p {
        font-size: 16px !important;
    }

    div[data-testid="stTextInput"] input {
        font-size: 16px !important;
        min-height: 40px !important;
        padding-left: 16px !important;
    }

    div[data-testid="stTextInput"] input::placeholder {
        font-size: 16px !important;
    }

    div[data-testid="stDateInput"] input {
        font-size: 16px !important;
        min-height: 52px !important;
    }

    /* 모니터링 시작 버튼 - 빨간색 */
    div[data-testid="stButton"] > button[kind="primary"] {
        background-color: #ef3b32 !important;
        border-color: #ef3b32 !important;
        color: white !important;
        min-height: 58px !important;
        font-size: 21px !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
    }

    div[data-testid="stButton"] > button[kind="primary"]:hover {
        background-color: #d93027 !important;
        border-color: #d93027 !important;
        color: white !important;
    }

    button[data-baseweb="tab"] {
        font-size: 16px !important;
        font-weight: 600 !important;
    }

    .news-title {
            font-size: 18px;
            font-weight: 700;
            line-height: 1.5;
    }

    .news-desc {
        font-size: 16px;
        line-height: 1.8;
        margin-top: 10px;
        margin-bottom: 12px;
    }

    .news-meta {
        color: #999999;
        font-size: 14px;
        margin-top: 10px;
        margin-bottom: 22px;
    }

    .news-source {
        font-size: 15px;
        font-weight: 700;
    }

    div[data-testid="stMetricLabel"] {
        font-size: 17px !important;
        font-weight: 600 !important;
    }

    div[data-testid="stMetricValue"] {
        font-size: 17px !important;
        font-weight: 750 !important;
    }

    div[data-testid="stAlert"] p {
        font-size: 17px !important;
    }

    hr {
        margin-top: 28px;
        margin-bottom: 28px;
        opacity: 0.25;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# =========================================================
# 3. 언론사 이름 변환
# =========================================================

PUBLISHER_MAP = {

    # 국내
    "yna.co.kr": "연합뉴스",
    "newsis.com": "뉴시스",
    "news1.kr": "뉴스1",
    "gukjenews.com": "국제뉴스",
    "heraldcorp.com": "헤럴드경제",
    "asiae.co.kr": "아시아경제",
    "jibs.co.kr": "JIBS",

    "chosun.com": "조선일보",
    "donga.com": "동아일보",
    "joongang.co.kr": "중앙일보",
    "hani.co.kr": "한겨레",
    "khan.co.kr": "경향신문",

    "mk.co.kr": "매일경제",
    "hankyung.com": "한국경제",
    "sedaily.com": "서울경제",
    "mt.co.kr": "머니투데이",
    "fnnews.com": "파이낸셜뉴스",
    "etoday.co.kr": "이투데이",
    "edaily.co.kr": "이데일리",

    "ytn.co.kr": "YTN",
    "kbs.co.kr": "KBS",
    "sbs.co.kr": "SBS",
    "mbc.co.kr": "MBC",
    "imbc.com": "MBC",
    "jtbc.co.kr": "JTBC",

    "nocutnews.co.kr": "노컷뉴스",
    "segye.com": "세계일보",
    "kmib.co.kr": "국민일보",
    "munhwa.com": "문화일보",
    "newspim.com": "뉴스핌",
    "yonhapnewstv.co.kr": "연합뉴스TV",
    "newsworks.co.kr": "뉴스웍스",

    "yna.co.kr": "연합뉴스",
    "yonhapnewstv.co.kr": "연합뉴스TV",
    "seoul.co.kr": "서울신문",
    "sedaily.com": "서울경제",
    "bizwatch.co.kr": "비즈워치",
    "biz.chosun.com": "조선비즈",
    "etnews.com": "전자신문",
    "zdnet.co.kr": "ZDNET Korea",
    "dt.co.kr": "디지털타임스",
    "bloter.net": "블로터",
    "ohmynews.com": "오마이뉴스",
    "pressian.com": "프레시안",
    "newdaily.co.kr": "뉴데일리",
    "newsis.com": "뉴시스",
    "inews24.com": "아이뉴스24",
    "inews365.com": "충북일보",
    "idaegu.co.kr": "대구일보",
    "daejonilbo.com": "대전일보",

        # 국내 추가

    "seoul.co.kr": "서울신문",
    "segye.com": "세계일보",
    "kmib.co.kr": "국민일보",
    "hankyung.com": "한국경제",
    "sedaily.com": "서울경제",

    "joongdo.co.kr": "중도일보",
    "daejonilbo.com": "대전일보",
    "cctoday.co.kr": "충청투데이",
    "ccdailynews.com": "충청일보",
    "inews365.com": "충북일보",
    "idaegu.co.kr": "대구일보",
    "yeongnam.com": "영남일보",
    "kado.net": "강원도민일보",
    "kwnews.co.kr": "강원일보",
    "busan.com": "부산일보",
    "kookje.co.kr": "국제신문",
    "knnews.co.kr": "경남신문",

    "ohmynews.com": "오마이뉴스",
    "pressian.com": "프레시안",
    "newdaily.co.kr": "뉴데일리",
    "dailian.co.kr": "데일리안",
    "m-i.kr": "매일일보",
    "breaknews.com": "브레이크뉴스",
    "viewsnnews.com": "뷰스앤뉴스",
    "mediatoday.co.kr": "미디어오늘",

    "huffingtonpost.kr": "허핑턴포스트코리아",
    "sisajournal.com": "시사저널",
    "sisain.co.kr": "시사IN",
    "weekly.chosun.com": "주간조선",

    "etnews.com": "전자신문",
    "zdnet.co.kr": "ZDNET Korea",
    "ddaily.co.kr": "디지털데일리",
    "itdaily.kr": "아이티데일리",
    "inews24.com": "아이뉴스24",
    "bloter.net": "블로터",

    "gameinsight.co.kr": "게임인사이트",

    "khan.co.kr": "경향신문",
    "hani.co.kr": "한겨레",
    "ohmynews.com": "오마이뉴스",

    "lawtimes.co.kr": "법률신문",
    "legalinsight.co.kr": "리걸인사이트",

    "fnnews.com": "파이낸셜뉴스",
    "heraldcorp.com": "헤럴드경제",
    "biz.heraldcorp.com": "헤럴드경제",

    "wowtv.co.kr": "한국경제TV",
    "wowtv.hankyung.com": "한국경제TV",

    "tvchosun.com": "TV조선",
    "ichannela.com": "채널A",
    "mbn.co.kr": "MBN",
    "jtbc.co.kr": "JTBC",
    "sbs.co.kr": "SBS",
    "sbsnews.co.kr": "SBS뉴스",
    "kbs.co.kr": "KBS",
    "imnews.imbc.com": "MBC",

    "lawtimes.co.kr": "법률신문",
    "hankyung.com": "한국경제",
    "mk.co.kr": "매일경제",
    "yna.co.kr": "연합뉴스",
    "news1.kr": "뉴스1",
    "newsis.com": "뉴시스",
    "edaily.co.kr": "이데일리",
    "seoul.co.kr": "서울신문",
    "segye.com": "세계일보",

    # 해외
    "reuters.com": "Reuters",
    "apnews.com": "AP",
    "bbc.com": "BBC",
    "bbc.co.uk": "BBC",
    "cnn.com": "CNN",
    "nytimes.com": "The New York Times",
    "washingtonpost.com": "The Washington Post",
    "theguardian.com": "The Guardian",
    "politico.com": "POLITICO",
    "bloomberg.com": "Bloomberg",
    "ft.com": "Financial Times",
    "npr.org": "NPR",
    "nbcnews.com": "NBC News",
    "cbsnews.com": "CBS News",
    "abcnews.go.com": "ABC News",
    "foxnews.com": "Fox News",
    "forbes.com": "Forbes",

        # 해외 추가

    # 영미권 주요 언론
    "wsj.com": "The Wall Street Journal",
    "wsj.com": "The Wall Street Journal",
    "time.com": "TIME",
    "newsweek.com": "Newsweek",
    "economist.com": "The Economist",
    "axios.com": "Axios",
    "thehill.com": "The Hill",
    "theatlantic.com": "The Atlantic",
    "vanityfair.com": "Vanity Fair",

    # 미국 주요 방송·통신
    "usatoday.com": "USA Today",
    "cnbc.com": "CNBC",
    "msnbc.com": "MSNBC",
    "abcnews.com": "ABC News",
    "pbs.org": "PBS",
    "voanews.com": "Voice of America",
    "rferl.org": "Radio Free Europe/Radio Liberty",

    # 영국
    "independent.co.uk": "The Independent",
    "telegraph.co.uk": "The Telegraph",
    "dailymail.co.uk": "Daily Mail",
    "mirror.co.uk": "Daily Mirror",
    "skynews.com": "Sky News",
    "channel4.com": "Channel 4 News",

    # 캐나다
    "cbc.ca": "CBC",
    "ctvnews.ca": "CTV News",
    "globalnews.ca": "Global News",

    # 호주
    "abc.net.au": "ABC Australia",
    "sbs.com.au": "SBS Australia",
    "news.com.au": "news.com.au",
    "smh.com.au": "The Sydney Morning Herald",

    # 일본
    "nhk.or.jp": "NHK",
    "nhk.jp": "NHK",
    "japantimes.co.jp": "The Japan Times",
    "asahi.com": "Asahi Shimbun",
    "mainichi.jp": "Mainichi Shimbun",
    "yomiuri.co.jp": "Yomiuri Shimbun",
    "nikkei.com": "Nikkei",

    # 중국·홍콩·대만
    "scmp.com": "South China Morning Post",
    "globaltimes.cn": "Global Times",
    "chinadaily.com.cn": "China Daily",
    "xinhuanet.com": "Xinhua",
    "taipeitimes.com": "Taipei Times",

    # 유럽
    "dw.com": "DW",
    "france24.com": "France 24",
    "lemonde.fr": "Le Monde",
    "lefigaro.fr": "Le Figaro",
    "euronews.com": "Euronews",
    "politico.eu": "POLITICO Europe",
    "spiegel.de": "Der Spiegel",
    "faz.net": "Frankfurter Allgemeine Zeitung",

    # 러시아·동유럽
    "tass.com": "TASS",
    "rt.com": "RT",
    "kyivindependent.com": "The Kyiv Independent",

    # 중동
    "aljazeera.com": "Al Jazeera",
    "arabnews.com": "Arab News",
    "middleeasteye.net": "Middle East Eye",
    "timesofisrael.com": "The Times of Israel",
    "haaretz.com": "Haaretz",

    # 인도·아시아
    "hindustantimes.com": "Hindustan Times",
    "thehindu.com": "The Hindu",
    "indianexpress.com": "The Indian Express",
    "straitstimes.com": "The Straits Times",
    "channelnewsasia.com": "CNA",
    "bangkokpost.com": "Bangkok Post",

    # 국제 전문·외교 분야
    "foreignpolicy.com": "Foreign Policy",
    "foreignaffairs.com": "Foreign Affairs",
    "defensenews.com": "Defense News",
    "janes.com": "Janes",

    "state.gov": "U.S. Department of State",
    "un.org": "United Nations",
    "europa.eu": "European Union",
    "who.int": "WHO",
    "reuters.com": "Reuters",
    "apnews.com": "AP",
    "bbc.com": "BBC",
    "aljazeera.com": "Al Jazeera",
    "dw.com": "DW",
    "france24.com": "France 24",
    "nhk.or.jp": "NHK",
    "scmp.com": "South China Morning Post",
    
}


def get_publisher(url, fallback=""):

    try:

        domain = urlparse(url).netloc.lower()
        domain = domain.replace("www.", "")

        for key, value in sorted(
            PUBLISHER_MAP.items(),
            key=lambda x: len(x[0]),
            reverse=True
        ):

             if key in domain:
                return value

                # 매핑되지 않은 경우
        clean_name = domain.split(".")[0]

        return fallback or clean_name or "언론사"

    except Exception:

        return fallback or "언론사"


# =========================================================
# 4. 텍스트 정리
# =========================================================

def clean_text(text):

    if not text:
        return ""

    text = html.unescape(text)

    text = BeautifulSoup(
        text,
        "html.parser"
    ).get_text(" ")

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def normalize(text):

    text = clean_text(text).lower()

    text = re.sub(
        r"[^0-9a-z가-힣\s-]",
        " ",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def contains_korean(text):

    return bool(
        re.search(
            r"[가-힣]",
            text
        )
    )


# =========================================================
# 5. 외교 업무 핵심 문맥
#
# 기사에 '외교'라는 단어 자체가 없어도
# 실제 외교부 업무 범위이면 허용
# =========================================================

DIPLOMACY_CONTEXT = {

    # 외교
    "외교",
    "외교부",
    "외교장관",
    "국제관계",
    "양자관계",
    "정상회담",
    "장관회담",
    "협정",
    "국제협정",
    "국제기구",

    # 영사·재외국민
    "영사",
    "영사관",
    "총영사",
    "대사",
    "대사관",
    "공관",
    "재외공관",
    "재외국민",
    "재외동포",

    # 비자·이민
    "사증",
    "비자",
    "이민",
    "이민정책",
    "출입국",
    "입국",
    "출국",
    "체류",
    "국적",
    "추방",
    "워킹홀리데이",
    "교환방문",
    "유학비자",

    # 해외안전
    "여행경보",
    "해외안전",
    "안전공지",
    "상황점검",
    "재난",
    "테러",
    "납치",

    # 미국 등
    "국무부",
    "이민국",
    "난민",
    "제재",

    # 영어
    "diplomacy",
    "diplomatic",
    "foreign ministry",
    "foreign minister",
    "foreign affairs",
    "state department",

    "embassy",
    "ambassador",
    "diplomatic mission",

    "consular",
    "consulate",

    "visa",
    "immigration",
    "migration",
    "citizenship",

    "border",
    "entry",

    "bilateral",
    "summit",

    "sanctions",
    "refugee",

    "working holiday",
    "exchange visitor",

    "travel advisory",
    "overseas nationals",
    "international student",

    "emergency",
    "evacuation"
}


# =========================================================
# 6. 명백한 오탐 문맥
# =========================================================

PROPERTY_CONTEXT = {
    "주차장",
    "주택공급",
    "주택 공급",
    "부동산",
    "아파트",
    "재건축",
    "재개발",
    "용적률",
    "캠프킴",
    "공원부지",
    "공원 부지",
    "부지 활용",
    "건물 활용",
}


SPORTS_CONTEXT = {
    "축구",
    "야구",
    "농구",
    "선수",
    "경기",
    "리그",
    "득점",
    "골",
    "감독",
    "우승",
    "시즌",

    "football",
    "soccer",
    "baseball",
    "basketball",
    "player",
    "match",
    "league",
    "goal",
    "coach",
    "season"
}


ENTERTAINMENT_CONTEXT = {
    "배우",
    "가수",
    "연예인",
    "방송",
    "예능",
    "드라마",
    "영화",
    "팬",
    "팬미팅",
    "화보",
    "유튜브",
    "유튜버",
    "인터뷰",
    "홍상수",
    "침착맨",

    "actor",
    "actress",
    "singer",
    "celebrity",
    "entertainment",
    "movie",
    "film",
    "drama"
}


PERSONAL_EXPERIENCE_CONTEXT = {
    "경험담",
    "후기",
    "생활기",
    "살았다",
    "살았던",
    "갔다왔다",
    "다녀왔다",
    "떠났다",
    "도피유학",
    "브이로그",
    "개인 경험",

    "my experience",
    "vlog",
    "personal story"
}


# =========================================================
# 7. 정책 / 제도 문맥
# 워홀 같은 검색어에서 연예뉴스를 제거하기 위해 사용
# =========================================================

POLICY_CONTEXT = {
    "비자",
    "사증",
    "신청",
    "발급",
    "자격",
    "정부",
    "외교부",
    "대사관",
    "협정",
    "제도",
    "정책",
    "규정",
    "체류",
    "입국",
    "출입국",
    "이민",
    "쿼터",
    "모집",
    "개정",
    "시행",
    "중단",
    "재개",

    "visa",
    "application",
    "issuance",
    "eligibility",
    "government",
    "embassy",
    "agreement",
    "policy",
    "regulation",
    "immigration",
    "quota",
    "program",
    "scheme"
}


# =========================================================
# 8. 비자 검색 확장
# =========================================================

QUERY_RULES = {

    "비자": {
        "intent": "visa",
        "ko": [
            "비자",
            "사증"
        ],
        "en": [
            "visa",
            "visa policy",
            "visa issuance"
        ]
    },

    "visa": {
        "intent": "visa",
        "ko": [
            "비자",
            "사증"
        ],
        "en": [
            "visa",
            "visa policy",
            "visa issuance"
        ]
    },

    "사증": {
        "intent": "visa",
        "ko": [
            "사증",
            "비자"
        ],
        "en": [
            "visa",
            "visa policy",
            "visa issuance"
        ]
    },

    # F 계열
    "f visa": {
        "intent": "visa",
        "ko": [
            "F 비자",
            "F-1 비자",
            "F1 비자",
            "F-2 비자",
            "F2 비자",
            "미국 학생비자",
            "학생비자"
        ],
        "en": [
            "F visa",
            "F-1 visa",
            "F1 visa",
            "F-2 visa",
            "F2 visa",
            "F student visa",
            "international student visa"
        ]
    },

    "f 비자": {
        "intent": "visa",
        "ko": [
            "F 비자",
            "F-1 비자",
            "F1 비자",
            "F-2 비자",
            "F2 비자",
            "학생비자"
        ],
        "en": [
            "F visa",
            "F-1 visa",
            "F1 visa",
            "F-2 visa",
            "F2 visa",
            "student visa"
        ]
    },

    "f1": {
        "intent": "visa",
        "ko": [
            "F1 비자",
            "F-1 비자",
            "미국 학생비자"
        ],
        "en": [
            "F1 visa",
            "F-1 visa",
            "F-1 student visa"
        ]
    },

    "f-1": {
        "intent": "visa",
        "ko": [
            "F-1 비자",
            "F1 비자",
            "미국 학생비자"
        ],
        "en": [
            "F-1 visa",
            "F1 visa",
            "F-1 student visa"
        ]
    },

    # J 계열
    "j visa": {
        "intent": "visa_j",
        "ko": [
            "J 비자",
            "J-1 비자",
            "J1 비자",
            "J-2 비자",
            "J2 비자",
            "교환방문 비자"
        ],
        "en": [
            "J visa",
            "J-1 visa",
            "J1 visa",
            "J-2 visa",
            "J2 visa",
            "exchange visitor visa"
        ]
    },

    "j 비자": {
        "intent": "visa_j",
        "ko": [
            "J 비자",
            "J-1 비자",
            "J1 비자",
            "J-2 비자",
            "J2 비자",
            "교환방문 비자"
        ],
        "en": [
            "J visa",
            "J-1 visa",
            "J1 visa",
            "J-2 visa",
            "J2 visa",
            "exchange visitor visa"
        ]
    },

    "j1": {
        "intent": "visa_j",
        "ko": [
            "J1 비자",
            "J-1 비자",
            "교환방문 비자"
        ],
        "en": [
            "J1 visa",
            "J-1 visa",
            "J-1 exchange visitor",
            "DS-2019",
            "SEVIS J-1"
        ]
    },

    "j-1": {
        "intent": "visa_j",
        "ko": [
            "J-1 비자",
            "J1 비자",
            "교환방문 비자"
        ],
        "en": [
            "J-1 visa",
            "J1 visa",
            "J-1 exchange visitor",
            "DS-2019",
            "SEVIS J-1"
        ]
    },

    # H 계열
    "h visa": {
        "intent": "visa",
        "ko": [
            "H 비자",
            "H-1B 비자",
            "H1B 비자",
            "H-2A 비자",
            "H2A 비자",
            "H-2B 비자",
            "H2B 비자"
        ],
        "en": [
            "H visa",
            "H-1B visa",
            "H1B visa",
            "H-2A visa",
            "H2A visa",
            "H-2B visa",
            "H2B visa"
        ]
    },

    # 대사관
    "대사관": {
        "intent": "embassy",
        "ko": [
            "대사관",
            "재외공관"
        ],
        "en": [
            "embassy",
            "diplomatic mission"
        ]
    },

    "embassy": {
        "intent": "embassy",
        "ko": [
            "대사관",
            "재외공관"
        ],
        "en": [
            "embassy",
            "diplomatic mission"
        ]
    },

    # 영사
    "영사관": {
        "intent": "consular",
        "ko": [
            "영사관",
            "총영사관",
            "영사"
        ],
        "en": [
            "consulate",
            "consular"
        ]
    },

    "consulate": {
        "intent": "consular",
        "ko": [
            "영사관",
            "총영사관",
            "영사"
        ],
        "en": [
            "consulate",
            "consular"
        ]
    },

    # 외교부
    "외교부": {
        "intent": "mofa",
        "ko": [
            "외교부",
            "외교장관"
        ],
        "en": [
            "foreign ministry",
            "ministry of foreign affairs",
            "foreign minister"
        ]
    },

    # 워홀
    "워킹홀리데이": {
        "intent": "working_holiday",
        "ko": [
            "워킹홀리데이",
            "워홀"
        ],
        "en": [
            "working holiday",
            "working holiday visa"
        ]
    },

    "워홀": {
        "intent": "working_holiday",
        "ko": [
            "워홀",
            "워킹홀리데이"
        ],
        "en": [
            "working holiday",
            "working holiday visa"
        ]
    },

    "working holiday": {
        "intent": "working_holiday",
        "ko": [
            "워킹홀리데이",
            "워홀"
        ],
        "en": [
            "working holiday",
            "working holiday visa"
        ]
    },

    "재외국민": {
        "intent": "consular",
        "ko": [
            "재외국민",
            "재외동포"
        ],
        "en": [
            "overseas nationals",
            "citizens abroad"
        ]
    }
}


# =========================================================
# 9. 일반 사건 / 재난 키워드
#
# 이런 키워드는 검색할 때 자동으로 외교 문맥을 붙임
# =========================================================

EVENT_TRANSLATIONS = {
    "태풍": "typhoon",
    "지진": "earthquake",
    "홍수": "flood",
    "산불": "wildfire",
    "테러": "terror attack",
    "테러사건": "terror attack",
    "시위": "protest",
    "폭동": "riot",
    "납치": "kidnapping",
    "총격": "shooting",
    "전쟁": "war",
    "분쟁": "conflict",
    "쿠데타": "coup",
    "허리케인": "hurricane",
    "쓰나미": "tsunami"
}


# =========================================================
# 10. 검색어 자동 확장
# =========================================================

@st.cache_data(show_spinner=False)
def expand_queries(keyword):

    key = normalize(keyword)

    # 지정된 업무 검색어
    if key in QUERY_RULES:

        rule = QUERY_RULES[key]

        return (
            rule["intent"],
            list(dict.fromkeys(rule["ko"])),
            list(dict.fromkeys(rule["en"]))
        )


    # 사건/재난 검색어
    if key in EVENT_TRANSLATIONS:

        translated = EVENT_TRANSLATIONS[key]

        ko_queries = [
            keyword,
        ]

        en_queries = [
            translated,
        ]

        return (
            "event",
            ko_queries,
            en_queries
        )


    # 일반 한국어 검색어
    if contains_korean(keyword):

        try:

            translated = GoogleTranslator(
                source="ko",
                target="en"
            ).translate(keyword)

        except Exception:

            translated = ""

        # 외교업무 전용 사이트이므로
        # 일반 키워드도 외교 관련 조합까지 자동 탐색
        ko_queries = [
            keyword,
        ]

        en_queries = [
            translated,
        ]

        return (
            "general",
            ko_queries,
            en_queries
        )


    # 일반 영어 검색어
    else:

        try:

            korean = GoogleTranslator(
                source="en",
                target="ko"
            ).translate(keyword)

        except Exception:

            korean = keyword


        ko_queries = [
            korean,
        ]

        en_queries = [
            keyword,
        ]

        return (
            "general",
            ko_queries,
            en_queries
        )


# =========================================================
# 11. 날짜 처리
# =========================================================

def parse_naver_date(value):

    try:

        dt = parsedate_to_datetime(value)

        if dt.tzinfo:

            dt = dt.astimezone(
                KST
            )

        return dt.replace(
            tzinfo=None
        )

    except Exception:

        return None


def parse_google_date(entry):

    try:

        if hasattr(
            entry,
            "published_parsed"
        ):

            t = entry.published_parsed

            dt = datetime(
                t.tm_year,
                t.tm_mon,
                t.tm_mday,
                t.tm_hour,
                t.tm_min,
                t.tm_sec,
                tzinfo=timezone.utc
            )

            return dt.astimezone(
                KST
            ).replace(
                tzinfo=None
            )

    except Exception:

        pass

    return None


def parse_gdelt_date(value):

    if not value:

        return None

    formats = [
        "%Y%m%dT%H%M%SZ",
        "%Y%m%d%H%M%S",
        "%Y-%m-%dT%H:%M:%SZ"
    ]

    for fmt in formats:

        try:

            dt = datetime.strptime(
                value,
                fmt
            )

            dt = dt.replace(
                tzinfo=timezone.utc
            )

            return dt.astimezone(
                KST
            ).replace(
                tzinfo=None
            )

        except Exception:

            pass

    return None


def in_period(pub_date, start_dt, end_dt):

    if not pub_date:
        return False

    return (
        start_dt
        <= pub_date
        <= end_dt
    )


# =========================================================
# 12. 외교업무 관련성 판단
# =========================================================

def is_relevant(
    article,
    keyword,
    intent,
    ko_queries,
    en_queries
):

    title = normalize(
        article.get(
            "title",
            ""
        )
    )

    description = normalize(
        article.get(
            "description",
            ""
        )
    )

    text = title
    text = title


    # -----------------------------------------------------
    # 부동산/시설 기사
    # -----------------------------------------------------

    property_hits = sum(
        1
        for word in PROPERTY_CONTEXT
        if normalize(word) in text
    )

    if property_hits >= 2:
        return False


    # -----------------------------------------------------
    # J 계열의 스포츠 오탐
    # -----------------------------------------------------

    if intent == "visa_j":

        sports_hits = sum(
            1
            for word in SPORTS_CONTEXT
            if normalize(word) in text
        )

        visa_hits = any(
            term in text
            for term in [
                "visa",
                "비자",
                "사증",
                "exchange visitor",
                "ds-2019",
                "sevis",
                "immigration",
                "state department",
                "국무부"
            ]
        )

        if sports_hits >= 1 and not visa_hits:
            return False


    # -----------------------------------------------------
    # 비자 관련 검색
    #
    # '외교'라는 단어 자체가 없어도 통과 가능
    # -----------------------------------------------------

    if intent in {
        "visa",
        "visa_j"
    }:

        visa_context = [
            "visa",
            "비자",
            "사증",
            "immigration",
            "student visa",
            "exchange visitor",
            "consular",
            "embassy",
            "sevis",
            "ds-2019",

            "f-1",
            "f1",
            "f-2",
            "f2",

            "j-1",
            "j1",
            "j-2",
            "j2",

            "h-1b",
            "h1b",
            "h-2a",
            "h2a",
            "h-2b",
            "h2b"
        ]

        return any(
            term in text
            for term in visa_context
        )


    # -----------------------------------------------------
    # 워킹홀리데이
    #
    # 연예인/개인 경험담은 제외
    # 정책·비자·정부·제도 문맥 필요
    # -----------------------------------------------------

    if intent == "working_holiday":

        working_hit = any(
            term in text
            for term in [
                "워킹홀리데이",
                "워홀",
                "working holiday"
            ]
        )

        if not working_hit:
            return False


        entertainment_hits = sum(
            1
            for term in ENTERTAINMENT_CONTEXT
            if normalize(term) in text
        )

        personal_hits = sum(
            1
            for term in PERSONAL_EXPERIENCE_CONTEXT
            if normalize(term) in text
        )

        policy_hits = sum(
            1
            for term in POLICY_CONTEXT
            if normalize(term) in text
        )


        # 연예 / 개인 경험담
        if (
            entertainment_hits >= 1
            and
            policy_hits == 0
        ):
            return False


        if (
            personal_hits >= 1
            and
            policy_hits == 0
        ):
            return False


        # 실제 업무 관련 문맥 필요
        return policy_hits >= 1


    # -----------------------------------------------------
    # 외교부
    # -----------------------------------------------------

    if intent == "mofa":

        if any(
            normalize(term) in text
            for term in PROPERTY_CONTEXT
        ):
            return False

        diplomacy_terms = [
            "외교",
            "외교장관",
            "영사",
            "대사관",
            "공관",
            "재외국민",
            "국제",
            "협정",
            "회담",
            "비자",
            "사증",
            "foreign",
            "diplomatic",
            "embassy",
            "consular"
        ]

        hits = sum(
            1
            for term in diplomacy_terms
            if term in text
        )

        priority_terms = [
            "회담",
            "정상회담",
            "비자",
            "사증",
            "영사",
            "대사관",
            "재외국민"
        ]
        
        if any(term in text for term in priority_terms):
            return True
        return hits >= 2


    # -----------------------------------------------------
    # 대사관
    # -----------------------------------------------------

    if intent == "embassy":

        terms = [
            "대사관",
            "재외공관",
            "embassy",
            "diplomatic mission",
            "ambassador",
            "consular",
            "consulate"
        ]

        return any(
            term in text
            for term in terms
        )


    # -----------------------------------------------------
    # 영사 / 재외국민
    # -----------------------------------------------------

    if intent == "consular":

        terms = [
            "영사",
            "영사관",
            "총영사",
            "재외국민",
            "재외동포",
            "consular",
            "consulate",
            "embassy",
            "visa",
            "사증"
        ]

        return any(
            term in text
            for term in terms
        )


    # -----------------------------------------------------
    # 태풍, 지진, 테러 등 일반 사건
    #
    # 사건 키워드 + 외교 업무 문맥이 모두 필요
    # -----------------------------------------------------

    if intent == "event":

        original_terms = [
            normalize(keyword)
        ]

        translated_terms = [
            normalize(q)
            for q in en_queries
        ]

        event_hit = any(
            term in text
            for term in (
                original_terms
                +
                translated_terms
            )
            if term
        )


        diplomacy_hit = any(
            normalize(term) in text
            for term in DIPLOMACY_CONTEXT
        )


        return (
            event_hit
            and
            diplomacy_hit
        )


    # -----------------------------------------------------
    # 일반 검색
    #
    # 검색 주제 + 외교부 업무 문맥 둘 다 필요
    # -----------------------------------------------------

    query_hit = any(
        normalize(q) in title
        for q in (
            ko_queries
            +
            en_queries
        )
        if len(normalize(q)) >= 2
    )


    diplomacy_hit = any(
        normalize(term) in text
        for term in DIPLOMACY_CONTEXT
    )


    return (
        query_hit
        and
        diplomacy_hit
    )


# =========================================================
# 13. NAVER API
# =========================================================

@st.cache_data(
    ttl=900,
    show_spinner=False
)
def naver_request(query):

    url = (
        "https://naverapihub.apigw.ntruss.com/"
        "search/v1/news"
    )

    headers = {
        "X-NCP-APIGW-API-KEY-ID":
            NAVER_CLIENT_ID,

        "X-NCP-APIGW-API-KEY":
            NAVER_CLIENT_SECRET
    }

    params = {
        "query": query,
        "display": 100,
        "start": 1,
        "sort": "date"
    }

    response = requests.get(
        url,
        headers=headers,
        params=params,
        timeout=15
    )

    response.raise_for_status()

    return response.json().get(
        "items",
        []
    )


def search_naver(
    queries,
    start_dt,
    end_dt
):

    results = []

    for query in queries:

        try:

            items = naver_request(
                query
            )

        except Exception:

            continue


        for item in items:

            pub_date = parse_naver_date(
                item.get(
                    "pubDate",
                    ""
                )
            )

            if not in_period(
                pub_date,
                start_dt,
                end_dt
            ):
                continue


            link = (
                item.get(
                    "originallink"
                )
                or
                item.get(
                    "link",
                    ""
                )
            )


            results.append(
                {
                    "title":
                        clean_text(
                            item.get(
                                "title",
                                ""
                            )
                        ),

                    "description":
                        clean_text(
                            item.get(
                                "description",
                                ""
                            )
                        ),

                    "link":
                        link,

                    "date":
                        pub_date,

                    "publisher":
                        get_publisher(
                            link
                        ),

                    "region":
                        "한국 언론",

                    "source":
                        "NAVER"
                }
            )


    return results


# =========================================================
# 14. Google News RSS
# =========================================================

@st.cache_data(
    ttl=900,
    show_spinner=False
)
def google_news_request(
    query,
    start_string,
    end_string
):

    search_query = (
        f"({query}) "
        f"after:{start_string} "
        f"before:{end_string}"
    )

    url = (
        "https://news.google.com/rss/search"
        f"?q={quote_plus(search_query)}"
        "&hl=en-US"
        "&gl=US"
        "&ceid=US:en"
    )

    return feedparser.parse(
        url
    )


def search_google_news(
    queries,
    start_dt,
    end_dt
):

    results = []

    google_end = (
        end_dt.date()
        +
        timedelta(days=1)
    )

    start_string = (
        start_dt.strftime(
            "%Y-%m-%d"
        )
    )

    end_string = (
        google_end.strftime(
            "%Y-%m-%d"
        )
    )


    for query in queries:

        try:

            feed = google_news_request(
                query,
                start_string,
                end_string
            )

        except Exception:

            continue


        for entry in feed.entries:

            pub_date = parse_google_date(
                entry
            )

            if not in_period(
                pub_date,
                start_dt,
                end_dt
            ):
                continue


            source_name = "해외 언론"

            try:

                if entry.source.title:

                    source_name = clean_text(
                        entry.source.title
                    )

            except Exception:

                pass


            title = clean_text(
                entry.get(
                    "title",
                    ""
                )
            )


            suffix = (
                f" - {source_name}"
            )

            if (
                source_name != "해외 언론"
                and
                title.endswith(suffix)
            ):

                title = title[
                    :-len(suffix)
                ]


            results.append(
                {
                    "title":
                        title,

                    "description":
                        clean_text(
                            entry.get(
                                "summary",
                                ""
                            )
                        ),

                    "link":
                        entry.get(
                            "link",
                            ""
                        ),

                    "date":
                        pub_date,

                    "publisher":
                        source_name,

                    "region":
                        "해외 언론",

                    "source":
                        "Google News"
                }
            )


    return results


# =========================================================
# 15. GDELT
# =========================================================

@st.cache_data(
    ttl=900,
    show_spinner=False
)
def gdelt_request(
    query,
    start_string,
    end_string
):

    url = (
        "https://api.gdeltproject.org/"
        "api/v2/doc/doc"
    )

    params = {
        "query": query,
        "mode": "artlist",
        "format": "json",
        "maxrecords": 250,
        "sort": "datedesc",
        "STARTDATETIME": start_string,
        "ENDDATETIME": end_string
    }

    response = requests.get(
        url,
        params=params,
        timeout=20
    )

    response.raise_for_status()

    return response.json()


def search_gdelt(
    queries,
    start_dt,
    end_dt
):

    results = []

    start_string = (
        start_dt.strftime(
            "%Y%m%d%H%M%S"
        )
    )

    end_string = (
        end_dt.strftime(
            "%Y%m%d%H%M%S"
        )
    )


    for query in queries:

        try:

            data = gdelt_request(
                query,
                start_string,
                end_string
            )

        except Exception:

            continue


        for item in data.get(
            "articles",
            []
        ):

            pub_date = (
                parse_gdelt_date(
                    item.get(
                        "seendate",
                        ""
                    )
                )
            )


            if (
                pub_date
                and
                not in_period(
                    pub_date,
                    start_dt,
                    end_dt
                )
            ):
                continue


            link = item.get(
                "url",
                ""
            )


            results.append(
                {
                    "title":
                        clean_text(
                            item.get(
                                "title",
                                ""
                            )
                        ),

                    "description":
                        "",

                    "link":
                        link,

                    "date":
                        pub_date,

                    "publisher":
                        get_publisher(
                            link,
                            item.get(
                                "domain",
                                ""
                            )
                        ),

                    "region":
                        "해외 언론",

                    "source":
                        "GDELT"
                }
            )


    return results


# =========================================================
# 16. 중복 / 유사 기사 제거
# =========================================================

def remove_duplicates(articles):

    output = []

    normalized_titles = []


    for article in articles:

        title_key = normalize(
            article.get(
                "title",
                ""
            )
        )

        if not title_key:
            continue


        duplicate = False


        for old_title in normalized_titles:

            similarity = SequenceMatcher(
                None,
                title_key,
                old_title
            ).ratio()


            if similarity >= 0.92:

                duplicate = True
                break


        if duplicate:
            continue


        normalized_titles.append(
            title_key
        )

        output.append(
            article
        )


    return output


# =========================================================
# 17. 기사 출력
# =========================================================

def format_date(dt):

    if not dt:

        return "시간 정보 없음"

    return dt.strftime(
        "%Y-%m-%d %H:%M"
    )


def show_article(article):

    title = html.escape(
        article["title"]
    )

    description = html.escape(
        article["description"]
    )

    publisher = html.escape(
        article["publisher"]
    )

    link = article["link"]


    st.markdown(
    f'<div class="news-title"><a href="{link}" target="_blank">{title}</a></div>',
    unsafe_allow_html=True
        )

    if description:

        st.markdown(
            f"""
            <div class="news-desc">
                {description}
            </div>
            """,
            unsafe_allow_html=True
        )


    st.markdown(
        f"""
        <div class="news-meta">
            <span class="news-source">
                {publisher}
            </span>
            &nbsp;·&nbsp;
            {format_date(article["date"])}
        </div>
        """,
        unsafe_allow_html=True
    )


    st.divider()


# =========================================================
# 18. 메인 화면
# =========================================================

st.title(
    "📰 업무 뉴스 모니터링"
)

st.subheader(
    "검색 조건"
)


# =========================================================
# 19. 기간
# =========================================================

period = st.radio(
    "기간",
    [
        "24시간",
        "3일",
        "1주",
        "1개월",
        "직접입력"
    ],
    index=0,
    horizontal=True
)


now = datetime.now()
today = date.today()


if period == "24시간":

    start_dt = (
        now
        -
        timedelta(hours=24)
    )

    end_dt = now


elif period == "3일":

    start_dt = (
        now
        -
        timedelta(days=3)
    )

    end_dt = now


elif period == "1주":

    start_dt = (
        now
        -
        timedelta(days=7)
    )

    end_dt = now


elif period == "1개월":

    start_dt = (
        now
        -
        timedelta(days=30)
    )

    end_dt = now


else:

    selected_dates = st.date_input(
        "검색 날짜 또는 기간",
        value=(
            today,
            today
        ),
        format="YYYY.MM.DD"
    )


    if isinstance(
        selected_dates,
        tuple
    ):

        if len(
            selected_dates
        ) == 2:

            start_day = (
                selected_dates[0]
            )

            end_day = (
                selected_dates[1]
            )

        elif len(
            selected_dates
        ) == 1:

            start_day = (
                selected_dates[0]
            )

            end_day = (
                selected_dates[0]
            )

        else:

            start_day = today
            end_day = today

    else:

        start_day = (
            selected_dates
        )

        end_day = (
            selected_dates
        )


    start_dt = datetime.combine(
        start_day,
        datetime.min.time()
    )

    end_dt = datetime.combine(
        end_day,
        datetime.max.time()
    )


# =========================================================
# 20. 정렬
# =========================================================

sort_option = st.radio(
    "정렬",
    [
        "최신순",
        "오래된순"
    ],
    horizontal=True
)


# =========================================================
# 21. 검색어
# =========================================================

keyword = st.text_input(
    "검색 키워드",
    placeholder="예: 사증"
)


# =========================================================
# 22. 실행
# =========================================================

if st.button(
    "🔍 모니터링 시작",
    type="primary",
    use_container_width=True
):

    keyword = (
        keyword.strip()
    )


    if not keyword:

        st.warning(
            "검색 키워드를 입력해주세요."
        )

        st.stop()


    if (
        not NAVER_CLIENT_ID
        or
        not NAVER_CLIENT_SECRET
    ):

        st.error(
            "NAVER API 인증정보를 확인해주세요."
        )

        st.stop()


    # -----------------------------------------------------
    # 검색어 확장
    # -----------------------------------------------------

    with st.spinner(
        "검색어의 국내·해외 표현을 분석하고 있습니다..."
    ):

        (
            intent,
            ko_queries,
            en_queries
        ) = expand_queries(
            keyword
        )


    # -----------------------------------------------------
    # 넓게 기사 수집
    # -----------------------------------------------------

    with st.spinner(
        "국내·해외 언론에서 관련 기사를 수집하고 있습니다..."
    ):

        korean_articles = (
            search_naver(
                ko_queries,
                start_dt,
                end_dt
            )
        )


        google_articles = (
            search_google_news(
                en_queries,
                start_dt,
                end_dt
            )
        )


        gdelt_articles = (
            search_gdelt(
                en_queries,
                start_dt,
                end_dt
            )
        )


    foreign_articles = (
        google_articles
        +
        gdelt_articles
    )


    # -----------------------------------------------------
    # 외교업무 관련 필터
    # -----------------------------------------------------

    with st.spinner(
        "외교 업무와 무관한 기사를 제외하고 있습니다..."
    ):

        korean_articles = [
            article
            for article
            in korean_articles

            if is_relevant(
                article,
                keyword,
                intent,
                ko_queries,
                en_queries
            )
        ]


        foreign_articles = [
            article
            for article
            in foreign_articles

            if is_relevant(
                article,
                keyword,
                intent,
                ko_queries,
                en_queries
            )
        ]


    # -----------------------------------------------------
    # 중복 제거
    # -----------------------------------------------------

    korean_articles = remove_duplicates(
        korean_articles
    )

    foreign_articles = remove_duplicates(
        foreign_articles
    )


    all_articles = remove_duplicates(
        korean_articles
        +
        foreign_articles
    )


    # -----------------------------------------------------
    # 정렬
    # -----------------------------------------------------

    reverse = (
        sort_option
        ==
        "최신순"
    )


    all_articles.sort(
        key=lambda x:
            x["date"]
            or datetime.min,

        reverse=reverse
    )


    korean_articles = [
        article
        for article
        in all_articles

        if article["region"]
        ==
        "한국 언론"
    ]


    foreign_articles = [
        article
        for article
        in all_articles

        if article["region"]
        ==
        "해외 언론"
    ]


    # =====================================================
    # 결과
    # =====================================================

    st.divider()


    st.subheader(
        f"'{keyword}' 모니터링 결과"
    )


    with st.expander(
        "검색어 확장 확인"
    ):

        st.markdown(
            "**한국 언론 검색어**"
        )

        st.write(
            " · ".join(
                ko_queries
            )
        )


        st.markdown(
            "**해외 언론 검색어**"
        )

        st.write(
            " · ".join(
                en_queries
            )
        )


    col1, col2, col3 = (
        st.columns(3)
    )


    col1.metric(
        "전체",
        f"{len(all_articles)}건"
    )

    col2.metric(
        "한국 언론",
        f"{len(korean_articles)}건"
    )

    col3.metric(
        "해외 언론",
        f"{len(foreign_articles)}건"
    )


    tab_all, tab_ko, tab_world = (
        st.tabs(
            [
                f"전체  {len(all_articles)}",
                f"한국 언론  {len(korean_articles)}",
                f"해외 언론  {len(foreign_articles)}"
            ]
        )
    )


    with tab_all:

        if not all_articles:

            st.info(
                "선택한 기간에 검색 주제와 관련된 기사를 찾지 못했습니다."
            )


        for article in all_articles:

            show_article(
                article
            )


    with tab_ko:

        if not korean_articles:

            st.info(
                "조건에 맞는 한국 언론 기사가 없습니다."
            )


        for article in korean_articles:

            show_article(
                article
            )


    with tab_world:

        if not foreign_articles:

            st.info(
                "조건에 맞는 해외 언론 기사가 없습니다."
            )


        for article in foreign_articles:

            show_article(
                article
            )
