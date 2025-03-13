from flask import Flask, request, jsonify
import pandas as pd
import os
from fuzzywuzzy import fuzz
from datetime import datetime
import re

app = Flask(__name__)

# Pad waar je geüploade bestanden tijdelijk opslaat
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Zorg ervoor dat de uploads map bestaat
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Pad naar het lokale Excel-bestand
LOCAL_FILE = 'Filmpercentages.xlsx'

# Nederlandse maandnamen
maanden = {
    'Jan': 'jan', 'Feb': 'feb', 'Mar': 'mrt', 'Apr': 'apr', 'May': 'mei', 'Jun': 'jun',
    'Jul': 'jul', 'Aug': 'aug', 'Sep': 'sep', 'Oct': 'okt', 'Nov': 'nov', 'Dec': 'dec'
}

# Functie om de Excel-gegevens te laden
def lees_facturen(bestand):
    try:
        # Lees het Excel-bestand in
        df = pd.read_excel(bestand)
    except Exception as e:
        return {"error": f"Kan bestand niet laden: {str(e)}"}

    # Benodigde kolommen
    kolommen_nodig = ['frm_perc', 'master_title_description', 'play_week']
    
    # Controleer of alle kolommen aanwezig zijn
    for kolom in kolommen_nodig:
        if kolom not in df.columns:
            return {"error": f"Kolom '{kolom}' ontbreekt in het bestand"}

    # Selecteer en retourneer de data als JSON
    return df[['frm_perc', 'master_title_description', 'net_rental', 'play_week']].to_dict(orient='records')


# Functie om speelweek-string te maken
def maak_speelweek_string(zoekdatum):
    zoekdatum = datetime.strptime(zoekdatum, '%d-%m-%Y')
    maand = zoekdatum.strftime('%b')
    maand_nl = maanden.get(maand, maand)
    dag = zoekdatum.day
    return f'Speelweek {dag} {maand_nl}'

# Functie om films te zoeken die lijken op een gegeven titel
def zoek_films(df, zoekterm, zoekdatum):
    zoekterm_lower = zoekterm.lower()
    speelweek_om_te_printen = maak_speelweek_string(zoekdatum)
    
    # Verwerking van speelweken
    speelweken_data = []
    current_speelweek = None
    current_data = []

    for index, row in df.iterrows():
        if isinstance(row.iloc[2], str) and 'Speelweek' in row.iloc[2]:
            if current_speelweek is not None:
                speelweken_data.append((current_speelweek, current_data))
            current_speelweek = row.iloc[2]
            current_data = []
        else:
            if index != 0:  # Sluit de header uit
                current_data.append(row)

    if current_speelweek is not None:
        speelweken_data.append((current_speelweek, current_data))

    # Zoeken op speelweek en fuzzy matching
    for week, data in speelweken_data:
        if week == speelweek_om_te_printen:
            speelweek_data = pd.DataFrame(data)
            speelweek_data = speelweek_data.dropna(axis=1, how='all')  # Verwijder lege kolommen

            # Controleer of er meer dan 3 kolommen zijn
            if len(speelweek_data.columns) > 3:
                speelweek_data = speelweek_data.drop(speelweek_data.columns[3], axis=1)

            matches = []
            for _, film_row in speelweek_data.iterrows():
                filmnaam = film_row.iloc[0]
                
                # Gebruik zowel partial_ratio als token_sort_ratio
                similarity_score_partial = fuzz.partial_ratio(str(filmnaam).lower(), zoekterm_lower)
                similarity_score_sort = fuzz.token_sort_ratio(str(filmnaam).lower(), zoekterm_lower)
                
                # Kies de hoogste score tussen de twee
                similarity_score = max(similarity_score_partial, similarity_score_sort)

                if similarity_score > 80:  # Stel een drempel in, hier 80%
                    matches.append(film_row)

            if matches:
                matches_df = pd.DataFrame(matches)
                return matches_df.to_dict(orient='records')
            else:
                return {"message": f"Geen exacte match gevonden voor '{zoekterm}'. Hier zijn alle films van {week}:", "data": speelweek_data.to_dict(orient='records')}
    
    return {"error": f"Geen gegevens gevonden voor speelweek '{speelweek_om_te_printen}'"}

# Route om een bestand te uploaden en facturen op te halen
@app.route('/upload_factuur', methods=['POST'])
def upload_factuur():
    if 'bestand' not in request.files:
        return jsonify({"error": "Geen bestand gevonden"}), 400

    bestand = request.files['bestand']
    if bestand.filename == '':
        return jsonify({"error": "Geen bestand geselecteerd"}), 400

    # Controleer of het bestand een Excel-bestand is
    if not (bestand.filename.endswith('.xls') or bestand.filename.endswith('.xlsx')):
        return jsonify({"error": "Ongeldig bestandstype, alleen Excel-bestanden zijn toegestaan"}), 400

    # Sla het bestand tijdelijk op
    bestand_pad = os.path.join(app.config['UPLOAD_FOLDER'], bestand.filename)
    bestand.save(bestand_pad)

    # Lees de facturen uit het geüploade bestand
    data = lees_facturen(bestand_pad)
    
    # Verwijder het bestand na verwerking (optioneel)
    os.remove(bestand_pad)

    return jsonify(data)

# Route om een bestand te uploaden en percentages op te halen
@app.route('/upload_percentages', methods=['POST'])
def upload_percentages():
    # Zorg ervoor dat het bestand aanwezig is in de request
    if 'bestand' not in request.files:
        return jsonify({"error": "Geen bestand ontvangen"}), 400
    
    file = request.files['bestand']
    
    if file.filename == '':
        return jsonify({"error": "Geen bestand geselecteerd"}), 400
    
    # Stel de naam in van het bestand als 'Film percentages' gevolgd door een extensie (bijvoorbeeld .xlsx)
    filename = 'Film percentages' + os.path.splitext(file.filename)[1]  # Houd de extensie van het bestand
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    # Sla het bestand op in de server
    file.save(file_path)
    
    # Hier kun je nu verdere verwerking van het bestand uitvoeren
    return jsonify({"message": "Bestand succesvol geüpload", "file_path": file_path}), 200

# Route om films te zoeken
@app.route('/zoek_films', methods=['POST'])
def zoek_films_route():
    master_title_description = request.json.get('master_title_description')
    play_week = request.json.get('play_week')

    if not master_title_description or not play_week:
        return jsonify({"error": "Geen master_title_description of play_week opgegeven"}), 400

    # Pad naar het bestand "Film percentages.xlsx" in de uploads map
    uploaded_file = os.path.join(app.config['UPLOAD_FOLDER'], 'Film percentages.xlsx')

    # Controleer of het bestand bestaat
    if not os.path.exists(uploaded_file):
        return jsonify({"error": "Bestand 'Film percentages.xlsx' niet gevonden"}), 400

    # Lees het Excel-bestand
    try:
        df = pd.read_excel(uploaded_file, sheet_name='Percentages')
    except Exception as e:
        return jsonify({"error": f"Fout bij het lezen van bestand: {str(e)}"}), 500

    # Functie om films te zoeken op basis van de gegevens
    gefilterde_films = zoek_films(df, master_title_description, play_week)

    if not gefilterde_films or isinstance(gefilterde_films, dict):
        response = {
            "result": "geen match",
            "message": f"Geen match gevonden voor '{master_title_description}' tijdens speelweek {play_week}."
        }
    else:
        response = gefilterde_films

    print("JSON Response:", response)  # Debugging output
    return jsonify(response)

# Start de Flask-server
if __name__ == '__main__':
    app.run(debug=True)
