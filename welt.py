import streamlit as st
import os
import time
from dotenv import load_dotenv
from PIL import Image
import weltengine 

# --- SETUP ---
load_dotenv()

api_key = None

# 1. Try loading from local .env file first
api_key = os.getenv("GEMINI_API_KEY")

# 2. If not found locally, try Streamlit Cloud Secrets
if not api_key:
    try:
        # This will only work on Streamlit Cloud
        api_key = st.secrets["GEMINI_API_KEY"]
    except FileNotFoundError:
        pass
    except Exception:
        pass

# 3. Final Check
if not api_key:
    st.error("No API Key found! Please set GEMINI_API_KEY in .env or Streamlit Secrets.")
    st.stop()

# Icon setup
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
st.subheader("Upload Video")

# 1. Define File Paths
MASTER_DEMO_PATH = "master_demo.webm"  # The permanent file (Must be in repo)
WORKING_VIDEO_PATH = "temp_video.mp4" # The active processing file

# 2. Standard Upload
uploaded_file = st.file_uploader("Drag and drop file here (Max 2GB)", type=["mp4", "mov", "avi", "webm"])

# 3. "Use Demo" Checkbox (Only if master file exists)
use_demo = False
if os.path.exists(MASTER_DEMO_PATH):
    use_demo = st.checkbox("Or use the pre-loaded Demo Video (Fastest)")
else:
    st.info(f"ℹ️ To use Demo Mode, rename your demo video to '{MASTER_DEMO_PATH}' and upload it to the project folder.")

# 4. Determine Active Source
start_processing = False
active_video_source = None
current_video_id = ""

if uploaded_file:
    start_processing = True
    # Save the upload to the WORKING path
    with open(WORKING_VIDEO_PATH, "wb") as f:
        f.write(uploaded_file.getbuffer())
    active_video_source = WORKING_VIDEO_PATH
    current_video_id = uploaded_file.name
    st.toast(f"✅ Uploaded: {uploaded_file.name}")

elif use_demo:
    start_processing = True
    # Just point to the MASTER path (Don't overwrite it!)
    active_video_source = MASTER_DEMO_PATH
    current_video_id = "Demo_Video_Master"
    st.toast("✅ Using Master Demo Video")

# 5. Main Logic
if start_processing and active_video_source:
    # A. ZOMBIE FIX & RESET
    if "last_video_id" not in st.session_state:
        st.session_state["last_video_id"] = ""

    if current_video_id != st.session_state["last_video_id"]:
        if os.path.exists("subtitles.srt"): os.remove("subtitles.srt")
        st.session_state.messages = [] 
        st.session_state.chapters = [] 
        st.session_state.video_start_time = 0 
        st.session_state["last_video_id"] = current_video_id
        st.rerun()

    # B. Layout
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("### Your Video") 
        # Video Player with Dynamic Start Time for Chapters
        subs_path = "subtitles.srt" if os.path.exists("subtitles.srt") else None
        
        # KEY FIX: Using the dynamic variable
        st.video(active_video_source, subtitles=subs_path, start_time=st.session_state.video_start_time)

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
                    # KEY FIX: Pass active_video_source
                    raw_srt = weltengine.generate_subtitles_backend(api_key, active_video_source, language, include_sfx)
                    
                    # B. Chapters
                    if include_chapters:
                        status.write("📑 Generating Smart Chapters...")
                        st.session_state.chapters = weltengine.generate_smart_chapters(api_key, active_video_source)
                    
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
                         st.session_state.chapters = weltengine.generate_smart_chapters(api_key, active_video_source)
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

# --- VX ASSISTANT SIDEBAR (UPDATED) ---
# Show sidebar as soon as a video is loaded
if active_video_source:
    with st.sidebar:
        st.markdown("### 🤖 VX Assistant")
        st.caption("I can see the video! Ask me questions or use the scanner.")
        st.divider()

        # --- 🛡️ NEW: CONTENT SAFETY SCANNER ---
        with st.expander("Content Safety Scan", expanded=False):
            st.caption("Check for specific content (e.g., spiders, blood, flashing lights).")
            safety_tag = st.text_input("Tag to search for:", placeholder="Ex: Spiders")
            
            if st.button("Run Safety Scan"):
                if safety_tag:
                    # 1. Add User's "Action" to chat history
                    prompt = f"Scan this video strictly for the presence of '{safety_tag}'. If present, provide timestamps. If not, confirm it is safe."
                    st.session_state.messages.append({"role": "user", "content": f"🔍 SCAN REQUEST: {safety_tag}"})
                    
                    # 2. Trigger the Assistant (Displaying a loading status)
                    with st.status(f"🕵️ Scanning for '{safety_tag}'...", expanded=True):
                         # Safe read of subtitles if they exist
                        current_srt = ""
                        if os.path.exists("subtitles.srt"):
                            with open("subtitles.srt", "r", encoding="utf-8") as f: current_srt = f.read()
                        
                        # Call Engine with ACTIVE source
                        response = weltengine.vx_assistant_fix(api_key, active_video_source, current_srt, prompt)
                        st.write(response)

                    # 3. Save result and refresh
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    st.rerun()
        
        st.divider()
        # ---------------------------------------

        # --- 💬 CHAT HISTORY (COLLAPSIBLE) ---
        with st.expander("💬 Chat History", expanded=True):
            if not st.session_state.messages:
                st.caption("No messages yet.")
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]): st.markdown(msg["content"])
        
        # --- CHAT INPUT (FIXED) ---
        if user_input := st.chat_input("Ex: 'What is he holding?' OR 'Fix typo at 00:05'"):
            st.session_state.messages.append({"role": "user", "content": user_input})
            # Force expand history to show new message
            with st.sidebar:
                with st.chat_message("user"): st.markdown(user_input)

            with st.chat_message("assistant"):
                with st.status("🧠 Analyzing...", expanded=True) as status:
                    
                    # SAFE READ
                    current_srt = ""
                    if os.path.exists("subtitles.srt"):
                        with open("subtitles.srt", "r", encoding="utf-8") as f: 
                            current_srt = f.read()
                    else:
                        current_srt = "(No subtitles generated yet)"
                    
                    # Call Engine with ACTIVE source
                    ai_response = weltengine.vx_assistant_fix(api_key, active_video_source, current_srt, user_input)
                    
                    # LOGIC: Check if it's a FIX (Patch) or a QUESTION (Answer)
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
                        # Fallback for general conversation
                        final_msg = ai_response
                        status.update(label="Response Received", state="complete")
                
                # We don't need to print here because rerunning updates the expander,
                # but for immediate feedback we append to state
            st.session_state.messages.append({"role": "assistant", "content": final_msg})
            st.rerun()