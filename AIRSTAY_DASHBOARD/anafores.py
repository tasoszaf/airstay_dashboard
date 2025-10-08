

import streamlit as st
import pandas as pd
import altair as alt
import requests
from msal import PublicClientApplication

# --- Ρυθμίσεις σελίδας ---
st.set_page_config(page_title="🏠Αναφορές", page_icon="🏠", layout="wide")
st.title("🏠Συγκεντρωτική Αναφορά")

# --- Ρυθμίσεις Azure AD ---
CLIENT_ID = "123f0bbb-bb67-4250-9b60-a2cf6a896815"
TENANT_ID = "87751865-5688-433e-8997-597f0d9ba4d6"
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPES = ["Files.Read", "Sites.Read.All"]  # Delegated permissions

# --- Δημιουργία PublicClientApplication ---
app = PublicClientApplication(CLIENT_ID, authority=AUTHORITY)

# --- Interactive login ---
st.info("🔑 Συνδεθείτε με τον εταιρικό σας λογαριασμό για να δείτε τα δεδομένα")
token_response = app.acquire_token_interactive(scopes=SCOPES)
access_token = token_response.get("access_token")

if not access_token:
    st.error("❌ Δεν ήταν δυνατή η λήψη του token από Azure AD.")
    st.stop()

# --- Graph API URL για Excel ---
# Αντικατάστησε με το πραγματικό path του Excel στο Teams/SharePoint
EXCEL_GRAPH_URL = "https://graph.microsoft.com/v1.0/sites/{site-id}/drive/root:/Οργάνωση κρατήσεων - Excel/Βιβλίο Καταλυμάτων 2025.xlsx:/content"

headers = {"Authorization": f"Bearer {access_token}"}
response = requests.get(EXCEL_GRAPH_URL, headers=headers)

if response.status_code != 200:
    st.error(f"❌ Σφάλμα λήψης αρχείου από Teams/OneDrive: {response.status_code}")
    st.stop()

# --- Αποθήκευση Excel προσωρινά ---
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

# --- Λίστα επιτρεπόμενων φύλλων ---
allowed_sheets = [
    "ZILEAN","NAUTILUS","ORIANNA","THRESH","KALISTA","ELISE","ANIVIA",
    "JAAX","NAMI","AKALI","CHELI","KOMOS","FINIKAS","ZED"
]

# --- Διαβάζουμε όλα τα φύλλα ---
sheets = pd.read_excel("temp.xlsx", sheet_name=None)
sheet_names = [name for name in allowed_sheets if name in sheets.keys()]

if not sheet_names:
    st.error("❌ Δεν υπάρχουν τα επιτρεπόμενα φύλλα στο Excel.")
    st.stop()

selected_sheet = st.selectbox("🗂️ Επιλέξτε ομάδα καταλυμάτων:", sheet_names)
df = sheets[selected_sheet]

# --- Αντιστοίχιση αριθμού μήνα -> όνομα ---
df["ΜΗΝΑΣ"] = df["ΜΗΝΑΣ"].map(month_map)
months_in_data = [m for m in month_order if m in df["ΜΗΝΑΣ"].dropna().unique()]
months = ["Όλοι οι μήνες"] + months_in_data
selected_month = st.selectbox("📅 Επιλέξτε μήνα:", months)

required_cols = ["ΤΙΜΗ", "ΠΛΑΤΦΟΡΜΑ", "ΑΡΙΘΜΟΣ ΔΙΑΝΥΚΤΕΡΕΥΣΕΩΝ", "ΕΣΟΔΑ ΙΔΙΟΚΤΗΤΗ", "ΜΗΝΑΣ"]
missing = [col for col in required_cols if col not in df.columns]
if missing:
    st.error(f"❌ Λείπουν οι στήλες: {', '.join(missing)}")
    st.stop()

st.success(f"✅ Δεδομένα για την ομάδα **{selected_sheet}**")

# --- Συγκεντρωτικοί πίνακες ---
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

# --- Σταθερό γράφημα ---
st.subheader("📈 ΤΖΙΡΟΣ & Έσοδα Ιδιοκτήτη")
fixed_chart = df.groupby("ΜΗΝΑΣ").agg({
    "ΤΙΜΗ": "sum",
    "ΕΣΟΔΑ ΙΔΙΟΚΤΗΤΗ": "sum"
}).reindex(month_order, fill_value=0).reset_index()

fixed_long = fixed_chart.melt(
    id_vars="ΜΗΝΑΣ",
    value_vars=["ΤΙΜΗ", "ΕΣΟΔΑ ΙΔΙΟΚΤΗΤΗ"],
    var_name="Κατηγορία",
    value_name="Ποσό"
)
fixed_long["Κατηγορία"] = fixed_long["Κατηγορία"].replace({"ΤΙΜΗ": "ΤΖΙΡΟΣ"})
fixed_long["Ποσό (€)"] = fixed_long["Ποσό"].map(lambda x: f"{x:,.2f} €")

chart = alt.Chart(fixed_long).mark_line(point=True).encode(
    x=alt.X('ΜΗΝΑΣ:N', sort=month_order, title="Μήνας"),
    y=alt.Y('Ποσό:Q', title="€"),
    color=alt.Color('Κατηγορία:N',
                    scale=alt.Scale(domain=["ΤΖΙΡΟΣ", "ΕΣΟΔΑ ΙΔΙΟΚΤΗΤΗ"],
                                    range=["#1f77b4", "#2ca02c"])),
    tooltip=['ΜΗΝΑΣ', 'Κατηγορία', 'Ποσό (€)']
).properties(width=700, height=400)

st.altair_chart(chart, use_container_width=True)
