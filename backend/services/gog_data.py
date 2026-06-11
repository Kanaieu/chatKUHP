from sklearn.metrics.pairwise import cosine_similarity
import requests
import json
import numpy as np
import pickle
from collections import OrderedDict
import os
import asyncio
import itertools
from copy import deepcopy
from tqdm import tqdm
import ast
import math
import hashlib
import tempfile

from openai import AsyncOpenAI, OpenAI
import tiktoken
import time
try:
    from google import genai
    from google.genai import types
    _HAS_GENAI = True
except Exception:
    _HAS_GENAI = False

try:
    from .gog_prompts import PROMPTS
except ImportError:
    from gog_prompts import PROMPTS

class GOGNode:
    def __init__(self, name, desc, preconditions, elements, postconditions, name_emb, preconditions_emb, elements_emb, postconditions_emb):
        # name: e.g. "Pasal 362 KUHP"
        # desc: full text of the article
        # preconditions: dict of legal preconditions / unsur (mapped from previous `tools`)
        # elements: dict of material elements / objek (mapped from previous `mats`)
        self.name = name
        self.desc = desc
        self.aliases = []
        # store alternatives as lists to support multiple ways a goal can be satisfied
        self.preconditions = [preconditions]
        self.elements = [elements]
        self.postconditions = [postconditions]
        self.name_emb = name_emb

        # These are lists of embeddings corresponding to the above
        self.preconditions_emb = [preconditions_emb]
        self.elements_emb = [elements_emb]
        self.postconditions_emb = [postconditions_emb]

    def add_alternative(self, preconditions, elements, postconditions, preconditions_emb, elements_emb, postconditions_emb):
        self.preconditions.append(preconditions)
        self.elements.append(elements)
        self.postconditions.append(postconditions)
        self.preconditions_emb.append(preconditions_emb)
        self.elements_emb.append(elements_emb)
        self.postconditions_emb.append(postconditions_emb)

class GOGEdge:
    def __init__(self, goal, subgoal, description):
        self.goal = goal
        self.subgoal = subgoal
        self.description = description

class GOGKB:
    def __init__(self, url="", port="", llm="", embedding_model=""):
        self.nodes = []
        self.edges = []
        self.goals_emb = []

        self.name2node = {}
        self.emb2node = {}
        # Node to Edges
        self.goal2subgoals = {}

        # Node name to postconditions of potential subgoal
        self.name2unmatchedreqs = {}
        self.postconditions2nodes = {}

        # bookkeeping and config
        self.doc_dir = "GoGs_Skripsi/src/optimus1/models/knowledge/"
        self.kb_dir = "gog_graph/"
        self.kb_file = os.path.join(self.kb_dir, "kb_kuhp.pkl")

        # Run async calls if using openai
        self.max_async = 16

        # Compatibility flags / helper mappings
        self.use_openai_llm = False
        # name_normalize maps variant names into normalized keys (optional)
        self.name_normalize = {}

        # Ensure KB dir exists
        os.makedirs(self.kb_dir, exist_ok=True)

        # The cosine similarity threshold for considering two goals to be equivalent
        # Name and postconditions of the goal are checked
        self.goal_similarity_threshold = 0.92

        # set providers
        self.set_llm(url, port, llm)
        self.set_embedding(url, port, embedding_model)

    @classmethod
    def load_kb(cls, kb_file="./gog_graph/kb.pkl"):
        import sys
        if 'gog_data' not in sys.modules:
            sys.modules['gog_data'] = sys.modules[__name__]
        with open(kb_file, "rb") as f:
            kb = pickle.load(f)
        return kb

    def set_llm(self, url="", port="", llm=""):
        self.url = url
        self.port = port
        self.chat_endpoint = "/v1"
        self.llm = llm
        if url != "":
            self.chat_url = self.url + ":" + self.port + self.chat_endpoint
        else:
            self.chat_url = ""

    def set_embedding(self, url="", port="", embedding_model=""):
        self.url = url
        self.port = port
        self.embed_endpoint = "/v1"
        self.embedding_model = embedding_model
        if url != "":
            self.embed_url = self.url + ":" + self.port + self.embed_endpoint
        else:
            self.embed_url = ""

    def save_kb(self):
        with open(self.kb_file, "wb") as f:
            pickle.dump(self, f)

    def add_node(self, node, name_embedding, postconditions):
        self.nodes.append(node)
        self.name2node[node.name] = node
        self.emb2node[tuple(name_embedding)] = node
        self.goals_emb.append(name_embedding)

        if postconditions != "None" and isinstance(postconditions, dict):
            for post in postconditions.keys():
                if post not in self.postconditions2nodes:
                    self.postconditions2nodes[post] = []    
                self.postconditions2nodes[post].append(node)

    def add_edge(self, goal, subgoal, relation_desc):
        # Check if relation already exists
        if goal in self.goal2subgoals:
            exists = False
            for e in self.goal2subgoals[goal]:
                if e.subgoal.name == subgoal.name:
                    exists = True
                    break
            if exists:
                return
        else:
            self.goal2subgoals[goal] = []

        edge = GOGEdge(goal, subgoal, relation_desc)
        self.edges.append(edge)
        self.goal2subgoals[goal].append(edge)

    async def gather_batch_embed_text(self, queries):
        import concurrent.futures
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(8, len(queries))) as ex:
            futures = [ex.submit(self.embed_text, q) for q in queries]
            for f in futures:
                results.append(f.result())
        return results

    async def embed_text_async(self, text, client):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.embed_text, text)

    async def gather_batch_llm_query(self, queries):
        async with AsyncOpenAI() as client:
            tasks = [self.query_llm_async(q, client) for q in queries]
            results = await asyncio.gather(*tasks)
        return results

    async def query_llm_async(self, query, client):
        response = await client.chat.completions.create(
            model= self.llm,
            temperature= 0.0,
            messages=[
                {
                    "role": "user",
                    "content": query,
                }
            ]
        )

        return response.choices[0].message.content

    def query_llm(self, query):
        if self.chat_url != "":
            client = OpenAI(base_url=self.chat_url, api_key="123")
        else:
            client = OpenAI()
        response = client.chat.completions.create(
            model= self.llm,
            temperature= 0.0,
            messages=[
                {
                    "role": "user",
                    "content": query,
                }
            ]
        )
        output = response.choices[0].message.content

        return output

    def get_reqs(self, preconditions, elements):
        """
        Convert preconditions (previously `tools`) and elements (previously `mats`) into
        a flat list of requirement keys used for subgoal linking.
        """
        reqs = []

        if preconditions != "None":
            pre_json = preconditions
        else:
            pre_json = {}

        if elements != "None":
            elem_json = elements
        else:
            elem_json = {}

        for p in pre_json:
            # keep a small heuristic mapping (preserved from original code)
            if p == "fuel":
                reqs.append("logs")
            elif p == "None":
                continue
            else:
                reqs.append(p)

        for e in elem_json:
            if e == "None":
                continue
            reqs.append(e)

        return reqs

    def check_goal_names_equivalent(self, goal_a, goal_b):
        goal_a_split = goal_a.split(" ")
        goal_b_split = goal_b.split(" ")

        if goal_a_split[0] == goal_b_split[0]:
            if goal_a_split[1] == "a":
                goal_a_item = " ".join(goal_a_split[2:])
            else:
                goal_a_item = " ".join(goal_a_split[1:])

            if goal_b_split[1] == "a":
                goal_b_item = " ".join(goal_b_split[2:])
            else:
                goal_b_item = " ".join(goal_b_split[1:])

            sim = cosine_similarity([self.embed_text(goal_a_item)],[self.embed_text(goal_b_item)])[0][0]

            if sim > self.goal_similarity_threshold:
                return True

        return False

    def check_conditions_equivalent(self, conds_a, conds_b):
        if conds_a == conds_b:
            return True

        if isinstance(conds_a,str) or isinstance(conds_b,str):
            return False

        if len(conds_a) != len(conds_b):
            return False

        keys_a = sorted(list(conds_a.keys()))
        keys_b = sorted(list(conds_b.keys()))
        for a,b in zip(keys_a, keys_b):
            sim = cosine_similarity([self.embed_text(a)],[self.embed_text(b)])[0][0]
            if sim < self.goal_similarity_threshold:
                return False
            if not conds_a[a] == conds_b[b]:
                return False

        return True

    def build_kb(self):
        # Simplified, runnable KB builder for local testing.
        # It supports two input formats:
        # 1) Structured JSON files where each file contains keys: name/title, desc/text, preconditions, elements, postconditions
        # 2) Plain text files containing a line like: "Title: ... Text: ..." which will be parsed with a simple heuristic.

        doc_dir_files = [x for x in os.listdir(self.doc_dir) if x.endswith('.json') or x.endswith('.txt') or x.endswith('.md') or x.endswith('.jsonl')]
        if len(doc_dir_files) == 0:
            print("No documents found in doc_dir.")
            return

        added_goals = {}
        parsed_entries = []
        unique_texts_to_embed = set()

        print("Phase 1: Parsing documents and collecting unique strings...")
        for file in doc_dir_files:
            path = os.path.join(self.doc_dir, file)
            if file.lower().endswith('.jsonl'):
                try:
                    with open(path, 'r', encoding='utf-8') as fh:
                        for line in fh:
                            if not line.strip(): continue
                            try:
                                entry = json.loads(line)
                            except Exception: continue
                            
                            name = entry.get('name') or entry.get('title') or entry.get('pasal')
                            desc = entry.get('desc') or entry.get('text') or entry.get('bunyi') or ""
                            preconditions = entry.get('preconditions') or {}
                            elements = entry.get('elements') or {}
                            postconditions = entry.get('postconditions') or {}

                            if isinstance(preconditions, str):
                                try: preconditions = ast.literal_eval(preconditions)
                                except Exception: preconditions = {preconditions: 1} if preconditions and preconditions.lower() != 'none' else {}
                            if isinstance(elements, str):
                                try: elements = ast.literal_eval(elements)
                                except Exception: elements = {elements: 1} if elements and elements.lower() != 'none' else {}
                            if isinstance(postconditions, str):
                                try: postconditions = ast.literal_eval(postconditions)
                                except Exception: postconditions = {postconditions: 1} if postconditions and postconditions.lower() != 'none' else {}

                            if not isinstance(preconditions, dict): preconditions = {} if preconditions in (None, "None") else dict(preconditions)
                            if not isinstance(elements, dict): elements = {} if elements in (None, "None") else dict(elements)
                            if not isinstance(postconditions, dict): postconditions = {} if postconditions in (None, "None") else dict(postconditions)

                            if not name: continue

                            # String representations for embeddings
                            name_str = str(name)
                            pre_str = ", ".join(preconditions.keys()) if preconditions else ""
                            elem_str = ", ".join(elements.keys()) if elements else ""
                            post_str = ", ".join(postconditions.keys()) if postconditions else ""

                            unique_texts_to_embed.update([name_str, pre_str, elem_str, post_str])
                            parsed_entries.append({
                                'name': name, 'desc': desc, 
                                'preconditions': preconditions, 'elements': elements, 'postconditions': postconditions,
                                'name_str': name_str, 'pre_str': pre_str, 'elem_str': elem_str, 'post_str': post_str
                            })
                except Exception as e:
                    print(f"Failed to read jsonl {file}: {e}")
            else:
                pass # You can preserve or add back `.json` and `.txt` handling here if needed.

        # Ignore empty strings
        unique_texts_to_embed.discard("")
        unique_texts_to_embed.discard("None")

        print(f"Phase 2: Generating batch embedding request for {len(unique_texts_to_embed)} unique strings...")
        batch_requests = []
        text2key = {}
        for t in unique_texts_to_embed:
            k = hashlib.md5(t.encode('utf-8')).hexdigest()
            text2key[t] = k
            batch_requests.append({
                "key": k,
                "request": {"content": {"parts": [{"text": t}]}}
            })

        key2emb = {}
        if batch_requests:
            temp_jsonl_path = os.path.join(self.kb_dir, "temp_batch_emb.jsonl")
            with open(temp_jsonl_path, 'w', encoding='utf-8') as f:
                for r in batch_requests:
                    f.write(json.dumps(r, ensure_ascii=False) + '\n')
            
            print(f"Phase 3: Uploading Batch Job to Gemini...")
            key2emb = self.gemini_batch_embeddings_from_jsonl(temp_jsonl_path, model=self.embedding_model)

        def get_cached_emb(text_val):
            if not text_val or text_val == "None":
                return [0.0] * 768
            k = text2key.get(text_val)
            if k in key2emb:
                return key2emb[k]
            # Fallback for unexpected missing keys
            return self.embed_text(text_val)

        print(f"Phase 4: Building Nodes and Edges...")
        for entry in parsed_entries:
            name, desc = entry['name'], entry['desc']
            preconditions, elements, postconditions = entry['preconditions'], entry['elements'], entry['postconditions']
            
            name_emb = get_cached_emb(entry['name_str'])
            pre_emb = get_cached_emb(entry['pre_str'])
            elem_emb = get_cached_emb(entry['elem_str'])
            post_emb = get_cached_emb(entry['post_str'])

            if name in self.name2node:
                existing = self.name2node[name]
                existing.add_alternative(preconditions, elements, postconditions, pre_emb, elem_emb, post_emb)
            else:
                node = GOGNode(name, desc, preconditions, elements, postconditions, name_emb, pre_emb, elem_emb, post_emb)
                self.add_node(node, name_emb, postconditions)
                reqs = self.get_reqs(preconditions, elements)
                if reqs:
                    added_goals[name] = {"node": node, "reqs": reqs}

        for g in list(added_goals.keys()):
            for r in added_goals[g]["reqs"]:
                if r in self.postconditions2nodes:
                    for subgoal in self.postconditions2nodes[r]:
                        goal = added_goals[g]["node"]
                        relation_desc = f"{subgoal.name} is used by {goal.name}"
                        self.add_edge(goal, subgoal, relation_desc)

        self.save_kb()
        print("Knowledge Base Built successfully!")

    def _get_cohere_client(self):
        try:
            import cohere
        except ImportError:
            raise RuntimeError("Please install cohere: pip install cohere")
        api_key = os.environ.get("COHERE_API_KEY")
        if not api_key:
            raise RuntimeError("COHERE_API_KEY not set in environment.")
        return cohere.Client(api_key)

    def cohere_sync_embeddings_batch(self, texts, batch_size=96, delay=10.0):
        """
        Embed a list of texts synchronously using Cohere API.
        Cohere allows up to 96 texts per request on trial keys.
        """
        client = self._get_cohere_client()
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            print(f"Embedding batch {i // batch_size + 1} / {math.ceil(len(texts) / batch_size)} ({len(batch)} texts)...")
            
            success = False
            retries = 0
            while not success and retries < 5:
                try:
                    response = client.embed(
                        texts=batch,
                        model=self.embedding_model,
                        input_type="search_document"
                    )
                    all_embeddings.extend(response.embeddings)
                    success = True
                except Exception as e:
                    error_msg = str(e).lower()
                    if "429" in error_msg or "rate limit" in error_msg:
                        print(f"Rate limit hit on batch {i // batch_size + 1}. Waiting 15 seconds before retrying...")
                        time.sleep(15.0)
                        retries += 1
                    else:
                        print(f"Error on batch {i // batch_size + 1}: {e}")
                        print("Appending zeros for this batch.")
                        for _ in batch:
                            all_embeddings.append([0.0] * 1024)
                        success = True
            
            if not success:
                for _ in batch:
                    all_embeddings.append([0.0] * 1024)

            if i + batch_size < len(texts):
                time.sleep(delay)
            
        return all_embeddings

    def build_kb_sync(self):
        # Simplified, runnable KB builder for local testing.
        # Uses synchronous embedding instead of Batch API
        # It supports two input formats:
        # 1) Structured JSON files where each file contains keys: name/title, desc/text, preconditions, elements, postconditions
        # 2) Plain text files containing a line like: "Title: ... Text: ..." which will be parsed with a simple heuristic.

        doc_dir_files = [x for x in os.listdir(self.doc_dir) if x.endswith('.json') or x.endswith('.txt') or x.endswith('.md') or x.endswith('.jsonl')]
        if len(doc_dir_files) == 0:
            print("No documents found in doc_dir.")
            return

        added_goals = {}
        parsed_entries = []
        unique_texts_to_embed = set()

        print("Phase 1: Parsing documents and collecting unique strings...")
        for file in doc_dir_files:
            path = os.path.join(self.doc_dir, file)
            if file.lower().endswith('.jsonl'):
                try:
                    with open(path, 'r', encoding='utf-8') as fh:
                        for line in fh:
                            if not line.strip(): continue
                            try:
                                entry = json.loads(line)
                            except Exception: continue
                            
                            name = entry.get('name') or entry.get('title') or entry.get('pasal')
                            desc = entry.get('desc') or entry.get('text') or entry.get('bunyi') or ""
                            preconditions = entry.get('preconditions') or {}
                            elements = entry.get('elements') or {}
                            postconditions = entry.get('postconditions') or {}

                            if isinstance(preconditions, str):
                                try: preconditions = ast.literal_eval(preconditions)
                                except Exception: preconditions = {preconditions: 1} if preconditions and preconditions.lower() != 'none' else {}
                            if isinstance(elements, str):
                                try: elements = ast.literal_eval(elements)
                                except Exception: elements = {elements: 1} if elements and elements.lower() != 'none' else {}
                            if isinstance(postconditions, str):
                                try: postconditions = ast.literal_eval(postconditions)
                                except Exception: postconditions = {postconditions: 1} if postconditions and postconditions.lower() != 'none' else {}

                            if not isinstance(preconditions, dict): preconditions = {} if preconditions in (None, "None") else dict(preconditions)
                            if not isinstance(elements, dict): elements = {} if elements in (None, "None") else dict(elements)
                            if not isinstance(postconditions, dict): postconditions = {} if postconditions in (None, "None") else dict(postconditions)

                            if not name: continue

                            # String representations for embeddings
                            name_str = str(name)
                            pre_str = ", ".join(preconditions.keys()) if preconditions else ""
                            elem_str = ", ".join(elements.keys()) if elements else ""
                            post_str = ", ".join(postconditions.keys()) if postconditions else ""

                            unique_texts_to_embed.update([name_str, pre_str, elem_str, post_str])
                            parsed_entries.append({
                                'name': name, 'desc': desc, 
                                'preconditions': preconditions, 'elements': elements, 'postconditions': postconditions,
                                'name_str': name_str, 'pre_str': pre_str, 'elem_str': elem_str, 'post_str': post_str
                            })
                except Exception as e:
                    print(f"Failed to read jsonl {file}: {e}")
            else:
                pass

        # Ignore empty strings
        unique_texts_to_embed.discard("")
        unique_texts_to_embed.discard("None")

        print(f"Phase 2 & 3: Generating embeddings via Cohere API for {len(unique_texts_to_embed)} unique strings...")
        text_list = list(unique_texts_to_embed)
        text2key = {}
        for t in text_list:
            k = hashlib.md5(t.encode('utf-8')).hexdigest()
            text2key[t] = k

        key2emb = {}
        if text_list:
            embeddings_list = self.cohere_sync_embeddings_batch(text_list, batch_size=96, delay=10.0)
            for t, emb in zip(text_list, embeddings_list):
                k = text2key[t]
                key2emb[k] = emb

        def get_cached_emb(text_val):
            if not text_val or text_val == "None":
                return [0.0] * 1024
            k = text2key.get(text_val)
            if k in key2emb:
                return key2emb[k]
            # Fallback for unexpected missing keys
            return self.embed_text(text_val)

        print(f"Phase 4: Building Nodes and Edges...")
        for entry in parsed_entries:
            name, desc = entry['name'], entry['desc']
            preconditions, elements, postconditions = entry['preconditions'], entry['elements'], entry['postconditions']
            
            name_emb = get_cached_emb(entry['name_str'])
            pre_emb = get_cached_emb(entry['pre_str'])
            elem_emb = get_cached_emb(entry['elem_str'])
            post_emb = get_cached_emb(entry['post_str'])

            if name in self.name2node:
                existing = self.name2node[name]
                existing.add_alternative(preconditions, elements, postconditions, pre_emb, elem_emb, post_emb)
            else:
                node = GOGNode(name, desc, preconditions, elements, postconditions, name_emb, pre_emb, elem_emb, post_emb)
                self.add_node(node, name_emb, postconditions)
                reqs = self.get_reqs(preconditions, elements)
                if reqs:
                    added_goals[name] = {"node": node, "reqs": reqs}

        for g in list(added_goals.keys()):
            for r in added_goals[g]["reqs"]:
                if r in self.postconditions2nodes:
                    for subgoal in self.postconditions2nodes[r]:
                        goal = added_goals[g]["node"]
                        relation_desc = f"{subgoal.name} is used by {goal.name}"
                        self.add_edge(goal, subgoal, relation_desc)

        self.save_kb()
        print("Knowledge Base Built successfully!")

    def load_recipes(self, files, recipe_dir):
        recipe_str = ""
        for file in files:
            recipe_str += "--- Recipe: {name} ---".format(name=file) + "\n"
            with open(recipe_dir+file) as f:
                recipe = json.load(f)
            recipe_str += json.dumps(recipe) + "\n"
        return recipe_str

    def process_doc(self, file, doc_dir):
        with open(doc_dir+file) as f:
            data_json = json.load(f)

        # Get table data
        tables = []
        for t in data_json["tables"]:
            row_len = math.gcd(len(t["headers"]["text"]), len(t["cells"]["text"]))
            table = "--- Table Start ---\n"
            table += "Headers: "
            for i, h in enumerate(t["headers"]["text"]):
                table += h
                if i < len(t["headers"]["text"])-1:
                    table += ", "
            table += "\n"
            table += "Cells: \n"
            for i, c in enumerate(t["cells"]["text"]):
                table += c
                if (i+1) % row_len == 0:
                    table += "\n"
                elif i < len(t["cells"]["text"])-1:
                    table += ", "
            table += "--- Table End ---\n"
            tables.append({"table": table, "bbox": t["bbox"]})

        # Arrange data in order from top to bottom
        doc = ""
        i = 0
        j = 0
        while i < len(data_json["texts"]) or j < len(tables):
            if j >= len(tables) or (i < len(data_json["texts"]) and data_json["texts"][i]["bbox"][1] < tables[j]["bbox"][1]):
                doc += data_json["texts"][i]["text"]
                i += 1
            else:
                doc += tables[j]["table"]
                j += 1
            doc += "\n"
        return doc

    def embed_text(self, text: str) -> list:
        """
        Instant Single-Call Embedding for Live User Queries.
        Used by the Chatbot (query_goals) and occasionally as a fallback.
        """
        if not text:
            return [0.0] * 1024
        
        client = self._get_cohere_client()
        response = client.embed(
            texts=[text],
            model=self.embedding_model,
            input_type="search_query"
        )
        return response.embeddings[0]

    def create_embeddings_jsonl(self, jsonl_path=None, include_meta=True):
        """Create JSONL file suitable for Gemini batch embeddings from files in self.doc_dir.
        Each line has fields: key, request:{content:{parts:[{text:...}]}} and optional meta.
        Returns the path to the JSONL file.
        """
        if jsonl_path is None:
            jsonl_path = os.path.join(self.kb_dir, "embeddings_requests.jsonl")

        docs = [x for x in os.listdir(self.doc_dir) if x.endswith('.json') or x.endswith('.txt') or x.endswith('.md')]
        records = []
        for i, fname in enumerate(docs):
            path = os.path.join(self.doc_dir, fname)
            try:
                if fname.endswith('.json'):
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    title = data.get('name') or data.get('title') or data.get('pasal') or fname
                    text = data.get('desc') or data.get('text') or data.get('bunyi') or ''
                    pre = data.get('preconditions') or data.get('unsur') or {}
                    elems = data.get('elements') or data.get('objek') or {}
                    post = data.get('postconditions') or data.get('sanksi') or {}
                else:
                    with open(path, 'r', encoding='utf-8') as f:
                        raw = f.read()
                    if 'Title:' in raw and 'Text:' in raw:
                        tpart = raw.split('Title:')[1]
                        title = tpart.split('Text:')[0].strip()
                        text = tpart.split('Text:')[1].strip()
                    else:
                        title = fname
                        text = raw
                    pre, elems, post = {}, {}, {}
            except Exception as e:
                print(f"Failed to read {fname}: {e}")
                continue

            combined = f"{title}. {text}"
            if include_meta:
                meta = {"file": fname, "preconditions": pre, "elements": elems, "postconditions": post}
            else:
                meta = {}

            entry = {"key": f"doc_{i}", "request": {"content": {"parts": [{"text": combined}]}}}
            if include_meta:
                entry["meta"] = meta
            records.append(entry)

        with open(jsonl_path, 'w', encoding='utf-8') as fw:
            for r in records:
                fw.write(json.dumps(r, ensure_ascii=False) + '\n')

        return jsonl_path

    def gemini_batch_embeddings_from_jsonl(self, jsonl_path, model="gemini-embedding-001", poll_interval=10):
        """Upload jsonl to Gemini, create batch embeddings job, poll until finished, download and return mapping key->embedding.
        Requires GOOGLE_API_KEY in env and google.genai installed.
        """
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("GOOGLE_API_KEY not set. Cannot run Gemini batch embeddings.")

        if not _HAS_GENAI:
            raise RuntimeError("google.genai package not available. Install 'google-genai' to use Gemini batch embeddings.")

        client = genai.Client(api_key=api_key)

        try:
            uploaded = client.files.upload(file=jsonl_path, config=types.UploadFileConfig(mime_type="jsonl"))
        except Exception as e:
            raise RuntimeError(f"Failed uploading file to Gemini: {e}")

        try:
            batch_job = client.batches.create_embeddings(
                model=model,
                src=types.EmbeddingsBatchJobSource(file_name=uploaded.name)
            )
        except Exception as e:
            raise RuntimeError(f"Failed to create embeddings batch job: {e}")

        # Poll until job finishes
        while True:
            batch_job = client.batches.get(name=batch_job.name)
            state_name = batch_job.state.name if hasattr(batch_job.state, 'name') else str(batch_job.state)
            if state_name in ('JOB_STATE_SUCCEEDED', 'JOB_STATE_FAILED', 'JOB_STATE_CANCELLED'):
                break
            print(f"Job not finished. Current state: {state_name}. Waiting {poll_interval} seconds...")
            time.sleep(poll_interval)

        if state_name != 'JOB_STATE_SUCCEEDED':
            raise RuntimeError(f"Gemini batch job ended with state {state_name}")

        # Download results
        try:
            file_content_bytes = client.files.download(file=batch_job.dest.file_name)
        except Exception as e:
            raise RuntimeError(f"Failed to download Gemini batch result file: {e}")

        try:
            file_content = file_content_bytes.decode('utf-8')
        except Exception:
            file_content = file_content_bytes if isinstance(file_content_bytes, str) else str(file_content_bytes)

        key2emb = {}
        for line in file_content.splitlines():
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            
            # Extract key. Try top-level or nested dynamically.
            key = obj.get('key') or obj.get('request', {}).get('key')
            
            # Extract embeddings. Google APIs widely use: {"response": {"embeddings": {"values": [...]}}}
            emb = None
            resp = obj.get('response', obj)
            
            if 'embeddings' in resp:
                val = resp['embeddings']
                emb = val.get('values', val) if isinstance(val, dict) else val
            elif 'embedding' in resp:
                val = resp['embedding']
                emb = val.get('values', val) if isinstance(val, dict) else val

            if key and emb is not None and isinstance(emb, list) and len(emb) > 0:
                key2emb[key] = emb

        return key2emb

    # Return the top-k nodes that have goal names most similar to the query
    def query_goals(self, query, top_k=5):
        embed_query = self.embed_text(query)
        similarities = [x[0] for x in cosine_similarity(self.goals_emb, [embed_query])]

        # Get top-k similarities (unordered)
        sim_idxs = [i for i in np.argpartition(similarities, -top_k)[-top_k:]]
        sim_values = [similarities[i] for i in sim_idxs]
        top = [self.goals_emb[i] for i in sim_idxs]

        nodes = []
        for emb in top:
            nodes.append(self.emb2node[tuple(emb)])

        return nodes, sim_values

    # Returns a list of alternative trees that can achieve the given goal
    # Assume that there's only one way to craft tools
    def dfs(self, goal, current_path=None):
        if type(goal) is str:
            goal = self.name2node[goal]
        if current_path is None:
            current_path = set()
        elif goal.name in current_path:
            return []
        current_path.add(goal.name)

        trees = []
        for preconds, elems, post in zip(goal.preconditions, goal.elements, goal.postconditions):
            mat_paths = []
            pre_subgoals = []

            if preconds != "None":
                for p in preconds:
                    if p in self.postconditions2nodes:
                        pre_subgoals += self.postconditions2nodes[p]

            if elems != "None":
                for e in elems:
                    if e in self.postconditions2nodes:
                        mat_paths.append(self.postconditions2nodes[e])
                mat_combinations = list(itertools.product(*mat_paths))
            else:
                mat_combinations = ["None"]

            for idx, mat_subgoals in enumerate(mat_combinations):
                goal_info = {
                    "description": goal.desc,
                    "aliases": goal.aliases,
                    "preconditions": preconds,
                    "elements": elems,
                    "postconditions": post,
                    "subgoals": [],
                }

                subgoals = list(mat_subgoals) + pre_subgoals
                if goal in self.goal2subgoals:
                    subgoal_edges = [x for x in self.goal2subgoals[goal] if x.subgoal in subgoals]
                else:
                    return [{goal.name: goal_info}]

                subgoal_trees = []
                for e in subgoal_edges:
                    subgoal = e.subgoal

                    goal_info["subgoals"].append({
                        "subgoal": subgoal.name,
                        "relationship_description": e.description
                    })
                    
                    results = self.dfs(subgoal, current_path.copy())
                    subgoal_trees.append(results)

                subgoal_combinations = list(itertools.product(*subgoal_trees))
                for sub_comb in subgoal_combinations:
                    tree = {}
                    tree[goal.name] = goal_info
                    # Check if a goal already exists in the tree in the loop below
                    # If yes, there's a conflict (do not need to consider two ways of achieving the same goal in one alternative, e.g. using planks to craft some sticks and bamboo to craft others)
                    # Not just if a goal already exists, but if there is a way to obtain the post-conditions of a given goal already in the tree
                    skip = False
                    for s in sub_comb:
                        for k in s:
                            # This checks if the materials used are the same if the goal already exists
                            if k in tree and tree[k] != s[k]:
                                skip = True
                                break

                            # Check the post-conditions
                            elif k not in tree:
                                for t in tree:
                                    if tree[t]["postconditions"].keys() == s[k]["postconditions"].keys():
                                        skip = True
                                        break
                            if skip:
                                break        

                        if skip:
                            break

                        tree.update(s)
                    if not skip:
                        trees.append(tree)
        return trees

if __name__ == "__main__":
    from tqdm import tqdm
    import re
    import os
    import ast
    import math

    kb = GOGKB()

    kb.build_kb()
    kb.save_kb()