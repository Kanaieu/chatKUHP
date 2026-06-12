import os
import json
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

    # Quick DFS Test
    test_query = "Baru-baru ini saudara saya (X) melakukan penggelapan uang di kantornya. Di sisi lain, saya pernah meminta bantuan uang ke si X dan saya tidak tahu bahwa ternyata uang yang diberikan kepada saya tersebut termasuk dari uang penggelapan yang dilakukannya. Kemudian oleh pihak kantor tempat si X bekerja saya diancam akan ikut dilaporkan ke polisi. Bagaimana posisi saya di mata hukum? Mohon penjelasannya."
    
    # 1. Cari pasal yang paling relevan dengan query menggunakan embedding
    print(f"\nSearching for most relevant goal for query: '{test_query}'...")
    relevant_goals, _ = kb.query_goals(test_query, top_k=3)
    
    if relevant_goals:
        print("Top 3 Candidates:")
        for idx, g in enumerate(relevant_goals):
            print(f"  {idx+1}. {g.name}")
            
        # Pilih kandidat pertama untuk dites DFS-nya
        target_goal = relevant_goals[0].name
        print(f"\nTesting DFS tree generation for top candidate: {target_goal}")
        trees = kb.dfs(target_goal)
        print(f"Generated {len(trees)} alternative reasoning paths.")
        
        if trees:
            print("\n--- DFS Tree Contents (Path 1) ---")
            print(json.dumps(trees[0], indent=4))
    else:
        print("No relevant goals found.")
    
if __name__ == "__main__":
    main()