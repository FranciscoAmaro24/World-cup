"""
Fetches 2026 FIFA World Cup squad data from Wikipedia and stores it in the DB.
Source: https://en.wikipedia.org/wiki/2026_FIFA_World_Cup_squads
"""
import re
import logging
import httpx
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

WIKI_URL = (
    "https://en.wikipedia.org/w/api.php"
    "?action=query&titles=2026_FIFA_World_Cup_squads"
    "&prop=revisions&rvprop=content&format=json&rvslots=main"
)

# Wikipedia country name → our DB team code
WIKI_NAME_TO_CODE = {
    "argentina": "ARG", "australia": "AUS", "austria": "AUT",
    "algeria": "ALG", "belgium": "BEL", "bosnia and herzegovina": "BIH",
    "brazil": "BRA", "canada": "CAN", "cape verde": "CPV",
    "colombia": "COL", "croatia": "CRO", "curaçao": "CUW", "curacao": "CUW",
    "czech republic": "CZE", "czechia": "CZE",
    "dr congo": "COD", "democratic republic of the congo": "COD",
    "ecuador": "ECU", "egypt": "EGY", "england": "ENG",
    "france": "FRA", "germany": "GER", "ghana": "GHA",
    "haiti": "HAI", "iran": "IRN", "iraq": "IRQ",
    "ivory coast": "CIV", "côte d'ivoire": "CIV", "cote d'ivoire": "CIV",
    "japan": "JPN", "jordan": "JOR", "mexico": "MEX",
    "morocco": "MAR", "netherlands": "NED", "new zealand": "NZL",
    "norway": "NOR", "panama": "PAN", "paraguay": "PAR",
    "portugal": "POR", "qatar": "QAT", "saudi arabia": "KSA",
    "scotland": "SCO", "senegal": "SEN", "south africa": "RSA",
    "south korea": "KOR", "spain": "ESP", "sweden": "SWE",
    "switzerland": "SUI", "tunisia": "TUN", "turkey": "TUR",
    "türkiye": "TUR", "united states": "USA", "usa": "USA",
    "uruguay": "URU", "uzbekistan": "UZB",
}


def _clean_wiki(text: str) -> str:
    """Strip [[Link|Display]] → Display, remove templates, extra brackets."""
    text = re.sub(r'\[\[(?:[^\]|]+\|)?([^\]]+)\]\]', r'\1', text)
    text = re.sub(r'\{\{[^}]+\}\}', '', text)
    text = re.sub(r"'''?", '', text)
    return text.strip()


def _parse_dob(template: str) -> str | None:
    """Extract yyyy-mm-dd from birth_date_and_age or birth date templates."""
    m = re.search(r'\|(\d{4})\|(\d{1,2})\|(\d{1,2})', template)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    return None


def _parse_players(section_text: str) -> list[dict]:
    players = []
    pattern = re.compile(
        r'\{\{nat fs g player'
        r'(?:\|no=(\d+))?'
        r'\|pos=(\w+)'
        r'\|name=([^\|]+)'
        r'(?:\|sortname=[^\|]+)?'
        r'(?:\|age=([^\|]+))?'
        r'(?:\|caps=(\d+))?'
        r'(?:\|goals=(\d+))?'
        r'(?:\|club=([^\|]+))?'
        r'(?:\|clubnat=([A-Z]+))?',
        re.IGNORECASE,
    )
    for m in pattern.finditer(section_text):
        number_str, pos, name_raw, age_raw, caps_str, goals_str, club_raw, club_nat = (
            m.group(1), m.group(2), m.group(3), m.group(4),
            m.group(5), m.group(6), m.group(7), m.group(8),
        )
        players.append({
            "squad_number": int(number_str) if number_str else None,
            "position":     pos.upper()[:3],
            "name":         _clean_wiki(name_raw or ""),
            "date_of_birth": _parse_dob(age_raw or ""),
            "caps":         int(caps_str) if caps_str else 0,
            "goals":        int(goals_str) if goals_str else 0,
            "club":         _clean_wiki(club_raw or "") or None,
            "club_country": club_nat or None,
        })
    return players


async def fetch_squads(db: Session) -> dict:
    """Fetch all squad data from Wikipedia and upsert into players table."""
    import models

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(WIKI_URL)
        resp.raise_for_status()
        data = resp.json()

    content = list(data["query"]["pages"].values())[0]["revisions"][0]["slots"]["main"]["*"]

    # Build team lookup: code → Team object
    teams_by_code = {t.code: t for t in db.query(models.Team).all()}

    # Teams are under ===Country=== (level-3) headers inside group sections
    sections = re.split(r'^===([^=\n]+)===\s*$', content, flags=re.MULTILINE)

    inserted = updated = skipped = 0

    for i in range(1, len(sections) - 1, 2):
        section_name = sections[i].strip()
        section_body = sections[i + 1] if i + 1 < len(sections) else ""

        code = WIKI_NAME_TO_CODE.get(section_name.lower())
        if not code or code not in teams_by_code:
            continue

        team = teams_by_code[code]
        players = _parse_players(section_body)
        if not players:
            skipped += 1
            continue

        # Delete existing squad for this team and re-insert
        db.query(models.Player).filter(models.Player.team_id == team.id).delete()
        for p in players:
            db.add(models.Player(team_id=team.id, **p))
        inserted += len(players)

    db.commit()
    logger.info(f"Squads fetched: {inserted} players inserted, {skipped} teams skipped")
    return {"players": inserted, "skipped": skipped}
