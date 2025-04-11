import streamlit as st
import os
import subprocess
import sys
import time
from pathlib import Path

st.set_page_config(layout="wide")
st.title("Visualizador IFC Interativo")

BASE_DIR = Path(__file__).parent  # já está em /pages
STATIC_DIR = BASE_DIR
UPLOAD_DIR = STATIC_DIR / "uploads"
STATIC_PORT = 8080

UPLOAD_DIR.mkdir(exist_ok=True)

@st.cache_resource
def start_static_server():
    os.chdir(STATIC_DIR)
    return subprocess.Popen([sys.executable, "-m", "http.server", str(STATIC_PORT)])

server = start_static_server()
time.sleep(1)

uploaded_file = st.file_uploader("Envie um arquivo IFC", type=["ifc"])

if uploaded_file:
    file_path = UPLOAD_DIR / uploaded_file.name
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    st.success("Arquivo enviado com sucesso!")

    iframe_url = f"http://localhost:{STATIC_PORT}/viewer.html?file=uploads/{uploaded_file.name}"
    st.markdown("### Modelo IFC")
    st.components.v1.iframe(iframe_url, height=800, scrolling=True)
