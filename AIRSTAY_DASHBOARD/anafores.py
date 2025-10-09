import streamlit as st
import pandas as pd
import altair as alt
import requests
from msal import ConfidentialClientApplication
from io import BytesIO

# --- Φόρμα σελίδας ---
st.set_page_config(page_title="🏠 Αναφορές", page_icon="🏠", layout="wide")
st.title("🏠 Συγκεντρωτική Αναφορά")

# --- Credentials Azure AD app (daemon) ---
TENANT_ID = "87751865-5688-433e-8997-597f0d9ba4d6"
CLIENT_ID = "123f0bbb-bb67-4250-9b60-a2cf6a896815"
CLIENT_SECRET = "lz~8Q~WnNNkXiyPdToKzE1F5DbNh1c~AZ87N6b-0"

# --- SharePoint / Teams site πληροφορίες ---
SITE_HOSTNAME = "airstayteam.sharepoint.com"
SITE_PATH = "/sites/AirstayTeam"
FILE_PATH = "/Shared Documents/Οργάνωση κρατήσεων - Excel/Βιβλίο Καταλυμάτων 2025.xlsx"

# --- Authentication ---
authority = f"https://login.microsoftonline.com/{TENANT_ID}"
scope = ["https://graph.microsoft.com/.default"]

app = ConfidentialClientApplication(
    CLIENT_ID, authority=authority, client_credential=CLIENT_SECRET
)
token_result = app.acquire_token_for_client(scopes=scope)

if "access_token" not in token_result:
    st.error(f"❌ Δεν πήραμε access token. Λεπτομέρειες:\n{token_result}")
    st.stop()

access_token = token_result["access_token"]
st.write("✅ Token OK")

# --- Βρες site id ---
site_url = f"https://graph.microsoft.com/v1.0/sites/{SITE_HOSTNAME}:{SITE_PATH}"
res_site = requests.get(site_url, headers={"Authorization": f"Bearer {access_token}"})
if res_site.status_code != 200:
    st.error(f"❌ Σφάλμα site id ({res_site.status_code}): {res_site.text}")
    st.stop()

site_json = res_site.json()
site_id = site_json.get("id")
st.write("Site ID:", site_id)

# --- Κατέβασε το αρχείο ---
file_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/root:{FILE_PATH}:/content"
res_file = requests.get(file_url, headers={"Authorization": f"Bearer {access_token}"})
if res_file.status_code != 200:
    st.error(f"❌ Σφάλμα λήψης αρχείου ({res_file.status_code}): {res_file.text}")
    st.stop()

st.write("✅ Αρχείο κατέβηκε")

file_bytes = res_file.content

# --- Διαβάζουμε το Excel ---
try:
    sheets = pd.read_excel(BytesIO(file_bytes), sheet_name=None)
except Exception as e:
    st.error(f"⚠️ Σφάλμα στην ανάγνωση του Excel: {e}")
    st.stop()

# --- Επιτρεπόμενα φύλλα ---
allowed_sheets = [
    "ZILEAN","NAUTILUS","ORIANNA","THRESH","KALISTA","ELISE","ANIVIA",
    "JAAX","NAMI","AKALI","CHELI","KOMOS","FINIKAS","ZED"
]
sheet_names = [name for name in allowed_sheets if name in sheets.keys()]
if not sheet_names:
    st.error("❌ Δεν υπάρχουν τα επιτρεπόμενα φύλλα στο Excel.")
    st.stop()

selected_sheet = st.selectbox("🗂️ Επιλέξτε ομάδα:", sheet_names)
df = sheets[selected_sheet]

# --- Μετατροπή μήνα σε όνομα ---
month_map = {
    1: "Ιανουάριος", 2: "Φεβρουάριος", 3: "Μάρτιος", 4: "Απρίλιος",
    5: "Μάιος", 6: "Ιούνιος", 7: "Ιούλιος", 8: "Αύγουστος",
    9: "Σεπτέμβριος", 10: "Οκτώβριος", 11: "Νοέμβριος", 12: "Δεκέμβριος"
}
df["ΜΗΝΑΣ"] = df["ΜΗΝΑΣ"].map(month_map)

# --- Επιλογή μήνα ---
month_order = list(month_map.values())
months_in_data = [m for m in month_order if m in df["ΜΗΝΑΣ"].dropna().unique()]
months = ["Όλοι οι μήνες"] + months_in_data
selected_month = st.selectbox("📅 Επιλέξτε μήνα:", months)

required_cols = ["ΤΙΜΗ", "ΠΛΑΤΦΟΡΜΑ", "ΑΡΙΘΜΟΣ ΔΙΑΝΥΚΤΕΡΕΥΣΕΩΝ", "ΕΣΟΔΑ ΙΔΙΟΚΤΗΤΗ", "ΜΗΝΑΣ"]
missing = [c for c in required_cols if c not in df.columns]
if missing:
    st.error(f"❌ Λείπουν στήλες: {missing}")
    st.stop()

st.success(f"✅ Δεδομένα για {selected_sheet}")

# --- Υπολόγισμοι & εμφάνιση όπως προηγουμένως ---
def format_euro(x):
    try:
        return f"{x:,.2f} €"
    except:
        return x

if selected_month != "Όλοι οι μήνες":
    dfm = df[df["ΜΗΝΑΣ"] == selected_month].copy()
    grouped = dfm.groupby("ΠΛΑΤΦΟΡΜΑ").agg({
        "ΤΙΜΗ": "sum",
        "ΑΡΙΘΜΟΣ ΔΙΑΝΥΚΤΕΡΕΥΣΕΩΝ": "sum"
    }).reset_index()
    grouped.rename(columns={"ΤΙΜΗ": "ΤΖΙΡΟΣ"}, inplace=True)
    grouped["ΤΖΙΡΟΣ"] = grouped["ΤΖΙΡΟΣ"].map(format_euro)
    grouped["ΑΡΙΘΜΟΣ ΔΙΑΝΥΚΤΕΡΕΥΣΕΩΝ"] = grouped["ΑΡΙΘΜΟΣ ΔΙΑΝΥΚΤΕΡΕΥΣΕΩΝ"].astype(int)

    st.subheader(f"📊 Σύνοψη – {selected_month}")
    st.dataframe(grouped, use_container_width=True, hide_index=True)

    total = dfm.agg({
        "ΤΙΜΗ": "sum",
        "ΑΡΙΘΜΟΣ ΔΙΑΝΥΚΤΕΡΕΥΣΕΩΝ": "sum",
        "ΕΣΟΔΑ ΙΔΙΟΚΤΗΤΗ": "sum"
    })
    st.markdown("---")
    st.markdown(
        f"**Σύνολο Μήνα:** ΤΖΙΡΟΣ: {format_euro(total['ΤΙΜΗ'])} | "
        f"Διανυκτερεύσεις: {int(total['ΑΡΙΘΜΟΣ ΔΙΑΝΥΚΤΕΡΕΥΣΕΩΝ'])} | "
        f"Έσοδα Ιδιοκτήτη: {format_euro(total['ΕΣΟΔΑ ΙΔΙΟΚΤΗΤΗ'] or 0)}"
    )
else:
    grouped_all = df.groupby("ΠΛΑΤΦΟΡΜΑ").agg({
        "ΤΙΜΗ": "sum",
        "ΑΡΙΘΜΟΣ ΔΙΑΝΥΚΤΕΡΕΥΣΕΩΝ": "sum"
    }).reset_index()
    grouped_all.rename(columns={"ΤΙΜΗ": "ΤΖΙΡΟΣ"}, inplace=True)
    grouped_all["ΤΖΙΡΟΣ"] = grouped_all["ΤΖΙΡΟΣ"].map(format_euro)
    grouped_all["ΑΡΙΘΜΟΣ ΔΙΑΝΥΚΤΕΡΕΥΣΕΩΝ"] = grouped_all["ΑΡΙΘΜΟΣ ΔΙΑΝΥΚΤΕΡΕΥΣΕΩΝ"].astype(int)

    st.subheader("📊 Σύνοψη (Όλοι οι μήνες)")
    st.dataframe(grouped_all, use_container_width=True, hide_index=True)

    total_all = df.agg({
        "ΤΙΜΗ": "sum",
        "ΑΡΙΘΜΟΣ ΔΙΑΝΥΚΤΕΡΕΥΣΕΩΝ": "sum",
        "ΕΣΟΔΑ ΙΔΙΟΚΤΗΤΗ": "sum"
    })
    st.markdown("---")
    st.markdown(
        f"**Σύνολο Όλων των Μηνών:** "
        f"ΤΖΙΡΟΣ: {format_euro(total_all['ΤΙΜΗ'])} | "
        f"Διανυκτερεύσεις: {int(total_all['ΑΡΙΘΜΟΣ ΔΙΑΝΥΚΤΕΡΕΥΣΕΝ'])} | "
        f"Έσοδα Ιδιοκτήτη: {format_euro(total_all['ΕΣΟΔΑ ΙΔΙΟΚΤΗΤΗ'] or 0)}"
    )

# --- Γράφημα ---
st.subheader("📈 ΤΖΙΡΟΣ & Έσοδα Ιδιοκτήτη")
fixed = df.groupby("ΜΗΝΑΣ").agg({
    "ΤΙΜΗ": "sum",
    "ΕΣΟΔΑ ΙΔΙΟΚΤΗΤΗ": "sum"
}).reindex(month_order, fill_value=0).reset_index()

melt = fixed.melt(
    id_vars="ΜΗΝΑΣ",
    value_vars=["ΤΙΜΗ", "ΕΣΟΔΑ ΙΔΙΟΚΤΗΤΗ"],
    var_name="Κατηγορία",
    value_name="Ποσό"
)
melt["Κατηγορία"] = melt["Κατηγορία"].replace({"ΤΙΜΗ": "ΤΖΙΡΟΣ"})
melt["Ποσό (€)"] = melt["Ποσό"].map(lambda x: format_euro(x))

chart = alt.Chart(melt).mark_line(point=True).encode(
    x=alt.X("ΜΗΝΑΣ:N", sort=month_order, title="Μήνας"),
    y=alt.Y("Ποσό:Q", title="€"),
    color=alt.Color("Κατηγορία:N",
                    scale=alt.Scale(domain=["ΤΖΙΡΟΣ", "ΕΣΟΔΑ ΙΔΙΟΚΤΗΤΗ"],
                                    range=["#1f77b4", "#2ca02c"])),
    tooltip=["ΜΗΝΑΣ", "Κατηγορία", "Ποσό (€)"]
).properties(width=700, height=400)

st.altair_chart(chart, use_container_width=True)
