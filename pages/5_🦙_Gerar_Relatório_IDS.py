import os
import ifcopenshell
import ifctester
from ifctester.reporter import Html, Ods  # Importar diretamente os reporters
import streamlit as st

# Função para gerar relatórios
def generate_reports(ifc_filepath, ids_filepath):
    # Extrair o nome do arquivo sem extensão
    ifc_filename = os.path.splitext(os.path.basename(ifc_filepath))[0]

    # Carregar o arquivo IDS
    ids = ifctester.ids.open(ids_filepath, validate=True)

    # Carregar o arquivo IFC
    ifc_file = ifcopenshell.open(ifc_filepath)

    # Validar o IFC com as regras IDS
    ids.validate(ifc_file)

    # Criar nomes de saída baseados no IFC
    html_filename = f"{ifc_filename}.html"
    ods_filename = f"{ifc_filename}.ods"

    # Exportar relatório em HTML
    html_reporter = ifctester.reporter.Html(ids)
    html_reporter.report()
    html_reporter.to_file(html_filename)

    # Exportar relatório em ODS (planilha)
    ods_reporter = ifctester.reporter.Ods(ids)
    ods_reporter.report()
    ods_reporter.to_file(ods_filename)

    return html_filename, ods_filename

# Configuração da página Streamlit
st.title("Validação de Arquivos IFC e IDS")
st.write("Carregue os arquivos IFC e IDS para gerar relatórios.")

# Upload dos arquivos
ifc_file = st.file_uploader("Escolha um arquivo IFC", type=["ifc"])
ids_file = st.file_uploader("Escolha um arquivo IDS", type=["ids"])

if st.button("Gerar Relatórios"):
    if ifc_file is not None and ids_file is not None:
        # Salvar os arquivos temporariamente
        ifc_filepath = f"temp_{ifc_file.name}"
        ids_filepath = f"temp_{ids_file.name}"

        with open(ifc_filepath, "wb") as f:
            f.write(ifc_file.getbuffer())
        
        with open(ids_filepath, "wb") as f:
            f.write(ids_file.getbuffer())

        # Gerar os relatórios
        try:
            html_filename, ods_filename = generate_reports(ifc_filepath, ids_filepath)

            # Exibir mensagem de sucesso
            st.success("Relatórios gerados com sucesso!")

            # Verificar se os arquivos foram gerados
            st.write(f"HTML Report Path: {html_filename}")
            st.write(f"ODS Report Path: {ods_filename}")

            # Usar st.download_button para permitir o download dos arquivos
            with open(html_filename, "rb") as f:
                st.download_button('📥 Baixar relatório HTML', f, file_name=os.path.basename(html_filename), mime='text/html')

            with open(ods_filename, "rb") as f:
                st.download_button('📥 Baixar relatório ODS', f, file_name=os.path.basename(ods_filename), mime='application/vnd.oasis.opendocument.spreadsheet')

        except Exception as e:
            st.error(f"Ocorreu um erro: {e}")
