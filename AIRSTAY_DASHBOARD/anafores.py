import streamlit as st
import pandas as pd
import altair as alt
import requests
from msal import ConfidentialClientApplication, PublicClientApplication
from urllib.parse import urlencode, urlparse, parse_qs

# --- Ρυθμίσεις σελίδας ---
st.set_page_config(page_title="🏠Αναφορές", page_icon="🏠", layout="wide")
st.title("🏠Συγκεντρωτική Αναφορά")

# --- Azure AD app settings ---
CLIENT_ID = "123f0bbb-bb67-4250-9b60-a2cf6a896815"
TENANT_ID = "87751865-5688-433e-8997-597f0d9ba4d6"
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
REDIRECT_URI = "https://airstaydashboard-4ka8sewvw8xmmscwxvzjhc.streamlit.app/"
SCOPE = ["Files.Read", "Sites.Read.All", "User.Read"]

# --- MSAL PublicClientApplication για Authorization Code Flow ---
app = PublicClientApplication(CLIENT_ID, authority=AUTHORITY)

# --- Συνάρτηση για λήψη token ---
def get_token():
    if "access_token" in st.session_state:
        return st.session_state.access_token

    # Έλεγχος για "code" στα query params
    query_params = st.experimental_get_query_params()
    code = query_params.get("code")
    if code:
        # Παίρνουμε token με authorization code
        result = app.acquire_token_by_authorization_code(code[0], scopes=SCOPE, redirect_uri=REDIRECT_URI)
        if "access_token" in result:
            st.session_state.access_token = result["access_token"]
            # Καθαρίζουμε το URL για να μην εμφανίζεται το code
            st.experimental_set_query_params()
            return st.session_state.access_token
        else:
            st.error(f"❌ Σφάλμα λήψης token: {result.get('error_description')}")
            st.stop()
    else:
        # Δημιουργία URL login
        auth_url = app.get_authorization_request_url(SCOPE, redirect_uri=REDIRECT_URI)
        st.markdown(f"[🔑 Συνδεθείτε με εταιρικό λογαριασμό]({auth_url})")
        st.stop()

# --- Παίρνουμε token ---
access_token = get_token()

# --- Graph API URL του Excel ---
EXCEL_GRAPH_URL = "https://graph.microsoft.com/v1.0/sites/341375e1-13a9-491a-97c8-964612df0b6a/drive/root:/Οργάνωση%20κρατήσεων%20-%20Excel/Βιβλίο%20Καταλυμάτων%202025.xlsx:/content"

# --- Κατέβασμα Excel ---
headers = {"Authorization": f"Bearer {access_token}"}
response = requests.get(EXCEL_GRAPH_URL, headers=headers)

if response.status_code != 200:
    st.error(f"❌ Σφάλμα λήψης αρχείου από Teams/OneDrive: {response.status_code}")
    st.stop()

with open("temp.xlsx", "wb") as f:
    f.write(response.content)
st.success("✅ Το αρχείο φορτώθηκε επιτυχώς από Teams/OneDrive")

# --- Χάρτης αριθμών -> ονόματα μηνών ---
month_map = {
    1: "Ιανουάριος", 2: "Φεβρουάριος", 3: "Μάρτιος", 4: "Απρίλιος",
    5: "Μάιος", 6: "Ιούνιος", 7: "Ιούλιος", 8: "Αύγουστος",
    9: "Σεπτέμβριος", 10: "Οκτώβριος", 11: "Νοέμβριος", 12: "Δεκέμβριος"
}
month_order = list(month_map.values())

# --- Επιτρεπόμενα φύλλα ---
allowed_sheets = [
    "ZILEAN","NAUTILUS","ORIANNA","THRESH","KALISTA","ELISE","ANIVIA",
    "JAAX","NAMI","AKALI","CHELI","KOMOS","FINIKAS","ZED"
]

# --- Διαβάζουμε φύλλα Excel ---
sheets = pd.read_excel("temp.xlsx", sheet_name=None)
sheet_names = [name for name in allowed_sheets if name in sheets.keys()]

if not sheet_names:
    st.error("❌ Δεν υπάρχουν τα επιτρεπόμενα φύλλα στο Excel.")
else:
    selected_sheet = st.selectbox("🗂️ Επιλέξτε ομάδα καταλυμάτων:", sheet_names)
    df = sheets[selected_sheet]
    df["ΜΗΝΑΣ"] = df["ΜΗΝΑΣ"].map(month_map)

    # --- Dropdown μηνών ---
    months_in_data = [m for m in month_order if m in df["ΜΗΝΑΣ"].dropna().unique()]
    months = ["Όλοι οι μήνες"] + months_in_data
    selected_month = st.selectbox("📅 Επιλέξτε μήνα:", months)

    # --- Συγκεντρωτικός πίνακας ---
    if selected_month != "Όλοι οι μήνες":
        df_month = df[df["ΜΗΝΑΣ"] == selected_month].copy()
        grouped = df_month.groupby("ΠΛΑΤΦΟΡΜΑ").agg({"ΤΙΜΗ":"sum","ΑΡΙΘΜΟΣ ΔΙΑΝΥΚΤΕΡΕΥΣΕΩΝ":"sum"}).reset_index()
    else:
        grouped = df.groupby("ΠΛΑΤΦΟΡΜΑ").agg({"ΤΙΜΗ":"sum","ΑΡΙΘΜΟΣ ΔΙΑΝΥΚΤΕΡΕΥΣΕΩΝ":"sum"}).reset_index()
    grouped.rename(columns={"ΤΙΜΗ":"ΤΖΙΡΟΣ"}, inplace=True)
    grouped["ΤΖΙΡΟΣ"] = grouped["ΤΖΙΡΟΣ"].map(lambda x: f"{x:,.2f} €")
    grouped["ΑΡΙΘΜΟΣ ΔΙΑΝΥΚΤΕΡΕΥΣΕΩΝ"] = grouped["ΑΡΙΘΜΟΣ ΔΙΑΝΥΚΤΕΡΕΥΣΕΩΝ"].astype(int)
    st.subheader("📊 Συγκεντρωτικός Πίνακας")
    st.dataframe(grouped, use_container_width=True, hide_index=True)

    # --- Γράφημα ---
    st.subheader("📈 ΤΖΙΡΟΣ & Έσοδα Ιδιοκτήτη")
    chart_df = df.groupby("ΜΗΝΑΣ").agg({"ΤΙΜΗ":"sum","ΕΣΟΔΑ ΙΔΙΟΚΤΗΤΗ":"sum"}).reindex(month_order, fill_value=0).reset_index()
    chart_long = chart_df.melt(id_vars="ΜΗΝΑΣ", value_vars=["ΤΙΜΗ","ΕΣΟΔΑ ΙΔΙΟΚΤΗΤΗ"], var_name="Κατηγορία", value_name="Ποσό")
    chart_long["Κατηγορία"] = chart_long["Κατηγορία"].replace({"ΤΙΜΗ":"ΤΖΙΡΟΣ"})
    chart_long["Ποσό (€)"] = chart_long["Ποσό"].map(lambda x: f"{x:,.2f} €")

    chart = alt.Chart(chart_long).mark_line(point=True).encode(
        x=alt.X('ΜΗΝΑΣ:N', sort=month_order, title="Μήνας"),
        y=alt.Y('Ποσό:Q', title="€"),
        color=alt.Color('Κατηγορία:N', scale=alt.Scale(domain=["ΤΖΙΡΟΣ","ΕΣΟΔΑ ΙΔΙΟΚΤΗΤΗ"], range=["#1f77b4","#2ca02c"])),
        tooltip=['ΜΗΝΑΣ','Κατηγορία','Ποσό (€)']
    ).properties(width=700, height=400)

    st.altair_chart(chart, use_container_width=True)
