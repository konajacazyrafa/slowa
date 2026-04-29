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


# --- LOGIKA SŁÓW DO GRY ---

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


# --- EKRAN TRENINGU ---

def training_screen(day_num: str, words: list[str]):
    if len(words) != 5:
        st.error(f"Dzień {day_num} musi mieć dokładnie 5 słów, a ma {len(words)}.")
        st.session_state["view"] = "list"
        st.rerun()
        return

    overlay_placeholder = st.empty()
    audio_placeholder = st.empty()

    for word in random.sample(words, len(words)):
        play_word(word, overlay_placeholder, audio_placeholder)
        time.sleep(3.5)
        overlay_placeholder.empty()
        audio_placeholder.empty()
        time.sleep(2.0)

    progress = load_progress()
    progress[day_num] = progress.get(day_num, 0) + 1
    save_progress(progress)

    st.session_state["view"] = "list"
    st.rerun()


# --- EKRAN GRY ---

def game_screen(day_num: str, words_by_day: dict):
    all_words = unique_words_until_day(words_by_day, day_num)

    if len(all_words) < 3:
        st.error("Do gry potrzebne są co najmniej 3 różne słowa.")
        if st.button("Wróć"):
            reset_game_state()
            st.session_state["view"] = "list"
            st.rerun()
        return

    if (
        st.session_state.get("game_day") != day_num
        or "game_target" not in st.session_state
        or "game_options" not in st.session_state
    ):
        target = random.choice(all_words)
        others = [w for w in all_words if w != target]
        options = random.sample(others, 2) + [target]
        random.shuffle(options)

        st.session_state["game_day"] = day_num
        st.session_state["game_target"] = target
        st.session_state["game_options"] = options
        st.session_state["game_audio_pending"] = True
        st.session_state["game_feedback_word"] = None
        st.session_state["game_feedback_correct"] = None

    target = st.session_state["game_target"]
    options = st.session_state["game_options"]
    feedback_word = st.session_state.get("game_feedback_word")
    feedback_correct = st.session_state.get("game_feedback_correct")

    audio_placeholder = st.empty()

    if st.session_state.get("game_audio_pending"):
        autoplay_audio(target, audio_placeholder)
        st.session_state["game_audio_pending"] = False

    st.markdown(
        """
        <style>
        .game-overlay {
            position: fixed;
            inset: 0;
            width: 100vw;
            height: 100vh;
            background: rgba(0, 0, 0, 0.6);
            z-index: 9000;
        }

        .main .block-container {
            position: relative;
            z-index: 9999;
            padding-top: 10vh !important;
            max-width: 100vw !important;
        }

        div.stButton > button {
            width: 100% !important;
            min-height: 150px !important;
            background-color: white !important;
            color: red !important;
            font-size: 80px !important;
            font-family: sans-serif !important;
            border-radius: 1rem !important;
            border: none !important;
            box-shadow: 0 0 20px rgba(0,0,0,0.3) !important;
            margin-bottom: 24px !important;
            text-align: center !important;
        }

        div.stButton > button:hover {
            background-color: white !important;
            color: red !important;
            border: none !important;
        }

        div.stButton > button:focus {
            background-color: white !important;
            color: red !important;
            border: none !important;
            outline: none !important;
            box-shadow: 0 0 20px rgba(0,0,0,0.3) !important;
        }

        div.stButton > button:active {
            background-color: white !important;
            color: red !important;
            border: none !important;
        }
        </style>

        <div class="game-overlay"></div>
        """,
        unsafe_allow_html=True,
    )

    left, center, right = st.columns([1, 3, 1])

    with center:
        for word in options:
            if feedback_word == word:
                bg = "#2e7d32" if feedback_correct else "#c62828"

                st.markdown(
                    f"""
                    <div style="
                        width: 100%;
                        min-height: 150px;
                        background-color: {bg};
                        color: white;
                        font-size: 80px;
                        font-family: sans-serif;
                        border-radius: 1rem;
                        box-shadow: 0 0 20px rgba(0,0,0,0.3);
                        margin-bottom: 24px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        text-align: center;
                    ">
                        {word}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                clicked = st.button(word, key=f"game_{day_num}_{word}")
                if clicked:
                    st.session_state["game_feedback_word"] = word
                    st.session_state["game_feedback_correct"] = (word == target)
                    st.rerun()

    if feedback_word is not None:
        time.sleep(1)

        if feedback_correct:
            reset_game_state()
            st.session_state["view"] = "list"
            st.rerun()
        else:
            st.session_state["game_feedback_word"] = None
            st.session_state["game_feedback_correct"] = None
            st.rerun()


# --- EKRAN LISTY DNI ---

def list_screen(words_by_day: dict):
    st.title("Nauka czytania")

    st.markdown(
        "Uruchom trening z wybranego dnia. "
        "Ostatni uruchamiany dzień jest podświetlony. "
        "Aby uruchomić nowy dzień, zalicz 3 powtórzenia dnia poprzedniego."
    )

    progress = load_progress()
    days_sorted = sorted(words_by_day.items(), key=lambda x: int(x[0]))
    last_day = st.session_state.get("last_day")

    for day_num, words in days_sorted:
        dn_int = int(day_num)
        count = progress.get(day_num, 0)
        status = "✅ zaliczony" if count >= 3 else "⏳ w trakcie"

        if dn_int == 1:
            can_play = True
        else:
            can_play = progress.get(str(dn_int - 1), 0) >= 3

        can_game = count >= 3
        is_last = day_num == last_day

        with st.container():
            col1, col2, col3 = st.columns([3, 4, 5])

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

            with col2:
                st.write(", ".join(words))

            with col3:
                bcol1, bcol2, bcol3, bcol4 = st.columns(4)

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

                with bcol2:
                    game_clicked = st.button(
                        "🎮",
                        key=f"game_start_{day_num}",
                        help="Gra dostępna po zaliczeniu dnia",
                        disabled=not can_game,
                    )

                if game_clicked and can_game:
                    reset_game_state()
                    st.session_state["view"] = "game"
                    st.session_state["game_day"] = day_num
                    st.session_state["last_day"] = day_num
                    st.rerun()

                with bcol3:
                    reset_clicked = st.button(
                        "🔄",
                        key=f"reset_{day_num}",
                        help="Reset licznika",
                    )

                if reset_clicked:
                    progress[day_num] = 0
                    save_progress(progress)
                    st.rerun()

                with bcol4:
                    manual_clicked = st.button(
                        "✔️",
                        key=f"manual_{day_num}",
                        help="Zalicz dzień ręcznie",
                    )

                if manual_clicked:
                    progress[day_num] = max(progress.get(day_num, 0), 3)
                    save_progress(progress)
                    st.rerun()

            st.markdown("")


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

    elif st.session_state["view"] == "game":
        day = st.session_state.get("game_day")

        if day is None or day not in words_by_day:
            reset_game_state()
            st.session_state["view"] = "list"
            st.rerun()

        game_screen(day, words_by_day)

    else:
        list_screen(words_by_day)


if __name__ == "__main__":
    main()
