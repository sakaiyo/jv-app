import base64
import io
import requests
from PIL import Image
from pillow_heif import register_heif_opener
import streamlit as st

# HEIC（iPhone画像）をPillowで読み込めるように登録
register_heif_opener()

# 画面設定
st.set_page_config(page_title="古着AI査定・データ作成", layout="wide")
st.title("👕 古着AI査定 & データ作成アプリ (3枚一括)")

# サイドバーでAPIキー入力
st.sidebar.header("設定")
api_key = st.sidebar.text_input("Gemini API Keyを入力", type="password")

if not api_key:
    st.warning("👈 左側のサイドバーに Gemini API Key を入力してください。")
    st.stop()

# 画像アップローダー（HEIC / JPG / PNG 対応）
st.subheader("1. 写真を3枚アップロード")
st.caption("①全体画像  ②ブランドタグ  ③品質表示・サイズタグ")
uploaded_files = st.file_uploader(
    "写真をまとめて選択してください (HEIC / JPG / PNG 対応)",
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
                st.image(img, caption=f"写真 {idx+1}", use_container_width=True)
        except Exception as e:
            st.error(f"写真 {idx+1} の読み込みに失敗しました: {e}")

# 査定ボタン
if st.button("🚀 AI査定実行", type="primary", disabled=not images):
    with st.spinner("タグや素材、デザインを分析中..."):
        try:
            # プロンプト（指示文）の設定
            prompt_text = """
            あなたはオーストラリア・ビクトリア州Fitzroy（フィッツロイ）にある「日本発の古着・ヴィンテージ専門店（Japanese Vintage Shop）」の優秀な専門査定員およびECデータ作成者です。

            【背景と前提条件】
            ・商品はすべて日本国内で買い付け・厳選（Sourced / Handpicked from Japan）された、クオリティの高い日本の古着・ヴィンテージ品です。
            ・オーストラリア・フィッツロイの感度の高い古着市場トレンド、および当店（Japanese Vintage専門店）のブランド価値にふさわしい販売価格（AUD $）を査定してください。

            提供された複数枚の写真（全体、ブランドタグ、品質表示タグ等）を総合的に分析して、以下のフォーマットで出力してください。

            【出力フォーマット】
            1. ブランド名 (Brand):
            2. カテゴリ (Category): (例: T-Shirt, Jeans, Jacket)
            3. サイズ (Size): (タグ表記のサイズ、不明なら推定サイズ)
            4. 素材 (Material): (例: Cotton 100%)
            5. 推定年代 (Era): (例: 1990s, 2000s, Unknown)
            6. 仕入れ地 / 規格 (Origin): Sourced from Japan (日本規格や日本製等の記載があれば併記)
            7. 推奨販売価格 (Suggested Price): (Fitzroyの店舗で販売する適正価格をオーストラリアドル $ で表示)
            8. 商品説明文 (Description): (日本から厳選された仕入れ背景、アイテムの魅力やコンディションを踏まえた店頭・EC用の説明文 2-3文)
            9. Square用タイトル (Square Title): (例: Levi's 501 Jeans - W32 L30)
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
                st.success("分析が完了しました！")
                st.markdown("---")
                st.subheader("📊 査定結果")
                st.markdown(result_text)
            else:
                st.error(
                    f"APIエラー ({response.status_code}): {res_data.get('error', {}).get('message', '不明なエラー')}"
                )

        except Exception as e:
            st.error(f"エラーが発生しました: {e}")