import os
from supabase import create_client, Client
import requests
import pandas as pd
from bs4 import BeautifulSoup
import re


SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# Configuration
EXAMEN_ID = "EXANR5L17PO59048B3210P2D1"
TEXTE_ID = "PRJLANR5L17B3210P2D1"
BASE_URL = "https://eliasse.assemblee-nationale.fr/api-eliasse"

# Load deputies list for political group mapping
df_deputes = pd.read_csv("../data/liste_deputes_libre_office.csv")
# Convert identifier to string to match clean numeric strings extracted from actor uids
df_deputes['identifiant'] = df_deputes['identifiant'].astype(str)

def get_adopted_uids():
    url = f"{BASE_URL}/examens/{EXAMEN_ID}/derouleur"
    r = requests.get(url)
    data = r.json()
    uids = []
    for place in data.get('places', []):
        for amd in place.get('amendements', []):
            if amd.get('sort') == "Adopté":
                uids.append(amd.get('uid'))
    return uids

def parse_financials_with_group(uid):
    url = f"{BASE_URL}/textes/{TEXTE_ID}/examens/{EXAMEN_ID}/amendements/{uid}/with_neighbors"
    r = requests.get(url)
    amd_data = next((x for x in r.json() if x['uid'] == uid), None)
    if not amd_data:
        return 0, "Inconnu"

    # Extract author ID (e.g., 'PA793374') and strip letters to match the numeric 'identifiant'
    auteur_ref = amd_data.get('auteur', {}).get('ref', '')
    clean_id = re.sub(r'\D', '', auteur_ref)

    # Get group
    matching_deputy = df_deputes[df_deputes['identifiant'] == clean_id]
    group = "Inconnu"
    if not matching_deputy.empty:
        group = matching_deputy.iloc[0]['Groupe politique (complet)']

    # Calculate financial impact
    if 'dispositif' not in amd_data:
        return 0, group

    soup = BeautifulSoup(amd_data['dispositif'], 'html.parser')
    rows = soup.select('tr.ligne_programme')

    net_change = 0
    for row in rows:
        cells = row.find_all('td')
        plus = int(re.sub(r'[^\d]', '', cells[1].text) or 0)
        minus = int(re.sub(r'[^\d]', '', cells[2].text) or 0)
        net_change += (plus - minus)

    return net_change, group

# Execution
adopted = get_adopted_uids()
results = []

for u in adopted:
    impact, group = parse_financials_with_group(u)
    results.append({"uid": u, "impact": impact, "group": group})

# Create DataFrame and summarize results per group
df_results = pd.DataFrame(results)
summary = df_results.groupby("group")["impact"].sum().reset_index()
summary.columns = ["Groupe politique", "Total Budgetary Impact (€)"]

# print(summary.to_string(index=False))

# Push data to Supabase
for _, row in summary.iterrows():
    data = {
        "groupe_politique": row["Groupe politique"],
        "total_impact": float(row["Total Budgetary Impact (€)"]),
    }
    supabase.table("budget_summary").upsert(data).execute()

print("Budget summary successfully updated in Supabase!")
