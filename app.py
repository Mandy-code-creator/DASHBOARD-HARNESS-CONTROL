import streamlit as st
import pandas as pd
import numpy as np
import requests
from io import StringIO

# ================================
# CONFIG
# ================================
DATA_URL = "https://docs.google.com/spreadsheets/d/1GdnY09hJ2qVHuEBAIJ-eU6B5z8ZdgcGf4P7ZjlAt4JI/export?format=csv"

st.set_page_config(page_title="Material-level Hardness Detail", layout="wide")
st.title("📊 Material-level Hardness & Mechanical Detail (Offline only)")

# ================================
# LOAD DATA
# ================================
@st.cache_data
def load_data(url):
    r = requests.get(url)
    r.encoding = "utf-8"
    return pd.read_csv(StringIO(r.text))

raw = load_data(DATA_URL)

# ================================
# COLUMN MAPPING
# ================================
column_mapping = {
    "PRODUCT SPECIFICATION CODE": "Product_Spec",
    "HR STEEL GRADE": "Material",
    "TOP COATMASS": "Top_Coatmass",
    "ORDER GAUGE": "Order_Gauge",
    "COIL NO": "Coil_No",
    "QUALITY_CODE": "Quality_Code",
    "Standard Hardness": "Std_Hardness",
    "HARDNESS 冶金": "Hardness_LAB",
    "HARDNESS 鍍鋅線 C": "Hardness_LINE",
    "TENSILE_YIELD": "YS",
    "TENSILE_TENSILE": "TS",
    "TENSILE_ELONG": "EL",
}

df = raw.rename(columns={k: v for k, v in column_mapping.items() if k in raw.columns})

# ================================
# REQUIRED COLUMNS CHECK
# ================================
required_cols = [
    "Product_Spec", "Material", "Top_Coatmass", "Order_Gauge",
    "Coil_No", "Quality_Code",
    "Std_Hardness", "Hardness_LAB", "Hardness_LINE",
    "YS", "TS", "EL"
]

missing = [c for c in required_cols if c not in df.columns]
if missing:
    st.error(f"❌ Missing required columns: {missing}")
    st.stop()

# ================================
# FORCE NUMERIC (OFFLINE MEASUREMENTS)
# ================================
for c in ["Std_Hardness", "Hardness_LAB", "Hardness_LINE", "YS", "TS", "EL"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")

# ================================
# QUALITY CODE FILTER (BUTTON STYLE)
# ================================
st.sidebar.header("🎛 QUALITY CODE")
quality_codes = sorted(df["Quality_Code"].dropna().unique())
selected_qc = st.sidebar.radio("Select Quality Code", quality_codes)

df = df[df["Quality_Code"] == selected_qc]

# ================================
# GROUP CONDITIONS (STRICT)
# ================================
GROUP_COLS = ["Product_Spec", "Material", "Top_Coatmass", "Order_Gauge"]

# ================================
# COUNT COILS PER CONDITION
# ================================
count_df = (
    df.groupby(GROUP_COLS)
      .agg(N_Coils=("Coil_No", "nunique"))
      .reset_index()
)

# ================================
# ONLY CONDITIONS WITH >= 30 COILS
# ================================
valid_conditions = count_df[count_df["N_Coils"] >= 30]

if valid_conditions.empty:
    st.warning("⚠️ No condition has ≥ 30 coils")
    st.stop()

# ================================
# SORT CONDITIONS BY SAMPLE SIZE
# ================================
valid_conditions = valid_conditions.sort_values("N_Coils", ascending=False)

# ================================
# DISPLAY TABLES
# ================================
st.subheader("📋 Coil-level Data (Offline measurements only)")
st.caption("• 1 table = 1 Material + Coatmass + Gauge  \n• No averaging, no SPC, no batch, no phase  \n• ≥ 30 coils only")

for _, cond in valid_conditions.iterrows():

    spec, mat, coat, gauge, n = (
        cond["Product_Spec"],
        cond["Material"],
        cond["Top_Coatmass"],
        cond["Order_Gauge"],
        int(cond["N_Coils"])
    )

    st.markdown(
        f"## 🧱 Product Spec: `{spec}`  \n"
        f"**Material:** {mat} | **Coatmass:** {coat} | **Gauge:** {gauge}  \n"
        f"➡️ **n = {n} coils**"
    )

    table_df = df[
        (df["Product_Spec"] == spec) &
        (df["Material"] == mat) &
        (df["Top_Coatmass"] == coat) &
        (df["Order_Gauge"] == gauge)
    ][[
        "Coil_No",
        "Quality_Code",
        "Std_Hardness",
        "Hardness_LAB",
        "Hardness_LINE",
        "YS", "TS", "EL"
    ]].sort_values("Coil_No")

    st.dataframe(table_df, use_container_width=True)

st.success("✅ Clean report generated – đúng logic nghiệp vụ")
