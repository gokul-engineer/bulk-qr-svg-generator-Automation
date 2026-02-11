import streamlit as st
import pandas as pd
import qrcode
import svgwrite
import zipfile
import io
import requests
import base64
import json

# -----------------------------
# 🔐 GitHub Config (from secrets)
# -----------------------------

GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
GITHUB_REPO = st.secrets["GITHUB_REPO"]
COUNTER_FILE_PATH = st.secrets["COUNTER_FILE_PATH"]

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

# -----------------------------
# 📂 GitHub Counter Functions
# -----------------------------

def get_counter():
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{COUNTER_FILE_PATH}"
    response = requests.get(url, headers=HEADERS)
    data = response.json()

    content = base64.b64decode(data["content"]).decode("utf-8")
    counter_data = json.loads(content)

    return counter_data, data["sha"]

def update_counter(new_data, sha):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{COUNTER_FILE_PATH}"

    encoded_content = base64.b64encode(
        json.dumps(new_data, indent=2).encode("utf-8")
    ).decode("utf-8")

    payload = {
        "message": "Update generate counter",
        "content": encoded_content,
        "sha": sha
    }

    requests.put(url, headers=HEADERS, json=payload)

# -----------------------------
# 🎯 Streamlit App
# -----------------------------

st.set_page_config(page_title="Bulk QR Code Generator (SVG)", layout="centered")
st.title("🎯 Bulk QR Code Generator")

with st.expander("🧾 Sample Excel Format"):
    st.dataframe(pd.DataFrame({
        "URL": ["https://www.google.com", "https://youtube.com"],
        "Name": ["Google", "YouTube"]
    }))

uploaded_file = st.file_uploader("📄 Upload Excel File", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)

    if not {'A', 'B'}.issubset(df.columns) and not {'Name', 'URL'}.issubset(df.columns):
        st.error("Excel must have either:\n- Columns A & B\n- or columns named 'Name' and 'URL'")
    else:
        col1 = df.columns[0]
        col2 = df.columns[1]

        if st.button("🚀 Generate QR Codes as SVG"):

            # 🔥 Update GitHub Counter
            counter_data, sha = get_counter()
            counter_data["generate"] += 1
            update_counter(counter_data, sha)

            zip_buffer = io.BytesIO()

            with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED) as zip_file:
                for _, row in df.iterrows():
                    link = str(row[col1])
                    filename = str(row[col2]).replace(" ", "_")

                    qr = qrcode.QRCode(
                        version=1,
                        error_correction=qrcode.constants.ERROR_CORRECT_L,
                        box_size=10,
                        border=4
                    )
                    qr.add_data(link)
                    qr.make(fit=True)
                    qr_matrix = qr.get_matrix()

                    cell_width = 10
                    dot_radius = cell_width / 2
                    svg_buffer = io.StringIO()
                    svg_document = svgwrite.Drawing(filename=svg_buffer, profile='tiny')

                    for r in range(len(qr_matrix)):
                        for c in range(len(qr_matrix)):
                            if qr_matrix[r][c]:
                                cx = c * cell_width + dot_radius
                                cy = r * cell_width + dot_radius
                                svg_document.add(
                                    svgwrite.shapes.Circle(center=(cx, cy), r=dot_radius, fill='black')
                                )

                    svg_document.write(svg_buffer)
                    zip_file.writestr(f"{filename}.svg", svg_buffer.getvalue())

            st.success("✅ QR Code SVGs generated!")
            st.download_button(
                label="📥 Download ZIP File",
                data=zip_buffer.getvalue(),
                file_name="qr_svgs.zip",
                mime="application/zip"
            )

# -----------------------------
# 📊 Show Current Global Count
# -----------------------------

try:
    counter_data, _ = get_counter()
    st.markdown("---")
    st.markdown("### 📊 Total Generate Button Clicks (Global)")
    st.write("🚀 Total Generates:", counter_data["generate"])
except:
    st.warning("Counter unavailable.")
