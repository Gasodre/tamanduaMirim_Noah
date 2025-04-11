import streamlit as st
import ifcopenshell
import ifcopenshell.util.shape
import ifcopenshell.util.unit
import pandas as pd
import ifcopenshell.geom
import multiprocessing
from io import BytesIO
import tempfile
import re
import os

# Função para carregar PropertySets de um arquivo Excel
def load_psets_from_excel(uploaded_file):
    df = pd.read_excel(uploaded_file)  # Carrega diretamente do BytesIO
    psets_by_code = {}

    for _, row in df.iterrows():
        codigo_disciplina = str(row["codigo_disciplina"]).strip()
        pset = str(row["pset"]).strip()

        if codigo_disciplina not in psets_by_code:
            psets_by_code[codigo_disciplina] = []
        
        psets_by_code[codigo_disciplina].append(pset)

    return psets_by_code

# Caminho do arquivo Excel com os PropertySets
psets_file = st.file_uploader("Carregue o arquivo de PropertySets", type=["xlsx"])

if psets_file:
    discipline_psets = load_psets_from_excel(psets_file)
else:
    discipline_psets = {}

# Função para extrair o código da disciplina do nome do arquivo IFC
def extract_discipline_code(filename):
    match = re.search(r"NH[0-9]+-([A-Za-z]{3})-", filename)
    return match.group(1) if match else None

def get_elements_without_property_set(ifc_file, accepted_psets):
    elements = []
    all_elements = ifc_file.by_type("IfcElement")
    total_elements = len(all_elements)
    
    incorrect_prefix_pattern = re.compile(r"^(nh_|NH_|Nh_|nH_|nh-|NH-|Nh-|nH-)")

    for element in all_elements:
        has_correct_pset = False
        incorrect_pset_name = ""
        aviso = ""

        if hasattr(element, "IsDefinedBy"):
            for rel in element.IsDefinedBy:
                if rel.is_a("IfcRelDefinesByProperties"):
                    prop_set = rel.RelatingPropertyDefinition
                    if prop_set.is_a("IfcPropertySet"):
                        prop_set_name = prop_set.Name
                        if prop_set_name in accepted_psets:
                            has_correct_pset = True
                        elif incorrect_prefix_pattern.match(prop_set_name):
                            incorrect_pset_name = prop_set_name
        
        if not has_correct_pset:
            aviso = "👮Sem PropertySet adequado🚓" if not incorrect_pset_name else "👮‍♀️Nome incorreto de PropertySet🪪"
            elements.append((element.GlobalId, element.Name, element.is_a(), aviso, incorrect_pset_name))
    
    return elements, total_elements

# =================== STREAMLIT INTERFACE ===================

st.subheader("🔍 Verificar PropertySets")

uploaded_file = st.file_uploader("Faça o upload do arquivo IFC", type=["ifc"])

disciplina_codigo = ""
if uploaded_file and discipline_psets:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".ifc") as temp_file:
        temp_file.write(uploaded_file.read())
        temp_file.flush()
        ifc_file = ifcopenshell.open(temp_file.name)

    disciplina_codigo = extract_discipline_code(uploaded_file.name)
    
# Permitir ao usuário substituir a disciplina manualmente
if disciplina_codigo not in discipline_psets:
    st.warning("Código de disciplina não encontrado no nome do arquivo. Selecione manualmente.")
disciplina_codigo = st.selectbox("Selecione a disciplina", options=list(discipline_psets.keys()), index=list(discipline_psets.keys()).index(disciplina_codigo) if disciplina_codigo in discipline_psets else 0)

accepted_psets = discipline_psets.get(disciplina_codigo, [])

if not accepted_psets:
    st.error("Código de disciplina não encontrado no arquivo de PropertySets. Verifique o nome do arquivo IFC ou selecione manualmente.")
else:
    run_pset_analysis = st.button("Verificar Elementos")

    if run_pset_analysis:
        elements, total_elements = get_elements_without_property_set(ifc_file, accepted_psets)
        num_issues = len(elements)
        percentage_issues = (num_issues / total_elements) * 100 if total_elements > 0 else 0
        percentage_correct = 100 - percentage_issues

        st.write(f"Total de elementos verificados: {total_elements}")
        st.write(f"Elementos com problemas: {num_issues} ({percentage_issues:.2f}%)")
        
        st.progress(percentage_correct / 100)
        st.markdown(f"<div style='width:100%; background:linear-gradient(to right, green {percentage_correct}%, red {percentage_issues}%); height:20px; border-radius:5px'></div>", unsafe_allow_html=True)

        if num_issues > 0:
            df_elements = pd.DataFrame(elements, columns=["GlobalId", "Nome do Elemento", "Tipo IFC", "Aviso", "Nome do PropertySet Incorreto"])
            st.dataframe(df_elements)
            
            excel_data = BytesIO()
            with pd.ExcelWriter(excel_data, engine='xlsxwriter') as writer:
                df_elements.to_excel(writer, sheet_name="Relatório de PropertySets", index=False)
            excel_data.seek(0)

            st.download_button(
                label="📥 Baixar relatório de PropertySets",
                data=excel_data,
                file_name="relatorio_propertysets.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.success("Todos os elementos possuem um PropertySet adequado!")