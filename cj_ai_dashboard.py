import streamlit as st
import pandas as pd
import requests
from datetime import datetime, date

st.set_page_config(page_title="AON WORLD BETS HR MODEL ⚾️💣", layout="wide")

# =========================
# CSS
# =========================
st.markdown("""
<style>
[data-testid="stAppViewContainer"] {
    background: #06101f;
    color: white;
}
[data-testid="stHeader"] {
    background: transparent;
}
.block-container {
    max-width: 1250px;
    padding-bottom: 4rem;
}
h1, h2, h3, p, label {
    color: white !important;
}
.stButton button {
    background: #071424;
    color: #2ef2d2;
    border: 1px solid #13c7b5;
    border-radius: 12px;
    font-weight: 800;
}
.stButton button:hover {
    background: #0b5f59;
    color: white;
}
div[data-baseweb="tab-list"] {
    gap: 10px;
}
div[data-baseweb="tab"] {
    background: #071424;
    border: 1px solid #18304c;
    border-radius: 12px;
    color: #2ef2d2;
    font-weight: 900;
}
.player-card {
    background: #071424;
    border: 1px solid #13c7b5;
    border-radius: 16px;
    padding: 14px;
    margin-bottom: 14px;
}
.metric-box {
    background: #101d31;
    border-radius: 10px;
    padding: 10px;
    text-align: center;
}
.green {
    color: #2ef2d2;
    font-weight: 900;
}
.gray {
    color: #9aa8bb;
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

def odds_from_score(score):
    if score >= 40:
        return "+240"
    if score >= 36:
        return "+300"
    if score >= 32:
        return "+360"
    return "+425"

def american_to_decimal(odds):
    odds = int(str(odds).replace("+", ""))
    return 1 + odds / 100

def implied_prob(odds):
    odds = int(str(odds).replace("+", ""))
    return round((100 / (odds + 100)) * 100, 1)

def calc_parlay(slip):
    if not slip:
        return "+0", "$0", 0

    dec = 1
    for leg in slip:
        dec *= american_to_decimal(leg["ODDS"])

    return f"+{int((dec - 1) * 100)}", f"${int((dec - 1) * 10)}", min(99, int(sum(x["MODEL_SCORE"] for x in slip) / len(slip)))

# =========================
# REAL DATA
# =========================
@st.cache_data(ttl=3600)
def load_hitters():
    url = (
        "https://statsapi.mlb.com/api/v1/stats"
        "?stats=season&group=hitting&season=2025"
        "&playerPool=ALL&limit=800&sportIds=1"
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

            if ab <= 0:
                continue

            iso = round(slg - avg, 3)
            hr_rate = round((hr / ab) * 100, 2)
            barrel_est = round((iso * 100 * .65) + (slg * 100 * .35), 1)

            model_score = round(
                (hr * 1.5)
                + (iso * 60)
                + (slg * 18)
                + (ops * 10)
                + (barrel_est * .22),
                1
            )

            odds = odds_from_score(model_score)
            book_prob = implied_prob(odds)
            model_prob = round(model_score / 1.45, 1)
            edge = round(model_prob - book_prob, 1)

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
                "MODEL_PROB": model_prob,
                "BOOK_PROB": book_prob,
                "EDGE": edge,
                "GRADE": grade_score(model_score),
                "ODDS": odds,
                "HEADSHOT": headshot(pid),
            })
        except Exception:
            pass

    df = pd.DataFrame(rows)
    return df.sort_values("MODEL_SCORE", ascending=False).head(300)

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
            away_pitcher = g["teams"]["away"].get("probablePitcher", {}).get("fullName", "TBD")
            home_pitcher = g["teams"]["home"].get("probablePitcher", {}).get("fullName", "TBD")
            rows.append({
                "Game": f"{away} @ {home}",
                "Away": away,
                "Home": home,
                "Away Pitcher": away_pitcher,
                "Home Pitcher": home_pitcher,
                "Time": g.get("gameDate", ""),
                "Venue": g.get("venue", {}).get("name", "Unknown")
            })

    return pd.DataFrame(rows)

hitters = load_hitters()
games = load_games()

if "slip" not in st.session_state:
    st.session_state.slip = []

# =========================
# HEADER
# =========================
st.title("AON WORLD BETS HR MODEL ⚾️💣")
st.caption(f"Real MLB Stats API data • Updated {datetime.now().strftime('%I:%M %p ET')}")

# =========================
# TOP PANEL
# =========================
top = hitters.iloc[0]
c1, c2, c3, c4 = st.columns(4)
c1.metric("Top HR Pick", top["Name"], top["Team"])
c2.metric("Model Score", top["MODEL_SCORE"], top["GRADE"])
c3.metric("HR Rate", f"{top['HR_RATE']}%")
c4.metric("Edge", f"+{top['EDGE']}%")

# =========================
# CLICKABLE BOTTOM/TOP TABS
# =========================
tab_home, tab_games, tab_research, tab_parlays, tab_table = st.tabs(
    ["🏠 Home", "⚾ Games", "📊 Research", "🎟️ My Parlays", "📋 Full Table"]
)

# =========================
# HOME TAB
# =========================
with tab_home:
    st.subheader("Top HR Model Plays")

    f1, f2, f3 = st.columns(3)
    with f1:
        min_grade = st.selectbox("Grade", ["All", "A+", "A", "A-", "B+", "B"])
    with f2:
        min_hr = st.slider("Minimum HR Rate", 0.0, 15.0, 2.0)
    with f3:
        sort_by = st.selectbox("Sort By", ["MODEL_SCORE", "EDGE", "HR_RATE", "HR", "ISO", "OPS"])

    search = st.text_input("Search player or team")

    filtered = hitters.copy()

    if min_grade != "All":
        order = {"A+": 5, "A": 4, "A-": 3, "B+": 2, "B": 1}
        filtered = filtered[filtered["GRADE"].map(order) >= order[min_grade]]

    filtered = filtered[filtered["HR_RATE"] >= min_hr]

    if search:
        s = search.lower()
        filtered = filtered[
            filtered["Name"].str.lower().str.contains(s, na=False)
            | filtered["Team"].str.lower().str.contains(s, na=False)
        ]

    filtered = filtered.sort_values(sort_by, ascending=False)

    for _, row in filtered.iterrows():
        with st.container():
            st.markdown('<div class="player-card">', unsafe_allow_html=True)

            a, b, c = st.columns([1, 4, 1.5])

            with a:
                st.image(row["HEADSHOT"], width=105)

            with b:
                st.markdown(f"### {row['Name']}  `{row['GRADE']}`")
                st.caption(row["Team"])
                m1, m2, m3, m4, m5, m6 = st.columns(6)
                m1.metric("Model", row["MODEL_SCORE"])
                m2.metric("HR", row["HR"])
                m3.metric("HR Rate", f"{row['HR_RATE']}%")
                m4.metric("ISO", row["ISO"])
                m5.metric("OPS", row["OPS"])
                m6.metric("Edge", f"+{row['EDGE']}%")

            with c:
                st.markdown(f"## {row['ODDS']}")
                st.markdown("**OVER 0.5 HR**")
                added = any(x["ID"] == row["ID"] for x in st.session_state.slip)

                if added:
                    if st.button("✅ Added", key=f"home_remove_{row['ID']}"):
                        st.session_state.slip = [x for x in st.session_state.slip if x["ID"] != row["ID"]]
                        st.rerun()
                else:
                    if st.button(f"+ Add {row['Name']}", key=f"home_add_{row['ID']}"):
                        st.session_state.slip.append(row.to_dict())
                        st.rerun()

            st.markdown("</div>", unsafe_allow_html=True)

# =========================
# GAMES TAB
# =========================
with tab_games:
    st.subheader("Today’s MLB Games")

    if games.empty:
        st.warning("No games found for today.")
    else:
        for _, g in games.iterrows():
            with st.expander(g["Game"], expanded=True):
                st.write(f"**Venue:** {g['Venue']}")
                st.write(f"**Probable Pitchers:** {g['Away Pitcher']} vs {g['Home Pitcher']}")

                game_hitters = hitters[
                    hitters["Team"].isin([g["Away"], g["Home"]])
                ].sort_values("MODEL_SCORE", ascending=False)

                if game_hitters.empty:
                    st.info("No graded hitters found for this game yet.")
                else:
                    st.dataframe(
                        game_hitters[
                            ["Name", "Team", "GRADE", "MODEL_SCORE", "HR", "HR_RATE", "ISO", "OPS", "EDGE", "ODDS"]
                        ],
                        use_container_width=True
                    )

# =========================
# RESEARCH TAB
# =========================
with tab_research:
    st.subheader("Research Breakdown By Game")

    if games.empty:
        st.warning("No games found for today.")
    else:
        for _, g in games.iterrows():
            game_hitters = hitters[
                hitters["Team"].isin([g["Away"], g["Home"]])
            ].sort_values("MODEL_SCORE", ascending=False)

            with st.expander(f"📊 {g['Game']} — {g['Venue']}", expanded=False):
                st.write(f"**Pitching Matchup:** {g['Away Pitcher']} vs {g['Home Pitcher']}")
                st.write("**Research collected:** HR, AB, PA, AVG, SLG, OPS, ISO, HR Rate, estimated barrel power, model probability, book probability, edge, grade.")

                if game_hitters.empty:
                    st.info("No hitters matched to this game.")
                else:
                    for _, p in game_hitters.iterrows():
                        x1, x2, x3 = st.columns([1, 3, 2])

                        with x1:
                            st.image(p["HEADSHOT"], width=85)

                        with x2:
                            st.markdown(f"### {p['Name']} — {p['Team']}")
                            st.write(
                                f"Grade **{p['GRADE']}** | Model Score **{p['MODEL_SCORE']}** | "
                                f"Model Prob **{p['MODEL_PROB']}%** | Edge **+{p['EDGE']}%**"
                            )
                            st.write(
                                f"HR: **{p['HR']}** | HR Rate: **{p['HR_RATE']}%** | "
                                f"ISO: **{p['ISO']}** | OPS: **{p['OPS']}** | SLG: **{p['SLG']}**"
                            )

                        with x3:
                            st.write(f"**Odds:** {p['ODDS']}")
                            st.write("**Market:** OVER 0.5 HR")
                            st.write(f"**Barrel Est:** {p['BARREL_EST']}")

                        st.divider()

# =========================
# PARLAYS TAB
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
            c1.image(leg["HEADSHOT"], width=70)
            c2.write(f"✅ **{leg['Name']}** — OVER 0.5 HR — {leg['ODDS']} — Grade {leg['GRADE']}")
            if c3.button("Remove", key=f"parlay_remove_{leg['ID']}"):
                st.session_state.slip = [x for x in st.session_state.slip if x["ID"] != leg["ID"]]
                st.rerun()

        if st.button("🗑 Clear All"):
            st.session_state.slip = []
            st.rerun()

# =========================
# FULL TABLE TAB
# =========================
with tab_table:
    st.subheader("Full Model Table")

    st.dataframe(
        hitters[
            [
                "Name", "Team", "GRADE", "MODEL_SCORE", "MODEL_PROB", "BOOK_PROB",
                "EDGE", "HR", "AB", "PA", "AVG", "SLG", "OPS", "ISO",
                "HR_RATE", "BARREL_EST", "ODDS"
            ]
        ],
        use_container_width=True,
        height=700
    )
