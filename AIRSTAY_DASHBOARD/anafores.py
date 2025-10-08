import streamlit as st
import pandas as pd
import altair as alt
import requests
from msal import ConfidentialClientApplication

# --- Ρυθμίσεις σελίδας ---
st.set_page_config(page_title="🏠Αναφορές", page_icon="🏠", layout="wide")
st.title("🏠Συγκεντρωτική Αναφορά")

# --- Ρυθμίσεις Azure AD ---
CLIENT_ID = "123f0bbb-bb67-4250-9b60-a2cf6a896815"
CLIENT_SECRET = "lz~8Q~WnNNkXiyPdToKzE1F5DbNh1c~AZ87N6b-0"
TENANT_ID = "87751865-5688-433e-8997-597f0d9ba4d6"

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPE = ["https://graph.microsoft.com/.default"]

app = ConfidentialClientApplication(CLIENT_ID, client_credential=CLIENT_SECRET, authority=AUTHORITY)
token_response = app.acquire_token_for_client(scopes=SCOPE)
access_token = token_response.get("access_token")

if not access_token:
    st.error("❌ Δεν ήταν δυνατή η λήψη του token από Azure AD.")
    st.stop()

# Πρέπει να το αντικαταστήσετε με το πραγματικό URL από Graph API
EXCEL_GRAPH_URL = "https://graph.microsoft.com/v1.0/sites/341375e1-13a9-491a-97c8-964612df0b6a/drive/root:/Οργάνωση%20κρατήσεων%20-%20Excel/Βιβλίο%20Καταλυμάτων%202025.xlsx:/content"


if EXCEL_GRAPH_URL:
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(EXCEL_GRAPH_URL, headers=headers)

    if response.status_code == 200:
        with open("temp.xlsx", "wb") as f:
            f.write(response.content)
        st.success("✅ Το αρχείο φορτώθηκε επιτυχώς από Teams/OneDrive")
        
        # --- Ονόματα μηνών ---
        month_map = {
            1: "Ιανουάριος", 2: "Φεβρουάριος", 3: "Μάρτιος", 4: "Απρίλιος",
            5: "Μάιος", 6: "Ιούνιος", 7: "Ιούλιος", 8: "Αύγουστος",
            9: "Σεπτέμβριος", 10: "Οκτώβριος", 11: "Νοέμβριος", 12: "Δεκέμβριος"
        }
        month_order = list(month_map.values())

        # --- Διαβάζουμε όλα τα φύλλα ---
        sheets = pd.read_excel("temp.xlsx", sheet_name=None)
        allowed_sheets = [
            "ZILEAN","NAUTILUS","ORIANNA","THRESH","KALISTA","ELISE","ANIVIA",
            "JAAX","NAMI","AKALI","CHELI","KOMOS","FINIKAS","ZED"
        ]
        sheet_names = [name for name in allowed_sheets if name in sheets.keys()]

        if not sheet_names:
            st.error("❌ Δεν υπάρχουν τα επιτρεπόμενα φύλλα στο Excel.")
        else:
            selected_sheet = st.selectbox("🗂️ Επιλέξτε ομάδα καταλυμάτων:", sheet_names)
            df = sheets[selected_sheet]

            # Αντιστοίχιση αριθμού μήνα -> όνομα
            df["ΜΗΝΑΣ"] = df["ΜΗΝΑΣ"].map(month_map)

            # --- Dropdown μηνών ---
            months_in_data = [m for m in month_order if m in df["ΜΗΝΑΣ"].dropna().unique()]
            months = ["Όλοι οι μήνες"] + months_in_data
            selected_month = st.selectbox("📅 Επιλέξτε μήνα:", months)

            required_cols = ["ΤΙΜΗ", "ΠΛΑΤΦΟΡΜΑ", "ΑΡΙΘΜΟΣ ΔΙΑΝΥΚΤΕΡΕΥΣΕΩΝ", "ΕΣΟΔΑ ΙΔΙΟΚΤΗΤΗ", "ΜΗΝΑΣ"]
            missing = [col for col in required_cols if col not in df.columns]
            if missing:
                st.error(f"❌ Λείπουν οι στήλες: {', '.join(missing)}")
            else:
                st.success(f"✅ Δεδομένα για την ομάδα **{selected_sheet}**")

                # --- Ομαδοποίηση ανά μήνα ---
                if selected_month != "Όλοι οι μήνες":
                    df_month = df[df["ΜΗΝΑΣ"] == selected_month].copy()
                    grouped = df_month.groupby("ΠΛΑΤΦΟΡΜΑ").agg({
                        "ΤΙΜΗ": "sum",
                        "ΑΡΙΘΜΟΣ ΔΙΑΝΥΚΤΕΡΕΥΣΕΩΝ": "sum"
                    }).reset_index()
                    grouped.rename(columns={"ΤΙΜΗ": "ΤΖΙΡΟΣ"}, inplace=True)
                    grouped["ΤΖΙΡΟΣ"] = grouped["ΤΖΙΡΟΣ"].map(lambda x: f"{x:,.2f} €")
                    grouped["ΑΡΙΘΜΟΣ ΔΙΑΝΥΚΤΕΡΕΥΣΕΩΝ"] = grouped["ΑΡΙΘΜΟΣ ΔΙΑΝΥΚΤΕΡΕΥΣΕΩΝ"].astype(int)
                    st.dataframe(grouped, use_container_width=True, hide_index=True)
                else:
                    grouped_all = df.groupby("ΠΛΑΤΦΟΡΜΑ").agg({
                        "ΤΙΜΗ": "sum",
                        "ΑΡΙΘΜΟΣ ΔΙΑΝΥΚΤΕΡΕΥΣΕΩΝ": "sum"
                    }).reset_index()
                    grouped_all.rename(columns={"ΤΙΜΗ": "ΤΖΙΡΟΣ"}, inplace=True)
                    grouped_all["ΤΖΙΡΟΣ"] = grouped_all["ΤΖΙΡΟΣ"].map(lambda x: f"{x:,.2f} €")
                    grouped_all["ΑΡΙΘΜΟΣ ΔΙΑΝΥΚΤΕΡΕΥΣΕΩΝ"] = grouped_all["ΑΡΙΘΜΟΣ ΔΙΑΝΥΚΤΕΡΕΥΣΕΩΝ"].astype(int)
                    st.dataframe(grouped_all, use_container_width=True, hide_index=True)

    else:
        st.error(f"❌ Σφάλμα λήψης αρχείου από Teams/OneDrive: {response.status_code}")
else:
    st.info("⬆️ Δώσε το Graph API URL του Excel για να ξεκινήσεις.")
