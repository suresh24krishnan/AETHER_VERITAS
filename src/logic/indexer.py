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
            "Global_Comprehensive": "Standard Base Policy, Theft, Stolen Vehicle, Fire, Flood, Vandalism, Glass Damage",
            "SafeDriver": "Safe Driver Discount, Clean Record, No Accidents, violation-free multiplier",
            "MultiPolicy": "linking multiple accounts, bundling discount, household bundle, multiple policies, combined insurance, cross-sell credit",
            "CA_Comprehensive": "CALIFORNIA ONLY, CA STATE RULES, California Stolen Car, Seismic Surcharge, West Coast Theft",
            "CA_Seismic_Surcharge": "California Earthquake Fee, Seismic Multiplier, Tremor Surcharge, mandatory disaster fee",
            "CA_LIA_Program": "California Low Income Automobile program, state subsidized insurance, eligibility affidavit, low-cost auto",
            "HighMileage": "15,000 miles, annual mileage limit, driving distance surcharge, high usage penalty, odometer threshold",
            "YouthfulDriver": "under 25, young driver surcharge, teen operator, student driver",
            "Uninsured_Motorist": "protection against drivers without insurance, hit and run liability",
            "Pet_Rider": "domestic animal coverage, dog injury protection, cat rider"
        }

    def chunk_xml(self, file_path, region):
        tree = ET.parse(file_path)
        chunks = []
        for node in tree.xpath(".//Coverage | .//Factor"):
            name = node.get('name', 'Unnamed')
            raw_xml = ET.tostring(node, encoding='unicode', pretty_print=True)
            lookup_key = f"{region}_{name}" if f"{region}_{name}" in self.semantic_bridge else name
            synonyms = self.semantic_bridge.get(lookup_key, "General Insurance Concept")
            
            searchable_text = f"DOMAIN: Insurance | REGION: {region} | TECHNICAL_ID: {name} | HUMAN_INTENT: {synonyms}"
            
            chunks.append({
                "id": f"{region}_{name}",
                "text": searchable_text, 
                "metadata": {
                    "region": region, 
                    "name": name, 
                    "synonyms": synonyms,
                    "raw_xml": raw_xml 
                }
            })
        return chunks

    def re_index_node(self, node_name, user_intent):
        """
        🚀 TARGETED SELF-HEALING:
        Updates specific node text and regenerates its specific vector.
        """
        if not os.path.exists(self.metadata_path) or not os.path.exists(self.vectors_path):
            return False

        with open(self.metadata_path, 'r') as f:
            all_chunks = json.load(f)
        vectors = np.load(self.vectors_path)

        updated_index = -1
        for i, chunk in enumerate(all_chunks):
            if chunk['metadata']['name'] == node_name:
                chunk['text'] += f" | HEALED_INTENT: {user_intent}"
                updated_index = i
                break

        if updated_index != -1:
            # Re-generate embedding for ONLY this updated text
            response = self.client.embeddings.create(
                input=all_chunks[updated_index]['text'], 
                model="text-embedding-3-small"
            )
            new_vector = response.data[0].embedding
            
            # Replace in vector array and save
            vectors[updated_index] = new_vector
            np.save(self.vectors_path, vectors)
            
            with open(self.metadata_path, 'w') as f:
                json.dump(all_chunks, f, indent=2)
            
            return True
        return False

    def run(self, files_config):
        all_chunks = []
        for region, path in files_config.items():
            if not os.path.exists(path): continue
            all_chunks.extend(self.chunk_xml(path, region))

        texts = [c['text'] for c in all_chunks]
        response = self.client.embeddings.create(input=texts, model="text-embedding-3-small")
        vectors = [data.embedding for data in response.data]

        os.makedirs("data/processed", exist_ok=True)
        np.save(self.vectors_path, np.array(vectors))
        with open(self.metadata_path, "w") as f:
            json.dump(all_chunks, f, indent=2)
            
        print("✅ Indexing Complete. Metadata and Vectors synchronized.")

if __name__ == "__main__":
    indexer = AetherIndexer()
    indexer.run({
        "Global": "data/manuscripts/global_base.xml", 
        "CA": "data/manuscripts/ca_overlay.xml"
    })