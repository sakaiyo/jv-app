import base64
import io
from google import genai
from PIL import Image
from pillow_heif import register_heif_opener
import streamlit as st

# HEIC対応
register_heif_opener()

st.set_page_config(page_title="Vintage AI Evaluator", layout="wide")
st.title("👕 Vintage AI Evaluator & Data Generator")

api_key = st.secrets.get("GEMINI_API_KEY", "")
correct_password = st.secrets.get("APP_PASSWORD", "")

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.subheader("🔒 Password Required")
    user_input = st.text_input("Enter password to use the app", type="password")
    if st.button("Login"):
        if user_input == correct_password:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    st.stop()

if not api_key:
    st.warning("👈 Please set GEMINI_API_KEY in Streamlit Secrets.")
    st.stop()

client = genai.Client(api_key=api_key)

if "uploader_key" not in st.session_state:
    st.session_state["uploader_key"] = 0

col_title, col_reset = st.columns([3, 1])
with col_reset:
    if st.button("🧹 Reset / Clear All", use_container_width=True):
        st.session_state["uploader_key"] += 1
        st.rerun()

st.subheader("1. Upload 3 Photos")
uploaded_files = st.file_uploader(
    "Select photos",
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
                st.image(img, caption=f"Photo {idx+1}", use_container_width=True)
        except Exception as e:
            st.error(f"Failed to load image: {e}")

is_made_in_japan = st.checkbox("🇯🇵 Made in Japan")
additional_info = st.text_input("📝 Additional Info (Optional)")

if st.button("🚀 Evaluate Item", type="primary", disabled=not images):
    with st.spinner("⚡ Analyzing item..."):
        try:
            japan_premium = ""
            if is_made_in_japan:
                japan_premium = "- Made in Japan Premium: The user confirmed this is 'Made in Japan'. Specify this under Origin and apply a modest price adjustment."
            
            user_notes = ""
            if additional_info.strip():
                user_notes = f"- USER NOTES: Prioritize this context: '{additional_info.strip()}'."

            prompt_text = f"""
            You are an experienced store buyer for "HOME", a curated vintage store in Fitzroy, Melbourne.
            - Currency: AUD $.
            - Goal: REALISTIC, FAIR, SELLABLE retail price.
            {japan_premium}
            {user_notes}

            Output strictly in this format:
            1. Brand: 
            2. Category: 
            3. Size: 
            4. Material: 
            5. Era: 
            6. Origin: 
            7. Suggested Retail Price: 
            8. Description: (Concise 2-3 sentences)
            9. Square Title: 
            10. Tag Title: (3-7 words max)
            """

            # 速度を上げるための画像軽量化（長辺800px）
            processed_images = []
            for img in images:
                img_rgb = img.convert("RGB")
                img_rgb.thumbnail((800, 800))
                processed_images.append(img_rgb)

            contents = [prompt_text] + processed_images

            # APIが推奨する最新の軽量モデルのみを指定
            response = client.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=contents
            )

            if response.text:
                st.success("Evaluation complete!")
                st.markdown("---")
                st.markdown(response.text)
            else:
                st.error("No response generated.")

        except Exception as e:
            st.error(f"Server error: {e}")
