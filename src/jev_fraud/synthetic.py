"""Synthetic card-transaction generator, same columns as data.load_frame().

Fraud is injected with realistic but noisy signals (high amounts in online/grocery/gas
categories, night hours, large home-merchant distance), and ~15% of fraud is made
"stealthy" (looks ordinary), so no system can reach perfect scores.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

CATS = ["grocery_pos", "gas_transport", "shopping_net", "shopping_pos", "misc_net", "misc_pos",
        "food_dining", "entertainment", "health_fitness", "home", "kids_pets", "personal_care",
        "travel", "grocery_net"]
# (median amount, sigma) per category for legit traffic
AMT = {"grocery_pos": (60, .5), "gas_transport": (45, .4), "shopping_net": (75, .8), "shopping_pos": (55, .8),
       "misc_net": (40, .8), "misc_pos": (35, .7), "food_dining": (30, .6), "entertainment": (40, .7),
       "health_fitness": (35, .6), "home": (55, .7), "kids_pets": (35, .6), "personal_care": (30, .6),
       "travel": (120, 1.0), "grocery_net": (45, .6)}
MERCH = ["Kuhn LLC", "Rippin Inc", "Bahringer-Schmidt", "Lang and Sons", "Kris Group", "Hudson PLC",
         "Dach, Ward and Bode", "Mraz Ltd", "Terry and Co", "Nikolaus-Wolff"]
JOBS = ["Nurse", "Teacher", "Engineer", "Accountant", "Electrician", "Chef", "Lawyer", "Retail manager",
        "Software developer", "Paramedic"]
CITIES = [("Austin", "TX", 950000), ("Fresno", "CA", 540000), ("Boise", "ID", 235000),
          ("Tulsa", "OK", 410000), ("Albany", "NY", 98000), ("Reno", "NV", 260000),
          ("Duluth", "MN", 86000), ("Macon", "GA", 153000)]


def generate(n: int = 20_000, fraud_rate: float = 0.03, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    is_fraud = (rng.random(n) < fraud_rate).astype(int)
    stealth = is_fraud & (rng.random(n) < 0.15)
    loud = (is_fraud == 1) & ~stealth.astype(bool)

    cat = np.where(
        loud,
        rng.choice(["shopping_net", "misc_net", "grocery_pos", "gas_transport", "shopping_pos", "travel"],
                   n, p=[.30, .25, .20, .12, .08, .05]),
        rng.choice(CATS, n),
    )
    mu = np.array([AMT[c][0] for c in cat]); sg = np.array([AMT[c][1] for c in cat])
    amt = rng.lognormal(np.log(mu), sg)
    amt = np.where(loud, amt * rng.uniform(3, 12, n), amt).round(2).clip(1.0)

    night = rng.choice([22, 23, 0, 1, 2, 3], n)
    day = np.clip(rng.normal(14, 4, n).round(), 6, 21).astype(int)
    hour = np.where(loud & (rng.random(n) < 0.75), night, day)

    ci = rng.integers(0, len(CITIES), n)
    dist = np.where(loud & (rng.random(n) < 0.4), rng.uniform(150, 1500, n), rng.gamma(2.0, 18.0, n)).round(1)
    age = np.clip(rng.normal(46, 15, n), 18, 90).astype(int)

    return pd.DataFrame({
        "amt": amt,
        "merchant": rng.choice(MERCH, n),
        "category": cat,
        "hour": hour,
        "weekday": rng.integers(0, 7, n),
        "gender": rng.choice(["F", "M"], n),
        "age": age,
        "job": rng.choice(JOBS, n),
        "city": [CITIES[i][0] for i in ci],
        "state": [CITIES[i][1] for i in ci],
        "city_pop": [CITIES[i][2] for i in ci],
        "dist_km": dist,
        "is_fraud": is_fraud,
    })
