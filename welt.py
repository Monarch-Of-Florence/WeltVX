import streamlit as st
import os
import time
from dotenv import load_dotenv
from PIL import Image
import weltengine 

# --- SETUP ---
load_dotenv()
APP_VERSION = "v1.2.0" 

# Load API Key
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
    except:
        pass

if not api_key:
    st.error("No API Key found! Please set GEMINI_API_KEY.")
    st.stop()

st.set_page_config(page_title=f"Welt VX {APP_VERSION}", page_icon="welt_icon.png", layout="wide")

# --- CUSTOM CSS & STYLING ---
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

            /* --- DYNAMIC SIDEBAR HEIGHT FIX --- */
            /* We restrict the chat history height so it doesn't push the input off-screen.
               calc(100vh - 250px) leaves exactly enough room for the Header (top) and Input (bottom).
            */
            section[data-testid="stSidebar"] div[data-testid="stVerticalBlockBorderWrapper"] {
                height: calc(100vh - 250px) !important;
                max-height: calc(100vh - 250px) !important;
                overflow-y: auto !important;
            }
            
            /* --- MODAL LINK STYLING --- */
            a {
                color: white !important;
                text-decoration: underline !important;
            }
        </style>
    """, unsafe_allow_html=True)

apply_cinema_style()

# --- SESSION STATE ---
if "messages" not in st.session_state: st.session_state.messages = []
if "chapters" not in st.session_state: st.session_state.chapters = []
if "video_start_time" not in st.session_state: st.session_state.video_start_time = 0
if "safety_settings" not in st.session_state:
    st.session_state.safety_settings = {
        "nsfw": False,
        "gore": False,
        "profanity": False
    }

# --- MODAL: ADVANCED SETTINGS ---
@st.dialog("⚙️ Advanced Safety Options")
def show_advanced_settings():
    st.caption("Customize the AI's content filters below.")
    
    # Checkboxes mapping to session state
    nsfw = st.checkbox("Allow NSFW Content (18+)", value=st.session_state.safety_settings["nsfw"], 
                       help="Enables analysis of nudity/sexual themes. Strictly blocks CSAM.")
    
    gore = st.checkbox("Allow Gore/Violence", value=st.session_state.safety_settings["gore"],
                       help="Enables analysis of war footage, medical procedures, or horror content.")
    
    profanity = st.checkbox("Allow Profanity", value=st.session_state.safety_settings["profanity"],
                            help="AI will not censor strong language in transcripts/responses.")

    st.divider()
    
    st.markdown("*NOTE: It is recommended to use VX assistant to moderate the video with specific guardrails.*")
    
    # The Policy Link (White & Underlined via CSS)
    st.markdown("Some type of content may be blocked even if the filters are disabled if they violate our policy. Please check our [content policy](https://ai.google.dev/gemini-api/docs/safety-guidance).")
    
    # Save & Close
    if st.button("Save Settings"):
        st.session_state.safety_settings["nsfw"] = nsfw
        st.session_state.safety_settings["gore"] = gore
        st.session_state.safety_settings["profanity"] = profanity
        st.rerun()

# --- HEADER ---
st.title("Welt VX")
st.markdown(f"*Refining Viewer Experience with Multimodal AI Agents ({APP_VERSION})*")

# --- MAIN APP ---
st.subheader("Upload Video")

MASTER_DEMO_PATH = "master_demo.webm" 
WORKING_VIDEO_PATH = "temp_video.mp4" 

uploaded_file = st.file_uploader("Drag and drop file here (Max 2GB)", type=["mp4", "mov", "avi", "webm"])

use_demo = False
if os.path.exists(MASTER_DEMO_PATH):
    use_demo = st.checkbox("Or use the pre-loaded Demo Video (Fastest)")

start_processing = False
active_video_source = None
current_video_id = ""

if uploaded_file:
    start_processing = True
    with open(WORKING_VIDEO_PATH, "wb") as f:
        f.write(uploaded_file.getbuffer())
    active_video_source = WORKING_VIDEO_PATH
    current_video_id = uploaded_file.name

elif use_demo:
    start_processing = True
    active_video_source = MASTER_DEMO_PATH
    current_video_id = "Demo_Video_Master"

if start_processing and active_video_source:
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
        
        # OPEN THE MODAL
        if st.button("⚙️ Advanced Options"):
            show_advanced_settings()

        st.divider()
        
        # 1. SUBTITLE GENERATION
        if not os.path.exists("subtitles.srt"):
            st.markdown("#### Subtitles")
            language = st.selectbox("Target Language", ["English", "Hindi", "Spanish", "German", "Japanese"])
            include_sfx = st.checkbox("Include Context/SFX", value=False)
            
            if st.button("Generate Subtitles (AI)", type="primary"):
                with st.status("🚀 Launching Welt Engine...", expanded=True) as status:
                    status.write("Analyzing audio & vision...")
                    # Pass the safety settings to the backend
                    raw_srt = weltengine.generate_subtitles_backend(
                        api_key, 
                        active_video_source, 
                        language, 
                        include_sfx,
                        # Pass settings as filters list for backend
                        user_filters=st.session_state.safety_settings 
                    )
                    
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

        # 2. SMART CHAPTERS
        st.markdown("#### Smart Chapters")
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
        else:
            if st.button("Generate Smart Chapters"):
                with st.spinner("Analyzing narrative structure..."):
                    st.session_state.chapters = weltengine.generate_smart_chapters(api_key, active_video_source)
                    st.rerun()

# --- SIDEBAR (DYNAMIC SCROLL) ---
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
        with c2:
            if st.button("🗑️"):
                st.session_state.messages = []
                st.rerun()
        
        st.divider()

        # 2. CHAT HISTORY (Math Override takes over here)
        chat_container = st.container(height=500, border=False)
        
        with chat_container:
            if not st.session_state.messages:
                st.caption("Ask me about the video...")
            
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]): 
                    st.markdown(msg["content"])

        # 3. CHAT INPUT (Pinned by CSS)
        if user_input := st.chat_input("Type here..."):
            st.session_state.messages.append({"role": "user", "content": user_input})
            
            with chat_container:
                with st.chat_message("assistant"):
                    with st.spinner("Thinking..."):
                        
                        # Get Contexts
                        current_srt = ""
                        if os.path.exists("subtitles.srt"):
                            with open("subtitles.srt", "r", encoding="utf-8") as f: current_srt = f.read()
                        
                        current_chapters = st.session_state.chapters
                        
                        # CALL ENGINE (Now passing chapters)
                        response = weltengine.vx_assistant_fix(
                            api_key, 
                            active_video_source, 
                            current_srt, 
                            current_chapters, 
                            user_input,
                            user_filters=st.session_state.safety_settings
                        )
                        
                        # --- RESPONSE ROUTER ---
                        final_msg = ""
                        
                        # CASE A: SUBTITLE PATCH
                        if response.startswith("PATCH:"):
                            clean_srt = weltengine.clean_and_repair_srt(response)
                            with open("subtitles.srt", "w", encoding="utf-8") as f: f.write(clean_srt)
                            final_msg = "✅ Subtitles updated based on your feedback."
                        
                        # CASE B: CHAPTER UPDATE
                        elif response.startswith("CHAPTERS:"):
                            raw_data = response.replace("CHAPTERS:", "").strip()
                            new_chapters = []
                            for line in raw_data.split("\n"):
                                if " - " in line:
                                    parts = line.split(" - ", 1)
                                    new_chapters.append((parts[0].strip(), parts[1].strip()))
                            
                            st.session_state.chapters = new_chapters
                            final_msg = "✅ Smart Chapters updated."

                        # CASE C: SEEK COMMAND (The "Director" Feature)
                        elif response.startswith("SEEK:"):
                            # Robust Parsing Logic
                            try:
                                # 1. Extract the raw string after "SEEK:"
                                raw_content = response.replace("SEEK:", "").strip()
                                
                                # 2. Separate Timestamp from Description
                                # Split only on the first space to keep the description intact
                                parts = raw_content.split(" ", 1) 
                                timestamp_str = parts[0].strip().replace("[", "").replace("]", "") # Remove brackets if AI added them
                                description = parts[1].strip() if len(parts) > 1 else "Jumping to scene..."
                                
                                # 3. Calculate Seconds (Handle MM:SS or H:MM:SS)
                                t_parts = timestamp_str.split(":")
                                if len(t_parts) == 3: # H:MM:SS
                                    seconds = int(t_parts[0]) * 3600 + int(t_parts[1]) * 60 + int(t_parts[2])
                                elif len(t_parts) == 2: # MM:SS
                                    seconds = int(t_parts[0]) * 60 + int(t_parts[1])
                                else:
                                    raise ValueError("Unknown format")
                                
                                # 4. Action
                                st.session_state.video_start_time = seconds
                                final_msg = f"🎥 **Jumped to {timestamp_str}**: {description}"
                                st.rerun()
                                
                            except Exception as e:
                                # Fallback: Print the error so we can see exactly what went wrong
                                final_msg = f"⚠️ Could not jump. AI sent: '{response}' (Error: {e})"

                        # CASE D: STANDARD ANSWER
                        else:
                            final_msg = response.replace("ANSWER:", "").strip()

            st.session_state.messages.append({"role": "assistant", "content": final_msg})
            st.rerun()