import json
from pathlib import Path

import pandas as pd
import streamlit as st


st.set_page_config(
    page_title="Project Doppel Dashboard",
    page_icon="📊",
    layout="wide"
)

st.title("Project Doppel")
st.subheader("Synthetic EHR Generation Dashboard")

st.write(
    "View generated datasets and generator metadata "
    "from the Phase 2 pipeline."
)

SYNTHETIC_DIR = Path("output/synthetic")

if not SYNTHETIC_DIR.exists():
    st.warning("Synthetic output directory does not exist.")
    st.stop()

csv_files = sorted(SYNTHETIC_DIR.glob("*.csv"))

if not csv_files:
    st.info("No synthetic datasets found.")
    st.stop()

selected_file = st.selectbox(
    "Select a generated dataset",
    csv_files,
    format_func=lambda path: path.name
)

try:
    df = pd.read_csv(selected_file)

    st.success(f"Loaded: {selected_file.name}")

    col1, col2, col3 = st.columns(3)

    col1.metric("Rows", df.shape[0])
    col2.metric("Columns", df.shape[1])
    col3.metric("Missing Values", int(df.isna().sum().sum()))

    st.subheader("Dataset Preview")
    st.dataframe(df.head(20), use_container_width=True)

    st.subheader("Column Information")
    column_info = pd.DataFrame({
        "Column": df.columns,
        "Data Type": df.dtypes.astype(str).values,
        "Missing Values": df.isna().sum().values
    })

    st.dataframe(column_info, use_container_width=True)

    manifest_file = selected_file.with_suffix(".manifest.json")

    if manifest_file.exists():
        st.subheader("Generator Manifest")

        manifest = json.loads(
            manifest_file.read_text(encoding="utf-8")
        )

        st.json(manifest)
    else:
        st.info("Manifest file not found.")

except Exception as error:
    st.error(f"Could not load dataset: {error}")