import streamlit as st
import os
import time
from dotenv import load_dotenv
from PIL import Image
import weltengine 

# --- SETUP ---
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if os.path.exists("welt_icon.png"):
    icon = Image.open("welt_icon.png")
else:
    icon = "🌏"

st.set_page_config(page_title="Welt VX", page_icon=icon, layout="wide")

def apply_cinema_style():
    st.markdown("""
        <style>
            .stApp { background-color: #000000; }
            /* Video Player Styling */
            [data-testid="stVideo"] {
                border: 1px solid #333;
                border-radius: 12px;
                box-shadow: 0px 0px 20px rgba(229, 9, 20, 0.3);
                transition: transform 0.3s ease;
            }
            [data-testid="stVideo"]:hover {
                box-shadow: 0px 0px 30px rgba(229, 9, 20, 0.6);
                transform: scale(1.01);
            }
            h3 { color: #e50914 !important; font-weight: 300; margin-bottom: 5px; }
            .block-container { padding-top: 2rem; }
            
            /* Buttons & Chat */
            div.stButton > button { width: 100%; border: 1px solid #333; }
            div.stButton > button:hover { border-color: #e50914; color: #e50914; }
            [data-testid="stChatMessage"] { background-color: #1a1a1a; border-radius: 10px; }
            [data-testid="stChatInput"] { position: fixed; bottom: 20px; }
        </style>
    """, unsafe_allow_html=True)

apply_cinema_style()

# --- SESSION STATE ---
if "messages" not in st.session_state: st.session_state.messages = []
if "chapters" not in st.session_state: st.session_state.chapters = []
if "video_start_time" not in st.session_state: st.session_state.video_start_time = 0

# --- HEADER ---
st.title("Welt VX")
st.markdown("*The Multimodal AI Subtitle Agent (Powered by Gemini 3)*")

# --- MAIN APP ---
video_file = st.file_uploader("Upload Video (Max 2GB)", type=["mp4", "mov", "avi", "webm"])

if video_file:
    # 1. ZOMBIE FIX & RESET
    if "last_video_name" not in st.session_state:
        st.session_state["last_video_name"] = ""

    if video_file.name != st.session_state["last_video_name"]:
        if os.path.exists("subtitles.srt"): os.remove("subtitles.srt")
        st.session_state.messages = [] 
        st.session_state.chapters = [] 
        st.session_state.video_start_time = 0 
        st.session_state["last_video_name"] = video_file.name
        st.rerun()

    # 2. Save Video
    with open("temp_video.mp4", "wb") as f:
        f.write(video_file.getbuffer())

    # 3. Layout
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("### Your Video") 
        # Video Player with Dynamic Start Time for Chapters
        subs_path = "subtitles.srt" if os.path.exists("subtitles.srt") else None
        st.video(video_file, subtitles=subs_path, start_time=st.session_state.video_start_time)

    with col2:
        st.markdown("### ⚙️ Control Deck")
        
        # SCENARIO A: No Subtitles Yet (Initial Generation)
        if not os.path.exists("subtitles.srt"):
            language = st.selectbox("Target Language", ["English", "Hindi", "Spanish", "Japanese", "German"])
            
            c1, c2 = st.columns(2)
            with c1: include_sfx = st.checkbox("Context/SFX", value=False, help="[Laughs], [Applause]")
            with c2: include_chapters = st.checkbox("Smart Chapters", value=False, help="Generate Table of Contents")

            if st.button("Generate Subtitles (AI)", type="primary"):
                if not api_key: st.error("❌ API Key missing!"); st.stop()
                
                with st.status("🚀 Launching Welt Engine...", expanded=True) as status:
                    # A. Subtitles
                    status.write("☁️ Uploading & Analyzing Video...")
                    raw_srt = weltengine.generate_subtitles_backend(api_key, "temp_video.mp4", language, include_sfx)
                    
                    # B. Chapters
                    if include_chapters:
                        status.write("📑 Generating Smart Chapters...")
                        st.session_state.chapters = weltengine.generate_smart_chapters(api_key, "temp_video.mp4")
                    
                    # C. Validation
                    if "Error" in raw_srt:
                        status.update(label="Generation Failed", state="error")
                        st.error(raw_srt)
                    else:
                        status.write("🧹 Polishing subtitles...")
                        final_srt = weltengine.clean_and_repair_srt(raw_srt)
                        with open("subtitles.srt", "w", encoding="utf-8") as f: f.write(final_srt)
                        status.update(label="Done!", state="complete", expanded=False)
                        st.rerun()
        
        # SCENARIO B: Subtitles Exist (Active Mode)
        else:
            st.success("✅ Subtitles Active")
            
            # --- NEW FEATURE: Add Chapters Later ---
            if not st.session_state.chapters:
                if st.button("➕ Add Smart Chapters"):
                     if not api_key: st.error("❌ API Key missing!"); st.stop()
                     with st.status("📑 Analyzing Scenes...", expanded=True) as status:
                         st.session_state.chapters = weltengine.generate_smart_chapters(api_key, "temp_video.mp4")
                         status.update(label="Chapters Added!", state="complete", expanded=False)
                         st.rerun()
            # ---------------------------------------

            # --- SMART CHAPTERS DISPLAY ---
            if st.session_state.chapters:
                st.markdown("### 📑 Smart Chapters")
                for timestamp, title in st.session_state.chapters:
                    parts = timestamp.split(":")
                    seconds = int(parts[0]) * 60 + int(parts[1])
                    if st.button(f"⏱️ {timestamp} - {title}"):
                        st.session_state.video_start_time = seconds
                        st.rerun()
                st.divider()

            with open("subtitles.srt", "r", encoding="utf-8") as f:
                st.download_button("Download .SRT", f, file_name="welt_subs.srt")
            
            if st.button("🗑️ Reset / Start Over"):
                os.remove("subtitles.srt")
                st.session_state.messages = []
                st.session_state.chapters = []
                st.session_state.video_start_time = 0
                st.rerun()

# --- VX ASSISTANT SIDEBAR ---
if os.path.exists("subtitles.srt"):
    with st.sidebar:
        st.markdown("### 🤖 VX Assistant")
        st.caption("I can see the video! Ask me questions or tell me to fix errors.")
        st.divider()

        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]): st.markdown(msg["content"])

        if user_input := st.chat_input("Ex: 'What is he holding?' OR 'Fix typo at 00:05'"):
            st.session_state.messages.append({"role": "user", "content": user_input})
            with st.chat_message("user"): st.markdown(user_input)

            with st.chat_message("assistant"):
                with st.status("🧠 Analyzing...", expanded=True) as status:
                    with open("subtitles.srt", "r", encoding="utf-8") as f: current_srt = f.read()
                    
                    ai_response = weltengine.vx_assistant_fix(api_key, "temp_video.mp4", current_srt, user_input)
                    
                    if ai_response.startswith("PATCH:"):
                        clean_srt = weltengine.clean_and_repair_srt(ai_response)
                        if "Error" in clean_srt:
                            status.update(label="Patch Failed", state="error")
                            final_msg = f"I tried to fix it, but failed: {clean_srt}"
                        else:
                            with open("subtitles.srt", "w", encoding="utf-8") as f: f.write(clean_srt)
                            status.update(label="Subtitles Updated!", state="complete", expanded=False)
                            final_msg = "✅ Fix applied. Refreshing player..."
                            time.sleep(1); st.rerun()
                    
                    elif ai_response.startswith("ANSWER:"):
                        final_msg = ai_response.replace("ANSWER:", "").strip()
                        status.update(label="Answer Ready", state="complete", expanded=False)
                    
                    else:
                        final_msg = ai_response
                        status.update(label="Response Received", state="complete")
                
                st.markdown(final_msg)
            st.session_state.messages.append({"role": "assistant", "content": final_msg})