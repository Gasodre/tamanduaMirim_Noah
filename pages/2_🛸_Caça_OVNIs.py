import streamlit as st
import ifcopenshell
import ifcopenshell.util.shape
import ifcopenshell.util.unit
import pandas as pd
import ifcopenshell.geom
import multiprocessing
import numpy as np #Para análise de de outliers 
from sklearn.cluster import DBSCAN #Para análise de de outliers
import matplotlib.pyplot as plt ##Para análise de de outliers
import plotly.graph_objects as go #Para análise de de outliers 
from io import BytesIO
import tempfile

def ensure_ifc_units_in_meters(ifc_file):
    """Garante que o arquivo IFC usa metros como unidade de medida."""
    
    current_unit = ifcopenshell.util.unit.get_project_unit(ifc_file, 'LENGTHUNIT')
    
    if current_unit:
        unit_name = getattr(current_unit, "Name", "Desconhecido")
        unit_prefix = getattr(current_unit, "Prefix", None) or ""
        full_unit = f"{unit_prefix}{unit_name}"
        print(f"📏 Unidade atual do arquivo: {full_unit}")
        
        if unit_name == "METRE" and not unit_prefix:
            print("✅ O arquivo já está em metros.")
            return ifc_file  # Retorna sem modificar
    
    print("⚠ Arquivo não está em metros, convertendo...")
    converted_ifc = ifcopenshell.util.unit.convert_file_length_units(ifc_file, target_units='METER')
    print("✅ Unidades convertidas para metros.")
    
    return converted_ifc
            
def get_element_xyz(ifc_file):
    """Obtém as coordenadas X, Y e Z do centróide da bounding box de elementos do modelo IFC."""
    settings = ifcopenshell.geom.settings()
    iterator = ifcopenshell.geom.iterator(settings, ifc_file, multiprocessing.cpu_count())

    element_ids, centroids_x, centroids_y, centroids_z, z_mins, z_maxs = [], [], [], [], [], []

    if iterator.initialize():
        while True:
            shape = iterator.get()
            element = ifc_file.by_id(shape.id)

            if hasattr(shape, "geometry"):
                verts = ifcopenshell.util.shape.get_element_vertices(element, shape.geometry)

                if verts is None or len(verts) == 0:
                    continue  # Ignora elementos sem vértices válidos

                bbox_min, bbox_max = ifcopenshell.util.shape.get_bbox(verts)

                if bbox_min is None or bbox_max is None or len(bbox_min) < 3 or len(bbox_max) < 3:
                    continue  # Ignora bounding boxes inválidas

                # Calcula as coordenadas do centróide
                centroid_x = (bbox_min[0] + bbox_max[0]) / 2
                centroid_y = (bbox_min[1] + bbox_max[1]) / 2
                centroid_z = (bbox_min[2] + bbox_max[2]) / 2

                # Adicionando aos arrays de retorno
                element_ids.append(element.GlobalId)
                centroids_x.append(centroid_x)
                centroids_y.append(centroid_y)
                centroids_z.append(centroid_z)
                z_mins.append(bbox_min[2])
                z_maxs.append(bbox_max[2])

            if not iterator.next():
                break

    return element_ids, centroids_x, centroids_y, centroids_z, z_mins, z_maxs
  
def get_levels(ifc_file):
    """Obtém os níveis do arquivo IFC e retorna um dicionário ordenado."""
    return dict(sorted({obj.Elevation: obj.Name for obj in ifc_file.by_type("IfcBuildingStorey")}.items()))

def define_intervals(levels, selected_levels, min_value=None, max_value=None):
    """Define os intervalos dos níveis selecionados."""
    elevations = sorted([elev for elev in levels.keys() if levels[elev] in selected_levels])
    intervals = {}

    lower_bound = min_value if min_value is not None else elevations[0]
    upper_bound = max_value if max_value is not None else elevations[-1] + 1

    if elevations:
        intervals['Tolerância'] = (lower_bound, elevations[0])

    for i in range(1, len(elevations)):
        intervals[levels[elevations[i - 1]]] = (elevations[i - 1], elevations[i])

    intervals[levels[elevations[-1]]] = (elevations[-1], upper_bound)
    
    return intervals

def validate_elements(ifc_file, intervals, elementType, min_value, max_value):
    """Valida se os elementos estão dentro do intervalo correto."""
    invalid_elements, z_mins_invalid, z_maxs_invalid = [], [], []

    element_ids, _, _, centroids_z, z_mins, z_maxs = get_element_xyz(ifc_file)
    element_map = {gid: (z, z_min, z_max) for gid, z, z_min, z_max in zip(element_ids, centroids_z, z_mins, z_maxs)}

    for element in ifc_file.by_type(elementType):
        if element.GlobalId in element_map:
            element_z, z_min, z_max = element_map[element.GlobalId]
            
            level_name = "Desconhecido"
            if hasattr(element, "ContainedInStructure") and element.ContainedInStructure:
                for rel in element.ContainedInStructure:
                    if rel.RelatingStructure.is_a("IfcBuildingStorey"):
                        level_name = rel.RelatingStructure.Name
                        break

            lower, upper = intervals.get(level_name, (None, None))
            aviso = ""
            if lower is None or upper is None or not (lower <= element_z <= upper):
                aviso = "👽 Geometria fora do intervalo do nível"

            if not (min_value <= element_z <= max_value):
                aviso = "🛸 Geometria fora do intervalo total"
                st.warning(f"Elemento {element.GlobalId} está fora do intervalo total.")

            if aviso:
                invalid_elements.append((element.GlobalId, element.Name, level_name, element_z, aviso))
                z_mins_invalid.append(z_min)
                z_maxs_invalid.append(z_max)

    return invalid_elements, z_mins_invalid, z_maxs_invalid

def detect_outliers(elements):
    """Aplica DBSCAN para detectar elementos outliers baseados na distribuição espacial."""
    coords = np.array([v[:3] for v in elements.values()])
    clustering = DBSCAN(eps=2.0, min_samples=2).fit(coords)
    labels = clustering.labels_
    
    outliers = {}
    for gid, label, coord in zip(elements.keys(), labels, coords):
        if label == -1:
            if abs(coord[2] - np.mean(coords[:, 2])) > 5:  # Distância no eixo Z
                outliers[gid] = "OVNI"
            else:
                outliers[gid] = "ALIEN"
    return outliers

def plot_element_distribution(element_ids, centroids_x, centroids_y, centroids_z, outliers=None):
    """Exibe apenas o gráfico 3D interativo com destaque para OVNIs e ALIENS."""

    st.subheader("Distribuição Espacial dos Elementos (XYZ)")
    fig3d = go.Figure()

    # Define cores com base nos outliers
    if outliers:
        colors = []
        for gid in element_ids:
            if gid in outliers:
                colors.append('red' if outliers[gid] == 'OVNI' else 'green')
            else:
                colors.append('blue')
        marker_settings = dict(color=colors)
    else:
        marker_settings = dict(color=centroids_z, colorscale='Viridis')

    fig3d.add_trace(go.Scatter3d(
        x=centroids_x,
        y=centroids_y,
        z=centroids_z,
        mode='markers',
        marker=dict(
            size=5,
            opacity=0.8,
            **marker_settings
        ),
        text=element_ids
    ))

    fig3d.update_layout(
        height=700,
        title="Distribuição Espacial dos Elementos (XYZ)",
        scene=dict(
            xaxis_title="X",
            yaxis_title="Y",
            zaxis_title="Z"
        )
    )

    st.plotly_chart(fig3d)

def export_to_excel(invalid_elements, intervals, z_mins, z_maxs):
    """Exporta os elementos inválidos e os intervalos usados para um arquivo Excel."""
    df_invalid = pd.DataFrame(invalid_elements, columns=["GlobalId", "Nome", "Nível Associado", "Coordenada Z", "Aviso"])
    df_invalid['Z Mínimo'] = z_mins
    df_invalid['Z Máximo'] = z_maxs

    df_intervals = pd.DataFrame([(k, v[0], v[1]) for k, v in intervals.items()], columns=["Nível", "Mínimo", "Máximo"])
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_invalid.to_excel(writer, sheet_name="Elementos Inválidos", index=False)
        df_intervals.to_excel(writer, sheet_name="Intervalos", index=False)
    
    output.seek(0)
    return output

# Interface do Streamlit
st.title("🛸 Esquadrão de Caça OVNIs IFC 👽")

uploaded_file = st.file_uploader("Faça o upload do arquivo IFC", type=["ifc"])

element_types = ["IfcElement", "IfcWall", "IfcSlab", "IfcColumn", "IfcBeam", "IfcDoor", "IfcWindow"]
element_type = st.selectbox("Selecione o tipo de elemento a ser analisado", element_types)

if uploaded_file:
    # Resetar session_state se o usuário subir um novo arquivo
    if "last_uploaded" not in st.session_state or uploaded_file.name != st.session_state.last_uploaded:
        st.session_state.excel_data = None
        st.session_state.last_uploaded = uploaded_file.name

    with tempfile.NamedTemporaryFile(delete=False, suffix=".ifc") as temp_file:
        temp_file.write(uploaded_file.read())
        temp_file.flush()
        ifc_file = ifcopenshell.open(temp_file.name)
        ifc_file = ensure_ifc_units_in_meters(ifc_file)

    levels = get_levels(ifc_file)
    selected_levels = st.multiselect("Selecione os níveis para análise", list(levels.values()), default=list(levels.values()))

    min_interval = st.number_input("Defina o intervalo mínimo", value=700)
    max_interval = st.number_input("Defina o intervalo máximo", value=750)

    run_analysis = st.button("Rodar Análise")

    element_ids, centroids_x, centroids_y, centroids_z, _, _ = get_element_xyz(ifc_file)
    elements = {gid: (x, y, z) for gid, x, y, z in zip(element_ids, centroids_x, centroids_y, centroids_z)}

    if run_analysis:
        outliers = detect_outliers(elements)
        st.write(f"Foram detectados {len(outliers)} elementos como OVNIs ou ALIENS.")

        plot_element_distribution(element_ids, centroids_x, centroids_y, centroids_z, outliers)        

        # Preparação dos níveis
        intervals = define_intervals(levels, selected_levels, min_value=min_interval, max_value=max_interval)
        invalid_elements, z_mins_invalid, z_maxs_invalid = validate_elements(ifc_file, intervals, element_type, min_interval, max_interval)

        if invalid_elements:
            st.write(f"Foram encontrados {len(invalid_elements)} elementos que precisam de atenção.")

            st.session_state.excel_data = export_to_excel(invalid_elements, intervals, z_mins_invalid, z_maxs_invalid)
        else:
            st.success("Nenhum elemento inválido encontrado.")
            st.session_state.excel_data = None

    if st.session_state.get("excel_data"):
        st.download_button(
            label="Baixar relatório em Excel",
            data=st.session_state.excel_data,
            file_name="relatorio_analisados.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
