from datetime import datetime
import pandas as pd
from pybaseball import statcast_batter_expected_stats, batting_stats

YEAR = datetime.now().year

def norm_name(x):
    x = str(x).strip()
    if "," in x:
        last, first = [p.strip() for p in x.split(",", 1)]
        return f"{first} {last}"
    return x

def find_col(df, names):
    lower = {str(c).lower().strip(): c for c in df.columns}
    for n in names:
        if n.lower() in lower:
            return lower[n.lower()]
    for n in names:
        for c in df.columns:
            if n.lower() in str(c).lower():
                return c
    return None

print("Pulling Baseball Savant expected stats...")
savant = statcast_batter_expected_stats(YEAR)

savant["_name"] = savant["last_name, first_name"].apply(norm_name)

print("Pulling FanGraphs batting stats...")
fg = batting_stats(YEAR, qual=0)
fg["_name"] = fg["Name"].astype(str)

team_col = find_col(fg, ["Team"])
iso_col = find_col(fg, ["ISO"])
k_col = find_col(fg, ["K%"])
barrel_col = find_col(fg, ["Barrel%", "Barrel"])
hard_col = find_col(fg, ["HardHit%", "Hard%"])

keep = ["_name"]
for c in [team_col, iso_col, k_col, barrel_col, hard_col]:
    if c and c not in keep:
        keep.append(c)

fg_small = fg[keep].copy()

rename = {}
if team_col: rename[team_col] = "team"
if iso_col: rename[iso_col] = "iso"
if k_col: rename[k_col] = "k_percent"
if barrel_col: rename[barrel_col] = "barrel"
if hard_col: rename[hard_col] = "hard_hit"

fg_small = fg_small.rename(columns=rename)

df = savant.merge(fg_small, on="_name", how="left")

needed_cols = [
    "last_name, first_name",
    "player_id",
    "year",
    "pa",
    "bip",
    "ba",
    "est_ba",
    "est_ba_minus_ba_diff",
    "slg",
    "est_slg",
    "est_slg_minus_slg_diff",
    "woba",
    "est_woba",
    "est_woba_minus_woba_diff",
    "team",
    "barrel",
    "hard_hit",
    "iso",
    "k_percent",
    "last7_slg",
    "ab_since_hr",
    "xslg_vs_rhp",
    "xslg_vs_lhp",
    "xslg_vs_fastball",
    "xslg_vs_breaking",
    "xslg_vs_offspeed",
]

for col in needed_cols:
    if col not in df.columns:
        df[col] = ""

df = df[needed_cols]

df.to_csv("batters.csv", index=False)

print("DONE: batters.csv created with advanced columns.")
print(df.head())
