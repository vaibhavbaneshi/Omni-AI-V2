from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "sample.txt"

def load_document(file_path):
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"{file_path} not found")

    text = path.read_text(encoding="utf-8")

    return text


if __name__ == "__main__":
    document = load_document(DATA_PATH)

    print(document[:500])