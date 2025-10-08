import streamlit as st
import pandas as pd
import altair as alt
import os

# --- Ρυθμίσεις σελίδας ---
st.set_page_config(page_title="🏠Αναφορές", page_icon="🏠", layout="wide")
st.title("🏠Συγκεντρωτική Αναφορά")

# --- Διαδρομή Excel στον υπολογιστή ---
excel_path = "/Users/anastasioszafeiriou/Library/CloudStorage/OneDrive-SharedLibraries-AIRSTAYIKE/Airstay Team - Έγγραφα/Οργάνωση κρατήσεων - Excel/Βιβλίο Καταλυμάτων 2025.xlsx"

# --- Χάρτης αριθμών -> ονόματα μηνών ---
month_map = {
    1: "Ιανουάριος", 2: "Φεβρουάριος", 3: "Μάρτιος", 4: "Απρίλιος",
    5: "Μάιος", 6: "Ιούνιος", 7: "Ιούλιος", 8: "Αύγουστος",
    9: "Σεπτέμβριος", 10: "Οκτώβριος", 11: "Νοέμβριος", 12: "Δεκέμβριος"
}
month_order = list(month_map.values())

# --- Λίστα επιτρεπόμενων φύλλων ---
allowed_sheets = [
    "ZILEAN","NAUTILUS","ORIANNA","THRESH","KALISTA","ELISE","ANIVIA",
    "JAAX","NAMI","AKALI","CHELI","KOMOS","FINIKAS","ZED"
]

if os.path.exists(excel_path):
    try:
        sheets = pd.read_excel(excel_path, sheet_name=None)
        sheet_names = [name for name in allowed_sheets if name in sheets.keys()]

        if not sheet_names:
            st.error("❌ Δεν υπάρχουν τα επιτρεπόμενα φύλλα στο Excel.")
        else:
            selected_sheet = st.selectbox("🗂️ Επιλέξτε ομάδα καταλυμάτων:", sheet_names)
            df = sheets[selected_sheet]

            # Αντιστοίχιση αριθμού μήνα -> όνομα
            df["ΜΗΝΑΣ"] = df["ΜΗΝΑΣ"].map(month_map)

            # --- Dropdown μηνών με φυσική σειρά ---
            months_in_data = [m for m in month_order if m in df["ΜΗΝΑΣ"].dropna().unique()]
            months = ["Όλοι οι μήνες"] + months_in_data
            selected_month = st.selectbox("📅 Επιλέξτε μήνα:", months)

            required_cols = ["ΤΙΜΗ", "ΠΛΑΤΦΟΡΜΑ", "ΑΡΙΘΜΟΣ ΔΙΑΝΥΚΤΕΡΕΥΣΕΩΝ", "ΕΣΟΔΑ ΙΔΙΟΚΤΗΤΗ", "ΜΗΝΑΣ"]
            missing = [col for col in required_cols if col not in df.columns]
            if missing:
                st.error(f"❌ Λείπουν οι στήλες: {', '.join(missing)}")
            else:
                st.success(f"✅ Δεδομένα για την ομάδα **{selected_sheet}**")

                # --- Συγκεντρωτικός πίνακας ---
                if selected_month != "Όλοι οι μήνες":
                    df_month = df[df["ΜΗΝΑΣ"] == selected_month].copy()
                    grouped = df_month.groupby("ΠΛΑΤΦΟΡΜΑ").agg({
                        "ΤΙΜΗ": "sum",
                        "ΑΡΙΘΜΟΣ ΔΙΑΝΥΚΤΕΡΕΥΣΕΩΝ": "sum"
                    }).reset_index()
                    grouped.rename(columns={"ΤΙΜΗ": "ΤΖΙΡΟΣ"}, inplace=True)
                    grouped["ΤΖΙΡΟΣ"] = grouped["ΤΖΙΡΟΣ"].map(lambda x: f"{x:,.2f} €")
                    grouped["ΑΡΙΘΜΟΣ ΔΙΑΝΥΚΤΕΡΕΥΣΕΩΝ"] = grouped["ΑΡΙΘΜΟΣ ΔΙΑΝΥΚΤΕΡΕΥΣΕΩΝ"].astype(int)
                    st.subheader(f"📊 Συγκεντρωτικός Πίνακας - {selected_month}")
                    st.dataframe(grouped, use_container_width=True, hide_index=True)

                else:
                    grouped_all = df.groupby("ΠΛΑΤΦΟΡΜΑ").agg({
                        "ΤΙΜΗ": "sum",
                        "ΑΡΙΘΜΟΣ ΔΙΑΝΥΚΤΕΡΕΥΣΕΩΝ": "sum"
                    }).reset_index()
                    grouped_all.rename(columns={"ΤΙΜΗ": "ΤΖΙΡΟΣ"}, inplace=True)
                    grouped_all["ΤΖΙΡΟΣ"] = grouped_all["ΤΖΙΡΟΣ"].map(lambda x: f"{x:,.2f} €")
                    grouped_all["ΑΡΙΘΜΟΣ ΔΙΑΝΥΚΤΕΡΕΥΣΕΩΝ"] = grouped_all["ΑΡΙΘΜΟΣ ΔΙΑΝΥΚΤΕΡΕΥΣΕΩΝ"].astype(int)
                    st.subheader("📊 Συγκεντρωτικός Πίνακας (Όλοι οι μήνες)")
                    st.dataframe(grouped_all, use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"⚠️ Σφάλμα κατά την ανάγνωση του αρχείου: {e}")
else:
    st.error(f"❌ Το αρχείο δεν βρέθηκε στο path: {excel_path}")
