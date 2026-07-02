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
    def __init__(self, llm_model="command-a-plus-05-2026", top_k=5, kb_file="gog_graph/kb_kuhp.pkl") -> None:
        self.llm_model = llm_model
        self.temperature = 0.0
        self.top_k = top_k
        
        # Initialize LLM Clients
        gemini_api_key = os.environ.get("GOOGLE_API_KEY")
        if gemini_api_key:
            self.client = genai.Client(api_key=gemini_api_key)
        else:
            self.client = None
            
        cohere_api_key = os.environ.get("COHERE_API_KEY")
        if cohere_api_key:
            import cohere
            try:
                self.co_client = cohere.ClientV2(api_key=cohere_api_key)
            except AttributeError:
                self.co_client = cohere.Client(api_key=cohere_api_key)
        else:
            self.co_client = None

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
        
        self.goal_kb.set_embedding(embedding_model="embed-multilingual-v3.0")
        print(f"[CHATBOT] Knowledge Base berhasil diload.", flush=True)
        
    def _call_llm_with_retry(self, prompt, system_instruction=None, temperature=0.0, is_json=False, response_schema=None, max_retries=5):
        """Helper untuk memanggil LLM (Gemini/Cohere) dengan retry dan tools disabled."""
        delay = 15
        for attempt in range(max_retries):
            try:
                print(f"[LLM] Memanggil API {self.llm_model} (Attempt {attempt + 1}/{max_retries})...", flush=True)
                
                if "command" in self.llm_model.lower(): # Cohere
                    if not self.co_client:
                        raise ValueError("COHERE_API_KEY not found in .env")                        
                    if type(self.co_client).__name__ == "ClientV2":
                        messages = []
                        if system_instruction:
                            sys_content = system_instruction
                            if is_json:
                                sys_content += "\n\nOutput MUST be valid JSON."
                            messages.append({"role": "system", "content": sys_content})
                        else:
                            if is_json:
                                messages.append({"role": "system", "content": "Output MUST be valid JSON."})
                                
                        messages.append({"role": "user", "content": prompt})
                        
                        kwargs = {
                            "model": self.llm_model,
                            "messages": messages,
                            "temperature": temperature,
                        }
                        if is_json:
                            kwargs["response_format"] = {"type": "json_object"}
                            
                        response = self.co_client.chat(**kwargs)
                        print(f"[LLM] Berhasil memanggil API Cohere (V2).", flush=True)
                        
                        class DummyResponse:
                            def __init__(self, text):
                                self.text = text
                        
                        # Cohere V2 SDK parses text inside message.content
                        res_text = ""
                        try:
                            if hasattr(response, "message") and hasattr(response.message, "content"):
                                for item in response.message.content:
                                    if getattr(item, "type", "") == "text" or type(item).__name__ == "TextAssistantMessageResponseContentItem":
                                        res_text = getattr(item, "text", "")
                                        break
                                if not res_text:
                                    # Fallback if no text item found
                                    res_text = str(response.message.content[-1])
                            else:
                                res_text = str(response)
                        except Exception:
                            res_text = str(response)
                            
                        return DummyResponse(res_text)
                        
                    else: # Cohere V1 fallback
                        kwargs = {
                            "message": prompt,
                            "model": self.llm_model,
                            "temperature": temperature,
                        }
                        if system_instruction:
                            kwargs["preamble"] = system_instruction
                            
                        if is_json:
                            if "preamble" in kwargs:
                                kwargs["preamble"] += "\n\nOutput MUST be valid JSON."
                            else:
                                kwargs["preamble"] = "Output MUST be valid JSON."
                                
                        response = self.co_client.chat(**kwargs)
                        print(f"[LLM] Berhasil memanggil API Cohere (V1).", flush=True)
                        
                        class DummyResponse:
                            def __init__(self, text):
                                self.text = text
                        return DummyResponse(response.text)
                    
                else: # Gemini
                    from google.genai import types
                    
                    # Disable tools to reduce bias
                    tools = []
                    
                    config_kwargs = {
                        "temperature": temperature,
                        "tools": tools
                    }
                    if system_instruction:
                        config_kwargs["system_instruction"] = system_instruction
                    if is_json:
                        config_kwargs["response_mime_type"] = "application/json"
                    if response_schema:
                        config_kwargs["response_schema"] = response_schema
                        
                    config = types.GenerateContentConfig(**config_kwargs)
                    
                    response = self.client.models.generate_content(
                        model=self.llm_model,
                        contents=prompt,
                        config=config
                    )
                    print(f"[LLM] Berhasil memanggil API Gemini.", flush=True)
                    return response
            except Exception as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e).upper() or "rate limit" in str(e).lower():
                    print(f"[LLM WARNING] Rate limit tercapai. Menunggu {delay} detik...", flush=True)
                    if attempt < max_retries - 1:
                        time.sleep(delay)
                        delay = min(delay + 5, 30)
                        continue
                print(f"[LLM ERROR] Gagal memanggil API: {e}", flush=True)
                raise e

    def _rewrite_query(self, task: str) -> str:
        prompt = (
            "Anda adalah pakar hukum pidana Indonesia. Tugas Anda adalah menulis ulang cerita pengguna "
            "menjadi deskripsi tindak pidana yang formal dan spesifik.\n\n"
            "ATURAN:\n"
            "1. Tulis 1-2 kalimat yang mendeskripsikan PERBUATAN yang dilakukan (bukan orangnya), "
            "menggunakan frasa aktif seperti 'perbuatan merusak...', 'tindakan menodai...', 'perbuatan menghasut...'.\n"
            "2. Frasa harus mencerminkan bagaimana bunyi pasal KUHP ditulis, "
            "misalnya: 'merusak, merobek, menginjak-injak, atau membakar bendera negara dengan maksud menodai kehormatannya'.\n"
            "3. Tambahkan nama TINDAK PIDANA formalnya (bukan hanya objek), "
            "misalnya: 'penodaan bendera negara', 'penghasutan', 'pemalsuan surat', 'perkosaan', 'makar'.\n"
            "4. JANGAN sebut nama orang, lokasi spesifik, atau detail emosional yang tidak relevan secara hukum.\n\n"
            f"Cerita Pengguna:\n{task}\n\n"
            "Deskripsi Tindak Pidana Formal:"
        )
        try:
            print(f"[LLM] Melakukan Query Rewriting...", flush=True)
            response = self._call_llm_with_retry(
                prompt=prompt,
                temperature=0.0
            )
            rewritten_task = response.text.strip()
            print(f"[LLM] Hasil Query Rewriting: {rewritten_task}", flush=True)
            return rewritten_task
        except Exception as e:
            print(f"[LLM ERROR] Gagal melakukan query rewriting: {e}", flush=True)
            return task

    def generate(self, task: str, goal_name: str, relevant_goals: list) -> dict:
        """
        Phase 2: Use DFS to expand the chosen goal into its subgoals.
        """
        print(f"[PHASE 2] Melakukan evaluasi DFS untuk goal '{goal_name}'...", flush=True)
        dfs_tree = {}
        used_preconditions = set()

        def dfs(current_goal_name: str, current_tree: dict, depth: int = 0):
            print(f"[DFS] Masuk ke node '{current_goal_name}' (depth {depth})", flush=True)
            if depth > 5:
                print(f"[DFS] Depth limit tercapai", flush=True)
                return
                
            goal_node = self.goal_kb.get_goal(current_goal_name)
            if not goal_node:
                print(f"[DFS ERROR] Goal node '{current_goal_name}' TIDAK DITEMUKAN di graph KB!", flush=True)
                return

            current_tree[current_goal_name] = {
                "description": goal_node.desc,
                "aliases": goal_node.aliases,
                "preconditions": goal_node.preconditions[0] if goal_node.preconditions else {},
                "elements": goal_node.elements[0] if goal_node.elements else {},
                "postconditions": goal_node.postconditions[0] if goal_node.postconditions else {},
                "subgoals": []
            }
            
            print(f"[DFS] Berhasil mengekstrak node '{current_goal_name}': Preconditions={current_tree[current_goal_name]['preconditions']}, Postconditions={current_tree[current_goal_name]['postconditions']}", flush=True)
            
            # Extract preconditions
            preconds = current_tree[current_goal_name]["preconditions"]
            if isinstance(preconds, dict):
                for pc in preconds.keys():
                    if pc and pc != "None":
                        used_preconditions.add(pc)

            # Recursive step (simplified for example)
            # In real implementation this would navigate graph relationships
            
        dfs(goal_name, dfs_tree)
        return {"tree": dfs_tree, "used_preconditions": list(used_preconditions)}

    def retrieve(
        self,
        task: str,
    ):
        """
        Phase 1: Identify which KUHP Article (Pasal) applies to the user's case.
        """
        print(f"[PHASE 1] Memulai retrieve subgoals...", flush=True)
        
        # LLM Query Rewriting to remove Semantic Noise
        rewritten_task = self._rewrite_query(task)
        
        relevant_goals, _ = self.goal_kb.query_goals(rewritten_task, top_k=self.top_k)
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
                    temperature=self.temperature,
                    is_json=True,
                    response_schema=GoalInferenceSchema
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
            goal_name, goal_choices = self.retrieve(task)

        # 1. Expand the selected Pasal using the DFS backward chaining
        print(f"[PHASE 2] Melakukan evaluasi DFS untuk goal '{goal_name}'...", flush=True)
        all_subgoals_trees = self.goal_kb.dfs(goal_name)
        print(f"[PHASE 2] DFS menghasilkan {len(all_subgoals_trees)} alternative reasoning paths.", flush=True)
        
        # Gunakan reduce_goals() untuk memilih tree terbaik berdasarkan:
        # 1. Kelengkapan unsur hukum (preconditions + elements)
        # 2. Relevansi semantik dengan query user
        query_emb = self.goal_kb.embed_text(task)
        selected_hierarchy, all_legal_elements, tree_score = self.goal_kb.reduce_goals(
            all_subgoals_trees,
            query_embedding=query_emb,
            w_precondition=0.5,
            w_element=0.5
        )
        print(f"[PHASE 2] Tree terpilih (score={tree_score:.4f}), unsur hukum ditemukan: {all_legal_elements}", flush=True)

        # Extract all used postconditions
        used_preconditions = set()
        print(f"[DEBUG DFS] Selected Hierarchy Nodes: {list(selected_hierarchy.keys())}", flush=True)
        for node_name, node_data in selected_hierarchy.items():
            preconds = node_data.get("preconditions", {})
            print(f"[DEBUG DFS] Node '{node_name}' Preconditions: {preconds}", flush=True)
            if isinstance(preconds, dict):
                for pc in preconds.keys():
                    if pc and pc != "None":
                        used_preconditions.add(pc)
            
            # Mari kita cek juga postconditions dan elements-nya
            postconds = node_data.get("postconditions", {})
            print(f"[DEBUG DFS] Node '{node_name}' Postconditions: {postconds}", flush=True)
            elements = node_data.get("elements", {})
            print(f"[DEBUG DFS] Node '{node_name}' Elements: {elements}", flush=True)
            
        print(f"[DEBUG DFS] Final Used Preconditions: {used_preconditions}", flush=True)

        # 2. Construct the Legal Prompt
        system_prompt = (
            "You are an expert Indonesian Legal AI Assistant (Ahli Hukum Pidana).\n"
            "Analyze the user's case carefully based on the provided Legal Context.\n"
            "The Legal Context contains the main Article (Pasal) and its required Sub-Articles (Subgoals).\n"
            "Please create the answer in markdown format.\n\n"
            "STRUKTURKAN JAWABAN ANDA PERSIS SEPERTI INI:\n"
            "1. **Inti Kesimpulan**: (Sampaikan di awal apakah perbuatan pengguna melanggar pasal tersebut atau tidak)\n"
            "2. **Saran Praktis**: (Langkah hukum atau antisipasi apa yang sebaiknya dilakukan pengguna)\n"
            "3. **Ringkasan Fakta & Analisis Unsur**: (Buat ringkasan fakta kasus dan bedah satu per satu unsur pasalnya, apakah terpenuhi atau tidak)\n"
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
                system_instruction=system_prompt,
                temperature=self.temperature
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

    def getcontext(self, task: str):
        """
        Retrieval-only pipeline untuk evaluation (RAGAS).
        Menjalankan Phase 1 (retrieve) + DFS + reduce_goals,
        lalu mengembalikan selected_hierarchy tanpa memanggil LLM untuk generation.
        """
        print(f"\n[GETCONTEXT] Memulai retrieval context untuk evaluasi...", flush=True)

        # Phase 1: retrieve goal
        goal_name, goal_choices = self.retrieve(task)

        # Phase 2: DFS + reduce
        print(f"[GETCONTEXT] Melakukan DFS untuk goal '{goal_name}'...", flush=True)
        all_subgoals_trees = self.goal_kb.dfs(goal_name)
        print(f"[GETCONTEXT] DFS menghasilkan {len(all_subgoals_trees)} alternative reasoning paths.", flush=True)

        query_emb = self.goal_kb.embed_text(task)
        selected_hierarchy, all_legal_elements, tree_score = self.goal_kb.reduce_goals(
            all_subgoals_trees,
            query_embedding=query_emb,
            w_precondition=0.5,
            w_element=0.5
        )
        print(f"[GETCONTEXT] Tree terpilih (score={tree_score:.4f}), unsur: {all_legal_elements}", flush=True)

        return {
            "chosen_goal": goal_name,
            "goal_choices": goal_choices,
            "contexts": selected_hierarchy,
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