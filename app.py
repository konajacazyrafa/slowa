import streamlit as st
import json
import random
import time
import hashlib
from pathlib import Path
from gtts import gTTS

# --- ŚCIEŻKI ---
BASE_DIR = Path(__file__).parent
WORDS_PATH = BASE_DIR / "words.json"
PROGRESS_PATH = BASE_DIR / "progress.json"
TTS_DIR = BASE_DIR / "tts_cache"
TTS_DIR.mkdir(exist_ok=True)


# --- FUNKCJE ---

def load_words():
    """Wczytuje jeden plik JSON: { "1": [...], "2": [...], ... }"""
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
    """Zwraca ścieżkę do zapisanego mp3, generuje jeśli nie istnieje."""
    h = hashlib.md5(word.encode("utf-8")).hexdigest()
    path = TTS_DIR / f"{h}.mp3"

    if not path.exists():
        tts = gTTS(text=word, lang="pl")
        tts.save(str(path))

    return path


def run_training(day_num: str, words: list[str]):
    """Wyświetla 5 słów w losowej kolejności z lektorem."""
    st.write(f"### Trening – dzień {day_num}")

    if len(words) != 5:
        st.error(f"Dzień {day_num} musi mieć **dokładnie 5 słów**, a ma {len(words)}.")
        return

    display = st.empty()
    audio_placeholder = st.empty()

    random_words = random.sample(words, len(words))

    for i, word in enumerate(random_words, start=1):
        display.markdown(
            f"<div style='text-align:center; font-size:80px; color:red;'>"
            f"{word}</div>",
            unsafe_allow_html=True
        )

        audio_file = get_tts_audio_path(word)
        with open(audio_file, "rb") as f:
            audio_placeholder.audio(f.read(), format="audio/mp3")

        time.sleep(3.5)

        display.empty()
        audio_placeholder.empty()
        time.sleep(2)

    st.success("Koniec treningu.")


# --- APLIKACJA ---

def main():
    st.set_page_config(page_title="Trening słownictwa", layout="centered")
    st.title("Trening słownictwa – jeden plik JSON")

    words_by_day = load_words()
    progress = load_progress()

    if not words_by_day:
        st.warning("Dodaj plik **words.json** w katalogu głównym repo!")
        return

    st.write("### Lista dni:")

    # Sortuj dni numerycznie
    days_sorted = sorted(words_by_day.items(), key=lambda x: int(x[0]))

    for day_num, words in days_sorted:
        col1, col2, col3 = st.columns([3, 3, 2])

        with col1:
            completed = progress.get(day_num, 0)
            status = "✅ zaliczony" if completed >= 3 else "⏳ w trakcie"
            st.markdown(
                f"**Dzień {day_num}** – 5 słów  \n"
                f"Odtworzenia: **{completed}**  \n"
                f"Status: {status}"
            )

        with col2:
            st.write(", ".join(words))

        with col3:
            if st.button(f"Trenuj dzień {day_num}", key=f"btn_{day_num}"):
                run_training(day_num, words)
                progress[day_num] = progress.get(day_num, 0) + 1
                save_progress(progress)
                st.experimental_rerun()


if __name__ == "__main__":
    main()
