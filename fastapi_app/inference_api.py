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

print("🌎 Loading translation model...")
TRANS_MODEL_NAME = "Helsinki-NLP/opus-mt-es-en"
translator_tokenizer = MarianTokenizer.from_pretrained(TRANS_MODEL_NAME)
translator_model = MarianMTModel.from_pretrained(TRANS_MODEL_NAME).to(DEVICE)
translator_model.eval()

# LANGUAGE DETECTION + TRANSLATION
def translate_to_english(text: str) -> str:
    tokens = translator_tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        padding=True
    ).to(DEVICE)

    with torch.no_grad():
        translated = translator_model.generate(**tokens)

    return translator_tokenizer.decode(
        translated[0],
        skip_special_tokens=True
    )

def preprocess_text(text: str) -> str:
    try:
        lang = detect(text)
        print(f"Detected language: {lang}")

        if lang != "en":
            print("Translating to English...")
            text = translate_to_english(text)

    except Exception as e:
        print(f"⚠ Language detection failed: {e}")

    return text


# Input model
class TextInput(BaseModel):
    #text: constr(min_length=1, max_length=1000)
    text: Annotated[str, StringConstraints(min_length=1, max_length=1000)]

# FastAPI app
app = FastAPI(title="Sentiment Analysis API", description="RoBERTa model for sentiment classification.", version="2.0.0")

if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static") # Mount static files for serving CSS/JS
    
templates = Jinja2Templates(directory="templates")   # Directory for HTML templates


def predict_sentiment(text: str) -> dict:
    """Predict sentiment from raw text."""
    # Step 1: Detect language + translate if needed
    processed_text = preprocess_text(text)

    # Step 2: Tokenize for sentiment model
    encoding = tokenizer(processed_text, truncation=True, padding="max_length", max_length=256, return_tensors="pt")

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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# To run locally (optional)
if __name__ == "__main__":
    uvicorn.run("inference_api:app", host="0.0.0.0", port=8000, reload=True)
