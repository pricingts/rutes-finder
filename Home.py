import streamlit as st
import pandas as pd
from auth import check_authentication

st.set_page_config(page_title="POL - POD Finder", layout="wide")

def identity_role(email):
    admin = [
        "manager@tradingsol.com", "pricing10@tradingsol.com", "pricing2@tradingsol.com", "pricing@tradingsol.com"
    ]

    if email in admin:
        return "admin"
    else:
        return None

@st.dialog("Warning", width="large")
def non_identiy():
    st.write("Dear user, it appears that you do not have an assigned role on the platform. This might restrict your access to certain features. Please contact the support team to have the appropriate role assigned. Thank you!")
    st.write("pricing@tradingsol.com")

col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    st.image("images/logo_trading.png", width=800)

check_authentication()
role = identity_role(st.experimental_user.email)

if role is None:
    non_identiy()
else:
    user = st.experimental_user.name

    if role in ["commercial", "admin"]:
        with st.sidebar:
            page = st.radio("Go to", ["Home",  "Your Quotations"])

        if page == "Your Quotations":
            import views.Your_Quotations as pricing 
            pricing.show(role)

    elif role in ["pricing", "ground"]:
        with st.sidebar:
            page = st.radio("Go to", ["Home", "Contracts Management", "Your Quotations"])

        if page == "Your Quotations":
            import views.Your_Quotations as pricing 
            pricing.show(role)
