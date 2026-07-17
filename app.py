from flask import Flask, render_template, request, redirect, jsonify  # type: ignore[import]
import sqlite3

app = Flask(__name__)

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,DELETE,OPTIONS'
    return response
# Initialisation de la base de données
def init_db():
    conn = sqlite3.connect('cs_banza.db')
    conn.execute('CREATE TABLE IF NOT EXISTS actualites (id INTEGER PRIMARY KEY, titre TEXT, contenu TEXT)')
    conn.execute('CREATE TABLE IF NOT EXISTS inscriptions (id INTEGER PRIMARY KEY, nomEleve TEXT, classe TEXT, option TEXT)')
    conn.close()

@app.route('/')
def dashboard():
    conn = sqlite3.connect('cs_banza.db')
    conn.row_factory = sqlite3.Row
    actu = conn.execute('SELECT * FROM actualites').fetchall()
    inscrits = conn.execute('SELECT * FROM inscriptions').fetchall()
    conn.close()
    return render_template('dashboard.html', actu=actu, inscrits=inscrits)

@app.route('/publier', methods=['POST'])
def publier():
    titre = request.form['titre']
    contenu = request.form['contenu']
    conn = sqlite3.connect('cs_banza.db')
    conn.execute('INSERT INTO actualites (titre, contenu) VALUES (?, ?)', (titre, contenu))
    conn.commit()
    conn.close()
    return redirect('/')

@app.route('/api/actualites', methods=['GET'])
def api_actualites():
    # On se connecte à la base de données
    conn = sqlite3.connect('cs_banza.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # On récupère toutes les actualités
    cursor.execute('SELECT * FROM actualites ORDER BY id DESC')
    rows = cursor.fetchall()
    
    # On transforme les données en liste de dictionnaires
    liste_actu = [dict(row) for row in rows]
    
    conn.close()
    
    # On renvoie le tout au format JSON
    return jsonify(liste_actu)

# Route pour supprimer une actualité
@app.route('/supprimer_actu/<int:id>')
def supprimer_actu(id):
    conn = sqlite3.connect('cs_banza.db')
    conn.execute('DELETE FROM actualites WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect('/')

# Route pour modifier (Exemple simple : mise à jour du contenu)
@app.route('/modifier_actu/<int:id>', methods=['POST'])
def modifier_actu(id):
    titre = request.form['titre']
    contenu = request.form['contenu']
    conn = sqlite3.connect('cs_banza.db')
    conn.execute('UPDATE actualites SET titre = ?, contenu = ? WHERE id = ?', (titre, contenu, id))
    conn.commit()
    conn.close()
    return redirect('/')

import pandas as pd # Installez-le avec : pip install pandas

@app.route('/')
def dashboard():
    # Remplacez le lien ci-dessous par VOTRE lien de publication CSV
    url_sheet = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSnehMzrPtz_JWvIUzyhY93nQC4Lm15gNB3YvMPXXw2zYPVeb04tKeIpCmTbxU5on8-gcY5AOkz_CXf/pub?gid=0&single=true&output=csv"
    
    # Lecture des données directement depuis le lien
    df = pd.read_csv(url_sheet)
    inscrits = df.to_dict(orient='records')
    
    # Récupération des actualités (toujours dans votre base SQLite)
    # ... (code habituel pour les actus) ...
    
    return render_template('dashboard.html', inscrits=inscrits, actu=actu)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)