# 🌏 Welt VX (Visual Experience)

### The Multimodal Localization Agent powered by Gemini 3.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Gemini](https://img.shields.io/badge/AI-Gemini_3_Flash-orange)
![Streamlit](https://img.shields.io/badge/UI-Streamlit_Cinema-red)

**Welt VX** is not just a subtitle tool; it is an **Agentic System** that watches video to understand context. It features a "Matrix Language" detection engine, multimodal sound effect visualization, and a Human-in-the-Loop Repair Assistant.

---

## 🚀 Key Features

### 1. 🧠 Matrix Language Logic (Context-Aware Translation)
Unlike standard translators that flatten dialogue, Welt VX identifies the **Matrix Language** (the dominant narrative language) vs. **Embedded Languages**.
- **Matrix Language:** Rendered as standard text.
- **Embedded Language:** Automatically tagged and *italicized* to preserve the director's original intent.

### 2. 👁️ Multimodal Vision (SDH)
Using **Gemini 3 Flash Preview**, the agent "watches" the video pixels to caption visual sound effects that audio-only models miss.
- *Example:* `[Phone lights up]`, `[Door slams]`, `[Character nods]`.

### 3. 🤖 VX Assistant (Human-in-the-Loop)
A specialized **Repair Agent** resides in the sidebar.
- **Natural Language Repair:** "Fix the typo at 00:45." (The agent edits the code; no regeneration needed).
- **Visual Q&A:** "What color is the car?" (The agent analyzes the video frame to answer).

### 4. 📑 Smart Chapters
The agent observes scene changes and narrative shifts to automatically generate a clickable, timestamped **Table of Contents**.

---

## 🛠️ Architecture

The project follows a **State-Machine Architecture** built on Streamlit:

1.  **Ingestion:** Video is uploaded to ephemeral storage (Privacy-First).
2.  **Observation:** Gemini 3 analyzes audio waveforms + visual frames.
3.  **Drafting:** The `weltengine.py` generates an SRT file with Matrix Logic.
4.  **Validation:** Timestamps are validated via the `srt` library.
5.  **Refinement:** The VX Assistant allows for iterative, conversational edits.

---

## 💻 Installation & Setup

**1. Clone the repository**
```bash
git clone [https://github.com/YOUR_USERNAME/welt-vx.git](https://github.com/YOUR_USERNAME/welt-vx.git)
cd welt-vx

**2. Install dependencies**
```bash
pip install -r requirements.txt

**3. Set up Gemini 3 API Key in .env file**
GEMINI_API_KEY=your_gemini_3_api_key_here

**4. Run the Streamlit app**
```bash
streamlit run app.py