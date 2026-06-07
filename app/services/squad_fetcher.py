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
    """Strip [[Link|Display]] → Display, remove templates and leftover brackets."""
    text = re.sub(r'\[\[(?:[^\]|]+\|)?([^\]]+)\]\]', r'\1', text)  # [[Link|Display]] → Display
    text = re.sub(r'\[\[[^\]|]*\|', '', text)   # orphaned [[Link| (pipe cut off)
    text = re.sub(r'\[\[', '', text)             # any remaining [[
    text = re.sub(r'\{\{[^}]*\}\}', '', text)   # {{template}}
    text = re.sub(r"'''?", '', text)
    # Strip Wikipedia disambiguation suffixes: "Rui Silva (footballer, born 1994)" → "Rui Silva"
    text = re.sub(r'\s*\(footballer[^)]*\)', '', text)
    text = re.sub(r'\s*\(born \d{4}\)', '', text)
    return text.strip()


def _parse_dob(template: str) -> str | None:
    """Extract yyyy-mm-dd from birth date templates.
    {{birth date and age2|ref_year|ref_m|ref_d|birth_year|birth_m|birth_d}} — take last plausible year.
    """
    for year, month, day in reversed(re.findall(r'\|(\d{4})\|(\d{1,2})\|(\d{1,2})', template)):
        if 1960 <= int(year) <= 2010:
            return f"{year}-{int(month):02d}-{int(day):02d}"
    return None


def _split_params(inner: str) -> dict[str, str]:
    """Parse 'key=val|key=val' respecting nested {{ }} so | inside them is ignored."""
    params: dict[str, str] = {}
    depth, buf = 0, []
    for ch in inner:
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
        if ch == '|' and depth == 0:
            part = ''.join(buf).strip()
            if '=' in part:
                k, _, v = part.partition('=')
                params[k.strip().lower()] = v.strip()
            buf = []
        else:
            buf.append(ch)
    part = ''.join(buf).strip()
    if '=' in part:
        k, _, v = part.partition('=')
        params[k.strip().lower()] = v.strip()
    return params


def _find_player_templates(text: str) -> list[str]:
    """Return inner text of every {{nat fs g player …}} using bracket counting."""
    results = []
    for m in re.finditer(r'\{\{nat fs g player', text, re.IGNORECASE):
        depth, i = 0, m.start()
        while i < len(text) - 1:
            if text[i:i+2] == '{{':
                depth += 1; i += 2
            elif text[i:i+2] == '}}':
                depth -= 1; i += 2
                if depth == 0:
                    results.append(text[m.start()+2:i-2])
                    break
            else:
                i += 1
    return results


def _parse_players(section_text: str) -> list[dict]:
    players = []
    for inner in _find_player_templates(section_text):
        p = _split_params(inner)
        players.append({
            "squad_number":  int(p['no']) if p.get('no', '').isdigit() else None,
            "position":      (p.get('pos', '') or 'MF').upper()[:3],
            "name":          _clean_wiki(p.get('name', '')),
            "date_of_birth": _parse_dob(p.get('age', '') or p.get('dob', '')),
            "caps":          int(p['caps']) if p.get('caps', '').isdigit() else 0,
            "goals":         int(p['goals']) if p.get('goals', '').isdigit() else 0,
            "club":          _clean_wiki(p.get('club', '')) or None,
            "club_country":  (p.get('clubnat') or '').upper()[:3] or None,
        })
    return players


async def fetch_squads(db: Session) -> dict:
    """Fetch all squad data from Wikipedia and upsert into players table."""
    import models

    headers = {"User-Agent": "WC2026Predictor/1.0 (https://github.com/; fdmamaro24@gmail.com) httpx"}
    async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
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
