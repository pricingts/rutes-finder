import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json
import os
import re
from st_aggrid import AgGrid, GridOptionsBuilder

def clean_text(value):
    if isinstance(value, str):
        value = value.replace("\n", " ") 
        value = " ".join(value.split()) 
    return value

@st.dialog("Quotation Details", width="large")
def show_dialog():

    if st.session_state.get("dialog_type") == "request":
        st.dataframe(st.session_state.selected_quotation_requested)
        st.session_state.dialog_type = None
        st.session_state.selected_quotation_requested = None 

def show(role):

    if "open_dialog" not in st.session_state:
        st.session_state.open_dialog = False
    if "selected_quotation_requested" not in st.session_state:
        st.session_state.selected_quotation_requested = None
    if "dialog_type" not in st.session_state:
        st.session_state.dialog_type = None

    quotations_requested = st.secrets["general"]["quotations_requested"]
    quotations_contracts = st.secrets["general"]["costs_sales_contracts"]

    creds = Credentials.from_service_account_info(
        st.secrets["google_sheets_credentials"],
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )

    client = gspread.authorize(creds)

    @st.cache_data(ttl=1800)
    def load_data_from_sheets(sheet_id: str, worksheet_name: str) -> pd.DataFrame:
        try:
            sheet = client.open_by_key(sheet_id)
            worksheet = sheet.worksheet(worksheet_name)
            data = worksheet.get_all_records()
            df = pd.DataFrame(data)

            return df
        except Exception as e:
            st.error(f"Error al cargar datos desde Google Sheets ({worksheet_name}): {str(e)}")
            return pd.DataFrame()

    name = st.experimental_user.name
    email = st.experimental_user.email

    if role == "commercial":
        request_df = load_data_from_sheets(quotations_requested, "All Quotes")
        contracts_df = load_data_from_sheets(quotations_contracts, "CONTRATOS")
        request_df = request_df[request_df["COMMERCIAL"] == name]
        contracts_df = contracts_df[contracts_df["Commercial"] == name]
    elif role == "pricing":
        request_df = load_data_from_sheets(quotations_requested, "All Quotes")
        contracts_df = load_data_from_sheets(quotations_contracts, "CONTRATOS")
        name_map = {
            'customer9@tradingsol.com': 'Luis',
            'pricing11@tradingsol.com': 'Esthefy',
            'pricing6@tradingsol.com': 'Heidi',
            'pricing8@tradingsol.com': 'Mafe'
        }
        if email in name_map:
            name = name_map[email]
            request_df = request_df[request_df["ASSIGNED_TO"].apply(lambda x: name in [correo.strip() for correo in str(x).split(",")])]
    elif role == "ground":
        request_df = load_data_from_sheets(quotations_requested, "Ground Quotations")
        contracts_df = pd.DataFrame()
    elif role == "admin":
        request_df = load_data_from_sheets(quotations_requested, "All Quotes")
        #ground_df = load_data_from_sheets(quotations_requested, "Ground Quotations") #incluir cotizaciones de graound
        #contracts_df = load_data_from_sheets(quotations_contracts, "CONTRATOS")
    else:
        request_df = pd.DataFrame()
        contracts_df = pd.DataFrame()

    tabs = st.tabs(["Quotations Requested"])

    with tabs[0]:

        def clear_filters():
            st.session_state["origen"] = []
            st.session_state["destino"] = []
            st.session_state["service"] = []
            st.session_state["transport"] = []
            st.session_state["cont_type"] = []
            st.session_state["client"] = []

        col1, col2, col3 = st.columns([1,  0.18, 0.18])
        with col1:
            st.header("Quotations Requested")
        with col2:
            st.write(" ")
            st.button("Clear Filters", on_click=clear_filters)
        with col3:
            st.write(" ")
            if st.button("Refresh Data", key="button_2"):
                load_data_from_sheets.clear() 
                st.rerun()

        df_full = request_df.copy()

        if df_full is None or df_full.empty:
            st.error("No data available. Try to update")
            df_filtered = pd.DataFrame()
        else:
            def extraer_origen_destino(rutas):
                origens, destinos = [], []
                for ruta in rutas.splitlines():
                    matches = re.findall(r"\((.*?)\)", ruta)
                    if len(matches) > 0:
                        origens.append(matches[0]) 
                    if len(matches) > 1:
                        destinos.append(matches[1])  
                return {"origen": origens, "destino": destinos}

            def combine_transport_modality(row):
                if row['TRANSPORT_TYPE'] == "Maritime":
                    return f"{row['TRANSPORT_TYPE']} - {row['MODALITY']}"
                else:
                    return row['TRANSPORT_TYPE']
            
            if "origen" not in st.session_state:
                st.session_state["origen"] = []
            if "destino" not in st.session_state:
                st.session_state["destino"] = []
            if "service" not in st.session_state:
                st.session_state["service"] = []
            if "transport" not in st.session_state:
                st.session_state["transport"] = []
            if "cont_type" not in st.session_state:
                st.session_state["cont_type"] = []
            if "client" not in st.session_state:
                st.session_state["client"] = []


            df_full[["origen", "destino"]] = df_full["ROUTES_INFO"].apply(
                lambda x: pd.Series(extraer_origen_destino(x))
            )

            df_full['TRANSPORT_COMBO'] = df_full.apply(combine_transport_modality, axis=1)

            df_filtered = df_full.copy()



            col1, col2, col3 = st.columns(3)
            col4, col5, col6 = st.columns(3)

            with col1:
                origen_options = sorted(set(o for sublist in df_full["origen"].dropna() for o in sublist))
                selected_origen = st.multiselect('**Port of Origin**', origen_options, key="origen")

            with col2:
                destino_options = sorted(set(d for sublist in df_full["destino"].dropna() for d in sublist))
                selected_destino = st.multiselect('**Port of Destination**', destino_options, key="destino")

            with col3:
                all_services = set()
                for service in df_full['SERVICE'].dropna():
                    splitted = re.split(r'[,\n;]+', service)
                    splitted = [item.strip() for item in splitted if item.strip() != ""]
                    all_services.update(splitted)
                service_options = sorted(all_services)
                selected_service = st.multiselect('**Service Requested**', service_options, key="service")

            with col4:
                transport_options = sorted(df_full['TRANSPORT_COMBO'].dropna().unique())
                selected_transport = st.multiselect("**Transport/Modality**", transport_options, key="transport")

            with col5: 
                all_containers = set()
                for container_str in df_full['TYPE_CONTAINER'].dropna():
                    splitted = re.split(r'[,\n;]+', container_str)
                    splitted = [item.strip() for item in splitted if item.strip() != ""]
                    all_containers.update(splitted)
                container_options = sorted(all_containers)
                selected_container = st.multiselect('**Container Type**', container_options, key="cont_type")

            with col6:
                if "client" not in st.session_state or st.session_state["client"] is None:
                    st.session_state["client"] = []
                client_options = sorted(df_full['CLIENT'].dropna().unique())
                selected_client = st.multiselect('**Client**', client_options, key="client")

            df_filtered = df_full.copy()

            if selected_origen:
                df_filtered = df_filtered[df_filtered["origen"].apply(lambda x: any(o in x for o in selected_origen))]
            if selected_destino:
                df_filtered = df_filtered[df_filtered["destino"].apply(lambda x: any(d in x for d in selected_destino))]
            if selected_client:
                df_filtered = df_filtered[df_filtered["CLIENT"].isin(selected_client)]
            if selected_service:
                df_filtered = df_filtered[df_filtered["SERVICE"].isin(selected_service)]
            if selected_container:
                def row_has_container(container_str, selected):
                    splitted = [item.strip() for item in re.split(r'[,\n;]+', str(container_str)) if item.strip()]
                    return any(cont in splitted for cont in selected)
                df_filtered = df_filtered[df_filtered["TYPE_CONTAINER"].apply(lambda x: row_has_container(x, selected_container))]
            if selected_transport:
                df_filtered = df_filtered[df_filtered["TRANSPORT_COMBO"].isin(selected_transport)]

            request_quantity = df_filtered.shape[0]
            counts = df_filtered["TRANSPORT_COMBO"].value_counts()
            maritime_fcl_count = counts.get("Maritime - FCL", 0)
            maritime_lcl_count = counts.get("Maritime - LCL", 0)
            air_count = counts.get("Air", 0)

            col1, col2, col3, col4 = st.columns(4)

            col1.metric(label="Number of Quotations Requested", value=request_quantity)
            col2.metric(label="Maritime - FCL", value=maritime_fcl_count)
            col3.metric(label="Maritime - LCL", value=maritime_lcl_count)
            col4.metric(label="Air", value=air_count)

        # -------------------- DATAFRAME --------------------
        if not df_filtered.empty:
            df_filtered['TIME'] = pd.to_datetime(df_filtered['TIME'], format='%d/%m/%Y %H:%M:%S')
            df_filtered = df_filtered.sort_values(by='TIME', ascending=False)

            gb = GridOptionsBuilder.from_dataframe(df_filtered)
            visible_columns = ["REQUEST_ID", "CLIENT", "ROUTES_INFO", "INCOTERM", 
                            "COMMODITY", "TRANSPORT_TYPE", "MODALITY", 
                            "TYPE_CONTAINER", "STATUS", "DESTINATION", "CUSTOMER", "FEEDBACK"]

            for col in df_filtered.columns:
                if col not in visible_columns:
                    gb.configure_column(col, hide=True)
                else:
                    gb.configure_column(col)

            gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=20)  
            gb.configure_selection("single", use_checkbox=True)  
            gb.configure_grid_options(domLayout='autoHeight')

            grid_options = gb.build()

            grid_response = AgGrid(df_filtered, gridOptions=grid_options, 
                        enable_enterprise_modules=True, 
                        fit_columns_on_grid_load=True, height=600)

            selected_rows = grid_response.get("selected_rows")

            if selected_rows is not None and len(selected_rows) > 0:
                selected_df = pd.DataFrame(selected_rows)
                exclude_columns = ["origen", "destino", "EMAIL_SENT", "FEEDBACK", "ASSIGNED_TO", "DEADLINE", "TRANSPORT_COMBO"]
                selected_df = selected_df.drop(columns=[col for col in exclude_columns if col in selected_df.columns])

                selected_df = selected_df.T.reset_index()
                selected_df.columns = ["Field", "Value"] 
                selected_df["Value"] = selected_df["Value"].astype(str)

                selected_df = selected_df[selected_df["Value"].str.strip() != ""] 
                selected_df = selected_df[selected_df["Value"].str.lower() != "nan"]  
                selected_df = selected_df.dropna()

                selected_df.set_index("Field", inplace=True)

                st.session_state.selected_quotation_requested = selected_df
                st.session_state.dialog_type = "request"
                st.session_state.open_dialog = True

        if st.session_state.get("open_dialog", False):
            show_dialog()
            st.session_state.open_dialog = False
            st.session_state.dialog_type = None
            st.session_state.selected_quotation_requested = None