import time
import srt
from google import genai

def generate_subtitles_backend(api_key, video_path, target_language="English", include_sfx=False):
    """
    The Core Agent Logic.
    Features:
    - Gemini 3 Flash Preview (Multimodal)
    - Auto-Retry logic for 503 Overload Errors
    - Alpha Language Detection (Tags foreign languages)
    - Optional Context/SFX (e.g., [Laughs])
    """
    client = genai.Client(api_key=api_key)
    
    # 1. Upload Video (Using the correct 'file=' parameter)
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
    
    # Logic for Sound Effects / Context
    if include_sfx:
        sfx_instruction = """
        - **Context Mode: ON**. You MUST transcribe significant non-speech sounds and visual context in brackets.
        - Examples: [Laughs], [Doorbell rings], [Upbeat music plays], [Sign reads: 'Danger'].
        - Integrate these naturally with the dialogue.
        """
    else:
        sfx_instruction = """
        - **Context Mode: OFF**. Do NOT subtitle sound effects, music, or visual context. 
        - Transcribe spoken dialogue ONLY.
        """

    # The System "Brain" (Prompt)
    system_prompt = f"""
    You are an expert Context-Aware Subtitler.
    
    DEFINITIONS:
    - **Alpha Language**: The most dominant/frequently spoken language in the narrative.
    - **Foreign Language**: Any spoken language that is NOT the Alpha Language.

    RULES:
    1. **Identify Alpha**: Listen to the full context to determine the main language.
    2. **Translate**: Translate ALL speech to the user's Target Language.
    3. **Tagging Logic (The 'Alpha' Rule)**: 
       - If a sentence is spoken in the **Alpha Language**, output the translated text purely (NO tags).
       - If a sentence is spoken in a **Foreign Language**, you MUST prefix the subtitle with the language name in parentheses.
       - Example (Alpha=English, Target=English):
         - Audio (English): "Hello." -> Subtitle: "Hello."
         - Audio (Spanish): "Hola." -> Subtitle: "(Spanish) Hello."
    4. **SFX Logic**: {sfx_instruction}
    5. **Format**: Return ONLY valid SRT string. No conversational filler.
    """

    # The User Task
    user_prompt = f"""
    Video Processed.
    Target Output Language: {target_language}.
    Include Sound Effects (SDH): {include_sfx}.

    Task:
    1. Identify the 'Alpha Language'.
    2. Generate synchronized SRT subtitles in {target_language}.
    3. STRICTLY apply the Alpha Tagging Logic.
    4. Apply the SFX/Context rules defined above.
    """

    # 3. Generate Content (With Retry Logic for 503 Errors)
    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"🔄 Generation Attempt {attempt + 1}/{max_retries}...")
            response = client.models.generate_content(
                model="gemini-3-flash-preview",  # <--- HACKATHON MODEL
                contents=[myfile, user_prompt],
                config={
                    "system_instruction": system_prompt,
                    "temperature": 0.2, 
                }
            )
            return response.text # Success! Return immediately.

        except Exception as e:
            error_str = str(e)
            # Check specifically for "503" or "Overloaded" errors
            if "503" in error_str or "overloaded" in error_str.lower():
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 5 # Wait 5s, then 10s...
                    print(f"⚠️ Model Overloaded (503). Waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue # Try again
                else:
                    return "Error: Server is too busy (503). Please wait 1 minute and try again."
            else:
                # If it's a different error (e.g., API Key), fail immediately
                return f"Error Generating: {e}"

def clean_and_repair_srt(raw_text):
    """
    Guardrail: Validates and repairs the SRT output to ensure player compatibility.
    """
    try:
        if "-->" not in raw_text:
             return "Error: AI did not generate valid timestamps."
        
        # Parse using the SRT library to check for syntax errors
        subtitle_generator = srt.parse(raw_text)
        subtitles = list(subtitle_generator)
        
        # Re-compose (Standardizes the format and removes hidden artifacts)
        clean_text = srt.compose(subtitles)
        return clean_text
        
    except Exception as e:
        return f"Error Repairing SRT: {e}"