"""
Seed World Cup 2026 data: 48 teams, 72 group stage matches.
Run: python seed_data.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))

from datetime import datetime
from database import engine, SessionLocal, Base
import models

Base.metadata.create_all(bind=engine)

TEAMS = [
    # (name, code, group, flag_emoji)
    ("Mexico",            "MEX", "A", "🇲🇽"),
    ("South Africa",      "RSA", "A", "🇿🇦"),
    ("South Korea",       "KOR", "A", "🇰🇷"),
    ("Czechia",           "CZE", "A", "🇨🇿"),
    ("Canada",            "CAN", "B", "🇨🇦"),
    ("Bosnia & Herz.",     "BIH", "B", "🇧🇦"),
    ("Qatar",             "QAT", "B", "🇶🇦"),
    ("Switzerland",       "SUI", "B", "🇨🇭"),
    ("Brazil",            "BRA", "C", "🇧🇷"),
    ("Morocco",           "MAR", "C", "🇲🇦"),
    ("Haiti",             "HAI", "C", "🇭🇹"),
    ("Scotland",          "SCO", "C", "🏴󠁧󠁢󠁳󠁣󠁴󠁿"),
    ("United States",     "USA", "D", "🇺🇸"),
    ("Paraguay",          "PAR", "D", "🇵🇾"),
    ("Australia",         "AUS", "D", "🇦🇺"),
    ("Türkiye",           "TUR", "D", "🇹🇷"),
    ("Germany",           "GER", "E", "🇩🇪"),
    ("Curaçao",           "CUW", "E", "🇨🇼"),
    ("Ivory Coast",       "CIV", "E", "🇨🇮"),
    ("Ecuador",           "ECU", "E", "🇪🇨"),
    ("Netherlands",       "NED", "F", "🇳🇱"),
    ("Japan",             "JPN", "F", "🇯🇵"),
    ("Sweden",            "SWE", "F", "🇸🇪"),
    ("Tunisia",           "TUN", "F", "🇹🇳"),
    ("Belgium",           "BEL", "G", "🇧🇪"),
    ("Egypt",             "EGY", "G", "🇪🇬"),
    ("Iran",              "IRN", "G", "🇮🇷"),
    ("New Zealand",       "NZL", "G", "🇳🇿"),
    ("Spain",             "ESP", "H", "🇪🇸"),
    ("Cape Verde",        "CPV", "H", "🇨🇻"),
    ("Saudi Arabia",      "KSA", "H", "🇸🇦"),
    ("Uruguay",           "URU", "H", "🇺🇾"),
    ("France",            "FRA", "I", "🇫🇷"),
    ("Senegal",           "SEN", "I", "🇸🇳"),
    ("Iraq",              "IRQ", "I", "🇮🇶"),
    ("Norway",            "NOR", "I", "🇳🇴"),
    ("Argentina",         "ARG", "J", "🇦🇷"),
    ("Algeria",           "ALG", "J", "🇩🇿"),
    ("Austria",           "AUT", "J", "🇦🇹"),
    ("Jordan",            "JOR", "J", "🇯🇴"),
    ("Portugal",          "POR", "K", "🇵🇹"),
    ("DR Congo",          "COD", "K", "🇨🇩"),
    ("Uzbekistan",        "UZB", "K", "🇺🇿"),
    ("Colombia",          "COL", "K", "🇨🇴"),
    ("England",           "ENG", "L", "🏴󠁧󠁢󠁥󠁮󠁧󠁿"),
    ("Croatia",           "CRO", "L", "🇭🇷"),
    ("Ghana",             "GHA", "L", "🇬🇭"),
    ("Panama",            "PAN", "L", "🇵🇦"),
]

# (match_num, home_code, away_code, date_utc, venue, group)
# All times in UTC. EDT = UTC-4, CDT = UTC-5, MDT = UTC-6, PDT = UTC-7
MATCHES = [
    # ── JUNE 11 ──────────────────────────────────────────────────────────────
    (1,  "MEX", "RSA",  "2026-06-11 19:00", "Estadio Azteca, Mexico City",       "A"),
    (2,  "KOR", "CZE",  "2026-06-12 02:00", "Estadio Akron, Zapopan",            "A"),
    # ── JUNE 12 ──────────────────────────────────────────────────────────────
    (3,  "CAN", "BIH",  "2026-06-12 19:00", "BMO Field, Toronto",                "B"),
    (4,  "USA", "PAR",  "2026-06-13 01:00", "SoFi Stadium, Inglewood",           "D"),
    # ── JUNE 13 ──────────────────────────────────────────────────────────────
    (5,  "QAT", "SUI",  "2026-06-13 19:00", "Levi's Stadium, Santa Clara",       "B"),
    (6,  "BRA", "MAR",  "2026-06-13 22:00", "MetLife Stadium, East Rutherford",  "C"),
    (7,  "HAI", "SCO",  "2026-06-14 01:00", "Gillette Stadium, Foxborough",      "C"),
    (8,  "AUS", "TUR",  "2026-06-14 04:00", "BC Place, Vancouver",               "D"),
    # ── JUNE 14 ──────────────────────────────────────────────────────────────
    (9,  "GER", "CUW",  "2026-06-14 17:00", "NRG Stadium, Houston",              "E"),
    (10, "NED", "JPN",  "2026-06-14 20:00", "AT&T Stadium, Arlington",           "F"),
    (11, "CIV", "ECU",  "2026-06-14 23:00", "Lincoln Financial Field, Philadelphia", "E"),
    (12, "SWE", "TUN",  "2026-06-15 02:00", "Estadio BBVA, Monterrey",           "F"),
    # ── JUNE 15 ──────────────────────────────────────────────────────────────
    (13, "ESP", "CPV",  "2026-06-15 17:00", "Mercedes-Benz Stadium, Atlanta",    "H"),
    (14, "BEL", "EGY",  "2026-06-15 22:00", "Lumen Field, Seattle",              "G"),
    (15, "KSA", "URU",  "2026-06-15 22:00", "Hard Rock Stadium, Miami Gardens",  "H"),
    (16, "IRN", "NZL",  "2026-06-16 04:00", "SoFi Stadium, Inglewood",           "G"),
    # ── JUNE 16 ──────────────────────────────────────────────────────────────
    (17, "FRA", "SEN",  "2026-06-16 19:00", "MetLife Stadium, East Rutherford",  "I"),
    (18, "IRQ", "NOR",  "2026-06-16 22:00", "Gillette Stadium, Foxborough",      "I"),
    (19, "ARG", "ALG",  "2026-06-17 01:00", "Arrowhead Stadium, Kansas City",    "J"),
    (20, "AUT", "JOR",  "2026-06-17 04:00", "Levi's Stadium, Santa Clara",       "J"),
    # ── JUNE 17 ──────────────────────────────────────────────────────────────
    (21, "POR", "COD",  "2026-06-17 17:00", "NRG Stadium, Houston",              "K"),
    (22, "ENG", "CRO",  "2026-06-17 20:00", "AT&T Stadium, Arlington",           "L"),
    (23, "GHA", "PAN",  "2026-06-17 23:00", "BMO Field, Toronto",                "L"),
    (24, "UZB", "COL",  "2026-06-18 02:00", "Estadio Azteca, Mexico City",       "K"),
    # ── JUNE 18 ──────────────────────────────────────────────────────────────
    (25, "CZE", "RSA",  "2026-06-18 16:00", "Mercedes-Benz Stadium, Atlanta",    "A"),
    (26, "SUI", "BIH",  "2026-06-18 19:00", "SoFi Stadium, Inglewood",           "B"),
    (27, "CAN", "QAT",  "2026-06-18 22:00", "BC Place, Vancouver",               "B"),
    (28, "MEX", "KOR",  "2026-06-19 03:00", "Estadio Akron, Zapopan",            "A"),
    # ── JUNE 19 ──────────────────────────────────────────────────────────────
    (29, "USA", "AUS",  "2026-06-19 19:00", "Lumen Field, Seattle",              "D"),
    (30, "SCO", "MAR",  "2026-06-19 22:00", "Gillette Stadium, Foxborough",      "C"),
    (31, "BRA", "HAI",  "2026-06-20 01:00", "Lincoln Financial Field, Philadelphia", "C"),
    (32, "TUR", "PAR",  "2026-06-20 04:00", "Levi's Stadium, Santa Clara",       "D"),
    # ── JUNE 20 ──────────────────────────────────────────────────────────────
    (33, "NED", "SWE",  "2026-06-20 17:00", "NRG Stadium, Houston",              "F"),
    (34, "GER", "CIV",  "2026-06-20 20:00", "BMO Field, Toronto",                "E"),
    (35, "ECU", "CUW",  "2026-06-21 00:00", "Arrowhead Stadium, Kansas City",    "E"),
    (36, "TUN", "JPN",  "2026-06-21 04:00", "Estadio BBVA, Monterrey",           "F"),
    # ── JUNE 21 ──────────────────────────────────────────────────────────────
    (37, "ESP", "KSA",  "2026-06-21 16:00", "Mercedes-Benz Stadium, Atlanta",    "H"),
    (38, "BEL", "IRN",  "2026-06-21 19:00", "SoFi Stadium, Inglewood",           "G"),
    (39, "URU", "CPV",  "2026-06-21 22:00", "Hard Rock Stadium, Miami Gardens",  "H"),
    (40, "NZL", "EGY",  "2026-06-22 01:00", "BC Place, Vancouver",               "G"),
    # ── JUNE 22 ──────────────────────────────────────────────────────────────
    (41, "ARG", "AUT",  "2026-06-22 17:00", "AT&T Stadium, Arlington",           "J"),
    (42, "FRA", "IRQ",  "2026-06-22 21:00", "Lincoln Financial Field, Philadelphia", "I"),
    (43, "NOR", "SEN",  "2026-06-23 00:00", "MetLife Stadium, East Rutherford",  "I"),
    (44, "JOR", "ALG",  "2026-06-23 03:00", "Levi's Stadium, Santa Clara",       "J"),
    # ── JUNE 23 ──────────────────────────────────────────────────────────────
    (45, "POR", "UZB",  "2026-06-23 17:00", "NRG Stadium, Houston",              "K"),
    (46, "ENG", "GHA",  "2026-06-23 20:00", "Gillette Stadium, Foxborough",      "L"),
    (47, "PAN", "CRO",  "2026-06-23 23:00", "BMO Field, Toronto",                "L"),
    (48, "COL", "COD",  "2026-06-24 02:00", "Estadio Akron, Zapopan",            "K"),
    # ── JUNE 24 ──────────────────────────────────────────────────────────────
    (49, "SUI", "CAN",  "2026-06-24 19:00", "BC Place, Vancouver",               "B"),
    (50, "BIH", "QAT",  "2026-06-24 19:00", "Lumen Field, Seattle",              "B"),
    (51, "SCO", "BRA",  "2026-06-24 22:00", "Hard Rock Stadium, Miami Gardens",  "C"),
    (52, "MAR", "HAI",  "2026-06-24 22:00", "Mercedes-Benz Stadium, Atlanta",    "C"),
    (53, "CZE", "MEX",  "2026-06-25 01:00", "Estadio Azteca, Mexico City",       "A"),
    (54, "RSA", "KOR",  "2026-06-25 01:00", "Estadio BBVA, Monterrey",           "A"),
    # ── JUNE 25 ──────────────────────────────────────────────────────────────
    (55, "ECU", "GER",  "2026-06-25 20:00", "MetLife Stadium, East Rutherford",  "E"),
    (56, "CUW", "CIV",  "2026-06-25 20:00", "Lincoln Financial Field, Philadelphia", "E"),
    (57, "JPN", "SWE",  "2026-06-25 23:00", "AT&T Stadium, Arlington",           "F"),
    (58, "TUN", "NED",  "2026-06-25 23:00", "Arrowhead Stadium, Kansas City",    "F"),
    (59, "TUR", "USA",  "2026-06-26 02:00", "SoFi Stadium, Inglewood",           "D"),
    (60, "PAR", "AUS",  "2026-06-26 02:00", "Levi's Stadium, Santa Clara",       "D"),
    # ── JUNE 26 ──────────────────────────────────────────────────────────────
    (61, "NOR", "FRA",  "2026-06-26 19:00", "Gillette Stadium, Foxborough",      "I"),
    (62, "SEN", "IRQ",  "2026-06-26 19:00", "BMO Field, Toronto",                "I"),
    (63, "CPV", "KSA",  "2026-06-27 00:00", "NRG Stadium, Houston",              "H"),
    (64, "URU", "ESP",  "2026-06-27 00:00", "Estadio Akron, Zapopan",            "H"),
    (65, "EGY", "IRN",  "2026-06-27 03:00", "Lumen Field, Seattle",              "G"),
    (66, "NZL", "BEL",  "2026-06-27 03:00", "BC Place, Vancouver",               "G"),
    # ── JUNE 27 ──────────────────────────────────────────────────────────────
    (67, "PAN", "ENG",  "2026-06-27 21:00", "MetLife Stadium, East Rutherford",  "L"),
    (68, "CRO", "GHA",  "2026-06-27 21:00", "Lincoln Financial Field, Philadelphia", "L"),
    (69, "COL", "POR",  "2026-06-27 23:30", "Hard Rock Stadium, Miami Gardens",  "K"),
    (70, "COD", "UZB",  "2026-06-27 23:30", "Mercedes-Benz Stadium, Atlanta",    "K"),
    (71, "ALG", "AUT",  "2026-06-28 02:00", "Arrowhead Stadium, Kansas City",    "J"),
    (72, "JOR", "ARG",  "2026-06-28 02:00", "AT&T Stadium, Arlington",           "J"),
]


def seed():
    db = SessionLocal()
    try:
        if db.query(models.Team).count() > 0:
            print("Database already seeded. Skipping.")
            return

        # Insert teams
        team_map = {}
        for name, code, group, flag in TEAMS:
            t = models.Team(name=name, code=code, group_letter=group, flag_emoji=flag)
            db.add(t)
            db.flush()
            team_map[code] = t.id

        # Insert group stage matches
        for num, home_code, away_code, dt_str, venue, group in MATCHES:
            dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
            m = models.Match(
                match_number=num,
                home_team_id=team_map[home_code],
                away_team_id=team_map[away_code],
                group_letter=group,
                round="group",
                match_date=dt,
                venue=venue,
            )
            db.add(m)

        db.commit()
        print(f"Seeded {len(TEAMS)} teams and {len(MATCHES)} group stage matches.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
