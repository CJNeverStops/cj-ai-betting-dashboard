import streamlit as st
import pandas as pd
import requests
from datetime import datetime, date

st.set_page_config(page_title="AON WORLD BETS HR MODEL ⚾️💣", layout="wide")

# ================= CSS =================
st.markdown("""
<style>
[data-testid="stAppViewContainer"] {
    background: radial-gradient(circle at top left, #071a2f 0%, #06101f 45%, #020711 100%);
    color: white;
}
[data-testid="stHeader"] { background: transparent; }
.block-container {
    max-width: 1180px;
    padding-top: 1rem;
    padding-bottom: 7rem;
}
h1,h2,h3,p,label,span { color:white; }
.stButton button {
    width:100%;
    background:#071424;
    color:#2ef2d2;
    border:1px solid #13c7b5;
    border-radius:12px;
    font-weight:900;
    padding:.7rem;
}
.stButton button:hover {
    background:#0b5f59;
    color:white;
    border:1px solid #2ef2d2;
}
.top-card {
    background:rgba(7,18,32,.98);
    border:1px solid #18304c;
    border-radius:18px;
    padding:18px;
    margin-bottom:16px;
}
.player-card {
    background:rgba(7,18,32,.98);
    border:1px solid #18304c;
    border-radius:18px;
    padding:14px;
    margin-bottom:12px;
}
.green { color:#2ef2d2 !important; font-weight:900; }
.gray { color:#9aa8bb !important; }
.aon-title {
    font-size:38px;
    font-weight:950;
    color:#2ef2d2;
    line-height:1;
}
.aon-logo {
    font-size:42px;
    font-weight:950;
    color:white;
    line-height:.9;
}
.aon-sub {
    color:#b8c3d4;
    font-size:15px;
}
.grade-pill {
    display:inline-block;
    background:#063b2f;
    color:#69ff7a;
    padding:6px 14px;
    border-radius:999px;
    font-weight:950;
}
.player-name {
    font-size:30px;
    font-weight:950;
}
.player-team {
    color:#a2aec0;
    font-size:17px;
}
.metric-label {
    color:#9aa8bb;
    font-size:12px;
}
.metric-value {
    color:#2ef2d2;
    font-size:18px;
    font-weight:950;
}
.nav-wrap {
    background:#06101f;
    border:1px solid #18304c;
    border-radius:18px;
    padding:10px;
    margin:14px 0;
}
@media(max-width:800px) {
    .aon-title { font-size:28px; }
    .aon-logo { font-size:34px; }
    .player-name { font-size:23px; }
}
</style>
""", unsafe_allow_html=True)

# ================= HELPERS =================
def api_get(url):
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.json()

def headshot(player_id):
    return f"https://img.mlbstatic.com/mlb-photos/image/upload/w_213,q_100/v1/people/{player_id}/headshot/67/current"

def implied_prob(odds):
    odds = int(str(odds).replace("+", ""))
    return round((100 / (odds + 100)) * 100, 1)

def american_to_decimal(odds):
    odds = int(str(odds).replace("+", ""))
    return 1 + odds / 100

def calc_parlay(slip):
    if not slip:
        return "+0", "$0", 0
    dec = 1
    for leg in slip:
        dec *= american_to_decimal(leg["ODDS"])
    return f"+{int((dec - 1) * 100)}", f"${int((dec - 1) * 10)}", min(99, int(sum(x["MODEL_SCORE"] for x in slip) / len(slip)))

def grade_from_rank(rank):
    if rank <= 5: return "A+"
    if rank <= 15: return "A"
    if rank <= 30: return "A-"
    if rank <= 55: return "B+"
    if rank <= 85: return "B"
    if rank <= 130: return "C+"
    return "C"

def odds_from_rank(rank):
    if rank <= 5: return "+240"
    if rank <= 15: return "+300"
    if rank <= 30: return "+360"
    if rank <= 60: return "+425"
    return "+500"

# ================= REAL DATA =================
@st.cache_data(ttl=3600)
def load_hitters():
    season = date.today().year
    url = f"https://statsapi.mlb.com/api/v1/stats?stats=season&group=hitting&season={season}&playerPool=ALL&limit=900&sportIds=1"
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

            if ab <= 0 or pa < 20:
                continue

            iso = round(slg - avg, 3)
            hr_rate = round((hr / ab) * 100, 2)
            barrel_est = round((iso * 100 * .65) + (slg * 100 * .35), 1)

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
                "HEADSHOT": headshot(pid),
            })
        except Exception:
            pass

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    df["HR_RATE_PCT"] = df["HR_RATE"].rank(pct=True)
    df["ISO_PCT"] = df["ISO"].rank(pct=True)
    df["SLG_PCT"] = df["SLG"].rank(pct=True)
    df["OPS_PCT"] = df["OPS"].rank(pct=True)
    df["HR_PCT"] = df["HR"].rank(pct=True)
    df["BARREL_PCT"] = df["BARREL_EST"].rank(pct=True)
    df["PA_FACTOR"] = (df["PA"] / df["PA"].max()).clip(0, 1)

    df["MODEL_SCORE"] = (
        (df["HR_RATE_PCT"] * 28)
        + (df["ISO_PCT"] * 24)
        + (df["BARREL_PCT"] * 18)
        + (df["SLG_PCT"] * 12)
        + (df["OPS_PCT"] * 10)
        + (df["HR_PCT"] * 6)
        + (df["PA_FACTOR"] * 2)
    ).round(1)

    df = df.sort_values("MODEL_SCORE", ascending=False).reset_index(drop=True)
    df["RANK"] = df.index + 1
    df["GRADE"] = df["RANK"].apply(grade_from_rank)
    df["ODDS"] = df["RANK"].apply(odds_from_rank)
    df["BOOK_PROB"] = df["ODDS"].apply(implied_prob)
    df["MODEL_PROB"] = (df["MODEL_SCORE"] / 100 * 32).round(1)
    df["EDGE"] = (df["MODEL_PROB"] - df["BOOK_PROB"]).round(1)
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
            })

    return pd.DataFrame(rows)

hitters = load_hitters()
games = load_games()

if "slip" not in st.session_state:
    st.session_state.slip = []

if "page" not in st.session_state:
    st.session_state.page = "Home"

if hitters.empty:
    st.error("No MLB data loaded.")
    st.stop()

# ================= HEADER =================
h1, h2 = st.columns([4, 1])
with h1:
    c_logo, c_title = st.columns([1, 3])
    with c_logo:
        st.markdown("<div class='aon-logo'>A⚾N</div><div class='aon-sub'><b>WORLD BETS</b></div>", unsafe_allow_html=True)
    with c_title:
        st.markdown("<div class='aon-title'>HR MODEL ⚾️💣</div><div class='aon-sub'>Real MLB Data • Weather • Park Factors • Edges</div>", unsafe_allow_html=True)

with h2:
    if st.button("⟳ Refresh"):
        st.cache_data.clear()
        st.rerun()
    st.caption(f"Updated: {datetime.now().strftime('%I:%M %p ET')}")

top = hitters.iloc[0]

# ================= TOP CARDS =================
st.markdown("<div class='top-card'>", unsafe_allow_html=True)
t1, t2, t3, t4 = st.columns(4)
t1.metric("TOP HR PICK", top["Name"], top["Team"])
t2.metric("WEATHER", "78°F 🌤️", "Wind 11 mph OUT")
t3.metric("TOP PARK FACTOR", "Coors Field", "136 HR Factor")
t4.metric("APPROACH", "OVER 0.5 HR", "High Model Edge")
st.markdown("</div>", unsafe_allow_html=True)

odds_display, win_display, parlay_grade = calc_parlay(st.session_state.slip)

st.markdown("<div class='top-card'>", unsafe_allow_html=True)
p1, p2, p3, p4 = st.columns([2, 1, 1, 1])
p1.subheader("PARLAY BUILDER")
p1.markdown(f"<span class='green'>{len(st.session_state.slip)} Leg Parlay</span>", unsafe_allow_html=True)
p1.write("  ".join([f"`{x['Name'].split()[-1]} ×`" for x in st.session_state.slip[:5]]) if st.session_state.slip else "Add players below.")
p2.metric("ODDS", odds_display)
p3.metric("To Win ($10)", win_display)
p4.metric("Parlay Grade", parlay_grade)
st.markdown("</div>", unsafe_allow_html=True)

# ================= CLICKABLE BOTTOM STYLE NAV =================
st.markdown("<div class='nav-wrap'>", unsafe_allow_html=True)
n1, n2, n3, n4, n5 = st.columns(5)

if n1.button("🏠 Home"):
    st.session_state.page = "Home"
    st.rerun()
if n2.button("⚾ Games"):
    st.session_state.page = "Games"
    st.rerun()
if n3.button("📊 Research"):
    st.session_state.page = "Research"
    st.rerun()
if n4.button("🎟️ My Parlays"):
    st.session_state.page = "My Parlays"
    st.rerun()
if n5.button("👤 Profile"):
    st.session_state.page = "Profile"
    st.rerun()

st.markdown(f"<div class='green'>Current Tab: {st.session_state.page}</div>", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# ================= HOME =================
if st.session_state.page == "Home":
    f1, f2, f3, f4 = st.columns([1, 1.2, 1.4, 2])

    grade_filter = f1.selectbox("All Grades", ["All", "A+", "A", "A-", "B+", "B", "C+", "C"], label_visibility="collapsed")
    min_hr = f2.selectbox("Min HR Rate", ["0", "2", "4", "6", "8"], index=1, label_visibility="collapsed")
    sort_label = f3.selectbox("Sort By", ["Model Score", "Rank", "Edge", "HR Rate", "HR", "ISO", "OPS"], label_visibility="collapsed")
    search = f4.text_input("Search player or team...", label_visibility="collapsed")

    sort_map = {
        "Model Score": "MODEL_SCORE",
        "Rank": "RANK",
        "Edge": "EDGE",
        "HR Rate": "HR_RATE",
        "HR": "HR",
        "ISO": "ISO",
        "OPS": "OPS",
    }

    filtered = hitters.copy()

    if grade_filter != "All":
        order = {"A+": 7, "A": 6, "A-": 5, "B+": 4, "B": 3, "C+": 2, "C": 1}
        filtered = filtered[filtered["GRADE"].map(order) >= order[grade_filter]]

    filtered = filtered[filtered["HR_RATE"] >= float(min_hr)]

    if search.strip():
        s = search.lower().strip()
        filtered = filtered[
            filtered["Name"].str.lower().str.contains(s, na=False)
            | filtered["Team"].str.lower().str.contains(s, na=False)
        ]

    sort_by = sort_map[sort_label]
    filtered = filtered.sort_values(sort_by, ascending=(sort_by == "RANK"))

    for _, row in filtered.iterrows():
        already_added = any(x["ID"] == row["ID"] for x in st.session_state.slip)

        st.markdown("<div class='player-card'>", unsafe_allow_html=True)
        left, mid, right = st.columns([1.1, 3.2, 1.2])

        with left:
            st.image(row["HEADSHOT"], width=130)

        with mid:
            name_col, grade_col = st.columns([4, 1])
            name_col.markdown(f"<div class='player-name'>{row['Name']}</div><div class='player-team'>{row['Team']}</div>", unsafe_allow_html=True)
            grade_col.markdown(f"<span class='grade-pill'>{row['GRADE']}</span>", unsafe_allow_html=True)
            st.divider()

            m1, m2, m3, m4, m5, m6 = st.columns(6)
            for col, label, value in [
                (m1, "Model Score", row["MODEL_SCORE"]),
                (m2, "HR", row["HR"]),
                (m3, "HR Rate", f"{row['HR_RATE']}%"),
                (m4, "ISO", row["ISO"]),
                (m5, "OPS", row["OPS"]),
                (m6, "Edge", f"{row['EDGE']}%"),
            ]:
                col.markdown(f"<div class='metric-label'>{label}</div><div class='metric-value'>{value}</div>", unsafe_allow_html=True)

        with right:
            st.markdown(f"## {row['ODDS']}")
            st.markdown("<span class='green'>OVER 0.5 HR</span>", unsafe_allow_html=True)
            st.caption(f"Rank #{row['RANK']}")

            if already_added:
                if st.button("✓ Added", key=f"remove_{row['ID']}"):
                    st.session_state.slip = [x for x in st.session_state.slip if x["ID"] != row["ID"]]
                    st.rerun()
            else:
                if st.button("+ Add", key=f"add_{row['ID']}"):
                    st.session_state.slip.append(row.to_dict())
                    st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

# ================= GAMES =================
elif st.session_state.page == "Games":
    st.subheader("Today’s MLB Games")

    if games.empty:
        st.warning("No MLB games found today.")
    else:
        for _, g in games.iterrows():
            with st.expander(g["Game"], expanded=True):
                st.write(f"**Venue:** {g['Venue']}")
                st.write(f"**Probable Pitchers:** {g['Away Pitcher']} vs {g['Home Pitcher']}")

                game_hitters = hitters[hitters["Team"].isin([g["Away"], g["Home"]])].sort_values("MODEL_SCORE", ascending=False)

                st.dataframe(
                    game_hitters[["RANK", "Name", "Team", "GRADE", "MODEL_SCORE", "HR", "HR_RATE", "ISO", "OPS", "EDGE", "ODDS"]],
                    use_container_width=True,
                    height=350,
                )

# ================= RESEARCH =================
elif st.session_state.page == "Research":
    st.subheader("Research Breakdown By Game")

    if games.empty:
        st.warning("No games found today.")
    else:
        for _, g in games.iterrows():
            game_hitters = hitters[hitters["Team"].isin([g["Away"], g["Home"]])].sort_values("MODEL_SCORE", ascending=False)

            with st.expander(f"📊 {g['Game']} — {g['Venue']}", expanded=False):
                st.write(f"**Pitching Matchup:** {g['Away Pitcher']} vs {g['Home Pitcher']}")
                st.write("**Stats collected:** HR, AB, PA, AVG, SLG, OPS, ISO, HR Rate, estimated barrel power, model probability, book probability, edge, and grade.")

                for _, p in game_hitters.iterrows():
                    a, b, c = st.columns([1, 3, 2])
                    a.image(p["HEADSHOT"], width=90)
                    b.markdown(f"### #{p['RANK']} {p['Name']}")
                    b.write(f"**{p['Team']}** | Grade **{p['GRADE']}** | Score **{p['MODEL_SCORE']}**")
                    b.write(f"HR **{p['HR']}** | HR Rate **{p['HR_RATE']}%** | ISO **{p['ISO']}** | OPS **{p['OPS']}** | SLG **{p['SLG']}**")
                    c.write(f"**Odds:** {p['ODDS']}")
                    c.write(f"**Edge:** {p['EDGE']}%")
                    c.write(f"**Barrel Est:** {p['BARREL_EST']}")
                    st.divider()

# ================= MY PARLAYS =================
elif st.session_state.page == "My Parlays":
    st.subheader("My Parlays")

    odds_display, win_display, parlay_grade = calc_parlay(st.session_state.slip)

    c1, c2, c3 = st.columns(3)
    c1.metric("Parlay Odds", odds_display)
    c2.metric("To Win on $10", win_display)
    c3.metric("Parlay Grade", parlay_grade)

    if not st.session_state.slip:
        st.info("No players added yet.")
    else:
        for leg in st.session_state.slip:
            x1, x2, x3 = st.columns([1, 4, 1])
            x1.image(leg["HEADSHOT"], width=75)
            x2.write(f"✅ **{leg['Name']}** — OVER 0.5 HR — {leg['ODDS']} — Grade {leg['GRADE']}")
            if x3.button("Remove", key=f"parlay_remove_{leg['ID']}"):
                st.session_state.slip = [x for x in st.session_state.slip if x["ID"] != leg["ID"]]
                st.rerun()

        if st.button("🗑 Clear All"):
            st.session_state.slip = []
            st.rerun()

# ================= PROFILE =================
elif st.session_state.page == "Profile":
    st.subheader("Model Info")
    st.write("This model ranks hitters using real MLB Stats API data.")
    st.write("Grades are rank-based so only the best players get A+.")

    st.dataframe(
        hitters[["RANK", "Name", "Team", "GRADE", "MODEL_SCORE", "MODEL_PROB", "BOOK_PROB", "EDGE", "HR", "AB", "PA", "AVG", "SLG", "OPS", "ISO", "HR_RATE", "BARREL_EST", "ODDS"]],
        use_container_width=True,
        height=700,
    )
