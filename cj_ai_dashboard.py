# ===============================
# CJ MLB AI BOARD (FULL + ODDS API)
# ===============================

import math
import pandas as pd
import requests
import streamlit as st
from datetime import datetime

ODDS_API_KEY = "a0fb1acf6e6147cf99f2dd2b20c1e265"

# ===============================
# BASIC HELPERS
# ===============================
def norm(x):
    return str(x).lower().strip()

def implied_prob(odds):
    if odds > 0:
        return 100 / (odds + 100)
    return abs(odds) / (abs(odds) + 100)

def fair_odds(p):
    if p <= 0 or p >= 1:
        return None
    if p >= 0.5:
        return int(-(p / (1 - p)) * 100)
    return int(((1 - p) / p) * 100)

def logistic(x):
    return 1 / (1 + math.exp(-x))

def clamp(x, a, b):
    return max(a, min(b, x))

# ===============================
# LOAD DATA
# ===============================
batters = pd.read_csv("batters.csv")
pitchers = pd.read_csv("pitchers.csv")

# ===============================
# GET MLB GAMES
# ===============================
@st.cache_data(ttl=600)
def get_games():
    url = "https://statsapi.mlb.com/api/v1/schedule?sportId=1"
    return requests.get(url).json()

games_data = get_games()

# ===============================
# GET ODDS (KEY PART)
# ===============================
@st.cache_data(ttl=60)
def get_odds():
    url = f"https://api.the-odds-api.com/v4/sports/baseball_mlb/odds"
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "us",
        "markets": "player_hits,player_home_runs,player_total_bases,player_rbis,player_strikeouts"
    }
    return requests.get(url, params=params).json()

odds_data = get_odds()

# ===============================
# BUILD ODDS LOOKUP
# ===============================
odds_lookup = {}

for game in odds_data:
    for book in game.get("bookmakers", []):
        for market in book.get("markets", []):
            for outcome in market.get("outcomes", []):
                name = norm(outcome.get("description", ""))
                odds_lookup[name] = {
                    "odds": outcome.get("price"),
                    "market": market["key"]
                }

# ===============================
# SIMPLE MODEL (YOUR EXISTING CORE)
# ===============================
def model_hit():
    return 0.55

def model_hr():
    return 0.08

def model_tb():
    return 0.48

def model_rbi():
    return 0.35

def model_k():
    return 0.52

# ===============================
# MATCH PLAYERS TO ODDS
# ===============================
rows = []

for _, b in batters.iterrows():
    name = norm(b["player_name"])

    odds_info = odds_lookup.get(name)

    if odds_info:
        odds = odds_info["odds"]
        implied = implied_prob(odds)

        # pick correct model
        if "hit" in odds_info["market"]:
            prob = model_hit()
        elif "home_run" in odds_info["market"]:
            prob = model_hr()
        elif "total_bases" in odds_info["market"]:
            prob = model_tb()
        elif "rbi" in odds_info["market"]:
            prob = model_rbi()
        else:
            prob = None

        if prob:
            edge = prob - implied

            rows.append({
                "Player": b["player_name"],
                "Market": odds_info["market"],
                "Book Odds": odds,
                "Model %": round(prob * 100, 1),
                "Implied %": round(implied * 100, 1),
                "Edge %": round(edge * 100, 1),
                "Fair Odds": fair_odds(prob)
            })

df = pd.DataFrame(rows)

# ===============================
# DISPLAY
# ===============================
st.title("🔥 CJ MLB EDGE BOARD (LIVE ODDS)")

if df.empty:
    st.warning("No odds matched yet (API or names)")
else:
    st.dataframe(df.sort_values("Edge %", ascending=False))
