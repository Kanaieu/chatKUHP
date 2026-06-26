import os
from dotenv import load_dotenv
from gog_data import GOGKB

# Load environment variables (API Key)
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

def main():
    print("Initializing GOGKB and starting build process...")
    # Change paths as necessary based on your working directory
    
    # Check if the saved KB exists, and load it
    kb_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "gog_graph"))
    kb_path = os.path.join(kb_dir, "kb_kuhp.pkl")
    
    if os.path.exists(kb_path):
        print(f"Loading existing KB from {kb_path}...")
        kb = GOGKB.load_kb(kb_path)
        kb.kb_dir = kb_dir
        kb.kb_file = kb_path
    else:
        print("Saved KB not found. Creating a new one...")
        kb = GOGKB(embedding_model="embed-multilingual-v3.0")
        kb.kb_dir = kb_dir
        kb.kb_file = kb_path
    
    kb.doc_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "knowledge"))
    print("Using knowledge directory:", kb.doc_dir)

    # Only build if the KB is empty
    if len(kb.nodes) == 0:
        # kb.build_kb()
        kb.build_kb_sync()
    
    print(f"Successfully loaded Knowledge Base!")
    print(f"Total Nodes: {len(kb.nodes)}")
    print(f"Total Edges: {len(kb.edges)}")

    print("Graph build complete.")
    
if __name__ == "__main__":
    main()