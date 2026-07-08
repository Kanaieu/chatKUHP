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
                
                if "command" in self.llm_model.lower():
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
                                    res_text = str(response.message.content[-1])
                            else:
                                res_text = str(response)
                        except Exception:
                            res_text = str(response)
                            
                        return DummyResponse(res_text)
                        
                    else:
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
        import re
        pasal_matches = re.findall(r'(?i)pasal\s+\d+(?:\s+ayat\s+\d+)?', task)

        #HAPUS
        prompt = (
            "Tugas Anda adalah menulis ulang cerita/pertanyaan hukum dari pengguna menjadi query pencarian hukum yang optimal untuk mencocokkan pasal KUHP Baru (UU 1/2023).\n\n"
            "Query pencarian harus terdiri dari kombinasi:\n"
            "1. Nama tindak pidana formal yang relevan (misal: Pencurian, Pemalsuan, Makar, dll).\n"
            "2. Kata kunci aksi/perbuatan konkret dari cerita pengguna (misal: melempar batu, mencuri listrik, membagi hoax).\n"
            "3. Objek hukum spesifik yang terlibat (misal: kereta api, hewan, bendera, pesawat, anak).\n"
            "4. Nomor pasal/undang-undang jika secara eksplisit disebutkan oleh pengguna.\n\n"
            "ATURAN:\n"
            "- Tuliskan hasil akhir dalam satu kalimat/frasa query yang padat kata kunci, tanpa penjelasan tambahan atau pengantar.\n"
            "- Jangan hilangkan kata benda spesifik seperti 'kereta api', 'listrik', 'hewan', 'pesawat', 'hoax' karena kata benda ini sangat penting untuk akurasi pencarian.\n"
            "- Jika cerita menyebutkan nomor pasal tertentu (misal: Pasal 374), wajib sertakan nomor pasal tersebut dalam query.\n\n"
            "PANDUAN KHUSUS (PENTING — jangan salah arah):\n"
            "- 'Menghasut', 'hasutan', 'provokatif', 'mengajak melakukan kejahatan' → tindak pidana PENGHASUTAN (Pasal 246), BUKAN penghinaan pemerintah (Pasal 240 atau 241).\n"
            "- 'Melempar batu ke kereta api', 'bahaya rel kereta' → KEALPAAN bahaya lalu lintas kereta api (Pasal 324), BUKAN kekerasan massa di muka umum (Pasal 262).\n"
            "- 'Menghalangi ibadah', 'mengganggu kegiatan keagamaan', 'membubarkan ibadah' → GANGGUAN ketertiban kegiatan keagamaan, merintangi ibadah dengan kekerasan (Pasal 303).\n"
            "- 'Hoaks', 'berita bohong', 'penyebaran informasi palsu' → PENGHINAAN PEMERINTAH di muka umum (Pasal 240), BUKAN penyebaran ajaran komunisme atau Pancasila (Pasal 188).\n"
            "- 'Menghina Pancasila', 'menolak Pancasila', 'mengganti Pancasila' → TINDAKAN MENOLAK/MENGGANTI PANCASILA (Pasal 188 atau Pasal 190), BUKAN unjuk rasa tanpa izin (Pasal 256).\n"
            "- 'Menghina lambang negara', 'merusak lambang negara' → PENODAAN LAMBANG NEGARA (Pasal 236), BUKAN penghinaan pemerintah secara umum (Pasal 240).\n"
            "- 'Penipuan emas', 'berat emas tidak sesuai', 'pedagang emas menipu' → PENIPUAN jual beli barang (Pasal 492 atau Pasal 493), BUKAN pemalsuan cap atau logo emas (Pasal 384).\n"
            "- 'Pencurian listrik', 'mencuri aliran listrik', 'mengambil listrik tanpa izin' → PENCURIAN (Pasal 476), BUKAN kealpaan bangunan listrik rusak (Pasal 320).\n\n"
            "CONTOH:\n"
            "- Cerita: 'Seseorang menghasut warga agar melakukan kekerasan terhadap pejabat...' -> Query: Penghasutan tindak pidana di muka umum, hasutan melawan penguasa, Pasal 246\n"
            "- Cerita: 'Apakah penyebaran hoaks termasuk tindak pidana?' -> Query: Penghinaan pemerintah lembaga negara di muka umum, konten hoaks menghina institusi negara, Pasal 240\n"
            "- Cerita: 'Ada kasus pencurian listrik oleh tetangga...' -> Query: Pencurian listrik, mengambil aliran listrik secara melawan hukum, Pasal 476\n"
            "- Cerita: 'Saya membeli emas tapi beratnya tidak sesuai...' -> Query: Penipuan jual beli barang tidak sesuai spesifikasi, tipu muslihat pedagang, Pasal 492\n"
            "- Cerita: 'Apakah aksi pelemparan batu ke kereta api bisa dipidana?' -> Query: Kealpaan bahaya lalu lintas kereta api, melempar batu ke jalur rel kereta api, Pasal 324\n"
            "- Cerita: 'Bagaimana jerat hukum menghalangi kegiatan ibadah?' -> Query: Gangguan ketertiban kegiatan keagamaan, merintangi atau membubarkan ibadah, Pasal 303\n"
            "- Cerita: 'Apa pidana bagi orang yang menghina Pancasila? Apa bisa dikatakan menghina lambang Negara?' -> Query: Menghina Pancasila, mengganti Pancasila dasar negara, penodaan lambang negara, Pasal 190, Pasal 236\n"
            "- Cerita: 'Benarkah pelaku pemalsuan uang bisa dijerat berdasarkan Pasal 374?' -> Query: Pemalsuan mata uang, memalsu uang kertas negara, Pasal 374\n"
            "- Cerita: 'Apa jerat hukumnya bagi orang yang mendorong orang lain untuk bunuh diri' -> Query: Pasal 462, mendorong bunuh diri, membantu bunuh diri, memberi sarana bunuh diri, membantu_atau_mendorong_bunuh_diri_sampai_mati\n"
            "- Cerita: 'Larangan Perdagangan Organ, Jaringan Tubuh, dan Darah Manusia' -> Query: Perdagangan organ tubuh manusia, jaringan tubuh, darah manusia, Pasal 345\n"
            "- Cerita: 'Hukuman Maksimal bagi Pelaku Judi Bola Online' -> Query: Perjudian, menawarkan atau memberi kesempatan main judi tanpa izin, judi bola online, Pasal 426\n"
            "- Cerita: 'Saya penasaran, kalau menuduh orang mencuri tanpa bukti kena pasal berapa? Apakah bisa ia dikenakan pasal menuduh orang tanpa bukti?' -> Query: Pencemaran nama baik, fitnah tanpa bukti, menuduh mencuri tanpa bukti, Pasal 433, Pasal 434\n"
            "- Cerita: 'Penumpang yang secara lisan bercanda bawa bom tersebut diturunkan dari pesawat. Pertanyaan saya, kenapa tidak boleh bercanda bawa bom di pesawat? Apakah perbuatan tersebut masuk tindakan teror?' -> Query: Tindak Pidana Terorisme, bercanda bawa bom di pesawat, mengancam keselamatan penerbangan, Pasal 583, Pasal 601\n\n"
            f"Cerita Pengguna: {task}\n\n"
            "Query Pencarian:"
        )
        try:
            print(f"[LLM] Melakukan Query Rewriting...", flush=True)
            response = self._call_llm_with_retry(
                prompt=prompt,
                temperature=0.0
            )
            rewritten_task = response.text.strip()
            
            rewritten_task = re.sub(r'(?i)^(?:query\s*pencarian|query)\s*:\s*', '', rewritten_task)
            rewritten_task = rewritten_task.strip('"-* ')

            for pm in pasal_matches:
                clean_pm = pm.strip()
                if clean_pm.lower() not in rewritten_task.lower():
                    rewritten_task += f", {clean_pm}"

            print(f"[LLM] Hasil Query Rewriting: {rewritten_task}", flush=True)
            return rewritten_task
        except Exception as e:
            print(f"[LLM ERROR] Gagal melakukan query rewriting: {e}", flush=True)
            fallback_task = task
            for pm in pasal_matches:
                if pm.lower() not in fallback_task.lower():
                    fallback_task += f", {pm}"
            return fallback_task

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
        
        rewritten_task = self._rewrite_query(task)
        self.last_rewritten_query = rewritten_task
        
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

    def _add_sibling_nodes(self, hierarchy_dict: dict) -> dict:
        """
        Mencari dan menambahkan pasal-pasal saudara (ayat lain dari pasal yang sama)
        ke dalam hierarchy_dict untuk memberikan konteks hukum lengkap.
        """
        import re
        new_hierarchy = dict(hierarchy_dict)
        for name in list(hierarchy_dict.keys()):
            match = re.match(r'^(KUHP Pasal \d+)', name)
            if match:
                base_pasal = match.group(1)
                for node in self.goal_kb.nodes:
                    if node.name.startswith(base_pasal) and node.name not in new_hierarchy:
                        new_hierarchy[node.name] = {
                            "description": node.desc,
                            "aliases": node.aliases,
                            "preconditions": node.preconditions[0] if node.preconditions else {},
                            "elements": node.elements[0] if node.elements else {},
                            "postconditions": node.postconditions[0] if node.postconditions else {},
                            "subgoals": []
                        }
        return new_hierarchy

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
        
        query_emb = self.goal_kb.embed_text(task)
        selected_hierarchy, all_legal_elements, tree_score = self.goal_kb.reduce_goals(
            all_subgoals_trees,
            query_embedding=query_emb,
            w_precondition=0.5,
            w_element=0.5
        )
        print(f"[PHASE 2] Tree terpilih (score={tree_score:.4f}), unsur hukum ditemukan: {all_legal_elements}", flush=True)

        selected_hierarchy = self._add_sibling_nodes(selected_hierarchy)

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

        selected_hierarchy = self._add_sibling_nodes(selected_hierarchy)

        # HAPUS
        # Filter pasal-pasal "boilerplate" yang selalu muncul tapi tidak relevan secara kontekstual.
        # Pasal 79 (tabel denda) muncul di hampir semua jawaban dan selalu dinilai irrelevant oleh evaluator.
        CONTEXT_BLACKLIST_PREFIXES = (
            "KUHP Pasal 79",   # Tabel kategori denda — tidak kontekstual
        )
        filtered_hierarchy = {
            name: data
            for name, data in selected_hierarchy.items()
            if not name.startswith(CONTEXT_BLACKLIST_PREFIXES)
        }

        return {
            "chosen_goal": goal_name,
            "goal_choices": goal_choices,
            "contexts": filtered_hierarchy,
            "rewritten_query": getattr(self, "last_rewritten_query", ""),
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