import streamlit as st
import pandas as pd
import requests
from datetime import datetime, date

st.set_page_config(
    page_title="AON WORLD BETS HR MODEL ⚾️💣",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# =========================
# STYLE
# =========================
st.markdown("""
<style>
[data-testid="stAppViewContainer"] {
    background: radial-gradient(circle at top, #071a2c 0%, #06101f 45%, #020712 100%);
    color: white;
}
[data-testid="stHeader"] {
    background: transparent;
}
.block-container {
    max-width: 1250px;
    padding: 1rem .7rem 6rem .7rem;
}
h1, h2, h3, p, label {
    color: white !important;
}
.stButton button {
    background: #071424;
    color: #2ef2d2;
    border: 1px solid #13c7b5;
    border-radius: 12px;
    font-weight: 900;
    padding: 11px;
}
.stButton button:hover {
    background: #0b5f59;
    color: white;
    border: 1px solid #2ef2d2;
}
div[data-baseweb="tab-list"] {
    gap: 8px;
}
div[data-baseweb="tab"] {
    background: #071424;
    border: 1px solid #18304c;
    border-radius: 12px;
    color: #2ef2d2;
    font-weight: 900;
}
.player-card {
    background: rgba(7,18,32,.98);
    border: 1px solid #13c7b5;
    border-radius: 18px;
    padding: 16px;
    margin-bottom: 16px;
}
.top-panel {
    background: rgba(7,18,32,.98);
    border: 1px solid #18304c;
    border-radius: 18px;
    padding: 16px;
    margin-bottom: 16px;
}
.green {
    color: #2ef2d2;
    font-weight: 900;
}
.gray {
    color: #9aa8bb;
}
.grade-pill {
    background: #063b2f;
    color: #69ff7a;
    padding: 6px 14px;
    border-radius: 999px;
    font-weight: 900;
}
.small-label {
    color: #9aa8bb;
    font-size: 12px;
    text-transform: uppercase;
}
.big-title {
    font-size: 34px;
    font-weight: 950;
    color: white;
}
@media(max-width:800px) {
    .big-title {
        font-size: 26px;
    }
}
</style>
""", unsafe_allow_html=True)

# =========================
# HELPERS
# =========================
def api_get(url):
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.json()

def headshot(player_id):
    return f"https://img.mlbstatic.com/mlb-photos/image/upload/w_213,q_100/v1/people/{player_id}/headshot/67/current"

def odds_from_rank(rank):
    if rank <= 5:
        return "+240"
    if rank <= 15:
        return "+300"
    if rank <= 30:
        return "+360"
    if rank <= 60:
        return "+425"
    return "+500"

def american_to_decimal(odds):
    odds = int(str(odds).replace("+", ""))
    return 1 + odds / 100

def implied_prob(odds):
    odds = int(str(odds).replace("+", ""))
    return round((100 / (odds + 100)) * 100, 1)

def assign_grades(df):
    df = df.sort_values("MODEL_SCORE", ascending=False).copy()
    df["RANK"] = range(1, len(df) + 1)

    def grade(rank):
        if rank <= 5:
            return "A+"
        elif rank <= 15:
            return "A"
        elif rank <= 30:
            return "A-"
        elif rank <= 50:
            return "B+"
        elif rank <= 80:
            return "B"
        elif rank <= 120:
            return "C+"
        return "C"

    df["GRADE"] = df["RANK"].apply(grade)
    df["ODDS"] = df["RANK"].apply(odds_from_rank)
    df["BOOK_PROB"] = df["ODDS"].apply(implied_prob)
    df["MODEL_PROB"] = (df["MODEL_SCORE"] / df["MODEL_SCORE"].max() * 32).round(1)
    df["EDGE"] = (df["MODEL_PROB"] - df["BOOK_PROB"]).round(1)
    return df

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

# =========================
# REAL MLB DATA
# =========================
@st.cache_data(ttl=3600)
def load_hitters():
    url = (
        "https://statsapi.mlb.com/api/v1/stats"
        "?stats=season&group=hitting&season=2025"
        "&playerPool=ALL&limit=900&sportIds=1"
    )

    data = api_get(url)
    rows = []

    for item in data.get("stats", [{}])[0].get("splits", []):
        stat = item.get("stat", {})
        player = item.get("player", {})
        team = item.get("team", {})

        try:
            pid = player.get("id")
            name = player.get("fullName")
            team_name = team.get("name")

            hr = int(stat.get("homeRuns", 0))
            ab = int(stat.get("atBats", 0))
            pa = int(stat.get("plateAppearances", 0))
            avg = float(stat.get("avg", 0) or 0)
            slg = float(stat.get("slg", 0) or 0)
            ops = float(stat.get("ops", 0) or 0)

            if ab <= 0 or pa <= 20:
                continue

            iso = round(slg - avg, 3)
            hr_rate = round((hr / ab) * 100, 2)
            sample_boost = min(pa / 100, 5)
            barrel_est = round((iso * 100 * 0.65) + (slg * 100 * 0.35), 1)

            model_score = round(
                (hr_rate * 3.2)
                + (iso * 55)
                + (slg * 18)
                + (ops * 8)
                + (barrel_est * 0.18)
                + (min(hr, 25) * 0.55)
                + sample_boost,
                1
            )

            rows.append({
                "ID": pid,
                "Name": name,
                "Team": team_name,
                "HR": hr,
                "AB": ab,
                "PA": pa,
                "AVG": avg,
                "SLG": slg,
                "OPS": ops,
                "ISO": iso,
                "HR_RATE": hr_rate,
                "BARREL_EST": barrel_est,
                "MODEL_SCORE": model_score,
                "HEADSHOT": headshot(pid),
            })

        except Exception:
            pass

    df = pd.DataFrame(rows)

    if df.empty:
        return df

    df = assign_grades(df)
    return df.head(300)

@st.cache_data(ttl=1800)
def load_games():
    today = date.today().isoformat()
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={today}&hydrate=probablePitcher,team"
    data = api_get(url)

    rows = []

    for d in data.get("dates", []):
        for g in d.get("games", []):
            away = g["teams"]["away"]["team"]["name"]
            home = g["teams"]["home"]["team"]["name"]

            rows.append({
                "Game": f"{away} @ {home}",
                "Away": away,
                "Home": home,
                "Venue": g.get("venue", {}).get("name", "Unknown"),
                "Away Pitcher": g["teams"]["away"].get("probablePitcher", {}).get("fullName", "TBD"),
                "Home Pitcher": g["teams"]["home"].get("probablePitcher", {}).get("fullName", "TBD"),
                "Time": g.get("gameDate", ""),
            })

    return pd.DataFrame(rows)

hitters = load_hitters()
games = load_games()

if "slip" not in st.session_state:
    st.session_state.slip = []

# =========================
# HEADER
# =========================
st.markdown("""
<div class="big-title">AON WORLD BETS HR MODEL ⚾️💣</div>
<div class="gray">Real MLB Stats API data • HR rates • ISO • OPS • model grades • player photos</div>
""", unsafe_allow_html=True)

st.caption(f"Updated: {datetime.now().strftime('%I:%M %p ET')}")

if hitters.empty:
    st.error("No MLB hitter data loaded.")
    st.stop()

top = hitters.iloc[0]

# =========================
# TOP PANEL
# =========================
st.markdown('<div class="top-panel">', unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Top HR Pick", top["Name"], top["Team"])
c2.metric("Model Score", top["MODEL_SCORE"], top["GRADE"])
c3.metric("HR Rate", f"{top['HR_RATE']}%")
c4.metric("Edge", f"{top['EDGE']}%")

st.markdown("</div>", unsafe_allow_html=True)

# =========================
# TABS
# =========================
tab_home, tab_games, tab_research, tab_parlays, tab_table = st.tabs(
    ["🏠 Home", "⚾ Games", "📊 Research", "🎟️ My Parlays", "📋 Full Table"]
)

# =========================
# HOME
# =========================
with tab_home:
    st.subheader("Top HR Model Plays")

    f1, f2, f3 = st.columns(3)

    with f1:
        min_grade = st.selectbox("Grade", ["All", "A+", "A", "A-", "B+", "B", "C+", "C"])

    with f2:
        min_hr = st.slider("Minimum HR Rate", 0.0, 15.0, 2.0)

    with f3:
        sort_by = st.selectbox("Sort By", ["MODEL_SCORE", "RANK", "EDGE", "HR_RATE", "HR", "ISO", "OPS", "SLG"])

    search = st.text_input("Search player or team")

    filtered = hitters.copy()

    if min_grade != "All":
        order = {"A+": 7, "A": 6, "A-": 5, "B+": 4, "B": 3, "C+": 2, "C": 1}
        filtered = filtered[filtered["GRADE"].map(order) >= order[min_grade]]

    filtered = filtered[filtered["HR_RATE"] >= min_hr]

    if search.strip():
        s = search.lower().strip()
        filtered = filtered[
            filtered["Name"].str.lower().str.contains(s, na=False)
            | filtered["Team"].str.lower().str.contains(s, na=False)
        ]

    ascending = True if sort_by == "RANK" else False
    filtered = filtered.sort_values(sort_by, ascending=ascending)

    for _, row in filtered.iterrows():
        already_added = any(x["ID"] == row["ID"] for x in st.session_state.slip)

        st.markdown('<div class="player-card">', unsafe_allow_html=True)

        left, middle, right = st.columns([1.15, 3.2, 1.25])

        with left:
            st.image(row["HEADSHOT"], width=120)
            st.metric("Model", row["MODEL_SCORE"])
            st.metric("Grade", row["GRADE"])
            st.caption(f"Rank #{row['RANK']}")

        with middle:
            st.markdown(f"### {row['Name']}  <span class='grade-pill'>{row['GRADE']}</span>", unsafe_allow_html=True)
            st.caption(row["Team"])

            m1, m2, m3 = st.columns(3)
            m1.metric("HR", row["HR"])
            m2.metric("HR Rate", f"{row['HR_RATE']}%")
            m3.metric("ISO", row["ISO"])

            m4, m5, m6 = st.columns(3)
            m4.metric("OPS", row["OPS"])
            m5.metric("SLG", row["SLG"])
            m6.metric("Edge", f"{row['EDGE']}%")

            st.caption(
                f"Research: AB {row['AB']} • PA {row['PA']} • AVG {row['AVG']} • "
                f"Barrel Est {row['BARREL_EST']} • Model Prob {row['MODEL_PROB']}%"
            )

        with right:
            st.markdown(f"## {row['ODDS']}")
            st.markdown("**OVER 0.5 HR**")
            st.caption(f"Book Prob {row['BOOK_PROB']}%")

            if already_added:
                if st.button("✅ Added", key=f"home_remove_{row['ID']}", use_container_width=True):
                    st.session_state.slip = [x for x in st.session_state.slip if x["ID"] != row["ID"]]
                    st.rerun()
            else:
                if st.button("➕ Add Parlay", key=f"home_add_{row['ID']}", use_container_width=True):
                    st.session_state.slip.append(row.to_dict())
                    st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

# =========================
# GAMES
# =========================
with tab_games:
    st.subheader("Today’s MLB Games")

    if games.empty:
        st.warning("No MLB games found today.")
    else:
        for _, g in games.iterrows():
            with st.expander(g["Game"], expanded=True):
                st.write(f"**Venue:** {g['Venue']}")
                st.write(f"**Probable Pitchers:** {g['Away Pitcher']} vs {g['Home Pitcher']}")

                game_hitters = hitters[
                    hitters["Team"].isin([g["Away"], g["Home"]])
                ].sort_values("MODEL_SCORE", ascending=False)

                if game_hitters.empty:
                    st.info("No graded hitters found for this game.")
                else:
                    st.dataframe(
                        game_hitters[
                            ["RANK", "Name", "Team", "GRADE", "MODEL_SCORE", "HR", "HR_RATE", "ISO", "OPS", "EDGE", "ODDS"]
                        ],
                        use_container_width=True
                    )

# =========================
# RESEARCH
# =========================
with tab_research:
    st.subheader("Research Breakdown By Game")

    if games.empty:
        st.warning("No games found today.")
    else:
        for _, g in games.iterrows():
            game_hitters = hitters[
                hitters["Team"].isin([g["Away"], g["Home"]])
            ].sort_values("MODEL_SCORE", ascending=False)

            with st.expander(f"📊 {g['Game']} — {g['Venue']}", expanded=False):
                st.write(f"**Pitching Matchup:** {g['Away Pitcher']} vs {g['Home Pitcher']}")
                st.write("**Stats collected:** HR, AB, PA, AVG, SLG, OPS, ISO, HR Rate, estimated barrel power, model probability, book probability, edge, and grade.")

                if game_hitters.empty:
                    st.info("No hitters matched to this game.")
                else:
                    for _, p in game_hitters.iterrows():
                        x1, x2, x3 = st.columns([1, 3, 2])

                        with x1:
                            st.image(p["HEADSHOT"], width=90)

                        with x2:
                            st.markdown(f"### #{p['RANK']} {p['Name']} — {p['Team']}")
                            st.write(
                                f"Grade **{p['GRADE']}** | Model Score **{p['MODEL_SCORE']}** | "
                                f"Model Prob **{p['MODEL_PROB']}%** | Edge **{p['EDGE']}%**"
                            )
                            st.write(
                                f"HR **{p['HR']}** | HR Rate **{p['HR_RATE']}%** | "
                                f"ISO **{p['ISO']}** | OPS **{p['OPS']}** | SLG **{p['SLG']}**"
                            )

                        with x3:
                            st.write(f"**Odds:** {p['ODDS']}")
                            st.write("**Market:** OVER 0.5 HR")
                            st.write(f"**Book Prob:** {p['BOOK_PROB']}%")
                            st.write(f"**Barrel Est:** {p['BARREL_EST']}")

                        st.divider()

# =========================
# PARLAYS
# =========================
with tab_parlays:
    st.subheader("My Parlay Builder")

    odds_display, win_display, parlay_grade = calc_parlay(st.session_state.slip)

    c1, c2, c3 = st.columns(3)
    c1.metric("Parlay Odds", odds_display)
    c2.metric("To Win on $10", win_display)
    c3.metric("Parlay Grade", parlay_grade)

    if not st.session_state.slip:
        st.info("No players added yet.")
    else:
        for leg in st.session_state.slip:
            c1, c2, c3 = st.columns([1, 4, 1])
            c1.image(leg["HEADSHOT"], width=75)
            c2.write(f"✅ **{leg['Name']}** — OVER 0.5 HR — {leg['ODDS']} — Grade {leg['GRADE']}")
            if c3.button("Remove", key=f"parlay_remove_{leg['ID']}", use_container_width=True):
                st.session_state.slip = [x for x in st.session_state.slip if x["ID"] != leg["ID"]]
                st.rerun()

        if st.button("🗑 Clear All", use_container_width=True):
            st.session_state.slip = []
            st.rerun()

# =========================
# FULL TABLE
# =========================
with tab_table:
    st.subheader("Full Model Table")

    st.dataframe(
        hitters[
            [
                "RANK", "Name", "Team", "GRADE", "MODEL_SCORE", "MODEL_PROB",
                "BOOK_PROB", "EDGE", "HR", "AB", "PA", "AVG", "SLG",
                "OPS", "ISO", "HR_RATE", "BARREL_EST", "ODDS"
            ]
        ],
        use_container_width=True,
        height=700
    )
