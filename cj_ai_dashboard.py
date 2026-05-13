import streamlit as st
import pandas as pd
import requests
from datetime import datetime

st.set_page_config(
    page_title="AON WORLD BETS HR MODEL ⚾️💣",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
[data-testid="stAppViewContainer"] {
    background: radial-gradient(circle at top, #071a2c 0%, #06101f 45%, #020712 100%);
    color: white;
}
[data-testid="stHeader"] { background: transparent; }
.block-container {
    max-width: 1200px;
    padding: 1rem .7rem 6rem .7rem;
}
.aon-header {
    display:flex;
    justify-content:space-between;
    align-items:center;
    gap:12px;
    margin-bottom:18px;
}
.logo-box {
    display:flex;
    align-items:center;
    gap:14px;
}
.logo-text {
    font-size:42px;
    font-weight:950;
    line-height:.9;
}
.logo-sub {
    font-size:16px;
    color:#d8e3f2;
    font-weight:800;
}
.model-title {
    color:#2ef2d2;
    font-size:36px;
    font-weight:950;
}
.model-sub {
    color:#9aa8bb;
    font-size:15px;
}
.refresh-box {
    border:1px solid #13c7b5;
    color:#2ef2d2;
    border-radius:10px;
    padding:10px 15px;
    font-weight:900;
    text-align:center;
}
.panel {
    background:rgba(7,18,32,.96);
    border:1px solid #18304c;
    border-radius:14px;
    padding:18px;
    margin-bottom:16px;
}
.panel-grid {
    display:grid;
    grid-template-columns:repeat(4,1fr);
    gap:14px;
}
.panel-item {
    border-right:1px solid #1e3653;
    padding-right:14px;
}
.panel-item:last-child { border-right:none; }
.label {
    color:#9ba8ba;
    font-size:13px;
    text-transform:uppercase;
    font-weight:800;
}
.big-white {
    font-size:25px;
    font-weight:950;
    color:white;
}
.big-green {
    font-size:28px;
    font-weight:950;
    color:#2ef2d2;
}
.green { color:#2ef2d2; }
.yellow { color:#ffc247; }
.card {
    background:rgba(7,18,32,.98);
    border:1px solid #18304c;
    border-radius:14px;
    padding:16px;
    margin-bottom:12px;
}
.card-inner {
    display:grid;
    grid-template-columns:130px 1fr 170px;
    gap:18px;
    align-items:center;
}
.headshot {
    width:120px;
    height:150px;
    object-fit:cover;
    object-position:top;
    border-radius:12px;
}
.player-name {
    font-size:30px;
    font-weight:950;
    color:white;
}
.team {
    color:#a2aec0;
    font-size:17px;
}
.pos {
    color:#9aa8bb;
    font-size:17px;
    margin-left:8px;
}
.grade-pill {
    background:#063b2f;
    color:#69ff7a;
    padding:7px 16px;
    border-radius:999px;
    display:inline-block;
    font-weight:950;
    margin-left:10px;
}
.metric-row {
    display:grid;
    grid-template-columns:repeat(6,1fr);
    gap:8px;
    margin-top:16px;
}
.metric {
    border-right:1px solid #1e3653;
}
.metric:last-child { border-right:none; }
.metric-main {
    color:#2ef2d2;
    font-size:18px;
    font-weight:950;
}
.metric-label {
    color:#96a4b6;
    font-size:12px;
}
.odds-box {
    border-left:1px solid #1e3653;
    padding-left:18px;
    text-align:center;
}
.odds {
    font-size:29px;
    font-weight:950;
    color:white;
}
.market {
    color:#2ef2d2;
    font-size:14px;
    font-weight:900;
    margin-bottom:22px;
}
.stButton>button {
    width:100%;
    background:#071424;
    color:#2ef2d2;
    border:1px solid #13c7b5;
    border-radius:10px;
    font-weight:950;
    padding:12px;
}
.stButton>button:hover {
    background:#0d665f;
    color:white;
    border:1px solid #2ef2d2;
}
[data-testid="stSelectbox"] label, [data-testid="stTextInput"] label {
    color:white !important;
}
.bottom-nav {
    position:fixed;
    bottom:0;
    left:0;
    right:0;
    background:#06101f;
    border-top:1px solid #172b45;
    display:flex;
    justify-content:space-around;
    padding:10px 0 12px;
    z-index:9999;
}
.nav-item {
    color:#7d8a9e;
    text-align:center;
    font-weight:800;
    font-size:13px;
}
.nav-active { color:#2ef2d2; }
.nav-icon { font-size:23px; }

@media(max-width:800px) {
    .aon-header {
        flex-direction:column;
        align-items:flex-start;
    }
    .logo-text { font-size:34px; }
    .model-title { font-size:28px; }
    .panel-grid {
        grid-template-columns:repeat(2,1fr);
    }
    .panel-item {
        border-right:none;
        border-bottom:1px solid #1e3653;
        padding-bottom:10px;
    }
    .card-inner {
        grid-template-columns:95px 1fr;
    }
    .headshot {
        width:88px;
        height:115px;
    }
    .player-name { font-size:23px; }
    .team { font-size:14px; }
    .odds-box {
        grid-column:1 / span 2;
        border-left:none;
        padding-left:0;
        display:grid;
        grid-template-columns:1fr 1fr;
        gap:10px;
        align-items:center;
    }
    .metric-row {
        grid-template-columns:repeat(3,1fr);
    }
}
</style>
""", unsafe_allow_html=True)


def implied_prob_from_odds(odds):
    odds = int(str(odds).replace("+", ""))
    return round((100 / (odds + 100)) * 100, 1)


def american_to_decimal(odds):
    odds = int(str(odds).replace("+", ""))
    return 1 + odds / 100


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


def get_headshot(player_id):
    return f"https://img.mlbstatic.com/mlb-photos/image/upload/w_213,q_100/v1/people/{player_id}/headshot/67/current"


@st.cache_data(ttl=3600)
def load_real_data():
    url = (
        "https://statsapi.mlb.com/api/v1/stats"
        "?stats=season"
        "&group=hitting"
        "&season=2025"
        "&playerPool=ALL"
        "&limit=700"
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

    for p in splits:
        stat = p.get("stat", {})
        player = p.get("player", {})
        team = p.get("team", {})

        try:
            player_id = player.get("id")
            name = player.get("fullName", "Unknown")
            team_name = team.get("name", "Unknown")

            hr = int(stat.get("homeRuns", 0))
            ab = int(stat.get("atBats", 0))
            pa = int(stat.get("plateAppearances", 0))
            avg = float(stat.get("avg", 0) or 0)
            slg = float(stat.get("slg", 0) or 0)
            ops = float(stat.get("ops", 0) or 0)

            if ab <= 0:
                continue

            iso = round(slg - avg, 3)
            hr_rate = round((hr / ab) * 100, 2)

            barrel_score = round((iso * 100 * .65) + (slg * 100 * .35), 1)

            model_score = round(
                (hr * 1.5)
                + (iso * 60)
                + (slg * 18)
                + (ops * 10)
                + (barrel_score * .22),
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
                "ID": player_id,
                "Name": name,
                "Team": team_name,
                "Pos": "",
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
                "ODDS": odds,
                "HEADSHOT": get_headshot(player_id)
            })

        except Exception:
            continue

    df = pd.DataFrame(rows)

    if df.empty:
        return df

    return df.sort_values("MODEL_SCORE", ascending=False).head(250)


df = load_real_data()

if "slip" not in st.session_state:
    st.session_state.slip = []


def calc_parlay(slip):
    if not slip:
        return "+0", "$0", 0

    dec = 1
    for leg in slip:
        dec *= american_to_decimal(leg["ODDS"])

    american = int((dec - 1) * 100)
    to_win = int((dec - 1) * 10)
    grade = min(99, int(sum(x["MODEL_SCORE"] for x in slip) / len(slip)))

    return f"+{american}", f"${to_win}", grade


st.markdown(f"""
<div class="aon-header">
    <div class="logo-box">
        <div>
            <div class="logo-text">A⚾N</div>
            <div class="logo-sub">WORLD BETS</div>
        </div>
        <div>
            <div class="model-title">HR MODEL ⚾️💣</div>
            <div class="model-sub">Real MLB Data • Weather • Park Factors • Edges</div>
        </div>
    </div>
    <div>
        <div class="refresh-box">⟳ Refresh</div>
        <div class="model-sub">Updated: {datetime.now().strftime("%I:%M %p ET")}</div>
    </div>
</div>
""", unsafe_allow_html=True)

if df.empty:
    st.stop()

top = df.iloc[0]

st.markdown(f"""
<div class="panel">
    <div class="panel-grid">
        <div class="panel-item">
            <div class="label">Top HR Pick</div>
            <div class="big-white">{top["Name"]}</div>
            <div class="team">{top["Team"]}</div>
            <div class="big-green">{top["MODEL_SCORE"]}</div>
            <div class="label">Model Score</div>
        </div>
        <div class="panel-item">
            <div class="label">Weather</div>
            <div class="big-white">78°F 🌤️</div>
            <div class="team">Wind 11 mph OUT</div>
        </div>
        <div class="panel-item">
            <div class="label">Top Park Factor</div>
            <div class="big-white">Coors Field</div>
            <div class="big-green">136</div>
            <div class="label">HR Factor</div>
        </div>
        <div class="panel-item">
            <div class="label">Approach</div>
            <div class="big-green">OVER 0.5 HR</div>
            <div class="team">High Model Edge</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

odds_display, win_display, parlay_grade = calc_parlay(st.session_state.slip)

selected_names = [x["Name"].split(" ")[-1] for x in st.session_state.slip[:4]]
selected_html = " ".join([f"<span style='border:1px solid #27405e;border-radius:8px;padding:8px 12px;margin-right:6px;'>{n} ×</span>" for n in selected_names])

st.markdown(f"""
<div class="panel">
    <div style="display:grid;grid-template-columns:1.5fr 1fr;gap:18px;align-items:center;">
        <div>
            <div class="big-white">PARLAY BUILDER</div>
            <div class="green" style="font-weight:900;">{len(st.session_state.slip)} Leg Parlay</div>
            <br>
            {selected_html if selected_html else "<div class='team'>Add players below to build your HR parlay.</div>"}
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;text-align:center;">
            <div>
                <div class="big-white">{odds_display}</div>
                <div class="label">Odds</div>
            </div>
            <div>
                <div class="big-green">{win_display}</div>
                <div class="label">To Win ($10)</div>
            </div>
            <div>
                <div class="big-white">{parlay_grade}</div>
                <div class="label">Parlay Grade</div>
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

if st.session_state.slip:
    if st.button("🗑 Clear Parlay"):
        st.session_state.slip = []
        st.rerun()

c1, c2, c3, c4 = st.columns(4)

with c1:
    min_grade = st.selectbox("Grade", ["All", "A+", "A", "A-", "B+", "B"])

with c2:
    min_hr_rate = st.selectbox("Min HR Rate", ["0%", "2%", "4%", "6%", "8%"])

with c3:
    sort_by = st.selectbox("Sort By", ["MODEL_SCORE", "EDGE", "HR_RATE", "HR", "ISO", "OPS", "SLG"])

with c4:
    search = st.text_input("Search player or team")

filtered = df.copy()

if min_grade != "All":
    order = {"A+": 5, "A": 4, "A-": 3, "B+": 2, "B": 1}
    filtered = filtered[filtered["GRADE"].map(order) >= order[min_grade]]

min_rate = float(min_hr_rate.replace("%", ""))
filtered = filtered[filtered["HR_RATE"] >= min_rate]

if search.strip():
    s = search.lower()
    filtered = filtered[
        filtered["Name"].str.lower().str.contains(s, na=False)
        | filtered["Team"].str.lower().str.contains(s, na=False)
    ]

filtered = filtered.sort_values(sort_by, ascending=False)

for _, row in filtered.iterrows():
    already_added = any(x["Name"] == row["Name"] for x in st.session_state.slip)

    st.markdown(f"""
    <div class="card">
        <div class="card-inner">
            <div>
                <img class="headshot" src="{row["HEADSHOT"]}">
            </div>

            <div>
                <div>
                    <span class="player-name">{row["Name"]}</span>
                    <span class="pos">{row["Pos"]}</span>
                    <span class="grade-pill">{row["GRADE"]}</span>
                </div>
                <div class="team">{row["Team"]}</div>

                <div class="metric-row">
                    <div class="metric">
                        <div class="metric-label">Model Score</div>
                        <div class="metric-main">{row["MODEL_SCORE"]}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">HR</div>
                        <div class="metric-main">{row["HR"]}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">HR Rate</div>
                        <div class="metric-main">{row["HR_RATE"]}%</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">ISO</div>
                        <div class="metric-main">{row["ISO"]}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">OPS</div>
                        <div class="metric-main">{row["OPS"]}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Edge</div>
                        <div class="metric-main">+{row["EDGE"]}%</div>
                    </div>
                </div>
            </div>

            <div class="odds-box">
                <div>
                    <div class="odds">{row["ODDS"]}</div>
                    <div class="market">OVER 0.5 HR</div>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1])

    with col1:
        if st.button(f"📊 Stats {row['Name']}", key=f"stats_{row['ID']}", use_container_width=True):
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
Edge: {row['EDGE']}%
Grade: {row['GRADE']}
                """
            )

    with col2:
        if already_added:
            if st.button(f"✓ Added {row['Name']}", key=f"added_{row['ID']}", use_container_width=True):
                st.session_state.slip = [x for x in st.session_state.slip if x["Name"] != row["Name"]]
                st.rerun()
        else:
            if st.button(f"+ Add {row['Name']}", key=f"add_{row['ID']}", use_container_width=True):
                st.session_state.slip.append(row.to_dict())
                st.rerun()

st.markdown("""
<div class="bottom-nav">
    <div class="nav-item nav-active"><div class="nav-icon">🏠</div>Home</div>
    <div class="nav-item"><div class="nav-icon">⚾</div>Games</div>
    <div class="nav-item"><div class="nav-icon">📊</div>Research</div>
    <div class="nav-item"><div class="nav-icon">🎟️</div>My Parlays</div>
    <div class="nav-item"><div class="nav-icon">👤</div>Profile</div>
</div>
""", unsafe_allow_html=True)
