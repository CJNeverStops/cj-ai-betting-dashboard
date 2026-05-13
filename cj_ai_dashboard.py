# app.py
# AON WORLD BETS HR MODEL ⚾️💣

import streamlit as st
import pandas as pd
import requests
from datetime import datetime

st.set_page_config(
    page_title="AON WORLD BETS HR MODEL ⚾️💣",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# -----------------------------
# STYLE
# -----------------------------
st.markdown("""
<style>
[data-testid="stAppViewContainer"] {
    background:#06101f;
    color:white;
}
[data-testid="stHeader"] {
    background:transparent;
}
.block-container {
    padding-top:1rem;
    padding-bottom:6rem;
    max-width:1500px;
}
.main-title {
    font-size:38px;
    font-weight:900;
    color:white;
    line-height:1;
}
.sub-title {
    color:#8fa0b8;
    font-size:15px;
    margin-top:5px;
}
.top-box {
    background:#0a1728;
    border:1px solid #17314b;
    border-radius:16px;
    padding:16px;
    margin-bottom:14px;
}
.player-card {
    background:#081424;
    border:1.5px solid #0fc7b5;
    border-radius:18px;
    padding:16px;
    margin-bottom:14px;
}
.player-name {
    font-size:27px;
    font-weight:900;
    color:white;
}
.team {
    color:#8d9cb2;
    font-size:16px;
}
.odds {
    font-size:24px;
    font-weight:900;
    color:white;
}
.green { color:#2ef2d2; }
.yellow { color:#ffc247; }
.red { color:#ff5c71; }
.stat-grid {
    display:grid;
    grid-template-columns:repeat(6,1fr);
    gap:8px;
    margin-top:14px;
}
.stat-box {
    background:#152238;
    border-radius:10px;
    padding:10px;
    text-align:center;
}
.stat-main {
    font-size:18px;
    font-weight:900;
    color:#2ef2d2;
}
.stat-label {
    font-size:10px;
    color:#8b98ab;
    text-transform:uppercase;
}
.stButton>button {
    background:#0fc7b5;
    color:#06101f;
    border:none;
    border-radius:10px;
    font-weight:900;
}
@media(max-width:700px) {
    .main-title { font-size:26px; }
    .player-name { font-size:21px; }
    .stat-grid { grid-template-columns:repeat(3,1fr); }
}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# HELPERS
# -----------------------------
def grade_score(score):
    if score >= 40:
        return "A+"
    if score >= 36:
        return "A"
    if score >= 32:
        return "A-"
    if score >= 28:
        return "B+"
    return "B"

def american_to_decimal(odds):
    odds = int(str(odds).replace("+", ""))
    if odds > 0:
        return 1 + odds / 100
    return 1 + 100 / abs(odds)

def implied_prob_from_odds(odds):
    odds = int(str(odds).replace("+", ""))
    if odds > 0:
        return round((100 / (odds + 100)) * 100, 1)
    return round((abs(odds) / (abs(odds) + 100)) * 100, 1)

def calc_parlay(slip):
    if not slip:
        return "+0", "$0", 0

    dec = 1
    for leg in slip:
        dec *= american_to_decimal(leg["ODDS"])

    american = int((dec - 1) * 100)
    to_win = int((dec - 1) * 10)
    grade = min(99, int(sum([x["MODEL_SCORE"] for x in slip]) / len(slip)))

    return f"+{american}", f"${to_win}", grade

# -----------------------------
# REAL MLB STATS API DATA
# -----------------------------
@st.cache_data(ttl=3600)
def load_real_data():
    url = (
        "https://statsapi.mlb.com/api/v1/stats"
        "?stats=season"
        "&group=hitting"
        "&season=2025"
        "&playerPool=ALL"
        "&limit=500"
        "&sportIds=1"
    )

    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        st.error(f"Could not load MLB data: {e}")
        return pd.DataFrame()

    rows = []

    splits = data.get("stats", [{}])[0].get("splits", [])

    for player in splits:
        stat = player.get("stat", {})

        try:
            name = player.get("player", {}).get("fullName", "Unknown")
            team = player.get("team", {}).get("name", "Unknown")

            hr = int(stat.get("homeRuns", 0))
            ab = int(stat.get("atBats", 0))
            pa = int(stat.get("plateAppearances", 0))
            slg = float(stat.get("slg", 0) or 0)
            ops = float(stat.get("ops", 0) or 0)
            avg = float(stat.get("avg", 0) or 0)

            if ab <= 0:
                continue

            iso = round(slg - avg, 3)
            hr_rate = round((hr / ab) * 100, 2)

            barrel_score = round(
                (iso * 100 * 0.65) +
                (slg * 100 * 0.35),
                1
            )

            model_score = round(
                (hr * 1.5) +
                (iso * 60) +
                (slg * 18) +
                (ops * 10) +
                (barrel_score * 0.22),
                1
            )

            grade = grade_score(model_score)

            if model_score >= 40:
                odds = "+240"
            elif model_score >= 36:
                odds = "+300"
            elif model_score >= 32:
                odds = "+360"
            else:
                odds = "+425"

            book_prob = implied_prob_from_odds(odds)
            model_prob = round(model_score / 1.45, 1)
            edge = round(model_prob - book_prob, 1)

            rows.append({
                "Name": name,
                "Team": team,
                "HR": hr,
                "AB": ab,
                "PA": pa,
                "AVG": avg,
                "SLG": slg,
                "OPS": ops,
                "ISO": iso,
                "HR_RATE": hr_rate,
                "BarrelScore": barrel_score,
                "MODEL_SCORE": model_score,
                "MODEL_PROB": model_prob,
                "BOOK_PROB": book_prob,
                "EDGE": edge,
                "GRADE": grade,
                "ODDS": odds
            })

        except Exception:
            continue

    df = pd.DataFrame(rows)

    if df.empty:
        return df

    df = df.sort_values("MODEL_SCORE", ascending=False)
    return df.head(200)

df = load_real_data()

# -----------------------------
# SESSION STATE
# -----------------------------
if "slip" not in st.session_state:
    st.session_state.slip = []

# -----------------------------
# HEADER
# -----------------------------
c1, c2 = st.columns([4, 1])

with c1:
    st.markdown("""
    <div class='main-title'>AON WORLD BETS HR MODEL ⚾️💣</div>
    <div class='sub-title'>REAL MLB DATA • HR RATES • ISO • OPS • MODEL GRADES</div>
    """, unsafe_allow_html=True)

with c2:
    st.metric("Updated", datetime.now().strftime("%I:%M %p"))

st.divider()

if df.empty:
    st.stop()

# -----------------------------
# TOP METRICS
# -----------------------------
top_player = df.iloc[0]

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown(f"""
    <div class='top-box'>
        <div class='yellow'>🔥 Top HR Pick</div>
        <div style='font-size:24px;font-weight:900;'>{top_player["Name"]}</div>
        <div class='team'>{top_player["Team"]}</div>
    </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown(f"""
    <div class='top-box'>
        <div class='yellow'>💣 Best Score</div>
        <div class='main-title'>{top_player["MODEL_SCORE"]}</div>
    </div>
    """, unsafe_allow_html=True)

with c3:
    st.markdown(f"""
    <div class='top-box'>
        <div class='yellow'>📈 HR Rate</div>
        <div class='main-title'>{top_player["HR_RATE"]}%</div>
    </div>
    """, unsafe_allow_html=True)

with c4:
    st.markdown(f"""
    <div class='top-box'>
        <div class='yellow'>⭐ Grade</div>
        <div class='main-title'>{top_player["GRADE"]}</div>
    </div>
    """, unsafe_allow_html=True)

# -----------------------------
# FILTERS
# -----------------------------
st.subheader("Filters")

c1, c2, c3, c4 = st.columns(4)

with c1:
    min_grade = st.selectbox("Minimum Grade", ["All", "A+", "A", "A-", "B+", "B"])

with c2:
    min_hr_rate = st.slider("Minimum HR Rate %", 0.0, 15.0, 2.0)

with c3:
    sort_by = st.selectbox(
        "Sort By",
        ["MODEL_SCORE", "EDGE", "HR", "HR_RATE", "ISO", "OPS", "SLG"]
    )

with c4:
    search = st.text_input("Search Player/Team", "")

filtered = df.copy()

if min_grade != "All":
    order = {"A+": 5, "A": 4, "A-": 3, "B+": 2, "B": 1}
    filtered = filtered[filtered["GRADE"].map(order) >= order[min_grade]]

filtered = filtered[filtered["HR_RATE"] >= min_hr_rate]

if search.strip():
    s = search.lower().strip()
    filtered = filtered[
        filtered["Name"].str.lower().str.contains(s, na=False) |
        filtered["Team"].str.lower().str.contains(s, na=False)
    ]

filtered = filtered.sort_values(sort_by, ascending=False)

# -----------------------------
# PARLAY BUILDER
# -----------------------------
st.subheader("Parlay Builder")

odds_display, win_display, parlay_grade = calc_parlay(st.session_state.slip)

st.markdown(f"""
<div class='top-box'>
    <div style='font-size:24px;font-weight:900;'>
        {len(st.session_state.slip)} leg HR parlay 
        <span class='green' style='float:right;'>{odds_display}</span>
    </div>
    <br>
    <div class='team'>TO WIN ON $10</div>
    <div class='green' style='font-size:30px;font-weight:900;'>{win_display}</div>
    <div class='team'>Parlay Grade: <span class='green'>{parlay_grade}</span></div>
</div>
""", unsafe_allow_html=True)

if st.session_state.slip:
    for leg in st.session_state.slip:
        c1, c2 = st.columns([4, 1])
        with c1:
            st.write(f"✅ **{leg['Name']}** OVER 0.5 HR — {leg['ODDS']} — Grade {leg['GRADE']}")
        with c2:
            if st.button("Remove", key=f"remove_{leg['Name']}", use_container_width=True):
                st.session_state.slip = [
                    x for x in st.session_state.slip if x["Name"] != leg["Name"]
                ]
                st.rerun()

    if st.button("🗑 Remove All Selections", use_container_width=True):
        st.session_state.slip = []
        st.rerun()
else:
    st.info("Add players below to build your HR parlay.")

st.divider()

# -----------------------------
# PLAYER CARDS
# -----------------------------
st.subheader("Top HR Model Plays")

for _, row in filtered.iterrows():
    already_added = any(x["Name"] == row["Name"] for x in st.session_state.slip)

    st.markdown(f"""
    <div class='player-card'>
        <div style='display:flex;justify-content:space-between;align-items:center;gap:10px;'>
            <div>
                <div class='player-name'>{row["Name"]}</div>
                <div class='team'>{row["Team"]}</div>
            </div>
            <div class='odds'>{row["ODDS"]}</div>
        </div>

        <br>
        <span class='green' style='font-weight:900;'>OVER 0.5 HR</span>

        <div class='stat-grid'>
            <div class='stat-box'>
                <div class='stat-main yellow'>{row["GRADE"]}</div>
                <div class='stat-label'>Grade</div>
            </div>
            <div class='stat-box'>
                <div class='stat-main'>{row["MODEL_SCORE"]}</div>
                <div class='stat-label'>Model</div>
            </div>
            <div class='stat-box'>
                <div class='stat-main'>{row["HR"]}</div>
                <div class='stat-label'>HR</div>
            </div>
            <div class='stat-box'>
                <div class='stat-main'>{row["HR_RATE"]}%</div>
                <div class='stat-label'>HR Rate</div>
            </div>
            <div class='stat-box'>
                <div class='stat-main'>{row["ISO"]}</div>
                <div class='stat-label'>ISO</div>
            </div>
            <div class='stat-box'>
                <div class='stat-main'>{row["OPS"]}</div>
                <div class='stat-label'>OPS</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns(2)

    with c1:
        if st.button(f"📊 Stats {row['Name']}", key=f"stats_{row['Name']}", use_container_width=True):
            st.info(
                f"""
Player: {row['Name']}
Team: {row['Team']}
HR: {row['HR']}
AB: {row['AB']}
PA: {row['PA']}
AVG: {row['AVG']}
SLG: {row['SLG']}
OPS: {row['OPS']}
ISO: {row['ISO']}
HR Rate: {row['HR_RATE']}%
Model Score: {row['MODEL_SCORE']}
Model Probability: {row['MODEL_PROB']}%
Book Probability: {row['BOOK_PROB']}%
Edge: {row['EDGE']}
Grade: {row['GRADE']}
                """
            )

    with c2:
        if already_added:
            if st.button(f"✅ Added {row['Name']}", key=f"added_{row['Name']}", use_container_width=True):
                st.session_state.slip = [
                    x for x in st.session_state.slip if x["Name"] != row["Name"]
                ]
                st.rerun()
        else:
            if st.button(f"➕ Add {row['Name']}", key=f"add_{row['Name']}", use_container_width=True):
                st.session_state.slip.append(row.to_dict())
                st.rerun()

# -----------------------------
# FULL TABLE
# -----------------------------
st.divider()
st.subheader("Full Model Table")

st.dataframe(
    filtered[
        [
            "Name", "Team", "HR", "AB", "PA", "AVG", "SLG", "OPS", "ISO",
            "HR_RATE", "BarrelScore", "MODEL_SCORE", "MODEL_PROB",
            "BOOK_PROB", "EDGE", "GRADE", "ODDS"
        ]
    ],
    use_container_width=True,
    height=600
)
