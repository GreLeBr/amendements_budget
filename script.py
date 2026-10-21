import os
from supabase import create_client, Client
from pathlib import Path
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
BASE_DIR = Path(__file__).resolve().parent

# Load deputies list for political group mapping
csv_path = BASE_DIR / "data" / "liste_deputes_libre_office.csv"
df_deputes = pd.read_csv(csv_path)
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

import requests
import pandas as pd
from bs4 import BeautifulSoup
import re

# Configuration
EXAMEN_ID = "EXANR5L17PO59048B3210P2D1"
TEXTE_ID = "PRJLANR5L17B3210P2D1"
BASE_URL = "https://eliasse.assemblee-nationale.fr/api-eliasse"

# Load deputies list directly from the official open data URL
DEPUTES_URL = "https://data.assemblee-nationale.fr/static/openData/repository/17/amo/deputes_actifs_csv_opendata/liste_deputes_libre_office.csv"
df_deputes = pd.read_csv(DEPUTES_URL)
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

def clean_and_parse_int(text):
    # Remove non-breaking spaces, HTML entities, and any standard whitespace
    cleaned = text.replace('\xa0', '').replace('&nbsp;', '').replace(' ', '').strip()
    # Extract only the sequence of digits
    digits = re.sub(r'[^\d]', '', cleaned)
    return int(digits) if digits else 0

def parse_financials_with_group(uid):
    url = f"{BASE_URL}/textes/{TEXTE_ID}/examens/{EXAMEN_ID}/amendements/{uid}/with_neighbors"
    r = requests.get(url)
    amd_data = next((x for x in r.json() if x['uid'] == uid), None)
    if not amd_data:
        return 0, "Inconnu"

    # Extract author ID
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

    total_plus = 0
    total_minus = 0

    for row in rows:
        cells = row.find_all('td')
        if len(cells) >= 3:
            plus = clean_and_parse_int(cells[1].text)
            minus = clean_and_parse_int(cells[2].text)
            total_plus += plus
            total_minus += minus

    # Amendment-level logic:
    # - If there is any addition (total_plus > 0) and subtraction, the subtraction is ignored.
    # - If there is only subtraction (total_plus == 0), then it should be counted (as negative).
    if total_plus > 0:
        net_change = total_plus
    else:
        net_change = -total_minus

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

print(summary.to_string(index=False))

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
