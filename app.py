import base64
import io
import os
import requests
from PIL import Image
from pillow_heif import register_heif_opener
import streamlit as st

# HEIC（iPhone画像）対応の登録
register_heif_opener()

# 画面設定
st.set_page_config(page_title="Vintage AI Evaluator", layout="wide")
st.title("👕 Vintage AI Evaluator & Data Generator")

# APIキーの自動読み込み（Streamlit Secrets -> サイドバー手入力の優先順）
api_key = st.secrets.get("GEMINI_API_KEY", "")

# 万が一Secrets未設定の場合のバックアップ用入力欄
if not api_key:
    st.sidebar.header("Settings")
    api_key = st.sidebar.text_input("Enter Gemini API Key", type="password")

if not api_key:
    st.warning("👈 Please set GEMINI_API_KEY in Streamlit Secrets.")
    st.stop()

# 画像アップローダー
st.subheader("1. Upload 3 Photos")
st.caption(
    "① Full Item View  ② Brand/Neck Tag  ③ Care/Size/Material Tag"
)
uploaded_files = st.file_uploader(
    "Select photos (HEIC, JPG, PNG supported)",
    type=["jpg", "jpeg", "png", "heic", "heif"],
    accept_multiple_files=True,
)

images = []
if uploaded_files:
    cols = st.columns(len(uploaded_files))
    for idx, file in enumerate(uploaded_files):
        try:
            img = Image.open(file)
            images.append(img)
            with cols[idx]:
                st.image(
                    img, caption=f"Photo {idx+1}", use_container_width=True
                )
        except Exception as e:
            st.error(f"Failed to load image {idx+1}: {e}")

# 査定ボタン
if st.button("🚀 Evaluate Item", type="primary", disabled=not images):
    with st.spinner("Analyzing tags, materials, and details..."):
        try:
            # 英語化 & プロンプトの全面刷新
            prompt_text = """
            You are an expert appraiser and curator for high-end Japanese vintage and archival fashion, serving a global market of collectors and enthusiasts.

            【Background & Context】
            - All items are authentically handpicked and sourced directly from Japan (Sourced from Japan).
            - Evaluate the photos provided (full item view, brand tags, care/material tags, details) and generate precise listing and appraisal data in ENGLISH.

            【Requirements for Description Field】
            - Write a compelling description aimed at a global audience.
            - DO NOT mention generic local shop context or abstract fluff.
            - Include:
              1. Brand background/context (especially if it is a Japanese domestic or niche designer brand).
              2. Key structural/design details and material highlights observed from the images.
              3. Vintage/archival significance or interesting trivia that justifies the evaluation (e.g., specific tag era, RN/CA numbers, unique stitching, Japanese manufacturing quality).

            【Output Format】(Respond strictly in English using the exact keys below)
            1. Brand: 
            2. Category: (e.g., Tailored Jacket, Denim Jeans, Graphic Tee)
            3. Size: (Tag size, or estimated size if missing)
            4. Material: (e.g., 100% Wool, Cotton Blend)
            5. Era: (e.g., 1990s, Early 2000s, Vintage)
            6. Origin: Sourced from Japan (Include "Made in Japan" or spec details if visible on tag)
            7. Suggested Retail Price: (Estimated market price in AUD $)
            8. Description: (3-4 sentences highlighting brand lore, item details, material, and vintage appraisal notes/trivia)
            9. Square Title: (e.g., Burberrys Wool Tailored Jacket - Size 11R)
            """

            # データを通信用に組み立て
            contents_parts = [{"text": prompt_text}]

            # アップロードされた画像をBase64形式に変換
            for img in images:
                buffered = io.BytesIO()
                img_rgb = img.convert("RGB")
                img_rgb.save(buffered, format="JPEG")
                img_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

                contents_parts.append(
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": img_b64,
                        }
                    }
                )

            # Gemini API呼び出し
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
            payload = {"contents": [{"parts": contents_parts}]}

            response = requests.post(url, json=payload)
            res_data = response.json()

            if response.status_code == 200:
                result_text = res_data["candidates"][0]["content"]["parts"][0][
                    "text"
                ]
                st.success("Evaluation complete!")
                st.markdown("---")
                st.subheader("📊 Appraisal & Listing Data")
                st.markdown(result_text)
            else:
                st.error(
                    f"API Error ({response.status_code}): {res_data.get('error', {}).get('message', 'Unknown error')}"
                )

        except Exception as e:
            st.error(f"An error occurred: {e}")
