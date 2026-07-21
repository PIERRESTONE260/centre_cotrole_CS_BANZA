from flask import Flask, render_template, request, redirect, jsonify, url_for
from flask_cors import CORS 
import sqlite3
import pandas as pd
import os
import requests # Nécessaire pour communiquer avec l'API Apps Script du Classeur B

app = Flask(__name__)
# Remplacez '*' par l'URL réelle de votre site Netlify pour plus de sécurité
CORS(app, resources={r"/api/*": {"origins": "https://csbanza.netlify.app"}})

# URL de l'API Web App du Classeur B (Côtes) déployée sur Google Apps Script
# Remplacez cette ligne par l'URL exacte obtenue lors du déploiement de votre Api.gs
URL_API_COTES_B = "https://script.google.com/macros/s/AKfycbzmyuv8SMVpHCjr9OTuS1jAVVGRXZhwyqbpCOcuY-dpLhT0L0Dag6u9SoUTLnEcWk0s/exec"

# Configuration du dossier d'upload pour les images
UPLOAD_FOLDER = 'static/images'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# --- INITIALISATION FORCÉE DE LA BASE DE DONNÉES ---
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

# Exécution immédiate au démarrage de l'application
init_db()

@app.route('/')
def dashboard():
    conn = sqlite3.connect('cs_banza.db')
    conn.row_factory = sqlite3.Row
    
    # Récupération des élèves inscrits directement depuis la base de données SQLite
    inscrits = conn.execute('SELECT * FROM inscriptions ORDER BY id DESC').fetchall()
    
    # Récupération des actualités
    actu = conn.execute('SELECT * FROM actualites ORDER BY id DESC').fetchall()
    conn.close()
    
    return render_template('dashboard.html', inscrits=inscrits, actu=actu)

@app.route('/publier', methods=['POST'])
def publier():
    try:
        titre = request.form['titre']
        date = request.form['date']
        extrait = request.form['extrait']
        contenu = request.form['contenu']
        
        # S'assurer que le dossier static/images existe physiquement
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

# --- NOUVELLE FONCTIONNALITÉ : Ajout dynamique de cours vers le Classeur B ---
@app.route('/ajouter_cours_admin', methods=['POST'])
def ajouter_cours_admin():
    classe_cible = request.form.get('classe_cible')
    nom_cours = request.form.get('nom_cours')
    
    if classe_cible and nom_cours:
        payload = {
            "action": "ajouterCours",
            "classe": classe_cible,
            "nomCours": nom_cours
        }
        try:
            # Envoi de la requête POST vers le script Google Apps Script du Classeur B
            response = requests.post(URL_API_COTES_B, json=payload)
            print("Réponse Apps Script :", response.text)
        except Exception as e:
            print("Erreur de communication avec le Classeur B :", str(e))
            
    return redirect('/')

@app.route('/api/actualites', methods=['GET'])
def api_actualites():
    conn = sqlite3.connect('cs_banza.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM actualites ORDER BY id DESC')
    rows = cursor.fetchall()
    
    liste_actu = [{
        "id": row["id"],
        "titre": row["titre"],
        "date": row["date"],
        "image": row["image"],
        "extrait": row["extrait"],
        "contenu": row["contenu_complet"]
    } for row in rows]
    
    conn.close()
    return jsonify(liste_actu)

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)