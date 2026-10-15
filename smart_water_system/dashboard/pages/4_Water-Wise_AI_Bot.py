"""WaterWise AI: Water Supply & Distribution Process Explainer Bot.

Main Streamlit Application Entrypoint.
Provides an educational interface for citizens to understand water treatment,
distribution networks, pressure dynamics, and conservation guidelines.
"""

from __future__ import annotations

import os
import sys
import streamlit as st

# The existing Render service runs from smart_water_system; keep all chatbot imports scoped there.
_SYSTEM_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _SYSTEM_ROOT not in sys.path:
    sys.path.insert(0, _SYSTEM_ROOT)

from waterwise import ai_service
from waterwise import config
from waterwise import knowledge
from waterwise import prompts
from waterwise import ui

# 1. Page Configuration
# 2. Inject Design Theme
ui.render_head()

# 3. Initialize Session State
if "waterwise_messages" not in st.session_state:
    st.session_state.waterwise_messages = []

if "waterwise_pending_query" not in st.session_state:
    st.session_state.waterwise_pending_query = None

# Retrieve system configuration
api_key_configured = config.is_api_configured()
current_model = config.get_model_name()
explainer = ai_service.get_ai_service()

# 4. Sidebar Controls & Boundaries
with st.sidebar:
    st.markdown("### 🛡️ Operational Boundaries")
    st.info(
        "**Allowed Topics:**\n"
        "- Water treatment phases\n"
        "- Distribution networks\n"
        "- Hydraulic pressure causes\n"
        "- Conservation guidelines\n"
        "- Utility terminology\n\n"
        "**Strictly Prohibited:**\n"
        "- Neighborhood arrival times\n"
        "- Real-time supply tracking\n"
        "- Complaint registration\n"
        "- Service ticket creation\n"
        "- Valve / pump operations"
    )

    st.markdown("---")
    if st.button("🗑️ Clear Conversation", use_container_width=True):
        st.session_state.waterwise_messages = []
        st.session_state.waterwise_pending_query = None
        st.rerun()

    st.markdown("---")
    st.caption(
        f"WaterWise AI • Project 26\n"
        f"Municipal Services Explainer\n"
        f"Model: `{current_model}`"
    )

# 5. Hero Header & Civic Notices
ui.render_header(current_model, api_key_configured)

# 6. Interactive Educational Topic Cards
st.markdown("### 📚 Core Learning Pillars")
col1, col2, col3, col4 = st.columns(4)

cards_data = [
    (col1, "🔬 Water Treatment", "Coagulation, filtration, disinfection & clearwells.", "Explain the water treatment process."),
    (col2, "🚰 Water Distribution", "Pumping mains, balancing towers & grid looping.", "How does water distribution work?"),
    (col3, "📊 Water Pressure", "Static head, friction losses, and peak demand.", "What causes low water pressure?"),
    (col4, "🌿 Water Conservation", "Leak detection, aerators, and community habits.", "What are some water conservation tips?"),
]

for col, title, desc, sample_q in cards_data:
    with col:
        st.markdown(
            f"""
            <div class="ww-card">
                <div class="ww-card-title">{title}</div>
                <div class="ww-card-desc">{desc}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button(f"Ask AI ➔", key=f"btn_card_{title}", use_container_width=True):
            st.session_state.waterwise_pending_query = sample_q

st.markdown("<br>", unsafe_allow_html=True)

# 7. Suggested Questions (Mandatory Assignment Questions + Additional Topics)
st.markdown("### 💡 Common Citizen Questions")
st.caption("Click any question below to submit it directly to WaterWise AI:")

sug_col1, sug_col2 = st.columns(2)

with sug_col1:
    st.markdown("**Required Demonstration Queries:**")
    for req_q in prompts.REQUIRED_ASSIGNMENT_QUESTIONS:
        if st.button(f"💧 {req_q}", key=f"req_{req_q}", use_container_width=True):
            st.session_state.waterwise_pending_query = req_q

with sug_col2:
    st.markdown("**Additional Educational Topics:**")
    extra_sample = [
        "How do municipal water distribution schedules generally work?",
        "How do water utilities generally handle complaints?",
        "What is the difference between filtration and disinfection?",
        "Why are water storage reservoirs important?",
    ]
    for ext_q in extra_sample:
        if st.button(f"🔍 {ext_q}", key=f"ext_{ext_q}", use_container_width=True):
            st.session_state.waterwise_pending_query = ext_q

st.markdown("---")

# 8. Main Tabs: Conversation & Educational Knowledge Centre
tab_chat, tab_knowledge, tab_glossary = st.tabs(["💬 Assistant Chat", "📖 Knowledge Centre", "📑 Utility Glossary"])

with tab_chat:
    # Display message history
    if not st.session_state.waterwise_messages:
        st.info(
            "👋 Welcome to WaterWise AI! Select a suggested question above or type your inquiry "
            "below to learn how municipal water systems collect, purify, and distribute water."
        )

    for msg in st.session_state.waterwise_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("is_refusal"):
                st.caption("🛡️ *Application Safety Notice: Operational or local prediction request refused.*")
            elif msg.get("is_offline_ref"):
                st.caption("📘 *Curated Offline Educational Reference (No API Key Configured).*")
            elif msg.get("model"):
                st.caption(f"✨ *Generated by Gemini Flash ({msg['model']})*")

    # Handle incoming input (either from chat input or clicked question)
    user_input = st.chat_input("Ask about water treatment, distribution, pressure, or conservation...")

    query_to_process = None
    if user_input:
        query_to_process = user_input
    elif st.session_state.waterwise_pending_query:
        query_to_process = st.session_state.waterwise_pending_query
        st.session_state.waterwise_pending_query = None

    if query_to_process:
        # Add user query to conversation
        st.session_state.waterwise_messages.append({"role": "user", "content": query_to_process})
        with st.chat_message("user"):
            st.markdown(query_to_process)

        # Generate response
        with st.chat_message("assistant"):
            with st.spinner("Analyzing municipal process principles..."):
                resp = explainer.explain(
                    user_query=query_to_process,
                    chat_history=st.session_state.waterwise_messages[:-1],
                )

                # If offline and key missing, check if we have a curated offline answer
                final_content = resp.content
                is_offline_ref = False

                if not api_key_configured and not resp.is_refusal:
                    curated = knowledge.get_curated_answer(query_to_process)
                    if curated:
                        final_content = (
                            f"{curated}\n\n"
                            "> [!NOTE]\n"
                            "> *Displayed from verified offline educational reference because `GEMINI_API_KEY` is not configured.*"
                        )
                        is_offline_ref = True

                st.markdown(final_content)

                if resp.is_refusal:
                    st.caption("🛡️ *Application Safety Notice: Operational or local prediction request refused.*")
                elif is_offline_ref:
                    st.caption("📘 *Curated Offline Educational Reference.*")
                elif resp.is_live_ai:
                    st.caption(f"✨ *Generated by Gemini Flash ({resp.model_used})*")

                st.session_state.waterwise_messages.append({
                    "role": "assistant",
                    "content": final_content,
                    "is_refusal": resp.is_refusal,
                    "is_offline_ref": is_offline_ref,
                    "model": resp.model_used,
                })

        st.rerun()

with tab_knowledge:
    st.markdown("### 💧 Municipal Water Knowledge Centre")
    st.markdown(
        "Explore interactive deep dives into treatment processes, hydraulic networks, "
        "pressure engineering, and conservation methods. Available completely offline."
    )

    topic_tabs = st.tabs([f"{t.id.capitalize()}: {t.title}" for t in knowledge.TOPICS])
    for idx, topic in enumerate(knowledge.TOPICS):
        with topic_tabs[idx]:
            st.markdown(f"#### {topic.title}")
            st.markdown(f"*{topic.subtitle}*")
            st.markdown(topic.summary)

            st.markdown("**Process Flow & Hydraulic Architecture:**")
            st.code(topic.diagram_ascii, language="text")

            st.markdown("**Key Process Stages:**")
            for stage in topic.key_stages:
                with st.expander(f"📌 {stage['name']}", expanded=True):
                    st.markdown(stage["desc"])

            st.markdown("**Frequently Asked Questions:**")
            for item in topic.faq:
                with st.expander(f"❓ {item['q']}"):
                    st.markdown(item["a"])

            if st.button(f"Ask the AI about {topic.title}", key=f"know_btn_{topic.id}"):
                st.session_state.waterwise_pending_query = topic.sample_prompt
                st.rerun()

with tab_glossary:
    st.markdown("### 📑 Municipal Water Utility Glossary")
    st.markdown("Common engineering and municipal terms explained in straightforward language:")
    for item in knowledge.GLOSSARY:
        col_g1, col_g2 = st.columns([1, 3])
        with col_g1:
            st.markdown(f"**{item['term']}**")
        with col_g2:
            st.markdown(item["def"])
        st.markdown("<hr style='margin: 0.3rem 0; border-color: #f1f5f9;'>", unsafe_allow_html=True)

# 9. Civic Technology Footer
ui.render_footer()
