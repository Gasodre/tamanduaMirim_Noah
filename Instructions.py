import streamlit as st
from PIL import Image
import pandas as pd
import importlib.resources as pkg_resources
import io

# =========================================================================================================================
# Função para carregar imagens
# =========================================================================================================================

def load_image_from_package(package: str, filename: str):
    try:
        with pkg_resources.files(package).joinpath(filename).open("rb") as f:
            image_data = f.read()
        return Image.open(io.BytesIO(image_data))
    except Exception as e:
        print(f"Erro ao carregar imagem {filename}: {e}")
        return None

# =========================================================================================================================
# Função para carregar template
# =========================================================================================================================

def load_template_from_package(package: str, filename: str):
    try:
        with pkg_resources.files(package).joinpath(filename).open("rb") as f:
            return io.BytesIO(f.read())
    except Exception as e:
        print(f"Erro ao carregar template {filename}: {e}")
        return None

# =========================================================================================================================
# ⚠️ SET PAGE CONFIG → tem que vir ANTES de qualquer st.*()
# =========================================================================================================================

icon_img = load_image_from_package('resources.img', 'logo_tamanduel.ico')
st.set_page_config(
    page_title="IDS Converter",
    page_icon=icon_img,
    layout="wide",
    initial_sidebar_state="expanded",
)
# =========================================================================================================================
# Pré-carregamento das imagens com segurança
# =========================================================================================================================

icon_img     = load_image_from_package('resources.img', 'logo_tamanduel.ico')
github_logo  = load_image_from_package('resources.img', 'github-logo.png')
schema_img   = load_image_from_package('resources.img', 'schema.png')
sheet1_img   = load_image_from_package('resources.img', 'sheet1.png')
sheet2_img   = load_image_from_package('resources.img', 'sheet2.png')
sheet3_img   = load_image_from_package('resources.img', 'sheet3.png')

# =========================================================================================================================
# Barra lateral
# =========================================================================================================================

with st.sidebar:
    st.title('🧰 IDS Converter v2.0 (Edição Noah)')
    st.write('🔗 [Open BIM Academy](https://openbimacademy.com.br/)')
    st.write('👆 Escolha uma opção no menu acima!')
    st.divider()
    if github_logo:
        st.image(github_logo, width=50)
    st.write('🐙 [Repositório original](https://github.com/c4rlosdias/ids_converter)')

# =========================================================================================================================
# Tela de introdução
# =========================================================================================================================

st.header("🧩 IDS Converter v2.0 – Edição Noah")
st.write('✨ Adaptado para Noah a partir do projeto original de **Carlos Dias**') 
st.write('📅 _Última atualização: 04 Abril 2025_')
st.markdown('')

st.markdown('📤 Este conversor gera um arquivo :blue[IDS] a partir de uma planilha :green[Excel].')
if schema_img:
    st.image(schema_img, width=450)

st.markdown(
    '📦 O **IDS (Information Delivery Specification)** é um padrão que descreve requisitos de troca de informação e tem grande potencial em fluxos BIM. '
    'Esta ferramenta foi adaptada com carinho para atender às necessidades da equipe da **Noah**, gerando arquivos `.ids` a partir das planilhas '
    '**Applicability** e **Requirements**, conforme as facetas definidas. A versão atual é compatível com o padrão **IDS 1.0**.'
)

st.markdown('🔧 _Esta versão do IDS Converter utiliza [IfcOpenShell](http://ifcopenshell.org/)_')
st.divider()

st.markdown('📑 Na aba **Specification**, você deve definir as especificações da troca de informação:')
if sheet1_img:
    st.image(sheet1_img, width=500)

st.markdown('📌 Na aba **Applicability**, devem ser indicados os elementos que devem atender aos requisitos:')
if sheet2_img:
    st.image(sheet2_img, width=1500)

st.markdown('📋 Na aba **Requirements**, você define quais requisitos devem ser atendidos:')
if sheet3_img:
    st.image(sheet3_img, width=1500)

# Template (abre como binário para download)
template_bytes = load_template_from_package('template', 'IDS_TEMPLATE.xlsx')

if template_bytes:
    st.download_button(
        '💾 Clique aqui para baixar o arquivo modelo!',
        data=template_bytes,
        file_name="IDS_TEMPLATE.xlsx"
    )
else:
    st.warning("⚠️ Não foi possível carregar o template.")

st.divider()
st.markdown('✅ Agora é com você! Use a barra lateral para enviar sua planilha XLSX e começar a conversão! 🚀')
