import streamlit as st
import os
import time
from dotenv import load_dotenv
from PIL import Image
import weltengine 

# --- SETUP ---
load_dotenv()
APP_VERSION = "v1.1.0"

# 1. Load API Key
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
    except:
        pass

if not api_key:
    st.error("No API Key found! Please set GEMINI_API_KEY.")
    st.stop()

# Icon setup
if os.path.exists("welt_icon.png"):
    icon = Image.open("welt_icon.png")
else:
    icon = "🌏"

st.set_page_config(page_title=f"Welt VX {APP_VERSION}", page_icon=icon, layout="wide")

def apply_cinema_style():
    st.markdown("""
        <style>
            .stApp { background-color: #000000; }
            
            /* Video Player Styling */
            [data-testid="stVideo"] {
                border: 1px solid #333;
                border-radius: 12px;
                box-shadow: 0px 0px 20px rgba(229, 9, 20, 0.3);
            }
            h3 { color: #e50914 !important; font-weight: 300; margin-bottom: 5px; }
            .block-container { padding-top: 2rem; }
            
            /* Buttons */
            div.stButton > button { width: 100%; border: 1px solid #333; }
            div.stButton > button:hover { border-color: #e50914; color: #e50914; }
            
            /* Chat Bubbles */
            [data-testid="stChatMessage"] { background-color: #1a1a1a; border-radius: 10px; }
            
            /* PIN THE CLOSE ARROW */
            [data-testid="stSidebarCollapseButton"] {
                position: fixed !important;
                top: 1rem !important;
                left: 1rem !important;
                z-index: 100000 !important;
                background-color: rgba(0,0,0,0.8) !important;
                border: 1px solid #333;
                border-radius: 50%;
                width: 2.5rem; 
                height: 2.5rem;
                display: flex;
                align-items: center;
                justify-content: center;
            }
        </style>
    """, unsafe_allow_html=True)

apply_cinema_style()

# --- SESSION STATE ---
if "messages" not in st.session_state: st.session_state.messages = []
if "chapters" not in st.session_state: st.session_state.chapters = []
if "video_start_time" not in st.session_state: st.session_state.video_start_time = 0

# --- HEADER ---
st.title("Welt VX")
st.markdown(f"*The Multimodal AI Subtitle Agent ({APP_VERSION})*")

# --- MAIN APP ---
st.subheader("Upload Video")

MASTER_DEMO_PATH = "master_demo.webm" 
WORKING_VIDEO_PATH = "temp_video.mp4" 

uploaded_file = st.file_uploader("Drag and drop file here (Max 2GB)", type=["mp4", "mov", "avi", "webm"])

use_demo = False
if os.path.exists(MASTER_DEMO_PATH):
    use_demo = st.checkbox("Or use the pre-loaded Demo Video (Fastest)")
else:
    st.info(f"ℹ️ Demo file '{MASTER_DEMO_PATH}' not found.")

start_processing = False
active_video_source = None
current_video_id = ""

if uploaded_file:
    start_processing = True
    with open(WORKING_VIDEO_PATH, "wb") as f:
        f.write(uploaded_file.getbuffer())
    active_video_source = WORKING_VIDEO_PATH
    current_video_id = uploaded_file.name
    st.toast(f"✅ Uploaded: {uploaded_file.name}")

elif use_demo:
    start_processing = True
    active_video_source = MASTER_DEMO_PATH
    current_video_id = "Demo_Video_Master"
    st.toast("✅ Using Master Demo Video")

if start_processing and active_video_source:
    # RESET LOGIC
    if "last_video_id" not in st.session_state:
        st.session_state["last_video_id"] = ""

    if current_video_id != st.session_state["last_video_id"]:
        if os.path.exists("subtitles.srt"): os.remove("subtitles.srt")
        st.session_state.messages = [] 
        st.session_state.chapters = [] 
        st.session_state.video_start_time = 0 
        st.session_state["last_video_id"] = current_video_id
        st.rerun()

    # LAYOUT
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("### Your Video") 
        subs_path = "subtitles.srt" if os.path.exists("subtitles.srt") else None
        st.video(active_video_source, subtitles=subs_path, start_time=st.session_state.video_start_time)

    with col2:
        st.markdown("### ⚙️ Control Deck")
        
        # 1. SUBTITLE GENERATION
        if not os.path.exists("subtitles.srt"):
            st.markdown("#### Subtitles")
            language = st.selectbox("Target Language", ["English", "Hindi", "Spanish", "German", "Japanese"])
            include_sfx = st.checkbox("Include Context/SFX", value=False)
            
            if st.button("Generate Subtitles (AI)", type="primary"):
                with st.status("🚀 Launching Welt Engine...", expanded=True) as status:
                    status.write("Analyzing audio & vision...")
                    raw_srt = weltengine.generate_subtitles_backend(api_key, active_video_source, language, include_sfx)
                    
                    if "Error" in raw_srt:
                        status.update(label="Failed", state="error")
                        st.error(raw_srt)
                    else:
                        status.write("Polishing...")
                        final_srt = weltengine.clean_and_repair_srt(raw_srt)
                        with open("subtitles.srt", "w", encoding="utf-8") as f: f.write(final_srt)
                        status.update(label="Done!", state="complete", expanded=False)
                        st.rerun()
        else:
            st.success("✅ Subtitles Active")
            with open("subtitles.srt", "r", encoding="utf-8") as f:
                st.download_button("Download .SRT", f, file_name="welt_subs.srt")
            
            if st.button("🗑️ Delete Subtitles & Reset"):
                os.remove("subtitles.srt")
                st.rerun()

        st.divider()

        # 2. SMART CHAPTERS (Independent Feature)
        st.markdown("#### Smart Chapters")
        
        # If chapters exist, show them
        if st.session_state.chapters:
            for timestamp, title in st.session_state.chapters:
                parts = timestamp.split(":")
                seconds = int(parts[0]) * 60 + int(parts[1])
                if st.button(f"⏱️ {timestamp} - {title}"):
                    st.session_state.video_start_time = seconds
                    st.rerun()
            
            if st.button("Refresh Chapters"):
                st.session_state.chapters = []
                st.rerun()
        
        # If no chapters, show Generate button
        else:
            if st.button("Generate Smart Chapters"):
                with st.spinner("Analyzing narrative structure..."):
                    st.session_state.chapters = weltengine.generate_smart_chapters(api_key, active_video_source)
                    st.rerun()

# --- SIDEBAR (FIXED CHAT LAYOUT) ---
if active_video_source:
    with st.sidebar:
        # 1. TOP ACTION BAR (Static)
        st.markdown("### VX Assistant")
        
        c1, c2 = st.columns([3, 1])
        with c1:
            with st.popover("Safety Scanner"):
                safety_tag = st.text_input("Search for content:")
                if st.button("Scan"):
                    if safety_tag:
                        st.session_state.messages.append({"role": "user", "content": f"SCAN: {safety_tag}"})
                        # Logic handled at bottom to prevent layout jumping
        with c2:
            if st.button("🗑️"):
                st.session_state.messages = []
                st.rerun()
        
        st.divider()

        # 2. CHAT HISTORY CONTAINER (Scrollable)
        # This fixes the "answer below input" issue by containing messages in a fixed box
        chat_container = st.container(height=400, border=False)
        
        with chat_container:
            if not st.session_state.messages:
                st.caption("Ask me about the video...")
            
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]): 
                    st.markdown(msg["content"])

        # 3. CHAT INPUT (Pinned Bottom)
        if user_input := st.chat_input("Type here..."):
            # A. Add User Message
            st.session_state.messages.append({"role": "user", "content": user_input})
            
            # B. Generate Response IMMEDIATELY
            with chat_container: # Display loading INSIDE container
                with st.chat_message("assistant"):
                    with st.spinner("Thinking..."):
                        current_srt = ""
                        if os.path.exists("subtitles.srt"):
                            with open("subtitles.srt", "r", encoding="utf-8") as f: current_srt = f.read()
                        
                        # Call Engine
                        response = weltengine.vx_assistant_fix(api_key, active_video_source, current_srt, user_input)
                        
                        # Handle Patches
                        if response.startswith("PATCH:"):
                            clean_srt = weltengine.clean_and_repair_srt(response)
                            with open("subtitles.srt", "w", encoding="utf-8") as f: f.write(clean_srt)
                            final_msg = "✅ Subtitles updated based on your feedback."
                        else:
                            final_msg = response.replace("ANSWER:", "").strip()

            # C. Save AI Message & Rerun
            st.session_state.messages.append({"role": "assistant", "content": final_msg})
            st.rerun() # This forces the layout to redraw perfectly with the new message inside the box