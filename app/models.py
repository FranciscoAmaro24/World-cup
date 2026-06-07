from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


AVATAR_COLORS = [
    "#1a47c0", "#7c3aed", "#dc2626", "#ea580c",
    "#0d9488", "#db2777", "#16a34a", "#d97706",
]
AVATAR_ICONS = ["⚽", "🏆", "⭐", "⚡", "🦁", "🦅", "🔥", "👑", "🎯", "🏅", "🐉", "🌟"]


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(200), nullable=False)
    is_superadmin = Column(Boolean, default=False)
    display_name = Column(String(50), nullable=True)
    bio = Column(String(120), nullable=True)
    credits = Column(Float, default=10.0)
    avatar_color = Column(String(10), default="#1a47c0")
    avatar_icon = Column(String(6), default="⚽")
    avatar_img_url = Column(String(200), nullable=True)
    profile_bg = Column(String(100), nullable=True)     # CSS gradient/color for whole-app background
    profile_banner_url = Column(String(200), nullable=True)  # banner image on profile page
    favorite_team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    memberships = relationship("LeagueMember", back_populates="user", cascade="all, delete-orphan")
    predictions = relationship("Prediction", back_populates="user", cascade="all, delete-orphan")
    sweepstake_assignments = relationship("SweepstakeAssignment", back_populates="user")
    tournament_picks = relationship("TournamentPick", back_populates="user", cascade="all, delete-orphan")
    favorite_team = relationship("Team", foreign_keys=[favorite_team_id])


class League(Base):
    __tablename__ = "leagues"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    invite_code = Column(String(8), unique=True, nullable=False, index=True)
    admin_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    description = Column(String(200), nullable=True)
    accent_color = Column(String(10), default="#1a47c0")
    badge_emoji = Column(String(6), default="🏆")
    banner_url = Column(String(200), nullable=True)

    # Match score prediction points
    points_exact_score = Column(Integer, default=3)
    points_correct_result = Column(Integer, default=1)

    # Bracket / tournament picks points
    points_bracket_winner = Column(Integer, default=10)
    points_bracket_finalist = Column(Integer, default=5)
    points_bracket_semi = Column(Integer, default=2)
    points_bracket_quarter = Column(Integer, default=1)

    # Sweepstake settings
    logo_url = Column(String(200), nullable=True)
    is_public = Column(Boolean, default=False)             # joinable without invite code
    category = Column(String(20), default="general")       # general / country / global
    sweepstake_enabled = Column(Boolean, default=False)
    sweepstake_buy_in = Column(Float, default=10.0)
    sweepstake_teams_per_person = Column(Integer, default=1)
    sweepstake_drawn = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    admin = relationship("User", foreign_keys=[admin_id])
    members = relationship("LeagueMember", back_populates="league", cascade="all, delete-orphan")
    predictions = relationship("Prediction", back_populates="league", cascade="all, delete-orphan")
    sweepstake_assignments = relationship("SweepstakeAssignment", back_populates="league", cascade="all, delete-orphan")
    tournament_picks = relationship("TournamentPick", back_populates="league", cascade="all, delete-orphan")


class LeagueMember(Base):
    __tablename__ = "league_members"
    id = Column(Integer, primary_key=True, index=True)
    league_id = Column(Integer, ForeignKey("leagues.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    nickname = Column(String(50), nullable=True)       # custom name shown on this league's leaderboard
    sweepstake_paid = Column(Boolean, default=False)
    joined_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("league_id", "user_id"),)

    league = relationship("League", back_populates="members")
    user = relationship("User", back_populates="memberships")


class Team(Base):
    __tablename__ = "teams"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    code = Column(String(3), nullable=False)
    group_letter = Column(String(1), nullable=False)
    flag_emoji = Column(String(10), nullable=False)
    eliminated = Column(Boolean, default=False)
    stage_reached = Column(String(20), default="group")  # group/r32/r16/qf/sf/final/winner

    home_matches = relationship("Match", foreign_keys="Match.home_team_id", back_populates="home_team")
    away_matches = relationship("Match", foreign_keys="Match.away_team_id", back_populates="away_team")
    sweepstake_assignments = relationship("SweepstakeAssignment", back_populates="team")
    players = relationship("Player", back_populates="team", order_by="Player.squad_number")


class Match(Base):
    __tablename__ = "matches"
    id = Column(Integer, primary_key=True, index=True)
    match_number = Column(Integer, nullable=False, unique=True)
    home_team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    away_team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    home_team_tbd = Column(String(50), nullable=True)
    away_team_tbd = Column(String(50), nullable=True)
    group_letter = Column(String(1), nullable=True)
    round = Column(String(20), nullable=False)  # group/r32/r16/qf/sf/third/final
    match_date = Column(DateTime, nullable=False)
    venue = Column(String(100), nullable=False)
    home_score = Column(Integer, nullable=True)   # score after 90 min
    away_score = Column(Integer, nullable=True)
    winner_team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)  # who advanced (for ET/pens)
    status = Column(String(20), default="scheduled")  # scheduled/live/finished

    home_team = relationship("Team", foreign_keys=[home_team_id], back_populates="home_matches")
    away_team = relationship("Team", foreign_keys=[away_team_id], back_populates="away_matches")
    winner_team = relationship("Team", foreign_keys=[winner_team_id])
    predictions = relationship("Prediction", back_populates="match", cascade="all, delete-orphan")
    goals = relationship("Goal", back_populates="match", cascade="all, delete-orphan", order_by="Goal.minute")

    def home_display(self):
        if self.home_team:
            return f"{self.home_team.flag_emoji} {self.home_team.name}"
        return self.home_team_tbd or "TBD"

    def away_display(self):
        if self.away_team:
            return f"{self.away_team.flag_emoji} {self.away_team.name}"
        return self.away_team_tbd or "TBD"

    def is_locked(self):
        return datetime.utcnow() >= self.match_date

    def is_knockout(self):
        return self.round != "group"


class Prediction(Base):
    __tablename__ = "predictions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False)
    league_id = Column(Integer, ForeignKey("leagues.id"), nullable=False)
    home_score_pred = Column(Integer, nullable=False)
    away_score_pred = Column(Integer, nullable=False)
    points_awarded = Column(Integer, nullable=True)
    submitted_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("user_id", "match_id", "league_id"),)

    user = relationship("User", back_populates="predictions")
    match = relationship("Match", back_populates="predictions")
    league = relationship("League", back_populates="predictions")


class TournamentPick(Base):
    """Pre-tournament bracket picks: who wins each round."""
    __tablename__ = "tournament_picks"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    league_id = Column(Integer, ForeignKey("leagues.id"), nullable=False)

    # QF: 4 teams that reach the semis (8 QF slots but we pick top 4 survivors)
    quarter_1_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    quarter_2_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    quarter_3_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    quarter_4_id = Column(Integer, ForeignKey("teams.id"), nullable=True)

    semi_1_id = Column(Integer, ForeignKey("teams.id"), nullable=True)      # SF: reaches final (not winner) 1
    semi_2_id = Column(Integer, ForeignKey("teams.id"), nullable=True)      # SF: reaches final (not winner) 2
    finalist_1_id = Column(Integer, ForeignKey("teams.id"), nullable=True)  # reaches final (not winner)
    winner_id = Column(Integer, ForeignKey("teams.id"), nullable=True)      # lifts the trophy

    points_awarded = Column(Integer, default=0)
    submitted_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("user_id", "league_id"),)

    user = relationship("User", back_populates="tournament_picks")
    league = relationship("League", back_populates="tournament_picks")
    quarter_1 = relationship("Team", foreign_keys=[quarter_1_id])
    quarter_2 = relationship("Team", foreign_keys=[quarter_2_id])
    quarter_3 = relationship("Team", foreign_keys=[quarter_3_id])
    quarter_4 = relationship("Team", foreign_keys=[quarter_4_id])
    semi_1 = relationship("Team", foreign_keys=[semi_1_id])
    semi_2 = relationship("Team", foreign_keys=[semi_2_id])
    finalist_1 = relationship("Team", foreign_keys=[finalist_1_id])
    winner = relationship("Team", foreign_keys=[winner_id])


class Goal(Base):
    __tablename__ = "goals"
    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    player_name = Column(String(100), nullable=False)
    minute = Column(Integer, nullable=True)
    is_own_goal = Column(Boolean, default=False)
    is_penalty = Column(Boolean, default=False)

    match = relationship("Match", back_populates="goals")
    team = relationship("Team")


class SweepstakeAssignment(Base):
    __tablename__ = "sweepstake_assignments"
    id = Column(Integer, primary_key=True, index=True)
    league_id = Column(Integer, ForeignKey("leagues.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)

    league = relationship("League", back_populates="sweepstake_assignments")
    user = relationship("User", back_populates="sweepstake_assignments")
    team = relationship("Team", back_populates="sweepstake_assignments")


# ── SQUAD / PLAYERS ──────────────────────────────────────────

class Player(Base):
    __tablename__ = "players"
    id            = Column(Integer, primary_key=True, index=True)
    team_id       = Column(Integer, ForeignKey("teams.id"), nullable=False)
    squad_number  = Column(Integer, nullable=True)
    position      = Column(String(3), nullable=False)   # GK / DF / MF / FW
    name          = Column(String(120), nullable=False)
    date_of_birth = Column(String(20),  nullable=True)
    caps          = Column(Integer, default=0)
    goals         = Column(Integer, default=0)
    club          = Column(String(120), nullable=True)
    club_country  = Column(String(3),   nullable=True)

    team = relationship("Team", back_populates="players")


# ── PREDICTION MARKET ────────────────────────────────────────

class MarketOption(Base):
    __tablename__ = "market_options"
    id = Column(Integer, primary_key=True, index=True)
    market_id = Column(Integer, ForeignKey("markets.id"), nullable=False)
    label = Column(String(100), nullable=False)
    total_credits = Column(Float, default=0.0)

    market = relationship("Market", back_populates="options")


class Market(Base):
    __tablename__ = "markets"
    id = Column(Integer, primary_key=True, index=True)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(String(500), nullable=True)
    img_url = Column(String(200), nullable=True)
    closes_at = Column(DateTime, nullable=False)
    resolved = Column(Boolean, default=False)
    winning_option_id = Column(Integer, nullable=True)  # plain int to avoid circular FK
    created_at = Column(DateTime, default=datetime.utcnow)

    creator = relationship("User")
    options = relationship(
        "MarketOption", back_populates="market",
        cascade="all, delete-orphan",
        primaryjoin="Market.id == MarketOption.market_id",
        order_by="MarketOption.id",
    )
    bets = relationship("Bet", back_populates="market", cascade="all, delete-orphan")

    def total_volume(self) -> float:
        return round(sum(o.total_credits for o in self.options), 2)

    def option_prob(self, option) -> float:
        total = self.total_volume()
        if total == 0:
            n = len(self.options)
            return round(100.0 / n, 1) if n else 50.0
        return round(option.total_credits / total * 100, 1)

    def is_open(self) -> bool:
        return not self.resolved and datetime.utcnow() < self.closes_at


class Bet(Base):
    __tablename__ = "bets"
    id = Column(Integer, primary_key=True, index=True)
    market_id = Column(Integer, ForeignKey("markets.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    option_id = Column(Integer, ForeignKey("market_options.id"), nullable=False)
    amount = Column(Float, nullable=False)
    payout = Column(Float, nullable=True)
    placed_at = Column(DateTime, default=datetime.utcnow)

    market = relationship("Market", back_populates="bets")
    option = relationship("MarketOption")
    user = relationship("User")
