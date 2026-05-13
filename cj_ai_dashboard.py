# app.py
# AON WORLD BETS HR MODEL ⚾️💣
# FULL STREAMLIT FILE

import streamlit as st
import pandas as pd
import requests
from datetime import datetime
from pybaseball import batting_stats

# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(
    page_title="AON WORLD BETS HR MODEL ⚾️💣",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# =====================================================
# STYLE
# =====================================================

st.markdown("""
<style>

[data-testid="stAppViewContainer"]{
    background:#06101f;
    color:white;
}

[data-testid="stHeader"]{
    background:transparent;
}

.block-container{
    padding-top:1rem;
    padding-bottom:6rem;
    max-width:1500px;
}

.main-title{
    font-size:42px;
    font-weight:900;
    color:white;
    line-height:1;
}

.sub-title{
    color:#8fa0b8;
    font-size:15px;
    margin-top:4px;
}

.top-box{
    background:#0a1728;
    border:1px solid #17314b;
    border-radius:16px;
    padding:18px;
    margin-bottom:18px;
}

.player-card{
    background:#081424;
    border:1.5px solid #0fc7b5;
    border-radius:18px;
    padding:16px;
    margin-bottom:14px;
}

.player-name{
    font-size:28px;
    font-weight:900;
    color:white;
}

.team{
    color:#8d9cb2;
    font-size:16px;
}

.odds{
    font-size:24px;
    font-weight:900;
    color:white;
}

.green{
    color:#2ef2d2;
}

.yellow{
    color:#ffc247;
}

.red{
    color:#ff5c71;
}

.stat-grid{
    display:grid;
    grid-template-columns:repeat(6,1fr);
    gap:8px;
    margin-top:14px;
}

.stat-box{
    background:#152238;
    border-radius:10px;
    padding:10px;
    text-align:center;
}

.stat-main{
    font-size:18px;
    font-weight:900;
    color:#2ef2d2;
}

.stat-label{
    font-size:10px;
    color:#8b98ab;
    text-transform:uppercase;
}

hr{
    border-color:#1c2f47;
}

.stButton>button{
    background:#0fc7b5;
    color:#06101f;
    border:none;
    border-radius:10px;
    font-weight:900;
}

.stSelectbox label{
    color:white !important;
}

</style>
""", unsafe_allow_html=True)

# =====================================================
# HELPERS
# =====================================================

def safe_div(a, b):
    if b == 0:
        return 0
    return a / b

def grade_score(score):
    if score >= 40:
        return "A+"
    elif score >= 36:
        return "A"
    elif score >= 32:
        return "A-"
    elif score >= 28:
        return "B+"
    else:
        return "B"

def calc_model_score(row):

    score = 0

    # HR
    score += row["HR"] * 1.5

    # ISO
    score += row["ISO"] * 65

    # SLG
    score += row["SLG"] * 20

    # OPS
    score += row["OPS"] * 10

    # Barrel estimate
    score += row["BarrelScore"]

    return round(score, 1)

def estimate_barrel(row):
    return round(
        (
            (row["ISO"] * 100) * 0.55 +
            (row["SLG"] * 100) * 0.45
        ),1
    )

def estimate_hr_rate(row):
    return round(
        safe_div(row["HR"], row["AB"]) * 100,
        2
    )

def implied_prob(odds):

    odds = int(odds)

    if odds > 0:
        return round((100 / (odds + 100)) * 100, 1)

    return round((abs(odds) / (abs(odds) + 100)) * 100, 1)

# =====================================================
# WEATHER / PARKS
# =====================================================

PARK_FACTORS = {
    "Yankee Stadium":118,
    "Dodger Stadium":102,
    "Coors Field":136,
    "Fenway Park":108,
    "Citizens Bank Park":112,
    "Great American Ball Park":124,
    "Camden Yards":106,
    "Petco Park":92,
    "Wrigley Field":109,
    "Truist Park":111
}

WEATHER = {
    "temp": 78,
    "wind": 11,
    "direction": "OUT"
}

# =====================================================
# LOAD REAL MLB DATA
# =====================================================

@st.cache_data(ttl=3600)
def load_real_data():

    # REAL DATA FROM PYBASEBALL
    hitting = batting_stats(2025, qual=50)

    cols = [
        "Name",
        "Team",
        "HR",
        "AB",
        "SLG",
        "OPS",
        "ISO",
        "PA"
    ]

    hitting = hitting[cols].copy()

    hitting["BarrelScore"] = hitting.apply(estimate_barrel, axis=1)

    hitting["HR_RATE"] = hitting.apply(estimate_hr_rate, axis=1)

    hitting["MODEL_SCORE"] = hitting.apply(calc_model_score, axis=1)

    hitting["GRADE"] = hitting["MODEL_SCORE"].apply(grade_score)

    # Fake odds for now until sportsbook API
    hitting["ODDS"] = (
        hitting["MODEL_SCORE"]
        .rank(ascending=False)
        .apply(lambda x:
            "+240" if x <= 10 else
            "+300" if x <= 20 else
            "+400"
        )
    )

    hitting["BOOK_PROB"] = hitting["ODDS"].apply(
        lambda x: implied_prob(x.replace("+",""))
    )

    hitting["MODEL_PROB"] = (
        hitting["MODEL_SCORE"] / 1.45
    ).round(1)

    hitting["EDGE"] = (
        hitting["MODEL_PROB"] - hitting["BOOK_PROB"]
    ).round(1)

    hitting = hitting.sort_values(
        "MODEL_SCORE",
        ascending=False
    )

    return hitting.head(100)

df = load_real_data()

# =====================================================
# HEADER
# =====================================================

c1, c2 = st.columns([4,1])

with c1:

    st.markdown("""
    <div class='main-title'>
    AON WORLD BETS HR MODEL ⚾️💣
    </div>

    <div class='sub-title'>
    REAL MLB DATA • WEATHER • PARK FACTORS • HR MODEL
    </div>
    """, unsafe_allow_html=True)

with c2:

    st.metric(
        "Updated",
        datetime.now().strftime("%I:%M %p")
    )

st.divider()

# =====================================================
# TOP INFO
# =====================================================

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown("""
    <div class='top-box'>
    <div class='yellow'>🌡 Temperature</div>
    <div class='main-title'>78°</div>
    </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown("""
    <div class='top-box'>
    <div class='yellow'>💨 Wind</div>
    <div class='main-title'>11 MPH</div>
    </div>
    """, unsafe_allow_html=True)

with c3:
    st.markdown("""
    <div class='top-box'>
    <div class='yellow'>⚾ Direction</div>
    <div class='main-title'>OUT</div>
    </div>
    """, unsafe_allow_html=True)

with c4:
    st.markdown("""
    <div class='top-box'>
    <div class='yellow'>🏟 Best Park</div>
    <div class='main-title'>Coors</div>
    </div>
    """, unsafe_allow_html=True)

# =====================================================
# FILTERS
# =====================================================

st.subheader("Filters")

c1, c2, c3 = st.columns(3)

with c1:

    min_grade = st.selectbox(
        "Minimum Grade",
        ["All","A+","A","A-","B+"]
    )

with c2:

    min_hr = st.slider(
        "Minimum HR Rate %",
        0.0,
        10.0,
        3.0
    )

with c3:

    sort_by = st.selectbox(
        "Sort By",
        [
            "MODEL_SCORE",
            "EDGE",
            "HR",
            "HR_RATE",
            "ISO",
            "OPS"
        ]
    )

# =====================================================
# FILTER LOGIC
# =====================================================

filtered = df.copy()

if min_grade != "All":

    order = {
        "A+":5,
        "A":4,
        "A-":3,
        "B+":2,
        "B":1
    }

    filtered = filtered[
        filtered["GRADE"].map(order)
        >= order[min_grade]
    ]

filtered = filtered[
    filtered["HR_RATE"] >= min_hr
]

filtered = filtered.sort_values(
    sort_by,
    ascending=False
)

# =====================================================
# PARLAY
# =====================================================

if "slip" not in st.session_state:
    st.session_state.slip = []

st.subheader("Parlay Builder")

if len(st.session_state.slip) > 0:

    parlay_df = pd.DataFrame(st.session_state.slip)

    st.dataframe(
        parlay_df[
            [
                "Name",
                "ODDS",
                "MODEL_SCORE",
                "EDGE",
                "GRADE"
            ]
        ],
        use_container_width=True
    )

    if st.button("Clear Parlay"):
        st.session_state.slip = []
        st.rerun()

else:
    st.info("Add players to build a HR parlay.")

st.divider()

# =====================================================
# PLAYER CARDS
# =====================================================

st.subheader("Top HR Model Plays")

for _, row in filtered.iterrows():

    already_added = any(
        x["Name"] == row["Name"]
        for x in st.session_state.slip
    )

    st.markdown(f"""
    <div class='player-card'>

    <div style='display:flex;justify-content:space-between;align-items:center;'>

        <div>
            <div class='player-name'>
            {row["Name"]}
            </div>

            <div class='team'>
            {row["Team"]}
            </div>
        </div>

        <div class='odds'>
        {row["ODDS"]}
        </div>

    </div>

    <br>

    <span class='green'>
    OVER 0.5 HR
    </span>

    <div class='stat-grid'>

        <div class='stat-box'>
            <div class='stat-main yellow'>
            {row["GRADE"]}
            </div>
            <div class='stat-label'>
            Grade
            </div>
        </div>

        <div class='stat-box'>
            <div class='stat-main'>
            {row["MODEL_SCORE"]}
            </div>
            <div class='stat-label'>
            Model
            </div>
        </div>

        <div class='stat-box'>
            <div class='stat-main'>
            {row["HR_RATE"]}%
            </div>
            <div class='stat-label'>
            HR Rate
            </div>
        </div>

        <div class='stat-box'>
            <div class='stat-main'>
            {row["ISO"]}
            </div>
            <div class='stat-label'>
            ISO
            </div>
        </div>

        <div class='stat-box'>
            <div class='stat-main'>
            {row["EDGE"]}
            </div>
            <div class='stat-label'>
            Edge
            </div>
        </div>

        <div class='stat-box'>
            <div class='stat-main'>
            {row["BarrelScore"]}
            </div>
            <div class='stat-label'>
            Barrel
            </div>
        </div>

    </div>

    </div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns(2)

    with c1:

        if st.button(
            f"📊 Stats {row['Name']}",
            key=f"stats_{row['Name']}",
            use_container_width=True
        ):

            st.info(f"""
            PLAYER: {row['Name']}

            TEAM: {row['Team']}

            HR: {row['HR']}

            HR RATE: {row['HR_RATE']}%

            ISO: {row['ISO']}

            OPS: {row['OPS']}

            MODEL SCORE: {row['MODEL_SCORE']}

            EDGE: {row['EDGE']}

            WEATHER:
            {WEATHER['temp']}° • {WEATHER['wind']} MPH {WEATHER['direction']}
            """)

    with c2:

        if already_added:

            if st.button(
                f"✅ Added {row['Name']}",
                key=f"added_{row['Name']}",
                use_container_width=True
            ):

                st.session_state.slip = [
                    x for x in st.session_state.slip
                    if x["Name"] != row["Name"]
                ]

                st.rerun()

        else:

            if st.button(
                f"➕ Add {row['Name']}",
                key=f"add_{row['Name']}",
                use_container_width=True
            ):

                st.session_state.slip.append(
                    row.to_dict()
                )

                st.rerun()

# =====================================================
# RAW TABLE
# =====================================================

st.divider()

st.subheader("Full Model Table")

st.dataframe(
    filtered[
        [
            "Name",
            "Team",
            "HR",
            "HR_RATE",
            "ISO",
            "OPS",
            "MODEL_SCORE",
            "EDGE",
            "GRADE",
            "ODDS"
        ]
    ],
    use_container_width=True,
    height=600
)
