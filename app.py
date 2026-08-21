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

if not api_key:
    st.sidebar.header("Settings")
    api_key = st.sidebar.text_input("Enter Gemini API Key", type="password")

if not api_key:
    st.warning("👈 Please set GEMINI_API_KEY in Streamlit Secrets.")
    st.stop()


# リセット機能用キーの初期化
if "uploader_key" not in st.session_state:
    st.session_state["uploader_key"] = 0

# 画面最上部にクリアボタンと新規査定エリアを配置
col_title, col_reset = st.columns([3, 1])
with col_reset:
    if st.button("🧹 Reset / Clear All", use_container_width=True):
        st.session_state["uploader_key"] += 1
        st.rerun()

# 画像アップローダー
st.subheader("1. Upload 3 Photos")
st.caption("① Full Item View  ② Brand/Neck Tag  ③ Care/Size/Material Tag")

uploaded_files = st.file_uploader(
    "Select photos (HEIC, JPG, PNG supported)",
    type=["jpg", "jpeg", "png", "heic", "heif"],
    accept_multiple_files=True,
    key=f"uploader_{st.session_state['uploader_key']}",
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

# 「Made in Japan」チェックボックス
is_made_in_japan = st.checkbox("🇯🇵 Made in Japan (Apply valuation premium)")

# 査定ボタン
if st.button("🚀 Evaluate Item", type="primary", disabled=not images):
    with st.spinner("Analyzing tags, materials, and details..."):
        try:
            # Made in Japanの有無に応じたプロンプト指示の分岐
            japan_premium_instruction = ""
            if is_made_in_japan:
                japan_premium_instruction = """
                - IMPORTANT: The user has confirmed that this item is "Made in Japan". 
                  Please explicitly specify "Made in Japan" under Origin. 
                  Factor in the premium craftsmanship and high vintage demand for Japanese-made garments when determining the Suggested Retail Price (increase valuation slightly compared to standard items).
                """

            prompt_text = f"""
            You are an expert appraiser and curator for high-end Japanese vintage and archival fashion, serving a global market of collectors and enthusiasts.

            【Background & Context】
            - All items are authentically handpicked and sourced directly from Japan (Sourced from Japan).
            - Evaluate the photos provided (full item view, brand tags, care/material tags, details) and generate precise listing and appraisal data in ENGLISH.
            {japan_premium_instruction}

            【Requirements for Description Field】
            - Keep it CONCISE and impactful (strictly 2-3 sentences total, approx. 50 words).
            - Highlight key brand lore/origin, material quality, and notable design or vintage appraisal details without fluff.

            【Output Format】(Respond strictly in English using the exact keys below)
            1. Brand: 
            2. Category: (e.g., Tailored Jacket, Denim Jeans, Graphic Tee)
            3. Size: (Tag size, or estimated size if missing)
            4. Material: (e.g., 100% Wool, Cotton Blend)
            5. Era: (e.g., 1990s, Early 2000s, Vintage)
            6. Origin: Sourced from Japan (Add "Made in Japan" if confirmed or visible)
            7. Suggested Retail Price: (Estimated market price in AUD $)
            8. Description: (Concise 2-3 sentences max covering brand context, key material/details, and vintage significance)
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
