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


# --- DATA ---

def load_words():
    if not WORDS_PATH.exists():
        return {}
    return json.load(open(WORDS_PATH, encoding="utf-8"))


def load_progress():
    if not PROGRESS_PATH.exists():
        return {}
    return json.load(open(PROGRESS_PATH, encoding="utf-8"))


def save_progress(p):
    json.dump(p, open(PROGRESS_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


# --- TTS ---

def get_tts_audio_path(word):
    h = hashlib.md5(word.encode()).hexdigest()
    path = TTS_DIR / f"{h}.mp3"
    if not path.exists():
        gTTS(word, lang="pl").save(path)
    return path


def autoplay(word):
    audio = get_tts_audio_path(word).read_bytes()
    b64 = base64.b64encode(audio).decode()
    st.markdown(f'<audio autoplay src="data:audio/mp3;base64,{b64}"></audio>', unsafe_allow_html=True)


# --- WORDS LOGIC ---

def words_until_day(words_by_day, day):
    out, seen = [], set()
    for d in range(1, int(day) + 1):
        for w in words_by_day.get(str(d), []):
            if w not in seen:
                seen.add(w)
                out.append(w)
    return out


def words_completed(words_by_day, progress):
    out, seen = [], set()
    for d, words in words_by_day.items():
        if progress.get(d, 0) >= 3:
            for w in words:
                if w not in seen:
                    seen.add(w)
                    out.append(w)
    return out


# --- GAME RESET ---

def reset_game():
    for k in list(st.session_state.keys()):
        if k.startswith("game_"):
            del st.session_state[k]


# --- TRAINING ---

def training(day, words):
    ph1, ph2 = st.empty(), st.empty()

    for w in random.sample(words, len(words)):
        ph1.markdown(f"<h1 style='color:red;text-align:center'>{w}</h1>", unsafe_allow_html=True)
        autoplay(w)
        time.sleep(3.5)
        ph1.empty()
        time.sleep(2)

    p = load_progress()
    p[day] = p.get(day, 0) + 1
    save_progress(p)

    st.session_state.view = "list"
    st.rerun()


# --- GAME 1 (3 options) ---

def game_multi(words):
    if len(words) < 3:
        st.error("Za mało słów")
        return

    if "game_target" not in st.session_state:
        t = random.choice(words)
        opts = random.sample([w for w in words if w != t], 2) + [t]
        random.shuffle(opts)

        st.session_state.game_target = t
        st.session_state.game_opts = opts
        st.session_state.game_feedback = None
        autoplay(t)

    target = st.session_state.game_target

    for w in st.session_state.game_opts:
        if st.session_state.game_feedback == w:
            color = "#2e7d32" if w == target else "#c62828"
            st.markdown(f"<div style='background:{color};color:white;padding:30px;font-size:60px;text-align:center;border-radius:12px'>{w}</div>", unsafe_allow_html=True)
        else:
            if st.button(w, use_container_width=True):
                st.session_state.game_feedback = w
                st.rerun()

    if st.session_state.game_feedback:
        time.sleep(1)
        if st.session_state.game_feedback == target:
            reset_game()
            st.session_state.view = "list"
        else:
            st.session_state.game_feedback = None
        st.rerun()


# --- GAME 2 (single word) ---

def game_single(words):
    if "game_word" not in st.session_state:
        w = random.choice(words)
        st.session_state.game_word = w
        autoplay(w)

    w = st.session_state.game_word

    if st.button(w, use_container_width=True):
        reset_game()
        st.session_state.view = "list"
        st.rerun()


# --- LIST SCREEN ---

def list_screen(words_by_day):
    st.title("Nauka czytania")

    progress = load_progress()

    # --- GLOBAL GAMES ---
    completed_words = words_completed(words_by_day, progress)

    colg1, colg2 = st.columns(2)

    if colg1.button("🎮 Gra (zaliczone dni)", disabled=len(completed_words) < 3):
        reset_game()
        st.session_state.view = "game_multi"
        st.session_state.game_words = completed_words
        st.rerun()

    if colg2.button("🎯 1 słowo (zaliczone dni)", disabled=len(completed_words) < 1):
        reset_game()
        st.session_state.view = "game_single"
        st.session_state.game_words = completed_words
        st.rerun()

    st.markdown("---")

    # --- DAYS ---
    for day, words in sorted(words_by_day.items(), key=lambda x: int(x[0])):
        count = progress.get(day, 0)
        done = count >= 3

        st.write(f"### Dzień {day} ({count})")

        c1, c2, c3, c4 = st.columns(4)

        if c1.button("▶️", key=f"t{day}"):
            st.session_state.view = "training"
            st.session_state.day = day
            st.rerun()

        if c2.button("🎮", key=f"g{day}", disabled=not done):
            reset_game()
            st.session_state.view = "game_multi"
            st.session_state.game_words = words_until_day(words_by_day, day)
            st.rerun()

        if c3.button("🎯", key=f"s{day}", disabled=not done):
            reset_game()
            st.session_state.view = "game_single"
            st.session_state.game_words = words_until_day(words_by_day, day)
            st.rerun()

        if c4.button("✔️", key=f"m{day}"):
            progress[day] = 3
            save_progress(progress)
            st.rerun()

        st.write(", ".join(words))


# --- MAIN ---

def main():
    if "view" not in st.session_state:
        st.session_state.view = "list"

    words = load_words()

    if st.session_state.view == "training":
        training(st.session_state.day, words[st.session_state.day])

    elif st.session_state.view == "game_multi":
        game_multi(st.session_state.game_words)

    elif st.session_state.view == "game_single":
        game_single(st.session_state.game_words)

    else:
        list_screen(words)


if __name__ == "__main__":
    main()
