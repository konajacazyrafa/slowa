import streamlit as st
import json
import random
import time
import hashlib
import base64
from pathlib import Path
from gtts import gTTS

# --- ŚCIEŻKI ---
BASE_DIR = Path(__file__).parent
WORDS_PATH = BASE_DIR / "words.json"
PROGRESS_PATH = BASE_DIR / "progress.json"
TTS_DIR = BASE_DIR / "tts_cache"
TTS_DIR.mkdir(exist_ok=True)


# --- FUNKCJE DANYCH ---

def load_words():
    """Wczytuje words.json: { "1": [...], "2": [...], ... }"""
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


# --- TTS ---

def get_tts_audio_path(word: str) -> Path:
    """Zwraca ścieżkę do mp3, generuje jeśli nie ma."""
    h = hashlib.md5(word.encode("utf-8")).hexdigest()
    path = TTS_DIR / f"{h}.mp3"
    if not path.exists():
        tts = gTTS(text=word, lang="pl")
        tts.save(str(path))
    return path


def play_word(word: str, word_placeholder, audio_placeholder):
    """Wyświetla słowo + automatycznie odtwarza dźwięk."""
    # tekst – czerwony, duży
    word_placeholder.markdown(
        f"<div style='text-align:center; font-size:80px; color:red; "
        f"font-family:sans-serif;'>{word}</div>",
        unsafe_allow_html=True
    )

    # audio jako <audio autoplay>
    audio_path = get_tts_audio_path(word)
    with audio_path.open("rb") as f:
        audio_bytes = f.read()
    b64 = base64.b64encode(audio_bytes).decode("utf-8")

    audio_html = f"""
    <audio autoplay>
        <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
    </audio>
    """
    audio_placeholder.markdown(audio_html, unsafe_allow_html=True)


# --- EKRAN TRENINGU ---

def training_screen(day_num: str, words: list[str]):
    st.title(f"Trening – dzień {day_num}")

    if len(words) != 5:
        st.error(f"Dzień {day_num} musi mieć **dokładnie 5 słów**, a ma {len(words)}.")
        if st.button("Wróć do listy dni"):
            st.session_state["view"] = "list"
            st.experimental_rerun()
        return

    st.write("Słowa na dziś:")
    st.write(", ".join(words))

    st.markdown("---")

    # Placeholdery na słowo i audio
    word_placeholder = st.empty()
    audio_placeholder = st.empty()

    st.info("Trening startuje automatycznie. Nie klikaj nic w trakcie odtwarzania.")

    # Losowa kolejność 5 słów
    random_words = random.sample(words, len(words))

    # Główna sekwencja
    for idx, w in enumerate(random_words, start=1):
        play_word(w, word_placeholder, audio_placeholder)
        time.sleep(3.5)  # czas wyświetlania słowa
        word_placeholder.empty()
        audio_placeholder.empty()
        time.sleep(2.0)  # przerwa

    st.success("Koniec treningu dla tego dnia.")

    # aktualizacja licznika odtworzeń
    progress = load_progress()
    progress[day_num] = progress.get(day_num, 0) + 1
    save_progress(progress)

    # przycisk powrotu
    if st.button("Wróć do listy dni"):
        st.session_state["view"] = "list"
        st.experimental_rerun()


# --- EKRAN LISTY DNI ---

def list_screen(words_by_day: dict):
    st.title("Trening słownictwa")

    st.markdown(
        """
        Wybierz dzień, żeby otworzyć **osobny ekran treningu**.  
        Każdy dzień ma 5 słów, odtwarzanych w losowej kolejności, z lektorem.
        """
    )

    progress = load_progress()
    days_sorted = sorted(words_by_day.items(), key=lambda x: int(x[0]))

    for day_num, words in days_sorted:
        col1, col2, col3 = st.columns([3, 4, 2])

        with col1:
            count = progress.get(day_num, 0)
            status = "✅ zaliczony" if count >= 3 else "⏳ w trakcie"
            st.markdown(
                f"**Dzień {day_num}**  \n"
                f"Odtworzenia: **{count}**  \n"
                f"Status: {status}"
            )

        with col2:
            st.write(", ".join(words))

        with col3:
            if st.button(f"Start", key=f"start_{day_num}"):
                st.session_state["view"] = "training"
                st.session_state["training_day"] = day_num
                st.experimental_rerun()


# --- GŁÓWNA FUNKCJA ---

def main():
    st.set_page_config(page_title="Trening słów", layout="centered")

    # stan widoku
    if "view" not in st.session_state:
        st.session_state["view"] = "list"

    words_by_day = load_words()
    if not words_by_day:
        st.error("Brak pliku **words.json** albo jest pusty.")
        st.stop()

    if st.session_state["view"] == "training":
        day = st.session_state.get("training_day")
        if day is None or day not in words_by_day:
            st.session_state["view"] = "list"
            st.experimental_rerun()
        training_screen(day, words_by_day[day])
    else:
        list_screen(words_by_day)


if __name__ == "__main__":
    main()
