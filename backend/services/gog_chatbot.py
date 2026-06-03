import base64
from typing import List
import json
import os
import sys
import time
import traceback
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from google import genai
from google.genai import types

try:
    from services.gog_data import GOGKB
except ImportError:
    from services.gog_data import GOGKB

try:
    from services.schemas import GoalInferenceSchema
except ImportError:
    from services.schemas import GoalInferenceSchema

try:
    from services.gog_prompts import PROMPTS
except ImportError:
    from services.gog_prompts import PROMPTS


def _encode_image(image_path: str) -> str:
    if not image_path or not os.path.exists(image_path):
        return ""
    with open(image_path, "rb") as image_file:
        a = base64.b64encode(image_file.read()).decode("utf-8")
    return a

class PlanningModel:
    def __init__(self, llm_model="gemini-2.5-flash", top_k=3, kb_file="gog_graph/kb_kuhp.pkl") -> None:
        self.llm_model = llm_model
        self.temperature = 0.0
        self.top_k = top_k
        
        # Initialize Gemini Client
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found in .env")
        self.client = genai.Client(api_key=api_key)

        # Resolve KB path relative to this services folder
        if not os.path.isabs(kb_file):
            kb_file = os.path.join(os.path.dirname(__file__), kb_file)

        if not os.path.exists(kb_file):
            raise FileNotFoundError(f"KB file not found: {kb_file}")

        # Initialize Knowledge Base
        print(f"[CHATBOT] Loading Knowledge Base dari '{kb_file}'...", flush=True)
        sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        self.goal_kb = GOGKB.load_kb(kb_file=kb_file)
        self.goal_kb.set_llm(url="", port="", llm=llm_model)
        
        self.goal_kb.set_embedding(embedding_model="gemini-embedding-001")
        print(f"[CHATBOT] Knowledge Base berhasil diload.", flush=True)
        
    def _call_llm_with_retry(self, prompt, config, max_retries=5):
        """Helper untuk melakukan retry jika terkena limit 429 API Gemini."""
        delay = 15  # UBAH DARI 2 MENJADI 15 DETIK
        for attempt in range(max_retries):
            try:
                print(f"[LLM] Memanggil API Gemini (Attempt {attempt + 1}/{max_retries})...", flush=True)
                response = self.client.models.generate_content(
                    model=self.llm_model,
                    contents=prompt,
                    config=config
                )
                print(f"[LLM] Berhasil memanggil API Gemini.", flush=True)
                return response
            except Exception as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e).upper():
                    print(f"[LLM WARNING] Rate limit 429 tercapai. Menunggu {delay} detik agar kuota per menit ter-reset...", flush=True)
                    if attempt < max_retries - 1:
                        time.sleep(delay)
                        delay = min(delay + 5, 30)
                        continue
                print(f"[LLM ERROR] Gagal memanggil API: {e}", flush=True)
                raise e

    def retrieve(
        self,
        task: str,
        image_path: str = None,
    ):
        """
        Phase 1: Identify which KUHP Article (Pasal) applies to the user's case.
        """
        print(f"[PHASE 1] Memulai retrieve subgoals...", flush=True)
        relevant_goals, _ = self.goal_kb.query_goals(task, top_k=self.top_k)
        print(f"[PHASE 1] Ditemukan {len(relevant_goals)} kandidat goals.", flush=True)

        context_info = ""
        for idx, goal in enumerate(relevant_goals):
            obj = {
                "nama_pasal": goal.name,
                "bunyi_pasal": goal.desc,
                "prasyarat": goal.preconditions[0] if goal.preconditions else {},
                "unsur_tindak_pidana": goal.elements[0] if goal.elements else {},
                "sanksi_akibat_hukum": goal.postconditions[0] if goal.postconditions else {}
            }
            context_info += f"Option {idx+1}:\n"
            context_info += f"{json.dumps(obj, indent=4)}\n\n"

        prompt_text = PROMPTS["goal_inference"].format(context=context_info, task=task)
        valid_names = [g.name for g in relevant_goals]

        while True:
            try:
                # Menggunakan helper retry
                print(f"[PHASE 1] Melakukan inferensi goal yang paling cocok...", flush=True)
                response = self._call_llm_with_retry(
                    prompt=prompt_text,
                    config=types.GenerateContentConfig(
                        temperature=self.temperature,
                        response_mime_type="application/json",
                        response_schema=GoalInferenceSchema,
                    )
                )
                
                resp_text = response.text.strip()
                if resp_text.startswith("```json"):
                    resp_text = resp_text[7:-3].strip()

                inference = json.loads(resp_text)
                
                if inference.get("goal inference") in valid_names:
                    print(f"[PHASE 1] Goal terpilih: {inference['goal inference']}", flush=True)
                    return inference["goal inference"], valid_names
                else:
                    print(f"[PHASE 1 WARNING] Goal '{inference.get('goal inference')}' tidak valid. Mengulang...", flush=True)

            except Exception as e:
                print(f"[PHASE 1 ERROR] Gagal memparsing JSON hasil inferensi: {e}", flush=True)
                continue

    def planning(
        self,
        task: str,
        image_path: str = None,
        example: str | None = None,
        visual_info: str | None = None,
        goal_name: str | None = None,
    ):
        """
        Phase 2: Question Answering based on the DFS Legal Context.
        """
        print(f"\n[PHASE 2] Memulai planning & penyusunan jawaban...", flush=True)
        goal_choices = []
        if not goal_name:
            goal_name, goal_choices = self.retrieve(task, image_path)

        # 1. Expand the selected Pasal using the DFS backward chaining
        print(f"[PHASE 2] Melakukan evaluasi DFS untuk goal '{goal_name}'...", flush=True)
        all_subgoals_trees = self.goal_kb.dfs(goal_name)
        
        # Take the first alternative tree generated by DFS
        selected_hierarchy = all_subgoals_trees[0] if all_subgoals_trees else {}

        # Extract all used postconditions
        used_preconditions = set()
        for node_name, node_data in selected_hierarchy.items():
            preconds = node_data.get("preconditions", {})
            if isinstance(preconds, dict):
                for pc in preconds.keys():
                    if pc and pc != "None":
                        used_preconditions.add(pc)

        # 2. Construct the Legal Prompt
        system_prompt = (
            "You are an expert Indonesian Legal AI Assistant (Ahli Hukum Pidana).\n"
            "Analyze the user's case based carefully on the provided Legal Context.\n"
            "The Legal Context contains the main Article (Pasal) and its required Sub-Articles (Subgoals).\n"
            "Format your answer cleanly, clearly state which Elements (Unsur) match the case, and conclude if the Article applies."
        )

        user_content = (
            f"USER CASE / QUESTION:\n{task}\n\n"
            f"TARGET PASAL:\n{goal_name}\n\n"
            f"LEGAL CONTEXT (DFS TREE):\n{json.dumps(selected_hierarchy, indent=4)}\n\n"
            f"Please provide your legal analysis:"
        )

        # 3. Query the LLM for the final Answer
        print(f"[PHASE 2] Menyusun final generation response...", flush=True)
        try:
            # Menggunakan helper retry
            response = self._call_llm_with_retry(
                prompt=user_content,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=self.temperature,
                )
            )
            print(f"[PHASE 2] Response akhir berhasil disusun.", flush=True)
            return {
                "answer": response.text.strip(),
                "chosen_goal": goal_name,
                "goal_choices": goal_choices,
                "used_preconditions": list(used_preconditions)
            }
            
        except Exception as e:
            print(f"[PHASE 2 ERROR] Error saat final generation: {e}", flush=True)
            traceback.print_exc()
            return {
                "answer": "Maaf, terjadi kesalahan saat melakukan analisis hukum.",
                "chosen_goal": goal_name,
                "goal_choices": goal_choices,
                "used_preconditions": list(used_preconditions)
            }

if __name__ == "__main__":
    chatbot = PlanningModel()
    
    user_query = "Seorang petugas polisi mendobrak pintu rumah warga tanpa izin untuk menangkap pelaku kejahatan atas perintah atasannya. Apakah perbuatan polisi tersebut merupakan tindak pidana?"
    # user_query = "Terpidana divonis denda Kategori II sebesar Rp8.000.000 namun tidak memiliki aset untuk disita. Jika ia memilih pidana kerja sosial, berapa lama ia harus menjalaninya dan apa syaratnya?"
    # user_query = "Berapa lama waktu maksimal pidana penjara untuk waktu tertentu?"
    print(f"User Query: {user_query}\n")
    print("Generating Answer...\n")
    
    answer = chatbot.planning(task=user_query)
    print(answer)