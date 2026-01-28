import streamlit as st
import os
from dotenv import load_dotenv
from PIL import Image
import weltengine  # Imports your backend logic

# --- SETUP ---
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

# Try to load custom icon, fallback to globe
if os.path.exists("welt_icon.png"):
    icon = Image.open("welt_icon.png")
else:
    icon = "🌏"

st.set_page_config(page_title="Welt VX", page_icon=icon, layout="wide")

# --- CINEMA STYLING (CSS) ---
def apply_cinema_style():
    st.markdown("""
        <style>
            /* 1. Reset Main Background to Pure Black */
            .stApp {
                background-color: #000000;
            }
            
            /* 2. Target the Video Player Container specifically */
            [data-testid="stVideo"] {
                border: 1px solid #333;
                border-radius: 12px;
                overflow: hidden; 
                box-shadow: 0px 0px 20px rgba(229, 9, 20, 0.3); /* Netflix Red Glow */
                transition: transform 0.3s ease;
            }
            
            /* 3. Subtle Hover Effect on Video */
            [data-testid="stVideo"]:hover {
                box-shadow: 0px 0px 30px rgba(229, 9, 20, 0.6);
                transform: scale(1.01);
            }

            /* 4. Custom Headers */
            h3 {
                color: #e50914 !important; /* Force Red Headers */
                font-weight: 300;
                margin-bottom: 5px;
            }
            
            /* 5. Remove Top Padding */
            .block-container {
                padding-top: 2rem;
            }
        </style>
    """, unsafe_allow_html=True)

apply_cinema_style()

# --- UI HEADER ---
st.title("Welt VX")
st.markdown("*The Multimodal AI Subtitle Agent (Powered by Gemini 3)*")

# --- MAIN APP ---
video_file = st.file_uploader("Upload Video (Max 2GB)", type=["mp4", "mov", "avi", "webm"])

if video_file:
    # 1. NEW: Zombie Subtitle Fix (Clears old SRTs on new upload)
    if "last_video_name" not in st.session_state:
        st.session_state["last_video_name"] = ""

    if video_file.name != st.session_state["last_video_name"]:
        # New video detected! Clean up old files
        if os.path.exists("subtitles.srt"):
            os.remove("subtitles.srt")
        st.session_state["last_video_name"] = video_file.name
        st.rerun() # Refresh app to clear the player

    # 2. Save File Locally
    with open("temp_video.mp4", "wb") as f:
        f.write(video_file.getbuffer())

    # 3. Layout
    col1, col2 = st.columns([2, 1])

    with col1:
        # Using Markdown header instead of st.info box for better style
        st.markdown("### 🎞️ Original Source") 
        st.video(video_file)

    with col2:
        st.markdown("### ⚙️ Control Deck")
        language = st.selectbox("Target Language", ["English", "Hindi", "Spanish", "Japanese", "German"])
        
        # --- CONTEXT SWITCH ---
        include_sfx = st.checkbox(
            "Include Context & Sound Effects (SDH)", 
            value=False, 
            help="If checked, AI will include [Laughs], [Applause], etc."
        )
        
        if st.button("Generate Subtitles (AI)", type="primary"):
            if not api_key:
                st.error("❌ API Key missing! Check your .env file.")
                st.stop()
            
            # 4. Call The Engine
            with st.status("🚀 Launching Welt Engine...", expanded=True) as status:
                status.write("☁️ Uploading to Gemini Secure Cloud...")
                
                # A. Generate Raw (Passing the new include_sfx variable)
                raw_srt = weltengine.generate_subtitles_backend(api_key, "temp_video.mp4", language, include_sfx)
                
                if "Error" in raw_srt:
                    status.update(label="Generation Failed", state="error")
                    st.error(raw_srt)
                else:
                    status.write("🧹 Polishing and validating subtitles...")
                    
                    # B. Clean & Repair
                    final_srt = weltengine.clean_and_repair_srt(raw_srt)
                    
                    if "Error" in final_srt:
                         status.update(label="Validation Failed", state="error")
                         st.error(f"AI Output Malformed: {final_srt}")
                    else:
                        # C. Save
                        with open("subtitles.srt", "w", encoding="utf-8") as f:
                            f.write(final_srt)
                        
                        status.update(label="Ready to Watch!", state="complete", expanded=False)
                        st.success("Subtitles Attached below! 👇")

    # --- RESULT PLAYER ---
    if os.path.exists("subtitles.srt"):
        st.divider()
        st.subheader(f"🎬 Welt VX Cinema Mode ({language})")
        st.video(video_file, subtitles="subtitles.srt")
        
        with open("subtitles.srt", "r", encoding="utf-8") as f:
            st.download_button("Download .SRT File", f, file_name="welt_subs.srt")