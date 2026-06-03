import os
from dotenv import load_dotenv

# load .env next to this file
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

try:
    from gog_data import GOGKB
except ImportError:
    from gog.gog_data import GOGKB

def run_test():
    kb = GOGKB(embedding_model="gemini-embedding-001")
    samples = [
        "test embedding",
        "Pembunuhan berencana",
        "Setiap Orang yang melakukan Tindak Pidana",
    ]
    for s in samples:
        try:
            emb = kb.embed_text(s)
            print(f"OK: '{s[:40]}' -> len={len(emb)} first5={emb[:5]}")
        except Exception as e:
            print(f"FAIL: '{s[:40]}' -> {e}")

if __name__ == "__main__":
    run_test()