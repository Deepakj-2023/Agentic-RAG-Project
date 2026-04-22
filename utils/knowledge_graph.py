# knowledge_graph.py : Precomputed facts for fast lookup and self-correction

import json
import os
import sqlite3
import pandas as pd

KG_PATH = "data/knowledge_graph.json"


def build_knowledge_graph():
    """
    Build a knowledge graph from the datasets.
    This creates verified facts that the agent can use
    to quickly answer common questions and cross-verify tool outputs.
    """
    kg = {
        "meta": {
            "datasets": [
                {
                    "name": "IPL",
                    "type": "cricket",
                    "source": "IPL.csv → ipl_matches (SQLite)",
                    "description": "Ball-by-ball IPL data aggregated into match summaries",
                    "columns": ["match_id", "season", "date", "venue", "winner", "player_of_match"],
                    "seasons_available": []
                },
                {
                    "name": "PSL",
                    "type": "cricket",
                    "source": "PSL datasets → multiple SQLite tables",
                    "description": "Pakistan Super League batting, bowling, team, and timeline records",
                    "tables": [
                        "psl_team_results", "psl_batting", "psl_bowling",
                        "psl_highest_scores", "psl_most_sixes", "psl_sixes_innings",
                        "psl_best_bowling", "psl_match_wins"
                    ]
                },
                {
                    "name": "FIFA",
                    "type": "football",
                    "source": "player_stats.csv → fifa_players (SQLite)",
                    "description": "FIFA player attributes and ratings",
                    "columns": ["player", "country", "club", "age", "dribbling", "finishing", "sprint_speed", "..."]
                }
            ]
        },
        "facts": {},
        "records": {}
    }

    # === Build facts from IPL data ===
    db_path = "data/sports_data.db"
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)

        # Get available seasons
        try:
            seasons = conn.execute("SELECT DISTINCT season FROM ipl_matches ORDER BY season").fetchall()
            kg["meta"]["datasets"][0]["seasons_available"] = [s[0] for s in seasons]
        except:
            pass

        # IPL Season Winners (the team that won the LAST match of each season = final winner)
        try:
            rows = conn.execute("""
                SELECT season, winner, player_of_match, date FROM ipl_matches
                WHERE (season, date) IN (
                    SELECT season, MAX(date) FROM ipl_matches GROUP BY season
                )
            """).fetchall()
            for season, winner, pom, date in rows:
                kg["facts"][f"IPL {season} champion"] = {
                    "answer": winner,
                    "player_of_match": pom,
                    "final_date": date,
                    "source": "ipl_matches (last match of season)"
                }
        except Exception as e:
            print(f"Warning building IPL facts: {e}")

        # IPL Top run scorers per season (most wins)
        try:
            rows = conn.execute("""
                SELECT season, winner, COUNT(*) as wins
                FROM ipl_matches
                GROUP BY season, winner
                ORDER BY season, wins DESC
            """).fetchall()
            season_data = {}
            for season, winner, wins in rows:
                if season not in season_data:
                    season_data[season] = []
                season_data[season].append({"team": winner, "wins": wins})
            for season, teams in season_data.items():
                kg["facts"][f"IPL {season} most match wins"] = {
                    "answer": teams[0]["team"],
                    "all_teams": teams[:5],
                    "source": "ipl_matches"
                }
        except Exception as e:
            print(f"Warning building IPL standings: {e}")

        # PSL Facts
        try:
            rows = conn.execute("SELECT Team, Won, Lost FROM psl_team_results ORDER BY Won DESC").fetchall()
            kg["facts"]["PSL all-time most wins"] = {
                "answer": rows[0][0] if rows else "Unknown",
                "top_teams": [{"team": r[0], "won": r[1], "lost": r[2]} for r in rows],
                "source": "psl_team_results"
            }
        except:
            pass

        # PSL top batters
        try:
            rows = conn.execute("SELECT Player, Runs FROM psl_batting ORDER BY Runs DESC LIMIT 5").fetchall()
            kg["records"]["PSL all-time top run scorers"] = [
                {"player": r[0], "runs": r[1]} for r in rows
            ]
        except:
            pass

        # PSL top bowlers
        try:
            rows = conn.execute("SELECT Player, Wkts FROM psl_bowling ORDER BY Wkts DESC LIMIT 5").fetchall()
            kg["records"]["PSL all-time top wicket takers"] = [
                {"player": r[0], "wickets": r[1]} for r in rows
            ]
        except:
            pass

        # FIFA top players
        try:
            rows = conn.execute("""
                SELECT player, country, club, dribbling, finishing, sprint_speed
                FROM fifa_players ORDER BY dribbling DESC LIMIT 5
            """).fetchall()
            kg["records"]["FIFA top dribblers"] = [
                {"player": r[0], "country": r[1], "club": r[2], "dribbling": r[3]} for r in rows
            ]
        except:
            pass

        conn.close()

    # Save
    with open(KG_PATH, "w", encoding="utf-8") as f:
        json.dump(kg, f, indent=2, ensure_ascii=False)
    print(f"Knowledge Graph built: {len(kg['facts'])} facts, {len(kg['records'])} record sets.")
    return kg


def load_knowledge_graph():
    """Load the knowledge graph from disk."""
    if os.path.exists(KG_PATH):
        with open(KG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"meta": {}, "facts": {}, "records": {}}


def lookup_fact(kg: dict, question: str) -> dict | None:
    """
    Try to find a precomputed fact that matches the question.
    Returns the fact dict if found, None otherwise.
    """
    question_lower = question.lower()

    for fact_key, fact_value in kg.get("facts", {}).items():
        # Simple keyword matching
        key_words = fact_key.lower().split()
        if all(w in question_lower for w in key_words if len(w) > 2):
            return {"matched_fact": fact_key, **fact_value}

    return None
