import os
import pandas as pd
import sqlite3
import glob
import json
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
# -----------------------------
# PATH CONFIG
# -----------------------------
BASE_PATH = r"D:\AgenticRAG\Proadapt-Project\data"

IPL_PATH = rf"{BASE_PATH}\structure_data\IPL.csv"
FIFA_PATH = rf"{BASE_PATH}\structure_data\player_stats.csv"

PSL_BASE = rf"{BASE_PATH}\structure_data\Pakistan Super League Datasets"

DB_PATH = rf"{BASE_PATH}\sports_data.db"
UNSTRUCTURED_DIR = rf"{BASE_PATH}\unstructured\*.txt"

SCHEMA_PATH = rf"{BASE_PATH}\schema_registry.json"

# -----------------------------
# GLOBAL SCHEMA REGISTRY
# -----------------------------
SCHEMA_REGISTRY = {}


# -----------------------------
# 🟢 PANDAS SETUP (IPL + FIFA)
# -----------------------------
def setup_pandas():
    print("=" * 50)
    print("STEP 1: Register Pandas Datasets")
    print("=" * 50)

    pandas_files = {
        "ipl": IPL_PATH,
        "fifa": FIFA_PATH
    }

    for name, path in pandas_files.items():
        if not os.path.exists(path):
            print(f"[PANDAS] Missing: {path}")
            continue

        df = pd.read_csv(path, nrows=50, low_memory=False,encoding="latin1")

        SCHEMA_REGISTRY[name] = {
            "type": "pandas",
            "path": path,
            "columns": {col: str(dtype) for col, dtype in df.dtypes.items()},
            "sample": df.head(3).to_dict(orient="records")
        }

        print(f"[PANDAS] Registered '{name}' with {len(df.columns)} columns.")


# -----------------------------
# 🔵 SQL SETUP (PSL DATA)
# -----------------------------
def clean_table_name(file_path):
    name = os.path.basename(file_path).replace(".csv", "")
    return "psl_" + name.lower().replace(" ", "_").replace("-", "_")


def setup_sqlite():
    print("\n" + "=" * 50)
    print("STEP 2: Building PSL SQLite DB")
    print("=" * 50)

    conn = sqlite3.connect(DB_PATH)

    psl_files = [
        # Batting
        rf"{PSL_BASE}\Batting records\Highest individual score.csv",
        rf"{PSL_BASE}\Batting records\Most runs by a player.csv",
        rf"{PSL_BASE}\Batting records\Most sixes in an innings.csv",
        rf"{PSL_BASE}\Batting records\Most sixes in PSL history.csv",

        # Bowling
        rf"{PSL_BASE}\Bowling records\Best bowling figures in an innings in PSL.csv",
        rf"{PSL_BASE}\Bowling records\Most wickets in PSL.csv",

        # Fielding
        rf"{PSL_BASE}\Fielding records\Most catches in PSL.csv",
        rf"{PSL_BASE}\Fielding records\Most dismissals by a Wicket-keeper in PSL.csv",

        # Team
        rf"{PSL_BASE}\Team records\Highest totals.csv",
        rf"{PSL_BASE}\Team records\Lowest totals.csv",
        rf"{PSL_BASE}\Team records\Result summary of teams.csv",

        # Timeline
        rf"{PSL_BASE}\Timeline data\Most match wins in PSL.csv",
    ]

    sql_schema = {"type": "sql", "tables": {}}

    for file_path in psl_files:
        if not os.path.exists(file_path):
            print(f"[PSL] Missing: {file_path}")
            continue

        try:
            df = pd.read_csv(file_path, low_memory=False,encoding="latin1")
            table_name = clean_table_name(file_path)

            df.to_sql(table_name, conn, if_exists="replace", index=False)

            # Save schema
            sql_schema["tables"][table_name] = {
                "columns": {col: str(dtype) for col, dtype in df.dtypes.items()}
            }

            print(f"[PSL] Loaded '{table_name}' ({len(df)} rows).")

        except Exception as e:
            print(f"[PSL] Error: {file_path} → {e}")

    conn.close()

    SCHEMA_REGISTRY["psl_db"] = sql_schema

    print(f"\n[SQL] Database ready at {DB_PATH}")


# -----------------------------
# 🟡 VECTOR STORE SETUP
# -----------------------------
def setup_vector_store():
    print("\n" + "=" * 50)
    print("STEP 3: Vector Store Setup")
    print("=" * 50)

    from utils.vector_store import vector_store_instance

    files = glob.glob(UNSTRUCTURED_DIR)

    if not files:
        print("[VECTOR] No files found.")
        return

    docs = []

    for file in files:
        try:
            with open(file, "r", encoding="utf-8") as f:
                content = f.read()

                chunks = content.split("\n\n")

                for chunk in chunks:
                    if len(chunk.strip()) > 50:
                        docs.append({
                            "text": chunk.strip(),
                            "source": os.path.basename(file)
                        })

        except Exception as e:
            print(f"[VECTOR] Error: {file} → {e}")

    if docs:
        vector_store_instance.add_documents(docs)
        print(f"[VECTOR] Indexed {len(docs)} chunks.")
    else:
        print("[VECTOR] No valid content.")


# -----------------------------
# 🧠 SAVE SCHEMA
# -----------------------------
def save_schema():
    with open(SCHEMA_PATH, "w") as f:
        json.dump(SCHEMA_REGISTRY, f, indent=2)

    print(f"\n[SCHEMA] Saved to {SCHEMA_PATH}")


# -----------------------------
# MAIN
# -----------------------------
if __name__ == "__main__":
    setup_pandas()      # IPL + FIFA (Pandas only)
    setup_sqlite()      # PSL → SQL
    setup_vector_store()  # Unstructured
    save_schema()       # Save schema registry

    print("\n[OK] Setup Complete!")