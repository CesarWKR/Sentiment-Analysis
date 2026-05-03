from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.requests import Request
from pydantic import BaseModel, constr, StringConstraints
from typing import Annotated
from transformers import RobertaTokenizer, RobertaForSequenceClassification, MarianMTModel, MarianTokenizer
import torch
import torch.nn.functional as F
from langdetect import detect
import uvicorn
import os

# Define labels
LABELS = ["Negative", "Neutral", "Positive"]

# Set device
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"🚀 Using device: {DEVICE}")

# Load model and tokenizer
MODEL_PATH = "Roberta_sentiment_model"
if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(f"Model path '{MODEL_PATH}' not found. Make sure it's correctly mounted.")

print("📦 Loading Sentiment model and tokenizer...")
tokenizer = RobertaTokenizer.from_pretrained(MODEL_PATH)
model = RobertaForSequenceClassification.from_pretrained(MODEL_PATH).to(DEVICE)
model.eval()

translation_models = {}
translation_tokenizers = {}

def get_translation_model(lang: str):
    """
    Returns the correct translation model name for a given language.
    """
    model_map = {
        "es": "Helsinki-NLP/opus-mt-es-en",
        "fr": "Helsinki-NLP/opus-mt-fr-en",
        "de": "Helsinki-NLP/opus-mt-de-en",
        "it": "Helsinki-NLP/opus-mt-it-en",
    }
    if lang not in model_map:
        return None

    return model_map.get(lang, None)


def load_translation_model(lang: str):
    """
    Load translation model and tokenizer dynamically and cache them.
    """
    model_name = get_translation_model(lang)

    if model_name is None:
        return None, None

    # If already loaded, reuse it
    if model_name in translation_models:
        return translation_models[model_name], translation_tokenizers[model_name]

    print(f"🌎 Loading translation model for '{lang}'...")

    tokenizer = MarianTokenizer.from_pretrained(model_name)
    model = MarianMTModel.from_pretrained(model_name).to(DEVICE)
    model.eval()

    translation_models[model_name] = model
    translation_tokenizers[model_name] = tokenizer

    return model, tokenizer

# LANGUAGE DETECTION + TRANSLATION
def translate_to_english(text: str, lang: str) -> str:
    model, tokenizer = load_translation_model(lang)

    if model is None:
        print(f"⚠ No translation model available for language: {lang}")
        return text  # fallback: return original text

    tokens = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        padding=True
    ).to(DEVICE)

    with torch.no_grad():
        translated = model.generate(**tokens)

    return tokenizer.decode(translated[0], skip_special_tokens=True)


def preprocess_text(text: str) -> str:
    try:
        lang = detect(text)
        print(f"Detected language: {lang}")

        if lang != "en":
            print(f"Translating from {lang} to English...")
            text = translate_to_english(text, lang)

    except Exception as e:
        print(f"⚠ Language detection failed: {e}")

    return text


# Input model
class TextInput(BaseModel):
    #text: constr(min_length=1, max_length=1000)
    text: Annotated[str, StringConstraints(min_length=1, max_length=500)]

# FastAPI app
app = FastAPI(title="Sentiment Analysis API", description="RoBERTa model for sentiment classification.", version="2.0.0")

if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static") # Mount static files for serving CSS/JS
    
templates = Jinja2Templates(directory="templates")   # Directory for HTML templates


def predict_sentiment(text: str) -> dict:
    """Predict sentiment from raw text."""
    MAX_TOKENS = 256

    encoding_test = tokenizer(text, truncation=False, return_tensors="pt")
    initial_token_count = len(encoding_test["input_ids"][0])

    if initial_token_count > MAX_TOKENS:
        raise ValueError(f"Text exceeds maximum token limit of {MAX_TOKENS}. Please shorten your input.")

    # Step 1: Detect language + translate if needed
    processed_text = preprocess_text(text)

    # Step 2: Tokenize for sentiment model
    encoding = tokenizer(processed_text, truncation=True, padding="max_length", max_length=MAX_TOKENS, return_tensors="pt")

    if len(encoding["input_ids"][0]) > MAX_TOKENS:
         raise ValueError(f"Processed text exceeds {MAX_TOKENS} tokens. Please review the content.")

    input_ids = encoding["input_ids"].to(DEVICE)
    attention_mask = encoding["attention_mask"].to(DEVICE)

    with torch.no_grad():
        outputs = model(input_ids, attention_mask=attention_mask)  
        probs = F.softmax(outputs.logits, dim=1).cpu().numpy()[0]
        predicted_idx = probs.argmax()

    return {
        "original_text": text,
        "processed_text": processed_text,
        "label_index": int(predicted_idx),
        "label": LABELS[predicted_idx],
        "probabilities": {LABELS[i]: float(p) for i, p in enumerate(probs)}
    }

@app.get("/form", response_class=HTMLResponse)   # Root endpoint to serve the HTML page
async def serve_form(request: Request):   # Function to render the HTML form
    """Serve the HTML form for sentiment analysis."""
    return templates.TemplateResponse("index.html", {"request": request})  # Endpoint to render index.html

@app.post("/predict")
def analyze_sentiment(input_text: TextInput):
    try:
        prediction = predict_sentiment(input_text.text)
        return {"input": input_text.text, "prediction": prediction}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) 
    
    except Exception as e:
        raise HTTPException(status_code=500, detail="An unexpected error occurred. Please try again later.")

# To run locally (optional)
if __name__ == "__main__":
    uvicorn.run("inference_api:app", host="0.0.0.0", port=8000, reload=True)
