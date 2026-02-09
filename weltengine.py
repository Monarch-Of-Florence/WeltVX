import time
import srt
from google import genai
from google.genai import types

# ⚠️ STRICT CONFIGURATION
# Optimized for the Gemini 3 Hackathon
MODEL_ID = "gemini-3-flash-preview"

# --- HELPER: ROBUST PROCESSING WAITER ---
def _wait_for_processing(client, myfile):
    """
    Prevents infinite loops if Google's server hangs. 
    Waits max 5 minutes (300s) for the video to become ACTIVE.
    """
    print(f"⏳ Waiting for video processing: {myfile.name}")
    # UPDATED: 150 checks * 2 seconds = 300 seconds (5 Minutes)
    for _ in range(150): 
        if myfile.state.name == "ACTIVE":
            print(f"✅ Video Active: {myfile.name}") # ADDED: Confirm active state
            return myfile
        elif myfile.state.name == "FAILED":
            raise Exception("Video processing failed on Google servers.")
        time.sleep(2)
        myfile = client.files.get(name=myfile.name)
    raise Exception("Video processing timed out (5-minute limit reached).")

# --- SAFETY CONFIGURATOR ---
def _configure_safety(user_filters):
    """
    Translates User Checkboxes into API Safety Settings + System Prompt Rules.
    """
    if not user_filters: user_filters = {}

    # 1. Default: Safety Shields UP (Block everything by default)
    api_settings = {
        "HARM_CATEGORY_HATE_SPEECH": "BLOCK_NONE",
        "HARM_CATEGORY_SEXUALLY_EXPLICIT": "BLOCK_NONE",
        "HARM_CATEGORY_HARASSMENT": "BLOCK_NONE",
        "HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_NONE",
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
    Main Subtitle Generation Function.
    """
    client = genai.Client(api_key=api_key)
    
    # 1. Upload Video (Protected)
    print(f"☁️ DEBUG: Starting Upload for {video_path}...") # ADDED: Debug print
    try:
        myfile = client.files.upload(file=video_path)
        myfile = _wait_for_processing(client, myfile)
    except Exception as e:
        print(f"❌ DEBUG: Upload Failed: {e}") # ADDED: Debug print
        return f"Error Uploading: {e}"

    # 2. Get Dynamic Safety Rules
    safety_conf, safety_prompt_instructions = _configure_safety(user_filters)

    # 3. Dynamic Prompt Construction
    if include_sfx:
        sfx_instruction = "- **Context Mode: ON**. You MUST transcribe significant non-speech sounds in brackets."
    else:
        sfx_instruction = "- **Context Mode: OFF**. Do NOT subtitle sound effects."

    system_prompt = f"""
    You are an expert Context-Aware Subtitler.

    IMPORTANT NOTE: IGNORE ANY SUBTITLES ALREADY IN THE VIDEO.

    SAFETY INSTRUCTIONS (FROM USER):
    {safety_prompt_instructions}

    DEFINITIONS:
    - **Matrix Language**: The prevalent language spoken in the video
    - **Foreign Language**: Any language that is NOT the Matrix Language.
    - **Significant SFX**: Non-speech sounds that are crucial for understanding the scene (e.g., [door creaks], [loud explosion]).
    - **Insignificant SFX**: Background noises that do not add meaningful context (e.g., [birds chirping]).
    - **Relevant Screen Text**: On-screen text that provides important info (signs, messages) that should be included.
    - **Irrelevant Screen Text**: On-screen text that is purely decorative.

    RULES:
    1. **Identify Matrix Language**: Listen to the full context of the video
    2. **Identify text on screen**: If it is subtitle text already present, IGNORE it.
          - If Relevant Screen Text → INCLUDE
          - If Irrelevant Screen Text → IGNORE
    3. **Translate ALL speech and relevant screen text to {target_language}**
    4. **Tagging logic**:
             - Matrix Language: keep as plain text
             - Foreign Language: prefix with (language name) + <i>italics</i>
    5. **Sound Effect Logic**: {sfx_instruction}
    6. **Timing**: Ensure subtitles are perfectly timed. Subtitles should flow naturally.
    7. **Output Format**: Return ONLY the valid SRT formatted subtitles.
    """

    user_prompt = f"Video Processed. Target: {target_language}. Task: Generate Subtitles."

    # 4. Generate with Retry Logic
    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"🔄 DEBUG: Generation Attempt {attempt + 1}/{max_retries}...") # ADDED: Debug print
            response = client.models.generate_content(
                model=MODEL_ID, 
                contents=[myfile, user_prompt],
                config={
                    "system_instruction": system_prompt,
                    "temperature": 0.2,
                    "safety_settings": safety_conf,
                }
            )
            
            # <--- FIX: ROBUST "THOUGHT" HANDLING --->
            # 1. Try extracting text parts manually (ignores thought_signature)
            if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                text_parts = []
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'text') and part.text:
                        text_parts.append(part.text)
                full_text = "".join(text_parts)
                if full_text:
                    print(f"📝 DEBUG: Received {len(full_text)} chars of text.") # ADDED
                    return full_text
            
            # 2. Fallback to standard property if above fails but text exists
            if response.text:
                print(f"📝 DEBUG: Fallback .text received {len(response.text)} chars.") # ADDED
                return response.text
                
            # 3. If neither works, it's a refusal/block
            reason = "Unknown"
            if response.candidates and response.candidates[0].finish_reason:
                reason = response.candidates[0].finish_reason.name
            
            print(f"⛔ DEBUG: Blocked! Finish Reason: {reason}") # ADDED: Critical info
            return f"Error: Content blocked by Safety Filters. Reason: {reason}"

        except Exception as e:
            error_str = str(e)
            print(f"⚠️ DEBUG: Exception Hit: {error_str}") # ADDED
            if "503" in error_str or "overloaded" in error_str.lower():
                time.sleep(5)
                continue 
            else:
                return f"Error Generating: {e}"
    return "Error: Server Overloaded."


def generate_smart_chapters(api_key, video_path):
    """
    Standard Chapter Generation.
    """
    client = genai.Client(api_key=api_key)
    try:
        myfile = client.files.upload(file=video_path)
        myfile = _wait_for_processing(client, myfile)
    except Exception as e:
        return [("00:00", f"Error: {e}")]

    prompt = "Analyze video. Generate Smart Chapters. Format STRICTLY: 'MM:SS - Chapter Title'. Start with 00:00."

    try:
        response = client.models.generate_content(
            model=MODEL_ID, 
            contents=[myfile, prompt],
            config={"temperature": 0.1}
        )
        
        # Apply the same robust extraction here (optional but safe)
        final_text = ""
        if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
             for part in response.candidates[0].content.parts:
                 if hasattr(part, 'text') and part.text:
                     final_text += part.text
        if not final_text and response.text:
            final_text = response.text

        chapters = []
        if final_text:
            raw_lines = final_text.strip().split('\n')
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
    VX Assistant Logic (Multimodal + Context Aware).
    """
    client = genai.Client(api_key=api_key)
    try:
        myfile = client.files.upload(file=video_path)
        myfile = _wait_for_processing(client, myfile)
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

    4. **NAVIGATION**: If user wants to 'go to' or 'jump to' a specific part/object in the video:
       - Output: "SEEK:MM:SS" followed by a short description
       - Example: "SEEK:12:34 - The part where the main character enters the room."

    5. **CONTENT SCAN**: If user wants to scan the content (if scene/time interval isn't specified, assume full video with audio) for specific themes, objects, or moments:
       IF SPECIFIED CONTENT/OBJECT FOUND:
           - Output: "(NAME) FOUND IN VIDEO (X) TIMES: [LIST OF TIMESTAMPS]".
       IF SPECIFIED CONTENT/OBJECT NOT FOUND:
           - Output: "(NAME) NOT FOUND IN VIDEO."
    """
    
    # Format Context (FULL CONTEXT ENABLED)
    srt_ctx = current_srt if current_srt else "(No subtitles)"
    
    # Format Chapter Context
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
        
        # <--- FIX: ROBUST "THOUGHT" HANDLING (Applied here too) --->
        if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
            full_text = ""
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'text') and part.text:
                    full_text += part.text
            if full_text:
                return full_text
                
        if response.text:
            return response.text
        else:
            reason = "Unknown"
            if response.candidates and response.candidates[0].finish_reason:
                reason = response.candidates[0].finish_reason.name
            return f"ANSWER: I cannot answer this. (Reason: {reason}). Check your Safety Settings."

    except Exception as e:
        return f"ANSWER: Error: {e}"


def clean_and_repair_srt(raw_text):
    """
    SRT Parsing & Repair.
    """
    if not raw_text: return "Error: Empty response."
    try:
        # Extra cleaning step for Gemini markdown artifacts
        clean_raw = raw_text.replace("PATCH:", "").replace("```srt", "").replace("```", "").strip()
        
        # ADDED: Check if the response is actually a subtitle file
        if "-->" not in clean_raw:
             print(f"⚠️ DEBUG: API returned text that is NOT a subtitle file: {clean_raw[:100]}...")
             return clean_raw # Return raw error/text so user sees it in the file

        subtitle_generator = srt.parse(clean_raw)
        subtitles = list(subtitle_generator)
        return srt.compose(subtitles)
        
    except Exception as e:
        print(f"❌ DEBUG: SRT Parse Failed: {e}") # ADDED
        return f"Error Repairing SRT: {e}"