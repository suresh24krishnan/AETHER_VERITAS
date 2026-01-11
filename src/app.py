import os
import sys
import streamlit as st
import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv
import re

# 🛡️ PROJECT AETHER_VERITAS: PATH INJECTION & ENVIRONMENT INTEGRITY
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.append(script_dir)

# --- 🏗️ ARCHITECTURAL SELF-PROVISIONING (Cloud-Resilience Layer) ---
def ensure_logic_fabric():
    """Checks for vectors.npy/metadata.json. Re-indexes only if missing."""
    v_path = os.path.join(script_dir, "..", "data", "processed", "vectors.npy")
    m_path = os.path.join(script_dir, "..", "data", "processed", "metadata.json")
    
    if not os.path.exists(v_path) or not os.path.exists(m_path):
        # We wrap in a spinner so the UI stays clean during first-time cloud setup
        with st.spinner("🛡️ AETHER_VERITAS: Reconstructing Knowledge Fabric..."):
            try:
                from logic.indexer import AetherIndexer
                # Ensure the directory exists
                os.makedirs(os.path.dirname(v_path), exist_ok=True)
                indexer = AetherIndexer()
                indexer.run_indexing_pipeline() 
            except Exception as e:
                # Silent fallback to avoid breaking the UI
                print(f"Provisioning skipped or failed: {e}")

ensure_logic_fabric()

try:
    from logic.resolver import AetherEngine 
except ImportError as e:
    st.error(f"Critical Error: Could not find AetherEngine. {e}")
    st.stop()

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
st.set_page_config(page_title="AETHER_VERITAS Command", page_icon="🛡️", layout="wide")

# --- UI THEMING (Enhanced Visual Clarity) ---
st.markdown("""
    <style>
    .stApp { background-color: #0D1117; color: #C9D1D9; }
    [data-testid="stSidebar"] { background-color: #161B22; border-right: 1px solid #30363D; }
    
    /* Audit Card Styling */
    .audit-card { 
        background: #161B22; 
        border: 1px solid #30363D; 
        border-radius: 12px; 
        padding: 25px; 
        margin-top: 20px; 
    }
    .governed-header { 
        color: #3fb950; 
        font-size: 1.5rem; 
        font-weight: bold; 
        display: flex; 
        align-items: center; 
        gap: 10px;
    }
    .escalated-header { 
        color: #f85149; 
        font-size: 1.5rem; 
        font-weight: bold; 
        display: flex; 
        align-items: center; 
        gap: 10px;
    }
    .self-heal-badge { 
        background-color: #1f6feb; 
        color: white; 
        border-radius: 4px; 
        padding: 4px 12px; 
        font-size: 0.85rem; 
        font-weight: bold; 
        margin-bottom: 15px; 
        display: inline-block; 
    }
    </style>
    """, unsafe_allow_html=True)

@st.cache_resource
def load_engine(): return AetherEngine()
engine = load_engine()

# Initialize State
if "audit_log" not in st.session_state:
    st.session_state.audit_log = []
if "node_heat" not in st.session_state:
    st.session_state.node_heat = {}

# --- 📊 SIDEBAR ---
with st.sidebar:
    st.title("⚖️ VERITAS Hub")
    st.subheader("📈 Governance Metrics")
    
    escalated = sum(1 for l in st.session_state.audit_log if l['status'] == "ESCALATED")
    governed = sum(1 for l in st.session_state.audit_log if l['status'] == "GOVERNED")
    healed_count = sum(1 for l in st.session_state.audit_log if l.get('healed'))
    
    m1, m2 = st.columns(2)
    m1.metric("Governed", governed)
    m2.metric("Escalated", escalated)
    st.metric("Self-Healed (Global)", healed_count)
    
    st.divider()

    if st.session_state.audit_log:
        df_export = pd.DataFrame(st.session_state.audit_log)
        csv = df_export.to_csv(index=False).encode('utf-8')
        st.download_button(label="📥 Download Audit Log", data=csv, file_name="aether_veritas_audit.csv", mime="text/csv", use_container_width=True)

    st.subheader("🔥 Logic Heatmap")
    if st.session_state.node_heat:
        for node, count in sorted(st.session_state.node_heat.items(), key=lambda x: x[1], reverse=True)[:5]:
            st.markdown(f"**{node}**: {'🔥' * min(count, 5)} ({count})")
    
    if st.button("Reset Session History", use_container_width=True):
        st.session_state.audit_log = []
        st.session_state.node_heat = {}
        st.rerun()

# --- MAIN COMMAND CENTER ---
st.header("🛡️ AETHER_VERITAS: Manuscript Command Center")

tab1, tab2, tab3 = st.tabs(["🚀 Audit Portal", "📖 VERITAS FAQ", "📋 Prompt Library"])

with tab1:
    query = st.text_input("Consulting AETHER layers...", placeholder="Enter query (e.g., 'What are the CA mandatory forms?')")
    
    if st.button("Execute Governance Audit", type="primary"):
        with st.spinner("Reconciling XML Layers..."):
            search_terms = query.lower()
            if "comprehensive" in search_terms or "deductible" in search_terms:
                search_terms += " Physical Damage deductible"

            _, _, reg_data = engine.get_aether_result(search_terms) 
            _, _, glob_data = engine.get_aether_result("Global Base Layer Manuscript")
            
            regional_xml = reg_data['metadata'].get('raw_xml', "MISSING_REGIONAL")
            global_xml = glob_data['metadata'].get('raw_xml', "MISSING_GLOBAL")
            
            nodes_found = re.findall(r'name="([^"]+)"', regional_xml + global_xml)
            for n in nodes_found:
                if n.lower() in query.lower().replace(" ", ""):
                    st.session_state.node_heat[n] = st.session_state.node_heat.get(n, 0) + 1

            ticket_id = f"VRTS-{len(st.session_state.audit_log)+101}"

            system_instructions = """
            You are the AETHER_VERITAS Auditor. 
            
            - Provide a natural, free-flowing narrative.
            - If data is in Regional, explain the local rule.
            - If missing in Regional but in Global, explain the 'Self-Healing' inheritance.
            - If missing in both, trigger an 'Anti-Hallucination' escalation.
            
            End with 'RESULT: GOVERNED' or 'RESULT: DATA GAP DETECTED'.
            """

            user_prompt = f"### XML DATA ###\nRegional: {regional_xml}\nGlobal: {global_xml}\n\n### USER QUERY ###\n{query}"
            
            res = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "system", "content": system_instructions}, {"role": "user", "content": user_prompt}],
                temperature=0.0
            )
            answer = res.choices[0].message.content
            status = "ESCALATED" if "DATA GAP" in answer.upper() else "GOVERNED"

            st.session_state.audit_log.insert(0, {
                "id": ticket_id, "query": query, "status": status, 
                "healed": "(GLOBAL)" in answer.upper() or "HEALED" in answer.upper() or "INHERIT" in answer.upper(), 
                "response": answer
            })
            st.rerun()

    if st.session_state.audit_log:
        log = st.session_state.audit_log[0]
        is_governed = log['status'] == "GOVERNED"
        
        st.markdown('<div class="audit-card">', unsafe_allow_html=True)
        if is_governed:
            st.markdown(f'<div class="governed-header">✅ GOVERNED | {log["id"]}</div>', unsafe_allow_html=True)
            if log['healed']: 
                st.markdown('<div class="self-heal-badge">🛡️ AETHER: SELF-HEALED</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="escalated-header">🚨 ESCALATED | {log["id"]}</div>', unsafe_allow_html=True)
            st.markdown('<div style="color: #f85149; font-weight: bold; margin-bottom: 10px;">🛡️ ANTI-HALLUCINATION: SOURCE DATA ABSENT</div>', unsafe_allow_html=True)
        
        st.write(log['response'])
        st.markdown('</div>', unsafe_allow_html=True)

with tab2:
    st.subheader("📖 Understanding AETHER_VERITAS")
    st.markdown("""
    **AETHER_VERITAS** is a specialized governance engine that reconciles insurance rating logic against verified XML manuscripts.
    
    * **Self-Healing**: If a regional manuscript (e.g., California) is missing a standard rule, the system "heals" by inheriting logic from the **Global Base Layer**.
    * **Governed**: Confirms that a query was resolved using explicit data found in a manuscript.
    * **Escalated**: Triggered when a required data point is absent from all layers, requiring manual intervention.
    * **Anti-Hallucination**: A zero-trust protocol that ensures the AI never "guesses" or uses industry common knowledge that isn't in your specific XML.
    """)

with tab3:
    st.subheader("📋 AETHER_VERITAS Prompt Library")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### ✅ Working Scenarios (Governed)")
        governed_prompts = [
            "What is the discount for a safe driver?",
            "How much is the seismic surcharge in California?",
            "What are the mandatory forms for CA Low Income Automobile (LIA)?",
            "Is there a bundle discount for multiple accounts?",
            "Explain the income tier requirements for CA LIA.",
            "What happens if I drive more than 15,000 miles per year?",
            "What is the liability limit for Uninsured Motorist coverage?",
            "Does the multi-policy factor apply if I have 2 or more links?",
            "Calculate the total multiplier for Safe Driver + Multi-Policy.",
            "List all mandatory forms for the California region."
        ]
        for p in governed_prompts: st.code(p, language=None)
        
    with c2:
        st.markdown("#### 🛡️ Anti-Hallucination Tests (Escalated)")
        gap_prompts = [
            "What is the deductible for the base policy?",
            "What is the exact income threshold for LIA Tier A?",
            "Does the policy offer a 'Good Student Discount'?",
            "Verify coverage for 'Identity Theft' protection.",
            "Is there a 'Military Service' discount available?",
            "Check for 'Electric Vehicle' (EV) incentives in the XML.",
            "Search for 'Paperless Billing' credit nodes.",
            "Does the manuscript define 'Pet Injury' coverage limits?",
            "Verify 'Cyber Risk' surcharges in the global layer.",
            "Is there a 'Homeowner' discount in the California overlay?"
        ]
        for p in gap_prompts: st.code(p, language=None)

# --- 📜 PERSISTENT HISTORY ---
if st.session_state.audit_log:
    st.divider()
    st.subheader("📜 Audit History")
    for log in st.session_state.audit_log:
        status_icon = "🟢" if log['status'] == "GOVERNED" else "🔴"
        heal_icon = " 🛡️" if log['healed'] else ""
        with st.expander(f"{status_icon}{heal_icon} {log['id']} | {log['query']}"):
            st.write(log['response'])