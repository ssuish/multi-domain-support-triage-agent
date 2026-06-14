from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INPUT_CSV = REPO_ROOT / "support_tickets" / "support_tickets.csv"
OUTPUT_CSV = REPO_ROOT / "support_tickets" / "output.csv"
RUNS_DIR = REPO_ROOT / "runs"
ENV_FILE = REPO_ROOT / ".env"
