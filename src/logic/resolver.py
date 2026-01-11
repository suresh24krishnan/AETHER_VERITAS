import os
import json
import numpy as np
import lxml.etree as ET
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class AetherIndexer:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.metadata_path = "data/processed/metadata.json"
        self.vectors_path = "data/processed/vectors.npy"
        
        self.semantic_bridge = {
            "Global_Base_Comprehensive": "Standard Base Policy, theft, fire, $500 deductible, master rules",
            "CA_Comprehensive": "CALIFORNIA ONLY, seismic surcharge, regional physical damage",
            "Governance_Rules": "Effective dates, Factor Precedence, Global Discount Caps, system metadata"
        }

    def _expand_synonyms(self, technical_id, xml_content):
        try:
            prompt = f"Identify insurance synonyms for: '{technical_id}'. XML: {xml_content[:300]}. Format: CSV list only."
            res = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100, temperature=0.3
            )
            return res.choices[0].message.content
        except: return "General Insurance"

    def chunk_xml(self, file_path, region):
        tree = ET.parse(file_path)
        chunks = []
        # 🛡️ SENTINEL UPDATE: Broadened XPath to see Governance_Rules and LOB_Configuration
        query = ".//Coverage | .//Factor | .//Governance_Rules | .//LOB_Configuration"
        
        for node in tree.xpath(query):
            name = node.get('name', node.tag) # Fallback to tag name for metadata nodes
            inherits = node.get('inheritsFrom', None)
            raw_xml = ET.tostring(node, encoding='unicode', pretty_print=True)
            
            lookup_key = f"{region}_{name}"
            static_keywords = self.semantic_bridge.get(lookup_key, self.semantic_bridge.get(name, "General Coverage"))
            dynamic_keywords = self._expand_synonyms(name, raw_xml)
            
            searchable_text = f"REGION: {region} | TAG: {node.tag} | ID: {name} | INTENT: {static_keywords} | COLLOQUIAL: {dynamic_keywords}"
            
            chunks.append({
                "id": f"{region}_{node.tag}_{name}",
                "text": searchable_text, 
                "metadata": {
                    "region": region, 
                    "name": name, 
                    "tag": node.tag,
                    "inheritsFrom": inherits,
                    "raw_xml": raw_xml 
                }
            })
        return chunks

    def run(self, files_config):
        all_chunks = []
        for region, path in files_config.items():
            if not os.path.exists(path): continue
            print(f"📂 Ingesting: {region}")
            all_chunks.extend(self.chunk_xml(path, region))

        texts = [c['text'] for c in all_chunks]
        response = self.client.embeddings.create(input=texts, model="text-embedding-3-small")
        vectors = [d.embedding for d in response.data]

        os.makedirs("data/processed", exist_ok=True)
        np.save(self.vectors_path, np.array(vectors))
        with open(self.metadata_path, "w") as f:
            json.dump(all_chunks, f, indent=2)
        print("✅ Indexing Complete.")

class AetherEngine:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.metadata_path = "data/processed/metadata.json"
        self.vectors_path = "data/processed/vectors.npy"
        
        with open(self.metadata_path, "r") as f:
            self.metadata = json.load(f)
        self.vectors = np.load(self.vectors_path)

    def _get_parent_node(self, parent_name):
        for entry in self.metadata:
            m = entry['metadata']
            if m.get('name') == parent_name and m.get('region') in ['Global', 'Global_Base']:
                return entry
        return None

    def get_aether_result(self, query, threshold=0.30):
        resp = self.client.embeddings.create(input=[query], model="text-embedding-3-small")
        q_vec = np.array(resp.data[0].embedding)
        
        sims = np.dot(self.vectors, q_vec) / (np.linalg.norm(self.vectors, axis=1) * np.linalg.norm(q_vec))
        idx = np.argmax(sims)
        score = float(sims[idx])

        # 🚨 SENTINEL JIRA TRIGGER: Explicitly flag for ticket creation if low score
        if score < threshold:
            return "ESCALATED", score, {
                "id": "JIRA-PENDING",
                "metadata": {
                    "name": "GAP_DETECTED", 
                    "raw_xml": "STATUS: No relevant policy found. Action: Create Ticket VRTS."
                }
            }

        result_node = self.metadata[idx]
        inherits_from = result_node['metadata'].get('inheritsFrom')
        
        # 🛡️ SELF-HEALING & LINEAGE INJECTION
        if inherits_from:
            parent_entry = self._get_parent_node(inherits_from)
            if parent_entry:
                combined_xml = (
                    f"### DATA_SOURCE_LINEAGE ###\n\n"
                    f"[[ SOURCE_A: GLOBAL_BASE_LAYER ]]\n"
                    f"ENTITY: {inherits_from}\n"
                    f"CONTENT:\n{parent_entry['metadata'].get('raw_xml')}\n\n"
                    f"[[ SOURCE_B: REGIONAL_OVERLAY ]]\n"
                    f"ENTITY: {result_node['metadata']['name']}\n"
                    f"REGION: {result_node['metadata']['region']}\n"
                    f"CONTENT:\n{result_node['metadata'].get('raw_xml')}\n\n"
                    f"### END_LINEAGE_DATA ###"
                )
                
                healed_data = {"id": result_node["id"], "metadata": result_node["metadata"].copy()}
                healed_data['metadata']['raw_xml'] = combined_xml
                return "SUCCESS", 1.0, healed_data

        return "SUCCESS", score, result_node