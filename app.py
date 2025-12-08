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


def play_word(word: str, overlay_placeholder, audio_placeholder):
    """Wyświetla słowo w pełnoekranowym overlayu + automatycznie odtwarza dźwięk."""
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
    # Ten ekran pokazuje tylko popup ze słowami
    if len(words) != 5:
        st.error(f"Dzień {day_num} musi mieć dokładnie 5 słów, a ma {len(words)}.")
        st.session_state["view"] = "list"
        st.rerun()
        return

    overlay_placeholder = st.empty()
    audio_placeholder = st.empty()

    random_words = random.sample(words, len(words))

    for w in random_words:
        play_word(w, overlay_placeholder, audio_placeholder)
        time.sleep(3.5)
        overlay_placeholder.empty()
        audio_placeholder.empty()
        time.sleep(2.0)

    # po zakończeniu: licznik + powrót na listę
    progress = load_progress()
    progress[day_num] = progress.get(day_num, 0) + 1
    save_progress(progress)

    st.session_state["view"] = "list"
    st.rerun()


# --- EKRAN LISTY DNI ---

def list_screen(words_by_day: dict):
    st.title("Nauka czytania")

    st.markdown(
        "Uruchom trening z wybranego dnia. "
        "Ostatni uruchamiany dzień jest podświetlony. "
        "Aby uruchomić nowy dzień, zalicz 3 powtórzenia dnia poprzedniego. "
    )

    progress = load_progress()
    days_sorted = sorted(words_by_day.items(), key=lambda x: int(x[0]))
    last_day = st.session_state.get("last_day")

    for day_num, words in days_sorted:
        dn_int = int(day_num)
        count = progress.get(day_num, 0)
        status = "✅ zaliczony" if count >= 3 else "⏳ w trakcie"

        # blokada: dzień N dostępny dopiero, gdy dzień N-1 zaliczony
        if dn_int == 1:
            can_play = True
        else:
            prev_key = str(dn_int - 1)
            can_play = progress.get(prev_key, 0) >= 3

        # czy to ostatnio uruchamiany dzień
        is_last = (day_num == last_day)

        with st.container():
            col1, col2, col3 = st.columns([3, 4, 4])

            # lewa kolumna – cały blok w niebieskim tle gdy is_last
            with col1:
                if is_last:
                    st.markdown(
                        f"""
                        <div style="
                            background-color: #edf7ff;
                            padding: 8px 12px;
                            border-radius: 8px;
                        ">
                        <strong>Dzień {day_num}</strong><br>
                        Odtworzenia: <strong>{count}</strong><br>
                        Status: {status}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        f"**Dzień {day_num}**  \n"
                        f"Odtworzenia: **{count}**  \n"
                        f"Status: {status}"
                    )

            # środkowa kolumna – słowa
            with col2:
                st.write(", ".join(words))

            # prawa kolumna – trzy małe przyciski (ikonki) w jednej linii
            with col3:
                bcol1, bcol2, bcol3 = st.columns(3)

                # START ▶️
                with bcol1:
                    start_clicked = st.button(
                        "▶️",
                        key=f"start_{day_num}",
                        help="Start treningu",
                        disabled=not can_play,
                    )
                if start_clicked and can_play:
                    st.session_state["view"] = "training"
                    st.session_state["training_day"] = day_num
                    st.session_state["last_day"] = day_num
                    st.rerun()

                # RESET 🔄
                with bcol2:
                    reset_clicked = st.button(
                        "🔄",
                        key=f"reset_{day_num}",
                        help="Reset licznika",
                    )
                if reset_clicked:
                    progress[day_num] = 0
                    save_progress(progress)
                    st.rerun()

                # RĘCZNE ZALICZENIE ✔️
                with bcol3:
                    manual_clicked = st.button(
                        "✔️",
                        key=f"manual_{day_num}",
                        help="Zalicz dzień ręcznie",
                    )
                if manual_clicked:
                    progress[day_num] = max(progress.get(day_num, 0), 3)
                    save_progress(progress)
                    st.rerun()

            st.markdown("")  # mały odstęp między dniami


# --- GŁÓWNA FUNKCJA ---

def main():
    st.set_page_config(page_title="Nauka czytania", layout="centered")

    if "view" not in st.session_state:
        st.session_state["view"] = "list"
    if "last_day" not in st.session_state:
        st.session_state["last_day"] = None

    words_by_day = load_words()
    if not words_by_day:
        st.error("Brak pliku words.json albo jest pusty.")
        st.stop()

    if st.session_state["view"] == "training":
        day = st.session_state.get("training_day")
        if day is None or day not in words_by_day:
            st.session_state["view"] = "list"
            st.rerun()
        training_screen(day, words_by_day[day])
    else:
        list_screen(words_by_day)


if __name__ == "__main__":
    main()
