from flask import Flask, render_template, request, redirect, jsonify, url_for
from flask_cors import CORS 
import sqlite3
import pandas as pd
import os
import requests 

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}}) # Autorise Netlify à communiquer

URL_API_COTES_B = "https://script.google.com/macros/s/AKfycbzmyuv8SMVpHCjr9OTuS1jAVVGRXZhwyqbpCOcuY-dpLhT0L0Dag6u9SoUTLnEcWk0s/exec"

UPLOAD_FOLDER = 'static/images'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def init_db():
    conn = sqlite3.connect('cs_banza.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS actualites (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, 
                        titre TEXT, 
                        date TEXT, 
                        image TEXT, 
                        extrait TEXT, 
                        contenu_complet TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS inscriptions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, 
                        nomEleve TEXT, 
                        classe TEXT, 
                        option TEXT)''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def dashboard():
    conn = sqlite3.connect('cs_banza.db')
    conn.row_factory = sqlite3.Row
    actu = conn.execute('SELECT * FROM actualites ORDER BY id DESC').fetchall()
    conn.close()

    inscrits = []
    try:
        # Récupération en temps réel des élèves inscrits depuis Google Sheets
        response = requests.get(URL_API_COTES_B + "?action=getInscriptions", timeout=8)
        if response.status_code == 200:
            inscrits = response.json()
    except Exception as e:
        print("Erreur de récupération des inscrits depuis Google Sheets :", str(e))
        # Fallback de secours sur la base locale SQLite
        conn = sqlite3.connect('cs_banza.db')
        conn.row_factory = sqlite3.Row
        inscrits = conn.execute('SELECT * FROM inscriptions ORDER BY id DESC').fetchall()
        conn.close()

    return render_template('dashboard.html', inscrits=inscrits, actu=actu)

@app.route('/publier', methods=['POST'])
def publier():
    try:
        titre = request.form['titre']
        date = request.form['date']
        extrait = request.form['extrait']
        contenu = request.form['contenu']
        
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        file = request.files.get('image')
        if file and file.filename != '':
            filename = file.filename
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_path = f"images/{filename}"
        else:
            image_path = "images/default.jpg"

        conn = sqlite3.connect('cs_banza.db')
        conn.execute('INSERT INTO actualites (titre, date, image, extrait, contenu_complet) VALUES (?, ?, ?, ?, ?)', 
                     (titre, date, image_path, extrait, contenu))
        conn.commit()
        conn.close()
        return redirect('/')
    except Exception as e:
        print("ERREUR LORS DE LA PUBLICATION :", str(e))
        return f"Erreur interne du serveur : {str(e)}", 500

# --- ROUTE ESSENTIELLE : Enregistrement d'un nouvel élève inscrit depuis le site ---
@app.route('/api/inscrire', methods=['POST'])
def api_inscrire():
    try:
        data = request.get_json() or request.form
        nomEleve = data.get('nomEleve')
        classe = data.get('classe')
        option = data.get('option')

        if nomEleve and classe:
            # Enregistrement local SQLite (Backup)
            conn = sqlite3.connect('cs_banza.db')
            conn.execute('INSERT INTO inscriptions (nomEleve, classe, option) VALUES (?, ?, ?)', 
                         (nomEleve, classe, option))
            conn.commit()
            conn.close()
            return jsonify({"status": "success", "message": "Inscription enregistrée avec succès !"}), 200
        else:
            return jsonify({"status": "error", "message": "Données incomplètes"}), 400
    except Exception as e:
        print("ERREUR INSCRIPTION :", str(e))
        return jsonify({"status": "error", "message": str(e)}), 500

# --- ROUTE API : Pour consulter la liste des inscrits en JSON si besoin ---
@app.route('/api/inscriptions', methods=['GET'])
def api_get_inscriptions():
    conn = sqlite3.connect('cs_banza.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM inscriptions ORDER BY id DESC')
    rows = cursor.fetchall()
    liste = [{"id": r["id"], "nomEleve": r["nomEleve"], "classe": r["classe"], "option": r["option"]} for r in rows]
    conn.close()
    return jsonify(liste)

@app.route('/ajouter_cours_admin', methods=['POST'])
def ajouter_cours_admin():
    classe_cible = request.form.get('classe_cible')
    nom_cours = request.form.get('nom_cours')
    
    if classe_cible and nom_cours:
        # Envoi de la requête au script Google Apps Script avec l'action et le nom exact de l'onglet cible
        payload = {
            "action": "ajouterCours", 
            "classe": classe_cible.strip(), 
            "nomCours": nom_cours.strip()
        }
        try:
            response = requests.post(URL_API_COTES_B, json=payload, allow_redirects=True, timeout=15)
            print("Réponse Google Apps Script (Statut) :", response.status_code)
            print("Réponse Google Apps Script (Contenu) :", response.text)
        except Exception as e:
            print("ERREUR CRITIQUE lors de l'envoi au Classeur B :", str(e))
            
    return redirect('/')

@app.route('/api/actualites', methods=['GET'])
def api_actualites():
    conn = sqlite3.connect('cs_banza.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM actualites ORDER BY id DESC')
    rows = cursor.fetchall()
    liste_actu = [{
        "id": row["id"], "titre": row["titre"], "date": row["date"],
        "image": row["image"], "extrait": row["extrait"], "contenu": row["contenu_complet"]
    } for row in rows]
    conn.close()
    return jsonify(liste_actu)

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)