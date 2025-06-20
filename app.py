import streamlit as st
import pandas as pd
from upsetplot import UpSet, from_indicators
import matplotlib.pyplot as plt
import io
import base64
from matplotlib.backends.backend_pdf import PdfPages
import re

st.set_page_config(page_title="Universal Biomedical UpSet Platform PRO", layout="wide")
st.title("🔬 Universal Biomedical UpSet Platform PRO - AI Assisted")

st.header("Select Type of Analysis")
col1, col2, col3, col4 = st.columns(4)

analysis_type = None

with col1:
    if st.button("🦠 Co-infection Patterns"):
        analysis_type = "Co-infection Patterns"
    if st.button("🧬 Genes/Mutations"):
        analysis_type = "Genes/Mutations"

with col2:
    if st.button("💊 Resistance Profiles"):
        analysis_type = "Resistance Profiles (Phenotypic)"
    if st.button("🔥 Virulence Factors"):
        analysis_type = "Virulence Factors"

with col3:
    if st.button("❤️ Risk Factors"):
        analysis_type = "Risk Factors"
    if st.button("💉 Serology / Vaccine Responses"):
        analysis_type = "Serology / Vaccine Responses"

with col4:
    if st.button("🌊 Environmental Sampling"):
        analysis_type = "Environmental Sampling"
    if st.button("⚠️ Multidrug Resistance (MDR) Detection"):
        analysis_type = "Multidrug Resistance (MDR) Detection"

if analysis_type:
    uploaded_file = st.file_uploader("📄 Upload your Excel file", type=["xlsx"])

    if uploaded_file is not None:
        try:
            excel_file = pd.ExcelFile(uploaded_file)
            sheet_names = excel_file.sheet_names
            sheet = st.selectbox("Select sheet", sheet_names)
            df = pd.read_excel(uploaded_file, sheet_name=sheet)
            df = df.reset_index(drop=True)
            df.columns = df.columns.str.strip()

            st.write(f"✅ Loaded {df.shape[0]} rows and {df.shape[1]} columns.")
            st.dataframe(df.head())

            all_columns = df.columns.tolist()

            st.header("🔍 AI-Suggested Columns")
            suggested_columns = []
            for col in all_columns:
                if any(re.search(pattern, col, re.IGNORECASE) for pattern in ["resist", "positive", "gene", "detected", "virul", "biofilm", "tox", "mecA", "bla", "tet", "ctx", "susc", "r "]):
                    suggested_columns.append(col)

            default_selection = suggested_columns if suggested_columns else all_columns
            selected_columns = st.multiselect("Select variables to include:", all_columns, default=default_selection)

            if selected_columns:
                def to_boolean(val):
                    val_str = str(val).strip().lower()
                    if val_str in ["positive", "detected", "yes", "present", "true", "1", "resistant", "r"]:
                        return True
                    elif val_str in ["negative", "not detected", "no", "absent", "false", "0", "susceptible", "s"]:
                        return False
                    try:
                        return float(val) > 0
                    except:
                        return False

                binary_df = df[selected_columns].applymap(to_boolean)
                upset_data = from_indicators(binary_df.columns, binary_df)

                plt.clf()
                plt.figure(figsize=(10, 6))
                upset = UpSet(upset_data, subset_size='count', show_counts=True)
                upset.plot()
                plt.suptitle(f"{analysis_type} UpSet Plot", fontsize=16)
                st.pyplot(plt.gcf())

                buf_png = io.BytesIO()
                plt.savefig(buf_png, format="png", dpi=600, bbox_inches='tight')
                st.download_button(f"Download {analysis_type} Plot (PNG)", data=buf_png.getvalue(), file_name=f"{analysis_type}_upset.png", mime="image/png")

                if analysis_type == "Multidrug Resistance (MDR) Detection":
                    st.subheader("💊 MDR Detection (≥3 antibiotics resistant)")
                    mdr_df = df[selected_columns].applymap(to_boolean)
                    df['MDR'] = mdr_df.sum(axis=1) >= 3
                    mdr_count = df['MDR'].sum()
                    total_cases = len(df)
                    st.write(f"Total isolates: {total_cases}")
                    st.write(f"MDR isolates (≥3 resistant): {mdr_count}")

                    mdr_upset_data = from_indicators(mdr_df.columns, mdr_df)
                    plt.figure(figsize=(10, 6))
                    upset_mdr = UpSet(mdr_upset_data, subset_size='count', show_counts=True)
                    upset_mdr.plot()
                    plt.suptitle("MDR UpSet Plot", fontsize=16)
                    st.pyplot(plt.gcf())

                st.header("📑 WHO/OIE Threshold Checks")
                if analysis_type == "Resistance Profiles (Phenotypic)" or analysis_type == "Multidrug Resistance (MDR) Detection":
                    if total_cases > 0 and mdr_count/total_cases > 0.5:
                        st.warning("⚠️ MDR rate exceeds 50% — WHO GLASS ALERT")

            st.header("📑 Generate Full Summary Report")
            if st.button("Generate Report"):
                pdf_buffer = io.BytesIO()
                with PdfPages(pdf_buffer) as pdf:
                    plt.figure(figsize=(8, 4))
                    plt.axis("off")
                    plt.title("Dataset Summary", fontsize=16)
                    plt.text(0, 0.6, f"Total isolates: {len(df)}", fontsize=12)
                    if analysis_type == "Multidrug Resistance (MDR) Detection":
                        plt.text(0, 0.5, f"MDR isolates: {mdr_count}", fontsize=12)
                    pdf.savefig()
                    plt.close()

                    plt.figure(figsize=(8, 6))
                    upset.plot()
                    plt.title(f"{analysis_type} UpSet Plot")
                    pdf.savefig()
                    plt.close()

                    if analysis_type == "Multidrug Resistance (MDR) Detection":
                        plt.figure(figsize=(8, 6))
                        upset_mdr.plot()
                        plt.title("MDR UpSet Plot")
                        pdf.savefig()
                        plt.close()

                st.download_button("Download PDF Report", data=pdf_buffer.getvalue(), file_name="full_report.pdf", mime="application/pdf")

        except Exception as e:
            st.error(f"❌ An error occurred: {e}")
