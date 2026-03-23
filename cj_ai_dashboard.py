import math
import pandas as pd
import streamlit as st

st.set_page_config(page_title="CJ AI Dashboard", layout="wide")

st.title("🔥 CJNeverStops AI Betting Dashboard")

# =========================================================
# LOAD FILES
# =========================================================
@st.cache_data(ttl=3600)
def load_csv(name):
    return pd.read_csv(name)

batters = load_csv("batters.csv")
pitchers = load_csv("pitchers.csv")
parks = load_csv("parks.csv")

# =========================================================
# HELPERS
# =========================================================
def norm(s):
    return str(s).lower().strip()

def logistic(x):
    return 1 / (1 + math.exp(-x))

def implied(odds):
    return 100/(odds+100) if odds>0 else abs(odds)/(abs(odds)+100)

def grade(edge):
    if edge > 0.07: return "🔥 LOCK"
    if edge > 0.05: return "✅ STRONG"
    if edge > 0.03: return "⚠️ LEAN"
    return "❌ PASS"

# =========================================================
# BASIC COLUMN MATCH
# =========================================================
def find_col(df, names):
    for n in names:
        for c in df.columns:
            if n.lower() in c.lower():
                return c
    return None

b_name = find_col(batters, ["name","player"])
p_name = find_col(pitchers, ["name","player"])

batters["_name"] = batters[b_name].apply(norm)
pitchers["_name"] = pitchers[p_name].apply(norm)

# =========================================================
# SELECTORS
# =========================================================
batter = st.selectbox("Batter", sorted(batters[b_name].unique()))
pitcher = st.selectbox("Pitcher", sorted(pitchers[p_name].unique()))
park = st.selectbox("Park", parks["park_name"])

odds = st.number_input("Odds", value=-110)
prop = st.selectbox("Prop", ["Hit","Home Run","Strikeout"])

# =========================================================
# GET ROWS
# =========================================================
b = batters[batters["_name"] == norm(batter)].iloc[0]
p = pitchers[pitchers["_name"] == norm(pitcher)].iloc[0]
park_row = parks[parks["park_name"] == park].iloc[0]

# =========================================================
# METRICS SAFE
# =========================================================
def g(row, key, d):
    try:
        return float(row[key])
    except:
        return d

# fallback defaults
b_xba = g(b, "xba", .240)
b_xslg = g(b, "xslg", .390)
b_k = g(b, "k_percent", .22)

p_xba = g(p, "xba", .240)
p_xslg = g(p, "xslg", .390)
p_k = g(p, "k_percent", .22)

hr_factor = g(park_row, "hr_factor", 1)
hit_factor = g(park_row, "hit_factor", 1)

# =========================================================
# MODEL
# =========================================================
hit_prob = logistic((b_xba - .24)*4 - (p_k - .22)*3) * hit_factor
hr_prob = logistic((b_xslg - .39)*6 + (p_xslg - .39)*4) * hr_factor
k_prob = logistic((p_k - .22)*5 + (b_k - .22)*3)

model = {"Hit":hit_prob,"Home Run":hr_prob,"Strikeout":k_prob}[prop]

book = implied(int(odds))
edge = model - book

# =========================================================
# DISPLAY
# =========================================================
c1,c2,c3,c4 = st.columns(4)
c1.metric("Model %", f"{model*100:.1f}%")
c2.metric("Book %", f"{book*100:.1f}%")
c3.metric("Edge %", f"{edge*100:.1f}%")
c4.metric("Grade", grade(edge))

st.divider()

# =========================================================
# AUTO PICKS ENGINE 🔥
# =========================================================
results = []

for _, b in batters.sample(min(50,len(batters))).iterrows():
    for _, p in pitchers.sample(min(30,len(pitchers))).iterrows():
        try:
            b_xba = g(b,"xba",.24)
            p_k = g(p,"k_percent",.22)

            prob = logistic((b_xba-.24)*4 - (p_k-.22)*3)

            fake_odds = -110
            edge = prob - implied(fake_odds)

            results.append({
                "Player": b[b_name],
                "Pitcher": p[p_name],
                "Prob %": round(prob*100,1),
                "Edge %": round(edge*100,1),
                "Grade": grade(edge)
            })
        except:
            pass

df = pd.DataFrame(results).sort_values("Edge %", ascending=False)

# =========================================================
# TOP PICKS
# =========================================================
st.subheader("🔥 Top 10 AI Picks")
st.dataframe(df.head(10), use_container_width=True)

# =========================================================
# LOCK OF DAY
# =========================================================
top = df.iloc[0]
st.subheader("💰 LOCK OF THE DAY")
st.write(top)

# =========================================================
# HR BOMB FINDER
# =========================================================
hr_list = batters.copy()
hr_list["power"] = hr_list.apply(lambda r: g(r,"xslg",.39), axis=1)
hr_list = hr_list.sort_values("power", ascending=False)

st.subheader("💣 HR Bomb Targets")
st.dataframe(hr_list[[b_name,"power"]].head(10), use_container_width=True)
