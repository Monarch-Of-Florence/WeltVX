import streamlit as st
import os
import time
from dotenv import load_dotenv
import weltengine 

# --- SETUP ---
load_dotenv()
APP_VERSION = "v1.4.7" # Minimalist Icon Update

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

# --- CUSTOM CSS ---
def apply_studio_style():
    st.markdown("""
        <style>
            .stApp { background-color: #0e0e0e; color: #e5e5e5; }
            
            /* --- 1. ALERT BLOCKS --- */
            div[data-testid="stAlert"] {
                background-color: #082a10 !important;
                border: 1px solid #1a5c20 !important;
                border-left: 5px solid #46d369 !important;
                color: #ffffff !important;
                border-radius: 8px;
            }
            div[data-testid="stAlert"] > div, div[data-testid="stAlert"] p {
                color: #ffffff !important;
            }
            div[data-testid="stAlert"] svg {
                fill: #46d369 !important;
                color: #46d369 !important;
            }

            /* --- 2. INPUT FOCUS --- */
            input:focus, textarea:focus, div[data-baseweb="select"] > div:focus-within {
                border-color: #46d369 !important;
                box-shadow: 0 0 0 1px #46d369 !important;
            }

            /* --- 3. UI ELEMENTS --- */
            .control-deck {
                background-color: #161616;
                padding: 15px;
                border-radius: 12px;
                border: 1px solid #333;
                margin-top: 10px;
            }
            div[data-testid="stButton"] button {
                border-radius: 8px;
                font-weight: 600;
                border: 1px solid #333;
                background-color: #1a1a1a;
                color: white;
                transition: all 0.2s;
            }
            div[data-testid="stButton"] button:hover {
                border-color: #46d369;
                color: #46d369;
                background-color: #0d1f0d;
            }
            
            /* Primary Button (Netflix Red / Green Logic) */
            div[data-testid="stButton"] button[kind="primary"] {
                background-color: #E50914; 
                border-color: #E50914;
                color: white;
            }
            div[data-testid="stButton"] button[kind="primary"]:hover {
                background-color: #b00610;
                border-color: #b00610;
            }
            
            /* --- 4. MATERIAL ICONS (ADDED: Force No Blue) --- */
            span[data-testid="stIconMaterial"] {
                color: inherit !important;
            }
            
            /* Link Styling */
            a.policy-link { color: #46d369 !important; text-decoration: underline !important; font-weight: bold; }
            
            /* Video Player Styling */
            [data-testid="stVideo"] { 
                border-radius: 12px; 
                border: 1px solid #1a1a1a; 
                box-shadow: 0px 5px 30px rgba(70, 211, 105, 0.15); 
            }
            
            /* Spinner */
            .stSpinner > div { border-top-color: #E50914 !important; }
        </style>
    """, unsafe_allow_html=True)

apply_studio_style()

# --- SESSION STATE ---
if "messages" not in st.session_state: st.session_state.messages = []
if "chapters" not in st.session_state: st.session_state.chapters = []
if "video_start_time" not in st.session_state: st.session_state.video_start_time = 0
if "show_assistant" not in st.session_state: st.session_state.show_assistant = False 
if "last_video_id" not in st.session_state: st.session_state.last_video_id = ""
if "form_reset_id" not in st.session_state: st.session_state.form_reset_id = 0 
if "safety_settings" not in st.session_state:
    st.session_state.safety_settings = {"nsfw": False, "gore": False, "profanity": False}

# --- MODAL 1: SUBTITLE STUDIO ---
@st.dialog("Subtitle Generator") # Removed Emoji
def open_subtitle_window():
    st.caption("Configure generation settings")
    c1, c2 = st.columns([2, 1])
    with c1:
        lang = st.selectbox("Target Language", ["English", "Hindi", "Japanese", "Spanish", "German"])
    with c2:
        st.write("") 
        st.write("") 
        sfx = st.checkbox("Include SFX", value=False, help="Include [Context] and [Sound Effects]")
    
    st.divider()
    
    # Updated Icon
    if st.button(":material/bolt: Generate Subtitles", type="primary", use_container_width=True):
        if "active_video_path" in st.session_state:
            with st.spinner("Initializing Agent..."):
                res = weltengine.generate_subtitles_backend(
                    api_key, 
                    st.session_state.active_video_path, 
                    lang, 
                    sfx, 
                    user_filters=st.session_state.safety_settings
                )
                final_srt = weltengine.clean_and_repair_srt(res)
                with open("subtitles.srt", "w", encoding="utf-8") as f: f.write(final_srt)
                st.rerun()
        else:
            st.error("Video source not found.")

# --- MODAL 2: ADVANCED OPTIONS ---
@st.dialog("Advanced Safety") # Removed Emoji
def open_advanced_options():
    st.caption("Global Content Filters")
    
    form_key = f"safety_form_{st.session_state.form_reset_id}"
    
    with st.form(key=form_key):
        current_nsfw = st.checkbox("Allow NSFW (18+)", value=st.session_state.safety_settings["nsfw"])
        current_gore = st.checkbox("Allow Gore/Violence", value=st.session_state.safety_settings["gore"])
        current_prof = st.checkbox("Allow Profanity", value=st.session_state.safety_settings["profanity"])
        
        st.info("Changes will only apply when you click Save.")
        
        st.markdown(
            """<a class="policy-link" href="https://ai.google.dev/gemini-api/docs/safety-guidance" target="_blank">Review Content Policy</a>""", 
            unsafe_allow_html=True
        )
        st.divider()
        
        # Updated Icon
        if st.form_submit_button(":material/check_circle: Save Changes", type="primary", use_container_width=True):
            st.session_state.safety_settings["nsfw"] = current_nsfw
            st.session_state.safety_settings["gore"] = current_gore
            st.session_state.safety_settings["profanity"] = current_prof
            st.rerun()

# --- MAIN APP LOGIC ---
st.title(f"Welt VX {APP_VERSION}")
st.subheader("Redefine Viewer Experience with Multimodal AI Agents")
st.caption("Powered by Gemini 3")
MASTER_DEMO_PATH = "master_demo.webm" 
WORKING_VIDEO_PATH = "temp_video.mp4" 

uploaded_file = st.file_uploader("Upload Video", type=["mp4", "mov", "avi", "webm"], label_visibility="collapsed")
use_demo = False
if os.path.exists(MASTER_DEMO_PATH):
    use_demo = st.checkbox("Or use the pre-loaded Demo Video")

start_processing = False
current_video_id = ""

if uploaded_file:
    start_processing = True
    with open(WORKING_VIDEO_PATH, "wb") as f: f.write(uploaded_file.getbuffer())
    st.session_state.active_video_path = WORKING_VIDEO_PATH
    current_video_id = uploaded_file.name
elif use_demo:
    start_processing = True
    st.session_state.active_video_path = MASTER_DEMO_PATH
    current_video_id = "Demo_Video_Master"

if start_processing and current_video_id != st.session_state.last_video_id:
    if os.path.exists("subtitles.srt"): os.remove("subtitles.srt")
    st.session_state.messages = []
    st.session_state.chapters = []
    st.session_state.video_start_time = 0
    st.session_state.last_video_id = current_video_id
    st.rerun()

# --- LAYOUT ---
if "active_video_path" in st.session_state:
    
    if st.session_state.show_assistant:
        col_video, col_assist = st.columns([2.5, 1.2]) 
    else:
        col_video, col_assist = st.columns([1, 0.001]) 

    # --- LEFT COLUMN (Player & Controls) ---
    with col_video:
        subs = "subtitles.srt" if os.path.exists("subtitles.srt") else None
        st.video(st.session_state.active_video_path, subtitles=subs, start_time=st.session_state.video_start_time)

        with st.container(border=True):
            c1, c2, c3, c4 = st.columns(4)
            
            with c1:
                # Updated Icon
                if st.button(":material/subtitles: Subtitles", use_container_width=True):
                    open_subtitle_window()
            
            with c2:
                # Updated Icon
                if st.button(":material/segment: Smart Chapters", use_container_width=True):
                    with st.spinner("Analyzing Narrative Arc..."):
                        st.session_state.chapters = weltengine.generate_smart_chapters(api_key, st.session_state.active_video_path)
                        st.rerun()
            
            with c3:
                # Updated Icons
                label = ":material/close: Close Assistant" if st.session_state.show_assistant else ":material/smart_toy: VX Assistant"
                type_color = "secondary" if st.session_state.show_assistant else "primary"
                if st.button(label, type=type_color, use_container_width=True):
                    st.session_state.show_assistant = not st.session_state.show_assistant
                    st.rerun()
            
            with c4:
                # Updated Icon
                if st.button(":material/settings: Options", use_container_width=True):
                    st.session_state.form_reset_id += 1 
                    open_advanced_options()

        if st.session_state.chapters:
            st.markdown("#### :material/menu_book: Chapters") # Updated Icon
            with st.container(height=200):
                for ts, title in st.session_state.chapters:
                    if st.button(f"{ts} - {title}", key=ts, use_container_width=True):
                        m, s = map(int, ts.split(":"))
                        st.session_state.video_start_time = m * 60 + s
                        st.rerun()

    # --- RIGHT COLUMN (VX Assistant) ---
    if st.session_state.show_assistant:
        with col_assist:
            h1, h2 = st.columns([3, 1])
            with h1: st.markdown("#### Assistant")
            with h2: 
                # Updated Icon
                if st.button(":material/delete:", help="Clear Chat"):
                    st.session_state.messages = []
                    st.rerun()
            
            chat_box = st.container(height=500)
            
            # --- 1. CHAT RENDER LOOP ---
            if not st.session_state.messages:
                with chat_box:
                    st.info("I can help you navigate, fix errors, or answer questions.")
                    
                    # --- CLEAN TEXT CHIPS (Removed Emojis) ---
                    sc1, sc2 = st.columns(2)
                    with sc1:
                        if st.button("Action Scan", use_container_width=True):
                            st.session_state.messages.append({"role": "user", "content": "Find the most exciting action scene."})
                            st.rerun()
                    with sc2:
                        if st.button("Safety Scan", use_container_width=True):
                            st.session_state.messages.append({"role": "user", "content": "Scan for any restricted content."})
                            st.rerun()
                    
                    sc3, sc4 = st.columns(2)
                    with sc3:
                         if st.button("Recap Arc", use_container_width=True):
                            st.session_state.messages.append({"role": "user", "content": "Summarize the key events so far."})
                            st.rerun()
                    with sc4:
                         if st.button("Repair Subs", use_container_width=True):
                            st.session_state.messages.append({"role": "user", "content": "Check the subtitles for any spelling errors."})
                            st.rerun()
            else:
                 with chat_box:
                    for msg in st.session_state.messages:
                        with st.chat_message(msg["role"]): st.markdown(msg["content"])
            
            # --- 2. INPUT HANDLER ---
            if prompt := st.chat_input("Ask Welt..."):
                st.session_state.messages.append({"role": "user", "content": prompt})
                st.rerun()

            # --- 3. BACKEND TRIGGER ---
            if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
                 with chat_box:
                    with st.chat_message("assistant"):
                        with st.spinner("Thinking..."):
                            current_srt = ""
                            if os.path.exists("subtitles.srt"):
                                with open("subtitles.srt", "r", encoding="utf-8") as f: current_srt = f.read()
                            
                            last_user_msg = st.session_state.messages[-1]["content"]
                            
                            response = weltengine.vx_assistant_fix(
                                api_key, 
                                st.session_state.active_video_path, 
                                current_srt, 
                                st.session_state.chapters, 
                                last_user_msg, 
                                user_filters=st.session_state.safety_settings
                            )
                            
                            final_msg = ""
                            if response.startswith("PATCH:"):
                                with open("subtitles.srt", "w", encoding="utf-8") as f: 
                                    f.write(weltengine.clean_and_repair_srt(response))
                                final_msg = "✅ Subtitles patched based on your feedback."
                            
                            elif response.startswith("CHAPTERS:"):
                                lines = response.replace("CHAPTERS:", "").strip().split('\n')
                                st.session_state.chapters = [tuple(l.split(" - ", 1)) for l in lines if " - " in l]
                                final_msg = "✅ Smart Chapters updated."
                            
                            elif response.startswith("SEEK:"):
                                try:
                                    raw = response.replace("SEEK:", "").strip()
                                    parts = raw.split(" ", 1)
                                    ts = parts[0].strip().replace("[", "").replace("]", "")
                                    desc = parts[1] if len(parts) > 1 else "Jumping..."
                                    
                                    t_parts = ts.split(":")
                                    if len(t_parts) == 3: sec = int(t_parts[0])*3600 + int(t_parts[1])*60 + int(t_parts[2])
                                    elif len(t_parts) == 2: sec = int(t_parts[0])*60 + int(t_parts[1])
                                    else: sec = 0
                                    
                                    st.session_state.video_start_time = sec
                                    final_msg = f"🎥 **Jumped to {ts}**: {desc}"
                                    
                                    st.session_state.messages.append({"role": "assistant", "content": final_msg})
                                    st.rerun()
                                    
                                except Exception: 
                                    final_msg = "⚠️ Seek failed."
                            
                            else:
                                final_msg = response.replace("ANSWER:", "").strip()
                
                 st.session_state.messages.append({"role": "assistant", "content": final_msg})
                 st.rerun()