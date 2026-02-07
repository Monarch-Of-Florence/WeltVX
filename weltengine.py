import time
import srt
from google import genai
from google.genai import types

# ⚠️ STRICT CONFIGURATION
MODEL_ID = "gemini-3-flash-preview"

# --- NEW: SAFETY CONFIGURATOR ---
def _configure_safety(user_filters):
    """
    Translates User Checkboxes into API Safety Settings + System Prompt Rules.
    """
    if not user_filters: user_filters = {}

    # 1. Default: Safety Shields UP (Block everything by default)
    api_settings = {
        "HARM_CATEGORY_HATE_SPEECH": "BLOCK_LOW_AND_ABOVE",
        "HARM_CATEGORY_SEXUALLY_EXPLICIT": "BLOCK_LOW_AND_ABOVE",
        "HARM_CATEGORY_HARASSMENT": "BLOCK_LOW_AND_ABOVE",
        "HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_LOW_AND_ABOVE",
    }
    
    prompt_rules = []

    # 2. GORE / VIOLENCE LOGIC
    if user_filters.get("gore"):
        api_settings["HARM_CATEGORY_DANGEROUS_CONTENT"] = "BLOCK_NONE"
        api_settings["HARM_CATEGORY_HARASSMENT"] = "BLOCK_NONE"
        prompt_rules.append("- **CONTEXT MODE: VIOLENCE ALLOWED.** You are authorized to process/describe violent or dangerous content objectively for analysis.")
    else:
        prompt_rules.append("- **SAFETY MODE: STRICT.** Strictly filter out or summarize descriptions of gore and violence.")

    # 3. NSFW LOGIC
    if user_filters.get("nsfw"):
        api_settings["HARM_CATEGORY_SEXUALLY_EXPLICIT"] = "BLOCK_NONE"
        prompt_rules.append("- **CONTEXT MODE: NSFW ALLOWED.** You are authorized to process nudity or mature themes if relevant to the narrative.")
    else:
        prompt_rules.append("- **SAFETY MODE: FAMILY FRIENDLY.** Strictly block or refuse to describe sexually explicit content.")

    # 4. PROFANITY LOGIC
    if user_filters.get("profanity"):
        prompt_rules.append("- **LANGUAGE:** Transcribe profanity exactly as spoken. Do not censor.")
    else:
        prompt_rules.append("- **LANGUAGE:** Replace strong profanity with asterisks (e.g., f***).")

    # Convert to Gemini API Objects
    final_safety_conf = [
        types.SafetySetting(category=k, threshold=v) for k, v in api_settings.items()
    ]
    
    return final_safety_conf, "\n".join(prompt_rules)


def generate_subtitles_backend(api_key, video_path, target_language="English", include_sfx=False, user_filters=None):
    """
    UPDATED: Now accepts 'user_filters' to apply Advanced Safety Options.
    """
    client = genai.Client(api_key=api_key)
    
    # 1. Upload Video
    print(f"☁️ Uploading {video_path}...")
    try:
        myfile = client.files.upload(file=video_path)
        while myfile.state.name == "PROCESSING":
            time.sleep(2) 
            myfile = client.files.get(name=myfile.name)
    except Exception as e:
        return f"Error Uploading: {e}"

    if myfile.state.name == "FAILED": return "Error: Video processing failed."

    # --- NEW: GET DYNAMIC SAFETY RULES ---
    safety_conf, safety_prompt_instructions = _configure_safety(user_filters)

    # --- DYNAMIC PROMPT CONSTRUCTION ---
    if include_sfx:
        sfx_instruction = "- **Context Mode: ON**. You MUST transcribe significant non-speech sounds in brackets."
    else:
        sfx_instruction = "- **Context Mode: OFF**. Do NOT subtitle sound effects."

    system_prompt = f"""
    You are an expert Context-Aware Subtitler.

    IMPORTANT NOTE: IGNORE ANY SUBTITLES ALREADY IN THE VIDEO.

    SAFETY INSTRUCTIONS (FROM USER):
    {safety_prompt_instructions}
    
    RULES:
    1. **Identify Alpha Language**: Listen to the full context.
    2. **Translate**: Translate ALL speech to {target_language}.
    3. **Tagging Logic**: 
       - Alpha Language = Plain Text.
       - Foreign Language = Prefix with (LanguageName) + <i>Italics</i>.
    4. **SFX Logic**: {sfx_instruction}
    5. **Format**: Return ONLY valid SRT string.
    """

    user_prompt = f"Video Processed. Target: {target_language}. Task: Generate Subtitles."

    # 3. Generate (Using Dynamic Safety Settings)
    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"🔄 Generation Attempt {attempt + 1}/{max_retries}...")
            response = client.models.generate_content(
                model=MODEL_ID, 
                contents=[myfile, user_prompt],
                config={
                    "system_instruction": system_prompt,
                    "temperature": 0.2,
                    "safety_settings": safety_conf, # <--- UPDATED HERE
                }
            )
            
            if not response.text: return "Error: Content blocked by Safety Filters."
            return response.text 

        except Exception as e:
            error_str = str(e)
            if "503" in error_str or "overloaded" in error_str.lower():
                time.sleep(5)
                continue 
            else:
                return f"Error Generating: {e}"
    return "Error: Server Overloaded."


def generate_smart_chapters(api_key, video_path):
    """
    Standard Chapter Generation (No changes needed here).
    """
    client = genai.Client(api_key=api_key)
    try:
        myfile = client.files.upload(file=video_path)
        while myfile.state.name == "PROCESSING":
            time.sleep(1) 
            myfile = client.files.get(name=myfile.name)
    except Exception as e:
        return [("00:00", f"Error: {e}")]

    prompt = "Analyze video. Generate Smart Chapters. Format STRICTLY: 'MM:SS - Chapter Title'. Start with 00:00."

    try:
        response = client.models.generate_content(
            model=MODEL_ID, 
            contents=[myfile, prompt],
            config={"temperature": 0.1}
        )
        
        chapters = []
        if response.text:
            raw_lines = response.text.strip().split('\n')
            for line in raw_lines:
                if " - " in line:
                    parts = line.split(" - ", 1)
                    if len(parts) == 2:
                        chapters.append((parts[0].strip(), parts[1].strip()))
        return chapters

    except Exception as e:
        return [("00:00", "Chapter Generation Failed")]


def vx_assistant_fix(api_key, video_path, current_srt, current_chapters, user_instruction, user_filters=None):
    """
    UPDATED: Now accepts 'current_chapters' and can edit them.
    """
    client = genai.Client(api_key=api_key)
    try:
        myfile = client.files.upload(file=video_path)
        while myfile.state.name == "PROCESSING":
            time.sleep(1)
            myfile = client.files.get(name=myfile.name)
    except Exception as e:
        return f"ANSWER: Error accessing video: {e}"

    # Get Safety Rules
    safety_conf, safety_prompt_instructions = _configure_safety(user_filters)

    system_prompt = f"""
    You are VX Assistant, a Multimodal Video Expert.
    
    YOUR SAFETY PROTOCOLS:
    {safety_prompt_instructions}
    
    TASK: Determine User Intent and Output ONE of these formats:
    
    1. **EDIT SUBTITLES**: If user wants to fix typos/timing in subtitles.
       - Output: "PATCH:" followed by the full corrected SRT block.
       
    2. **EDIT CHAPTERS**: If user wants to rename, move, add, or delete chapters.
       - Output: "CHAPTERS:" followed by the new list.
       - Format: "MM:SS - Title" (one per line).
       
    3. **QUESTION**: If user asks about video content.
       - Output: "ANSWER:" followed by your helpful response.

    4. **NAVIGATION**: If user wants to 'go to', 'jump to', or 'find' a specific part/object in the video:
       - Output: "SEEK:MM:SS" followed by a short description
       - Example: "SEEK:12:34 - The part where the main character enters the room."
    """
    
    # Format Context
    srt_ctx = current_srt[:5000] if current_srt else "(No subtitles)"
    
    # Format Chapter Context (NEW)
    if current_chapters:
        chap_ctx = "\n".join([f"{ts} - {title}" for ts, title in current_chapters])
    else:
        chap_ctx = "(No chapters generated yet)"

    user_prompt = f"""
    [CURRENT CHAPTERS]
    {chap_ctx}

    [CURRENT SRT SAMPLE]
    {srt_ctx}

    [USER INSTRUCTION]
    {user_instruction}
    """

    try:
        response = client.models.generate_content(
            model=MODEL_ID, 
            contents=[myfile, user_prompt],
            config={
                "system_instruction": system_prompt, 
                "temperature": 0.2,
                "safety_settings": safety_conf
            }
        )
        return response.text
    except Exception as e:
        return f"ANSWER: Error: {e}"


def clean_and_repair_srt(raw_text):
    """
    UPDATED: Added fix for Markdown code blocks (```srt)
    """
    if not raw_text: return "Error: Empty response."
    try:
        # Extra cleaning step for Gemini markdown artifacts
        clean_raw = raw_text.replace("PATCH:", "").replace("```srt", "").replace("```", "").strip()
        
        if "-->" not in clean_raw: return clean_raw
        
        subtitle_generator = srt.parse(clean_raw)
        subtitles = list(subtitle_generator)
        return srt.compose(subtitles)
        
    except Exception as e:
        return f"Error Repairing SRT: {e}"