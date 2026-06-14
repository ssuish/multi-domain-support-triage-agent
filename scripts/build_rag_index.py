from pathlib import Path

from agent_triager.rag.index import build_index


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    n_files, n_chunks = build_index(repo_root)
    print(f"Indexed markdown files={n_files}, chunks_in_chroma={n_chunks}")


if __name__ == "__main__":
    main()
