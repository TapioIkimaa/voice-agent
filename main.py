import io
import json
from contextlib import asynccontextmanager
import soundfile
import torch
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from faster_whisper import WhisperModel
from sentence_transformers import SentenceTransformer, util
from starlette.responses import StreamingResponse
from transformers import AutoModelForTextToWaveform, AutoTokenizer, pipeline

load_dotenv()

# Predefined appointment types and slots
APPOINTMENT_TYPES = ["hammaslääkäri", "suuhygienisti", "työterveys"]
AVAILABLE_SLOTS = [
    {"type": "hammaslääkäri", "time": "torstaina kello yksitoista"},
    {"type": "hammaslääkäri", "time": "tiistaina kello yhdeksän"},
    {"type": "suuhygienisti", "time": "maanantaina kello viisitoista"},
    {"type": "työterveys", "time": "keskiviikkona kello kolmetoista"},
]

# Global Variables for Models and Data
stt_whisper: WhisperModel
tts_pipeline: tuple[any, any] = (None, None)
ner_pipeline: pipeline
zero_shot_classifier: pipeline
sentence_transformer: SentenceTransformer

# In-memory conversation state for a single user
conversation_state = {
    "current_step": "greeting",
    "appointment_type": None,
    "preferred_time": None,
    "selected_time": None,
    "user_name": None,
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Asynchronously loads all required models and data when the application starts.
    """
    global stt_whisper, tts_pipeline, ner_pipeline, zero_shot_classifier, sentence_transformer

    print("Loading Speech-to-Text (STT) model...")
    stt_whisper = WhisperModel("medium", compute_type="auto")
    print("STT model loaded.")

    print("Loading Text-to-Speech (TTS) model...")
    tts_model_id = "facebook/mms-tts-fin"
    tts_model = AutoModelForTextToWaveform.from_pretrained(tts_model_id)
    tts_tokenizer = AutoTokenizer.from_pretrained(tts_model_id)
    tts_pipeline = (tts_model, tts_tokenizer)
    print("TTS model loaded.")

    print("Loading token classification model...")
    ner_pipeline = pipeline("token-classification", model="Davlan/bert-base-multilingual-cased-ner-hrl",
                            aggregation_strategy="simple")
    print("Token classification model loaded.")

    print("Loading zero-shot classification model...")
    zero_shot_classifier = pipeline("zero-shot-classification", model="MoritzLaurer/mDeBERTa-v3-base-mnli-xnli")
    print("Zero-shot classification model loaded.")

    print("Loading sentence transformer model...")
    sentence_transformer = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    print("Sentence transformer model loaded.")

    yield


app = FastAPI(lifespan=lifespan)
# Mount the static directory to serve the frontend files
app.mount("/static", StaticFiles(directory="static"), name="static")

yes_meanings = [
    "kyllä", "joo", "totta kai", "tietysti", "ehdottomasti", "kyllä vain",
    "juuri niin", "varmaan", "ilman muuta", "totta", "sopii", "ok", "hyvä on", "mielellään"
]

no_meanings = [
    "ei", "en", "en halua", "ei nyt", "ei kiitos", "ei koskaan",
    "ei sovi", "ei ole mahdollista", "ei tällä kertaa", "ei onnistu",
    "ei todellakaan", "ei kiinnosta", "ei ole tarvetta", "ei ole"
]


def get_max_similarity(text: str, meanings: list[str]) -> float:
    """Calculates the maximum cosine similarity between a text and a list of meanings."""
    text_embedding = sentence_transformer.encode(text, convert_to_tensor=True)
    meanings_embeddings = sentence_transformer.encode(meanings, convert_to_tensor=True)
    cosine_scores = util.pytorch_cos_sim(text_embedding, meanings_embeddings)
    return torch.max(cosine_scores).item()


@app.get("/")
async def read_index():
    return FileResponse("static/index.html")


@app.post("/process-recording")
async def process_audio(recording: UploadFile):
    audio_bytes = await recording.read()
    segments, info = stt_whisper.transcribe(io.BytesIO(audio_bytes), language="fi")
    transcript = " ".join([segment.text.strip() for segment in segments])
    print(f"User said: {transcript}")

    response_text = "En valitettavasti ymmärtänyt, voisitko toistaa?"

    if conversation_state["current_step"] == "greeting":
        response_text = "Tervetuloa! Minkä tyyppisen ajan haluaisit varata?"
        conversation_state["current_step"] = "ask_appointment_type"

    elif conversation_state["current_step"] == "ask_appointment_type":
        result = zero_shot_classifier(transcript, APPOINTMENT_TYPES)
        found_type = result["labels"][0]
        confidence = result["scores"][0]

        if confidence > 0.6:
            conversation_state["appointment_type"] = found_type
            response_text = f"Selvä, {found_type}aika. Onko sinulla toiveita ajankohdalle?"
            conversation_state["current_step"] = "ask_preferred_time"
        else:
            response_text = "En valitettavasti ymmärtänyt. Minkä tyyppisen ajan haluaisit varata, hammaslääkäri, suuhygienisti vai työterveys?"

    elif conversation_state["current_step"] == "ask_preferred_time":
        matching_slots = [s for s in AVAILABLE_SLOTS if s["type"] == conversation_state["appointment_type"]]
        if len(matching_slots) == 0:
            response_text = "Valitettavasti en löytänyt vapaita aikoja valitsemallesi palvelulle. Minkä tyyppisen ajan haluaisit varata?"
            conversation_state["current_step"] = "ask_appointment_type"
        elif len(matching_slots) == 1:
            response_text = f"Löytyi vapaa aika, {matching_slots[0]["time"]}. Millä nimellä varaus tehdään?"
            conversation_state["current_step"] = "ask_name"
        else:
            response_text = "Vapaita aikoja ovat: " + ", ".join(
                [s["time"] for s in matching_slots]) + ". Minkä näistä haluaisit varata?"
            conversation_state["current_step"] = "suggest_slots"

    elif conversation_state["current_step"] == "suggest_slots":
        matching_slots = [s for s in AVAILABLE_SLOTS if s["type"] == conversation_state["appointment_type"]]
        result = zero_shot_classifier(transcript, [s["time"] for s in matching_slots])
        found_type = result["labels"][0]
        confidence = result["scores"][0]
        if confidence > 0.5:
            selected_slot = next((s for s in matching_slots if s["time"] == found_type), None)
            conversation_state["selected_time"] = selected_slot["time"]
            response_text = f"Valitsit ajan {selected_slot["time"]} palvelulle {selected_slot["type"]}. Millä nimellä varaus tehdään?"
            conversation_state["current_step"] = "ask_name"
        else:
            response_text = "Valitettavasti en tunnistanut valitsemaasi aikaa. Vapaita aikoja ovat: " + ", ".join(
                [s["time"] for s in matching_slots]) + ". Minkä näistä haluaisit varata?"

    elif conversation_state["current_step"] == "ask_name":
        user_name = transcript.strip()
        conversation_state["user_name"] = user_name
        response_text = f"Kiitos, {user_name}. Vahvistetaan varaus: {conversation_state["appointment_type"]} {conversation_state["selected_time"]}. Onko tämä oikein?"
        conversation_state["current_step"] = "confirm_booking"

    elif conversation_state["current_step"] == "confirm_booking":
        yes_similarity = get_max_similarity(transcript, yes_meanings)
        no_similarity = get_max_similarity(transcript, no_meanings)

        if yes_similarity > no_similarity and yes_similarity > 0.4:
            response_text = f"Kiitos! Varauksesi on vahvistettu. Tervetuloa!"
            conversation_state["current_step"] = "greeting"

            bookings_file = "bookings.json"
            try:
                with open(bookings_file, "r") as f:
                    bookings = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                bookings = []
            bookings.append({
                "name": conversation_state["user_name"],
                "appointment_type": conversation_state["appointment_type"],
                "time": conversation_state["selected_time"],
            })
            with open(bookings_file, "w", encoding="utf-8") as f:
                json.dump(bookings, f, ensure_ascii=False, indent=4)

        elif no_similarity > yes_similarity and no_similarity > 0.4:
            response_text = "Selvä, peruutetaan varaus. Haluatko aloittaa alusta?"
            conversation_state["current_step"] = "greeting"
        else:
            response_text = "En valitettavasti ymmärtänyt. Vahvistetaanko varaus: kyllä vai ei?"

    print(f"Agent says: {response_text}")
    model, tokenizer = tts_pipeline
    inputs = tokenizer(response_text, return_tensors="pt")
    with torch.no_grad():
        output = model(**inputs).waveform
    buffer = io.BytesIO()
    soundfile.write(buffer, output.squeeze().numpy(), samplerate=model.config.sampling_rate, format="WAV")
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="audio/wav")
