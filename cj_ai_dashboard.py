import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(
    page_title="AON WORLD BETS HR MODEL ⚾️💣",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# -----------------------------
# STYLE
# -----------------------------
st.markdown("""
<style>
[data-testid="stAppViewContainer"] {
    background: radial-gradient(circle at top, #0b1d35 0%, #06101f 45%, #040914 100%);
    color: white;
}
[data-testid="stHeader"] {
    background: transparent;
}
.block-container {
    padding: 1rem .65rem 6rem .65rem;
    max-width: 760px;
}
h1, h2, h3, p {
    margin: 0;
}
.header {
    display:flex;
    justify-content:space-between;
    align-items:center;
    margin-bottom:18px;
}
.brand {
    display:flex;
    align-items:center;
    gap:12px;
}
.logo {
    width:56px;
    height:56px;
    border-radius:50%;
    background:#ffffff;
    color:#06101f;
    display:flex;
    justify-content:center;
    align-items:center;
    font-size:28px;
    font-weight:900;
}
.title {
    font-size:28px;
    font-weight:950;
    line-height:1.05;
}
.subtitle {
    color:#9aa4b5;
    font-size:15px;
    margin-top:3px;
}
.refresh {
    border:1px solid #0fb7a6;
    color:#31f6d1;
    border-radius:10px;
    padding:10px 13px;
    font-weight:900;
    text-align:center;
    font-size:15px;
}
.updated {
    color:#9aa4b5;
    font-size:12px;
    text-align:right;
    margin-top:5px;
}
.slip {
    background:rgba(10, 20, 39, .92);
    border:1px solid #1a2b44;
    border-radius:15px;
    padding:14px;
    margin-bottom:14px;
    box-shadow: 0 0 20px rgba(0,0,0,.25);
}
.slip-title {
    font-size:20px;
    font-weight:950;
}
.green {
    color:#2ff2d2;
}
.win-row {
    display:grid;
    grid-template-columns: 1fr 95px;
    gap:8px;
    margin-top:12px;
}
.win-box {
    background:#0a1222;
    border:1px solid #1b2a43;
    border-radius:9px;
    padding:12px;
}
.win-label {
    color:#7c8799;
    font-size:11px;
}
.win-money {
    color:#2ff2d2;
    font-size:26px;
    font-weight:950;
}
.grade-box {
    background:#0d1728;
    border:1px solid #22314a;
    border-radius:9px;
    padding:12px;
    text-align:center;
}
.grade-num {
    color:#ffad45;
    font-size:27px;
    font-weight:950;
}
.grade-label {
    color:#8d96a8;
    font-size:11px;
}
.action-row {
    display:grid;
    grid-template-columns:1fr 1fr 1fr;
    gap:8px;
    margin-top:12px;
}
.action-btn {
    border:1px solid #263a59;
    background:#111b2d;
    border-radius:8px;
    padding:11px 7px;
    text-align:center;
    color:#39f3d2;
    font-weight:900;
}
.primary-btn {
    background:linear-gradient(135deg,#0b7e78,#12b5a7);
    color:#06101f;
}
.remove {
    color:#ff5367;
    text-align:center;
    margin-top:16px;
    font-weight:900;
}
.tabs {
    display:flex;
    gap:8px;
    overflow-x:auto;
    background:#071523;
    border:1px solid #14344b;
    border-radius:13px;
    padding:8px;
    margin-bottom:14px;
}
.tab {
    color:#29e6c8;
    font-weight:900;
    white-space:nowrap;
    padding:10px 12px;
    border-radius:8px;
}
.tab-active {
    border:1px solid #10cab7;
    background:#082329;
}
.card {
    background:rgba(8, 18, 32, .96);
    border:1.5px solid #10bfae;
    border-radius:14px;
    padding:14px;
    margin-bottom:12px;
    box-shadow: 0 0 14px rgba(16,191,174,.08);
}
.top-row {
    display:flex;
    justify-content:space-between;
    gap:8px;
}
.name-wrap {
    display:flex;
    gap:10px;
    align-items:center;
}
.avatar {
    width:54px;
    height:54px;
    border-radius:50%;
    background:linear-gradient(135deg,#13294b,#0fb7a6);
    display:flex;
    align-items:center;
    justify-content:center;
    font-weight:950;
    color:white;
    font-size:18px;
    flex-shrink:0;
}
.player-name {
    font-size:23px;
    font-weight:950;
    color:white;
}
.team {
    color:#8e97aa;
    font-size:16px;
}
.odds {
    font-size:23px;
    font-weight:950;
}
.pill-row {
    margin-top:8px;
    margin-left:64px;
}
.pill {
    display:inline-block;
    background:#062b2c;
    color:#38f3d1;
    border-radius:999px;
    padding:6px 12px;
    margin-right:6px;
    font-weight:950;
    font-size:14px;
}
.over {
    color:#43ff67;
}
.game {
    color:#9ba3b3;
    font-size:16px;
    margin-top:12px;
    margin-left:64px;
}
.time {
    float:right;
}
.stat-grid {
    display:grid;
    grid-template-columns: repeat(6, 1fr);
    gap:6px;
    margin-top:14px;
}
.stat {
    background:#162235;
    border:1px solid #25354d;
    border-radius:8px;
    padding:9px 4px;
    text-align:center;
    min-height:48px;
}
.stat-main {
    color:#36f5d2;
    font-weight:950;
    font-size:15px;
}
.stat-yellow {
    color:#ffca36;
}
.stat-green {
    color:#42ff68;
}
.stat-label {
    color:#8d96a8;
    font-size:9px;
    text-transform:uppercase;
    margin-top:3px;
}
.added {
    border:1px solid #13cab7;
    color:#36f5d2;
}
.bottom-nav {
    position:fixed;
    bottom:0;
    left:0;
    right:0;
    background:#081225;
    border-top:1px solid #15233a;
    display:flex;
    justify-content:space-around;
    padding:9px 0 12px 0;
    z-index:9999;
}
.nav {
    color:#7f8899;
    text-align:center;
    font-size:12px;
    font-weight:800;
}
.nav span {
    font-size:22px;
}
.active {
    color:#2ff2d2;
}
@media(max-width:560px) {
    .title {font-size:23px;}
    .subtitle {font-size:13px;}
    .player-name {font-size:20px;}
    .team {font-size:14px;}
    .stat-grid {grid-template-columns: repeat(3, 1fr);}
    .game, .pill-row {margin-left:0;}
    .avatar {width:48px;height:48px;}
}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# SAMPLE MODEL DATA
# Replace this with your real model output later.
# -----------------------------
players = [
    {
        "player": "Aaron Judge",
        "team": "New York Yankees",
        "pos": "RF",
        "odds": "+240",
        "market": "0.5 HR",
        "game": "New York Yankees @ Baltimore Orioles",
        "time": "01:05 ET",
        "score": 40,
        "hr_rate": "6.7%",
        "barrel": "25.8%",
        "matchup": 62,
        "grade": "A+",
        "model": "28.7%",
        "initials": "AJ",
    },
    {
        "player": "James Wood",
        "team": "Washington Nationals",
        "pos": "RF",
        "odds": "+360",
        "market": "0.5 HR",
        "game": "Washington Nationals @ Cincinnati Reds",
        "time": "06:40 ET",
        "score": 38,
        "hr_rate": "4.3%",
        "barrel": "26.3%",
        "matchup": 73,
        "grade": "A",
        "model": "24.1%",
        "initials": "JW",
    },
    {
        "player": "Kyle Schwarber",
        "team": "Philadelphia Phillies",
        "pos": "DH",
        "odds": "+240",
        "market": "0.5 HR",
        "game": "Philadelphia Phillies @ Boston Red Sox",
        "time": "06:45 ET",
        "score": 41,
        "hr_rate": "5.9%",
        "barrel": "24.4%",
        "matchup": 69,
        "grade": "A",
        "model": "25.3%",
        "initials": "KS",
    },
    {
        "player": "Shohei Ohtani",
        "team": "Los Angeles Dodgers",
        "pos": "DH",
        "odds": "+300",
        "market": "0.5 HR",
        "game": "Los Angeles Dodgers @ San Diego Padres",
        "time": "08:10 ET",
        "score": 39,
        "hr_rate": "5.5%",
        "barrel": "22.8%",
        "matchup": 66,
        "grade": "A-",
        "model": "23.8%",
        "initials": "SO",
    },
]

df = pd.DataFrame(players)

# -----------------------------
# HELPERS
# -----------------------------
def calculate_parlay_display(selected_count: int):
    if selected_count <= 0:
        return "+0", "$0", 0
    if selected_count == 1:
        return "+240", "$24", 31
    if selected_count == 2:
        return "+1280", "$128", 34
    return "+5218", "$532", 37

selected_count = 3
parlay_odds, to_win, parlay_grade = calculate_parlay_display(selected_count)

# -----------------------------
# HEADER
# -----------------------------
st.markdown(f"""
<div class="header">
    <div class="brand">
        <div class="logo">⚾</div>
        <div>
            <div class="title">AON WORLD BETS HR MODEL ⚾️💣</div>
            <div class="subtitle">Top HR model picks. Smarter slips.</div>
        </div>
    </div>
    <div>
        <div class="refresh">↻ Refresh</div>
        <div class="updated">Updated: {datetime.now().strftime("%I:%M %p ET")}</div>
    </div>
</div>
""", unsafe_allow_html=True)

# -----------------------------
# PARLAY SLIP
# -----------------------------
st.markdown(f"""
<div class="slip">
    <div class="slip-title">{selected_count} leg parlay <span class="green" style="float:right;">{parlay_odds}</span></div>

    <div class="win-row">
        <div class="win-box">
            <div class="win-label">TO WIN</div>
            <div class="win-money">{to_win}</div>
        </div>
        <div class="grade-box">
            <div class="grade-num">{parlay_grade}</div>
            <div class="grade-label">PARLAY GRADE</div>
        </div>
    </div>

    <div class="action-row">
        <div class="action-btn">🛡️ 💵 🏆</div>
        <div class="action-btn primary-btn">Save & Play</div>
        <div class="action-btn">↗ Share</div>
    </div>

    <div class="remove">🗑 Remove all selections</div>
</div>
""", unsafe_allow_html=True)

# -----------------------------
# FILTER TABS
# -----------------------------
st.markdown("""
<div class="tabs">
    <div class="tab tab-active">By Game</div>
    <div class="tab">By Market</div>
    <div class="tab">By Grade</div>
    <div class="tab">By Rate</div>
    <div class="tab">By Form</div>
    <div class="tab">By Matchup</div>
</div>
""", unsafe_allow_html=True)

# -----------------------------
# PLAYER CARDS
# -----------------------------
for _, p in df.iterrows():
    st.markdown(f"""
    <div class="card">
        <div class="top-row">
            <div class="name-wrap">
                <div class="avatar">{p["initials"]}</div>
                <div>
                    <div>
                        <span class="player-name">{p["player"]}</span>
                        <span class="team"> · {p["team"]} {p["pos"]}</span>
                    </div>
                </div>
            </div>
            <div class="odds">{p["odds"]}</div>
        </div>

        <div class="pill-row">
            <span class="pill over">OVER</span>
            <span class="pill">{p["market"]}</span>
        </div>

        <div class="game">
            {p["game"]}
            <span class="time">{p["time"]}</span>
        </div>

        <div class="stat-grid">
            <div class="stat">
                <div class="stat-main">STATS</div>
                <div class="stat-label">View</div>
            </div>
            <div class="stat">
                <div class="stat-main stat-yellow">{p["score"]}</div>
                <div class="stat-label">Score</div>
            </div>
            <div class="stat">
                <div class="stat-main stat-green">{p["hr_rate"]}</div>
                <div class="stat-label">HR Rate</div>
            </div>
            <div class="stat">
                <div class="stat-main stat-green">{p["barrel"]}</div>
                <div class="stat-label">L30 BRL%</div>
            </div>
            <div class="stat">
                <div class="stat-main stat-green">{p["matchup"]}</div>
                <div class="stat-label">Matchup</div>
            </div>
            <div class="stat added">
                <div class="stat-main">{p["grade"]}</div>
                <div class="stat-label">Added</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# -----------------------------
# BOTTOM NAV
# -----------------------------
st.markdown("""
<div class="bottom-nav">
    <div class="nav"><span>⚾</span><br>Games</div>
    <div class="nav"><span>🔍</span><br>Research</div>
    <div class="nav active"><span>🏠</span><br>Home</div>
    <div class="nav"><span>🔖</span><br>My Parlays</div>
    <div class="nav"><span>🏆</span><br>Arena</div>
</div>
""", unsafe_allow_html=True)
