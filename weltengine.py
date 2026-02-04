import time
import srt
from google import genai
from google.genai import types

def generate_subtitles_backend(api_key, video_path, target_language="English", include_sfx=False):
    """
    The Core Agent Logic.
    Features:
    - Gemini 3 Flash Preview (Strict Adherence)
    - Alpha Language Logic: Tags Foreign Languages + Applies Italics <i>
    - Context Mode: Optional SFX support
    - Resilience: Auto-retries on 503 Overload errors
    - Safety: Graceful handling of Content Policy blocks
    """
    client = genai.Client(api_key=api_key)
    
    # 1. Upload Video
    print(f"☁️ Uploading {video_path}...")
    try:
        myfile = client.files.upload(file=video_path)
    except Exception as e:
        return f"Error Uploading: {e}"

    # 2. Polling Wait Loop
    print("⏳ Processing video...")
    while myfile.state.name == "PROCESSING":
        time.sleep(2) 
        myfile = client.files.get(name=myfile.name)
    
    if myfile.state.name == "FAILED":
        return "Error: Video processing failed."

    # --- DYNAMIC PROMPT CONSTRUCTION ---
    
    # SFX Instruction
    if include_sfx:
        sfx_instruction = """
        - **Context Mode: ON**. You MUST transcribe significant non-speech sounds in brackets.
        - Examples: [Laughs], [Doorbell rings], [Music fades].
        """
    else:
        sfx_instruction = """
        - **Context Mode: OFF**. Do NOT subtitle sound effects. Transcribe spoken dialogue ONLY.
        """

    # System "Brain" (Prompt)
    system_prompt = f"""
    You are an expert Context-Aware Subtitler.

    IMPORTANT NOTE: IGNORE ANY SUBTITLES ALREADY IN THE VIDEO, GENERATE FRESH ONES BASED ON AUDIO, AND IF APPLICABLE, VISUAL CONTEXT.
    
    DEFINITIONS:
    - **Alpha Language**: The dominant/narrative language of the video.
    - **Foreign Language**: Any spoken language that is NOT the Alpha Language.

    RULES:
    1. **Identify Alpha**: Listen to the full context to determine the main language.
    2. **Translate**: Translate ALL speech to the user's Target Language ({target_language}).
    3. **Tagging & Formatting Logic (The 'Alpha' Rule)**: 
       - If a sentence is spoken in the **Alpha Language**, output plain text (NO tags, NO italics).
       - If a sentence is spoken in a **Foreign Language**:
         1. Prefix with (LanguageName).
         2. Wrap the text in HTML italic tags <i>...</i>.
       - Example (Alpha=English, Target=English):
         - Audio (English): "Hello." -> Subtitle: "Hello."
         - Audio (Spanish): "Hola." -> Subtitle: "(Spanish) <i>Hello.</i>"
    4. **SFX Logic**: {sfx_instruction}
    5. **Format**: Return ONLY valid SRT string. No conversational filler.
    """

    # User Task
    user_prompt = f"""
    Video Processed.
    Target Language: {target_language}.
    Include SFX: {include_sfx}.

    Task:
    1. Identify Alpha Language.
    2. Translate.
    3. Apply Alpha Tagging + Italics for foreign speech.
    """

    # --- SAFETY SETTINGS (Hackathon Standard) ---
    safety_conf = [
        types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_LOW_AND_ABOVE"),
        types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_LOW_AND_ABOVE"),
        types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_LOW_AND_ABOVE"),
        types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_LOW_AND_ABOVE"),
    ]

    # 3. Generate (STRICTLY Gemini 3 Flash Preview)
    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"🔄 Generation Attempt {attempt + 1}/{max_retries}...")
            response = client.models.generate_content(
                model="gemini-3-flash-preview", 
                contents=[myfile, user_prompt],
                config={
                    "system_instruction": system_prompt,
                    "temperature": 0.2,
                    "safety_settings": safety_conf,
                }
            )
            
            # Safety Checks
            if not response.candidates: return "Error: Content blocked by Safety Filters."
            if response.candidates[0].finish_reason != "STOP": return f"Error: Stopped due to {response.candidates[0].finish_reason}"
            
            return response.text 

        except Exception as e:
            error_str = str(e)
            # Retry only on Server Overload (503)
            if "503" in error_str or "overloaded" in error_str.lower():
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 5
                    print(f"⚠️ Model Overloaded (503). Waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue 
                else:
                    return "Error: Server is too busy (503). Please wait 1 minute and try again."
            else:
                return f"Error Generating: {e}"

def generate_smart_chapters(api_key, video_path):
    """
    Analyzes the video to create timestamped chapters using Multimodal reasoning.
    Returns a list of tuples: [("00:00", "Intro"), ...]
    """
    client = genai.Client(api_key=api_key)
    
    # Re-upload/get file handle for statelessness
    try:
        myfile = client.files.upload(file=video_path)
        while myfile.state.name == "PROCESSING":
            time.sleep(1) 
            myfile = client.files.get(name=myfile.name)
    except Exception as e:
        return [("00:00", f"Error: {e}")]

    prompt = """
    Analyze this video and generate a list of Smart Chapters.
    RULES:
    1. Identify major scene changes or topic shifts.
    2. Format output STRICTLY as: "MM:SS - Chapter Title" per line.
    3. Start with "00:00 - Introduction".
    4. Keep titles short (2-4 words).
    """

    try:
        response = client.models.generate_content(
            model="gemini-3-flash-preview", 
            contents=[myfile, prompt],
            config={"temperature": 0.1}
        )
        
        chapters = []
        raw_lines = response.text.strip().split('\n')
        for line in raw_lines:
            if " - " in line:
                parts = line.split(" - ", 1)
                if len(parts) == 2:
                    chapters.append((parts[0].strip(), parts[1].strip()))
        return chapters

    except Exception as e:
        return [("00:00", "Chapter Generation Failed")]

def vx_assistant_fix(api_key, video_path, current_srt, user_instruction):
    """
    The Multimodal Repair Agent (Visual Q&A + SRT Patching).
    """
    client = genai.Client(api_key=api_key)
    
    # Enable Multimodality (Pass Video)
    try:
        myfile = client.files.upload(file=video_path)
        while myfile.state.name == "PROCESSING":
            time.sleep(1)
            myfile = client.files.get(name=myfile.name)
    except Exception as e:
        return f"ANSWER: Error accessing video: {e}"

    system_prompt = """
    You are VX Assistant, a Multimodal Video Expert & Subtitle Editor.
    YOUR TASK: Determine the user's intent.
    
    --- MODE A: EDIT REQUEST ---
    If the user wants to fix subtitles (typos, timing, translation):
    1. Apply the fix to the provided SRT.
    2. Output strictly the SRT content prefixed with "PATCH:".
    
    --- MODE B: VISUAL Q&A ---
    If the user asks a question about the video content (e.g., "What color is the car?"):
    1. Analyze the video visuals/audio.
    2. Answer the question helpfully.
    3. Prefix the output with "ANSWER:".
    """
    
    user_prompt = f"[CURRENT SRT]\n{current_srt}\n\n[USER INSTRUCTION]\n{user_instruction}"

    try:
        response = client.models.generate_content(
            model="gemini-3-flash-preview", 
            contents=[myfile, user_prompt],
            config={"system_instruction": system_prompt, "temperature": 0.2}
        )
        return response.text
    except Exception as e:
        return f"ANSWER: Error: {e}"

def clean_and_repair_srt(raw_text):
    """
    Guardrail: Validates SRT syntax and removes API artifacts.
    """
    try:
        clean_raw = raw_text.replace("PATCH:", "").strip()
        if "-->" not in clean_raw: return "Error: Invalid SRT format."
        
        subtitle_generator = srt.parse(clean_raw)
        subtitles = list(subtitle_generator)
        return srt.compose(subtitles)
        
    except Exception as e:
        return f"Error Repairing SRT: {e}"