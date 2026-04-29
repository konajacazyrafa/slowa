import streamlit as st
import json
import random
import time
import hashlib
import base64
from pathlib import Path
from gtts import gTTS

BASE_DIR = Path(__file__).parent
WORDS_PATH = BASE_DIR / "words.json"
PROGRESS_PATH = BASE_DIR / "progress.json"
TTS_DIR = BASE_DIR / "tts_cache"
TTS_DIR.mkdir(exist_ok=True)


def load_words():
    if not WORDS_PATH.exists():
        return {}
    with WORDS_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_progress():
    if not PROGRESS_PATH.exists():
        return {}
    with PROGRESS_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_progress(progress_dict):
    with PROGRESS_PATH.open("w", encoding="utf-8") as f:
        json.dump(progress_dict, f, ensure_ascii=False, indent=2)


def get_tts_audio_path(word: str) -> Path:
    h = hashlib.md5(word.encode("utf-8")).hexdigest()
    path = TTS_DIR / f"{h}.mp3"
    if not path.exists():
        tts = gTTS(text=word, lang="pl")
        tts.save(str(path))
    return path


def autoplay_audio(word: str, audio_placeholder):
    audio_path = get_tts_audio_path(word)
    with audio_path.open("rb") as f:
        audio_bytes = f.read()

    b64 = base64.b64encode(audio_bytes).decode("utf-8")
    audio_placeholder.markdown(
        f"""
        <audio autoplay>
            <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
        </audio>
        """,
        unsafe_allow_html=True,
    )


def play_word(word: str, overlay_placeholder, audio_placeholder):
    overlay_html = f"""
    <div style="
        position: fixed;
        top: 0; left: 0;
        width: 100vw;
        height: 100vh;
        background: rgba(0, 0, 0, 0.6);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 9999;
    ">
        <div style="
            background: white;
            padding: 2rem 3rem;
            border-radius: 1rem;
            box-shadow: 0 0 20px rgba(0,0,0,0.3);
            min-width: 60%;
            text-align: center;
        ">
            <div style="
                font-size: 80px;
                color: red;
                font-family: sans-serif;
            ">
                {word}
            </div>
        </div>
    </div>
    """
    overlay_placeholder.markdown(overlay_html, unsafe_allow_html=True)
    autoplay_audio(word, audio_placeholder)


def unique_words_until_day(words_by_day: dict, day_num: str) -> list[str]:
    result = []
    seen = set()
    target_day = int(day_num)

    for d in range(1, target_day + 1):
        for word in words_by_day.get(str(d), []):
            clean = word.strip()
            if clean and clean not in seen:
                seen.add(clean)
                result.append(clean)

    return result


def reset_game_state():
    for key in [
        "game_day",
        "game_target",
        "game_options",
        "game_feedback_word",
        "game_feedback_correct",
        "game_audio_pending",
    ]:
        if key in st.session_state:
            del st.session_state[key]


def training_screen(day_num: str, words: list[str]):
    if len(words) != 5:
        st.error(f"Dzień {day_num} musi mieć dokładnie 5 słów, a ma {len(words)}.")
        st.session_state["view"] = "list"
        st.rerun()
        return

    overlay_placeholder = st.empty()
    audio_placeholder = st.empty()

    for w in random.sample(words, len(words)):
        play_word(w, overlay_placeholder, audio_placeholder)
        time.sleep(3.5)
        overlay_placeholder.empty()
        audio_placeholder.empty()
        time.sleep(2.0)

    progress = load_progress()
    progress[
