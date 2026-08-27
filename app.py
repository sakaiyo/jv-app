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

# Secretsからの安全な呼び出し
api_key = st.secrets.get("GEMINI_API_KEY", "")
correct_password = st.secrets.get("APP_PASSWORD", "")

# 🔑 パスワード認証機能
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.subheader("🔒 Password Required")
    user_input = st.text_input(
        "Enter password to use the app", type="password"
    )

    if st.button("Login"):
        if user_input == correct_password:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Incorrect password.")

    st.stop()  # パスワード不一致時は処理を中断

# --- ログイン成功時のみ以下を表示 ---

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

# オプション機能エリア
is_made_in_japan = st.checkbox("🇯🇵 Made in Japan (Apply valuation premium)")

# 📝 追加情報・修正指示用のテキスト入力欄
additional_info = st.text_input(
    "📝 Additional Info / Notes (Optional)",
    placeholder="e.g., Brand is actually Yohji Yamamoto / Material is 100% Wool / Era is late 80s",
)

# 査定ボタン
if st.button("🚀 Evaluate Item", type="primary", disabled=not images):
    with st.spinner("Analyzing tags, materials, and details..."):
        try:
            # Made in Japan のプロンプト指示
            japan_premium_instruction = ""
            if is_made_in_japan:
                japan_premium_instruction = """
                - Made in Japan Premium: The user has confirmed this item is "Made in Japan". Specify "Made in Japan" under Origin and apply a modest, realistic price adjustment for Japanese craftsmanship.
                """

            # 追加情報・修正指示のプロンプト指示
            user_notes_instruction = ""
            if additional_info.strip():
                user_notes_instruction = f"""
                - CRITICAL USER CORRECTION / NOTES: The user provided the following supplementary context: "{additional_info.strip()}".
                  Prioritize this user-provided information over purely visual guessing if there is a conflict (e.g., override brand name, material, or era as specified by the user).
                """

            # メルボルンFitzroy店舗用のリアルな評価プロンプト
            prompt_text = f"""
            You are an experienced store buyer and pricing specialist for "HOME", a curated vintage & secondhand fashion store located in Fitzroy, Melbourne, Australia.

            【Core Pricing Philosophy - VERY IMPORTANT】
            - Target Market: Physical store in Fitzroy, Melbourne & local Australian webstore.
            - Currency: Australian Dollars (AUD $).
            - Pricing Goal: Provide a REALISTIC, FAIR, and SELLABLE retail price in AUD that balances healthy store profit margin with good inventory turnover.
            - DO NOT base prices on hyper-inflated top-tier international online asking prices (e.g., peak Grailed or eBay asking prices).
            - Be realistic about tags and origins: Rare 80s/90s Made in Japan grails command higher value, but standard commercial streetwear lines, general brand items, or Made in China/Vietnam garments must be priced pragmatically for immediate store sales in Melbourne.

            【Background & Context】
            - All items are authentically handpicked and sourced directly from Japan.
            - Evaluate the photos provided (full item view, brand tags, care/material tags, details) and generate precise listing and appraisal data in ENGLISH.
            {japan_premium_instruction}
            {user_notes_instruction}

            【Requirements for Description Field】
            - Keep it CONCISE and impactful (strictly 2-3 sentences total, approx. 50 words).
            - Highlight key brand lore/origin, material quality, and notable design or vintage appraisal details without fluff.

            【Requirements for Tag Title Field】
            - Ultra-short, catchy, and concise phrase (3-7 words max) designed for handwritten paper price tags.
            - Examples: "Rare 90s Wool Trench Coat", "100% Silk / Made in Japan", "Archival 2000s Graphic Tee".

            【Output Format】(Respond strictly in English using the exact keys below)
            1. Brand: 
            2. Category: (e.g., Tailored Jacket, Denim Jeans, Graphic Tee)
            3. Size: (Tag size, or estimated size if missing)
            4. Material: (e.g., 100% Wool, Cotton Blend)
            5. Era: (e.g., 1990s, Early 2000s, Vintage)
            6. Origin: Sourced from Japan (Add "Made in Japan" if confirmed or visible)
            7. Suggested Retail Price: (Realistic Fitzroy retail price in AUD $, e.g., $280 AUD)
            8. Description: (Concise 2-3 sentences max covering brand context, key material/details, and vintage significance)
            9. Square Title: (e.g., Burberrys Wool Tailored Jacket - Size 11R)
            10. Tag Title: (Ultra-short catchy phrase for handwritten price tags)
            """

            contents_parts = [{"text": prompt_text}]

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
