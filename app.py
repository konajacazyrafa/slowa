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
TTS_DIR = BASE_DIR / "tls_cache"
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


# --- AUDIO ---

def get_tts_audio_path(word: str) -> Path:
    h = hashlib.md5(word.encode("utf-8")).hexdigest()
    p = TTS_DIR / f"{h}.mp3"
    if not p.exists():
        gTTS(text=word, lang="pl").save(str(p))
    return p


def play_word(word, overlay_placeholder, audio_placeholder):
    overlay_html = f"""
    <div style="
        position: fixed; top:0; left:0;
        width:100vw; height:100vh;
        background: rgba(0, 0, 0, 0.6);
        display:flex; justify-content:center; align-items:center;
        z-index:9999;
    ">
        <div style="
            background:white; padding:2rem 3rem;
            border-radius:1rem;
            box-shadow:0 0 30px rgba(0,0,0,0.4);
            text-align:center;
        ">
            <div style="font-size:80px; color:red; font-family:sans-serif;">
                {word}
            </div>
        </div>
    </div>
    """

    overlay_placeholder.markdown(overlay_html, unsafe_allow_html=True)

    audio_path = get_tts_audio_path(word)
    with audio_path.open("rb") as f:
        audio_bytes = f.read()

    audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

    audio_placeholder.markdown(
        f"""
        <audio autoplay>
            <source src="data:audio/mp3;base64,{audio_b64}" type="audio/mp3">
        </audio>
        """,
        unsafe_allow_html=True,
    )


# --- EKRAN TRENINGU ---

def training_screen(day_num, words):
    if len(words) != 5:
        st.session_state["view"] = "list"
        st.rerun()

    overlay = st.empty()
    audio = st.empty()

    for w in random.sample(words, len(words)):
        play_word(w, overlay, audio)
        time.sleep(3.5)
        overlay.empty()
        audio.empty()
        time.sleep(2)

    progress = load_progress()
    progress[day_num] = progress.get(day_num, 0) + 1
    save_progress(progress)

    st.session_state["view"] = "list"
    st.rerun()


# --- PRZYCISK Z IKONĄ I TOOLTIPEM ---

def icon_button(icon, tooltip, key, disabled=False):
    btn_html = f"""
    <button title="{tooltip}"
        style="
            background:#f0f0f0;
            border:1px solid #ccc;
            padding:6px 10px;
            border-radius:6px;
            font-size:20px;
            cursor:pointer;
            margin-right:8px;
        "
        {'disabled' if disabled else ''}
        onClick="fetch('/_st_btn/{key}').then(() => window.parent.location.reload());"
    >{icon}</button>

    <script>
    const b = document.querySelector('button[title="{tooltip}"]');
    if (b) {{
        b.onclick = () => fetch('/_st_btn/{key}');
    }}
    </script>
    """
    st.markdown(btn_html, unsafe_allow_html=True)


# --- HACK DO OBSŁUGI "gołego HTML-owego kliknięcia" ---
# (minimalny serwerowy endpoint do obsługi wciśnięcia guzika).
# W Streamlit Cloud działa OK.

if "_st_btn_callbacks" not in st.session_state:
    st.session_state["_st_btn_callbacks"] = {}

def register_html_button(key, callback):
    st.session_state["_st_btn_callbacks"][key] = callback

def process_html_buttons():
    params = st.query_params
    if "_st_btn" in params:
        key = params["_st_btn"]
        if key in st.session_state["_st_btn_callbacks"]:
            st.session_state["_st_btn_callbacks"][key]()
            st.query_params.clear()
            st.rerun()


# --- EKRAN LISTY DNI ---

def list_screen(words_by_day):
    st.title("Trening słownictwa")

    progress = load_progress()
    last_day = st.session_state.get("last_day")
    days_sorted = sorted(words_by_day.items(), key=lambda x: int(x[0]))

    for day_num, words in days_sorted:
        dn = int(day_num)
        count = progress.get(day_num, 0)
        status = "✅ zaliczony" if count >= 3 else "⏳ w trakcie"

        if dn == 1:
            can_play = True
        else:
            can_play = progress.get(str(dn - 1), 0) >= 3

        row_bg = "background:#e6f3ff;" if day_num == last_day else ""

        st.markdown(
            f"<div style='{row_bg} padding:0.6rem; border-radius:0.4rem;'>",
            unsafe_allow_html=True,
        )

        cols = st.columns([3, 4, 4])

        with cols[0]:
            st.markdown(
                f"**Dzień {day_num}**  \n"
                f"Odtworzenia: **{count}**  \n"
                f"Status: {status}"
            )

        with cols[1]:
            st.write(", ".join(words))

        with cols[2]:
            # rejestracja akcji
            start_key = f"start_{day_num}"
            reset_key = f"reset_{day_num}"
            manual_key = f"manual_{day_num}"

            def do_start(day=day_num):
                st.session_state["view"] = "training"
                st.session_state["training_day"] = day
                st.session_state["last_day"] = day

            def do_reset(day=day_num):
                progress = load_progress()
                progress[day] = 0
                save_progress(progress)

            def do_manual(day=day_num):
                progress = load_progress()
                progress[day] = 3
                save_progress(progress)

            register_html_button(start_key, do_start)
            register_html_button(reset_key, do_reset)
            register_html_button(manual_key, do_manual)

            # ikonki w jednej linii
            icon_button("▶️", "Start treningu", start_key, disabled=not can_play)
            icon_button("🔄", "Reset licznika", reset_key)
            icon_button("✔️", "Zalicz ręcznie", manual_key)

        st.markdown("</div>", unsafe_allow_html=True)


# --- GŁÓWNA FUNKCJA ---

def main():
    st.set_page_config(page_title="Trening słów", layout="centered")

    if "view" not in st.session_state:
        st.session_state["view"] = "list"

    process_html_buttons()

    words = load_words()
    if not words:
        st.error("Brak pliku words.json!")
        return

    if st.session_state["view"] == "training":
        d = st.session_state.get("training_day")
        training_screen(d, words[d])
    else:
        list_screen(words)


if __name__ == "__main__":
    main()
