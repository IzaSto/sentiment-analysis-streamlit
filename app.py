import json
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from wordcloud import WordCloud
from transformers import pipeline
import torch

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Web Scraping App", layout="wide")

DATA_REVIEWS = "data/reviews_data.json"
DATA_PRODUCTS = "data/products_data.json"
DATA_TESTIMONIALS = "data/testimonials_data.json"

# ---------------- LOAD DATA ----------------
@st.cache_data
def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

reviews = pd.DataFrame(load_json(DATA_REVIEWS))
products = pd.DataFrame(load_json(DATA_PRODUCTS))
testimonials = pd.DataFrame(load_json(DATA_TESTIMONIALS))

reviews["date"] = pd.to_datetime(reviews["date"])

# ---------------- LOAD MODEL ----------------
@st.cache_resource
def load_model():
    return pipeline(
        "sentiment-analysis",
        model="distilbert-base-uncased-finetuned-sst-2-english",
        device=-1
    )

sentiment_model = load_model()

# ---------------- SIDEBAR ----------------
section = st.sidebar.radio(
    "Choose a section",
    ["Products", "Testimonials", "Reviews"]
)

# ---------------- PRODUCTS ----------------
if section == "Products":
    st.title("🛍️ Products")
    st.dataframe(products)

# ---------------- TESTIMONIALS ----------------
elif section == "Testimonials":
    st.title("💬 Testimonials")
    st.dataframe(testimonials)

# ---------------- REVIEWS ----------------
else:
    st.title("📝 Reviews – Sentiment Analysis")

    months = pd.date_range("2023-01-01", "2023-12-01", freq="MS")
    month_labels = [m.strftime("%B %Y") for m in months]

    selected = st.select_slider(
        "Select Month",
        options=month_labels,
        value="January 2023"
    )

    selected_month = pd.to_datetime(selected)

    filtered = reviews[
        (reviews["date"].dt.year == 2023) &
        (reviews["date"].dt.month == selected_month.month)
    ]

    st.subheader(f"Reviews for {selected}")
    st.write(f"Total reviews: {len(filtered)}")

    if filtered.empty:
        st.warning("No reviews found for this month.")
        st.stop()

    # ---------- SENTIMENT ----------
    results = sentiment_model(filtered["text"].tolist())

    filtered["sentiment"] = [r["label"] for r in results]
    filtered["confidence"] = [r["score"] for r in results]

    # ---------- BAR CHART ----------
    counts = filtered["sentiment"].value_counts()

    fig, ax = plt.subplots()
    counts.plot(kind="bar", ax=ax)
    ax.set_ylabel("Count")
    ax.set_title("Sentiment Distribution")
    st.pyplot(fig)

    st.write("Average confidence:")
    st.write(filtered.groupby("sentiment")["confidence"].mean())

    # ---------- WORD CLOUD ----------
    text_blob = " ".join(filtered["text"].tolist())
    wc = WordCloud(width=800, height=400, background_color="black").generate(text_blob)

    fig2, ax2 = plt.subplots(figsize=(10, 5))
    ax2.imshow(wc, interpolation="bilinear")
    ax2.axis("off")
    st.pyplot(fig2)
