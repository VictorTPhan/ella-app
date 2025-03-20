import os
import json
import random
import streamlit as st

# Access the OpenAI API key from the secrets
api_key = st.secrets["OPENAI_API_KEY"]

# 3) Use your custom OpenAI class
from openai import OpenAI
client = OpenAI(api_key=api_key)

# --------------------------------------
# 2. Helper Functions (Same as Original, but no repeated generation)
# --------------------------------------

def get_json_response(system_prompt, user_prompt):
    response = client.chat.completions.create(
        model="gpt-4o",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )
    return json.loads(response.choices[0].message.content)

def get_random_topic():
    system_prompt = """
    A user will ask for a random topic from you. They want to learn Korean.
    Your response will be in JSON format, as so:

    {
        "topic": "<string>",
        "tutorial": "<how to translate into Korean>"
    }
    """
    user_prompt = "Come up with a random noun or phrase."
    return get_json_response(system_prompt, user_prompt)

def make_korean_sentence(topic):
    system_prompt = """
    Come up with a sentence in Korean. You will clip off the subject of the sentence.
    Your response will be in JSON format, as so:

    {
        "subject": "<string>",
        "sentence_with_blank": "<string>"
    }
    """
    return get_json_response(system_prompt, topic)

def english_to_korean(english):
    system_prompt = """
    A user will give you an English phrase. Translate it into Korean (Hangul).
    Your response will be in JSON format, as so:

    {
        "hangul": "<string>"
    }
    """
    return get_json_response(system_prompt, english)["hangul"]

def english_to_korean_pronunciation(english):
    system_prompt = """
    I want to be able to speak Korean without knowing any Korean. I will give you an English phrase.
    Translate it into Korean, and for each syllable, give me the closest sounding word in English.
    Your response will be in JSON format, as so:

    {
        "thought_process": "<string>",
        "final_sequence": "<string>"
    }
    """
    return get_json_response(system_prompt, english)

def hangul_to_korean_pronunciation(korean):
    system_prompt = """
    I want to be able to speak Korean without knowing any Korean. I will give you a Korean phrase.
    For each syllable, give me the closest sounding word in English.
    Your response will be in JSON format, as so:

    {
        "thought_process": "<string>",
        "final_sequence": "<string>"
    }
    """
    return get_json_response(system_prompt, korean)

def create_wrong_answers(correct_answer):
    system_prompt = """
    A user will give you a string representing a sequence of phonetic syllables.
    Modify the sequence 3 times, such that each one would be pronounced different and looks significantly different.
    Your response will be in JSON format, as so:

    {
        "mutation_1": "<string>",
        "mutation_2": "<string>",
        "mutation_3": "<string>"
    }
    """
    wrong_answers = get_json_response(system_prompt, correct_answer)
    return list(wrong_answers.values())

# --------------------------------------
# 3. Streamlit Setup
# --------------------------------------

st.title("Korean Learning Game")

# We use session_state to store data so that it doesn't regenerate on each interaction
if "topic_info" not in st.session_state:
    st.session_state.topic_info = None
if "step" not in st.session_state:
    st.session_state.step = 0

# For each step, we'll store all the data needed for that question exactly once
# so that multiple re-runs don't change the question
if "hangul_quiz_data" not in st.session_state:
    st.session_state.hangul_quiz_data = {}
if "english_quiz_data" not in st.session_state:
    st.session_state.english_quiz_data = {}
if "fill_blank_data" not in st.session_state:
    st.session_state.fill_blank_data = {}

def next_step():
    st.session_state.step += 1

def reset_game():
    st.session_state.topic_info = None
    st.session_state.step = 0
    st.session_state.hangul_quiz_data = {}
    st.session_state.english_quiz_data = {}
    st.session_state.fill_blank_data = {}

# --------------------------------------
# 4. Step-by-step logic
# --------------------------------------

def run_game_step():
    """
    Steps:
      0: Generate a random topic and show it.
      1: ask_hangul_to_korean
      2: ask_english_to_korean
      3: fill_in_blank
      4: Ask to continue or end
    """
    step = st.session_state.step

    # STEP 0: Get a random topic
    if step == 0:
        st.subheader("Step 1: Generate a Random Topic")
        if st.session_state.topic_info is None:
            st.session_state.topic_info = get_random_topic()
        topic_info = st.session_state.topic_info

        st.write("**Topic:**", topic_info["topic"])
        st.write("**Tutorial:**", topic_info["tutorial"])

        if st.button("Next: Pronunciation from Hangul"):
            next_step()

    # STEP 1: Pronunciation from Hangul
    elif step == 1:
        st.subheader("Step 2: Pronunciation from Hangul")
        topic = st.session_state.topic_info["topic"]

        # Only generate data if we haven't already
        if not st.session_state.hangul_quiz_data:
            # 1) English -> Hangul
            hangul = english_to_korean(topic)
            # 2) Hangul -> phonetic
            translation = hangul_to_korean_pronunciation(hangul)
            correct_answer = translation["final_sequence"]
            explanation = translation["thought_process"]
            # 3) Create wrong answers
            wrong_answers = create_wrong_answers(correct_answer)
            answer_choices = wrong_answers + [correct_answer]
            random.shuffle(answer_choices)

            # Store in session_state
            st.session_state.hangul_quiz_data = {
                "hangul": hangul,
                "correct_answer": correct_answer,
                "explanation": explanation,
                "answer_choices": answer_choices
            }

        # Retrieve stored data so it doesn't change on rerun
        data = st.session_state.hangul_quiz_data
        st.write("What is the pronunciation of the following Korean text?")
        st.write(f"**{data['hangul']}**")

        # Let the user pick
        user_choice = st.radio(
            "Choose the correct answer:",
            data["answer_choices"],
            key="hangul_choice"
        )

        if st.button("Check Answer"):
            if user_choice == data["correct_answer"]:
                st.success("Correct!")
            else:
                st.error("Wrong!")
                st.write("**Correct Answer:**", data["correct_answer"])
                st.write("**Explanation:**", data["explanation"])
            st.button("Next: Pronunciation from English", on_click=next_step)

    # STEP 2: Pronunciation from English
    elif step == 2:
        st.subheader("Step 3: Pronunciation from English")
        topic = st.session_state.topic_info["topic"]

        if not st.session_state.english_quiz_data:
            # Generate data once
            translation = english_to_korean_pronunciation(topic)
            correct_answer = translation["final_sequence"]
            explanation = translation["thought_process"]
            # wrong answers
            wrong_answers = create_wrong_answers(correct_answer)
            answer_choices = wrong_answers + [correct_answer]
            random.shuffle(answer_choices)

            st.session_state.english_quiz_data = {
                "correct_answer": correct_answer,
                "explanation": explanation,
                "answer_choices": answer_choices
            }

        data = st.session_state.english_quiz_data

        st.write("What is the Korean pronunciation of this English word or phrase?")
        st.write(f"**{topic}**")

        user_choice = st.radio(
            "Choose the correct answer:",
            data["answer_choices"],
            key="english_choice"
        )

        if st.button("Check Answer"):
            if user_choice == data["correct_answer"]:
                st.success("Correct!")
            else:
                st.error("Wrong!")
                st.write("**Correct Answer:**", data["correct_answer"])
                st.write("**Explanation:**", data["explanation"])
            st.button("Next: Fill-in-the-Blank", on_click=next_step)

    # STEP 3: Fill-in-the-Blank
    elif step == 3:
        st.subheader("Step 4: Fill in the Blank")
        topic = st.session_state.topic_info["topic"]

        if not st.session_state.fill_blank_data:
            sentence_data = make_korean_sentence(topic)
            subject = sentence_data["subject"]
            sentence_with_blank = sentence_data["sentence_with_blank"]

            # Convert subject to phonetic
            translation = hangul_to_korean_pronunciation(subject)
            correct_answer = translation["final_sequence"]
            explanation = translation["thought_process"]

            wrong_answers = create_wrong_answers(correct_answer)
            answer_choices = wrong_answers + [correct_answer]
            random.shuffle(answer_choices)

            st.session_state.fill_blank_data = {
                "sentence_with_blank": sentence_with_blank,
                "correct_answer": correct_answer,
                "explanation": explanation,
                "answer_choices": answer_choices
            }

        data = st.session_state.fill_blank_data

        st.write("Fill in the blank in this Korean sentence:")
        st.write(f"**{data['sentence_with_blank']}**")

        user_choice = st.radio(
            "Which subject completes the sentence?",
            data["answer_choices"],
            key="fillin_choice"
        )

        if st.button("Check Answer"):
            if user_choice == data["correct_answer"]:
                st.success("Correct!")
            else:
                st.error("Wrong!")
                st.write("**Correct Answer:**", data["correct_answer"])
                st.write("**Explanation:**", data["explanation"])
            st.button("Next: Continue or End", on_click=next_step)

    # STEP 4: Ask to continue or end
    elif step == 4:
        st.subheader("Step 5: Continue or End?")
        col1, col2 = st.columns(2)

        with col1:
            if st.button("New Topic!"):
                reset_game()

        with col2:
            if st.button("End Game"):
                st.write("---")
                st.write("# Thanks for playing!")
                st.stop()

# --------------------------------------
# 5. Start the game
# --------------------------------------
run_game_step()
