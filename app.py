import sqlite3
import requests
import json
from flask import Flask, render_template, request, g, redirect, jsonify
from collections import Counter
from flask_sqlalchemy import SQLAlchemy


app = Flask(__name__)
app.secret_key = "NuP56etw6zg2wpctYIgqupJaZrllgMhw"

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mytvshows.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Show(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    start_date = db.Column(db.Date)
    finish_date = db.Column(db.Date)
    status = db.Column(db.String(20), nullable=False)
    genre = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    user_rating = db.Column(db.String(5))
    user_notes = db.Column(db.Text)
    poster_url = db.Column(db.String(255))

def get_db():
    conn = sqlite3.connect('mytvshows.db')
    cursor = conn.cursor()
    return conn, cursor

def init_db():
    conn, cursor = get_db()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS shows (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            start_date DATE,
            finish_date DATE,
            status TEXT NOT NULL,
            genre TEXT NOT NULL,
            description TEXT,
            user_rating TEXT,
            user_notes TEXT,
            poster_url TEXT
        )
    ''')
    
    
    conn.commit()
    
@app.route("/")
def index():
    conn, cursor = get_db()
    cursor.execute("SELECT DISTINCT genre FROM shows")
    genres = [row[0] for row in cursor.fetchall()]
    cursor.execute("SELECT DISTINCT user_rating FROM shows")
    ratings = [row[0] for row in cursor.fetchall()]
    cursor.execute("SELECT * FROM shows")
    shows = cursor.fetchall()
    conn.close()
    return render_template("index.html", shows=shows, genres=genres, ratings=ratings)


@app.route("/add_show", methods=["GET"])
def add_show_form():
    return render_template("add_show.html")

@app.route("/add_show", methods=["POST"])
def add_show():
    show_name = request.form.get('show_name')
    start_date = request.form.get('start_date')
    finish_date = request.form.get('finish_date')
    status = request.form.get('status')
    user_rating = request.form.get('user_rating')
    show_description = request.form.get('show_description')
    genre = request.form.get('genre')
    user_notes = request.form.get('user_notes')

    if show_name:
        conn, cursor = get_db()
        
        show_title_for_api = show_name.replace(" ", "%20")
        api_key = 'c4a9354307c3c98a2eb14eb4d3cfbcb7'
        tmdb_url = f'https://api.themoviedb.org/3/search/tv?api_key={api_key}&query={show_title_for_api}'
        tmdb_response = requests.get(url=tmdb_url)
        tmdb_data = tmdb_response.json()
        show_description = tmdb_data.get('results', [{}])[0].get('overview', 'No description available')
        
        poster_path = tmdb_data.get('results', [{}])[0].get('poster_path')
        poster_base_url = 'https://image.tmdb.org/t/p/'
        poster_size = 'w500'  
        full_poster_url = f"{poster_base_url}{poster_size}{poster_path}" if poster_path else None

        cursor.execute(
            "INSERT INTO shows (name, start_date, finish_date, status, description, poster_url, user_rating, genre, user_notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (show_name, start_date, finish_date, status, show_description, full_poster_url, user_rating, genre, user_notes)
        )
        conn.commit()

    return redirect("/")

@app.route("/get_show_details/<int:show_id>")
def get_show_details(show_id):
    show = Show.query.get(show_id)

    if show:
        show_details = {
            'id': show.id,
            'name': show.name,
            'start_date': str(show.start_date),
            'finish_date': str(show.finish_date),
            'status': show.status,
            'genre': show.genre,
            'description': show.description,
            'user_rating': show.user_rating,
            'user_notes': show.user_notes,
            'poster_url': show.poster_url
        }
        return jsonify(show_details)
    else:
        return jsonify(error="Show not found"), 404

@app.route('/filtered_page', methods=['POST'])
def filtered_page():
    filtered_data = request.form.get('filtered_data')
    filtered_data = json.loads(filtered_data)
    count = 0
    total = 0
    genres = []

    for show in filtered_data:
        total += show[7]
        count += 1
        genres.append(show[5]) 
        
    average_rating = total / count
    genre_counter = Counter(genres)
    most_common_genres = genre_counter.most_common()
    if len(most_common_genres) > 1 and most_common_genres[0][1] == most_common_genres[1][1]:
        most_common_genre = "N/A"
    else:
        most_common_genre = most_common_genres[0][0] if most_common_genres else None
        
    return render_template('filtered_shows.html', shows=filtered_data, average_rating=average_rating, most_common_genre=most_common_genre)


@app.route("/edit_show/<int:id>", methods=["GET", "POST"])
def edit_show(id):
    if request.method == "GET":
        conn, cursor = get_db()
        cursor.execute("SELECT * FROM shows WHERE id = ?", (id,))
        show = cursor.fetchone()
        conn.close()
        return render_template("edit_show.html", show=show)
    elif request.method == "POST":
        start_date = request.form.get('start_date')
        finish_date = request.form.get('finish_date')
        status = request.form.get('status')
        user_rating = request.form.get('user_rating')
        genre = request.form.get('genre')
        user_notes = request.form.get('user_notes')

        conn, cursor = get_db()
        cursor.execute(
                "UPDATE shows SET start_date=?, finish_date=?, status=?, user_rating=?, genre=?, user_notes=? WHERE id=?",
                (start_date, finish_date, status, user_rating, genre, user_notes, id)
        )
        conn.commit()
        conn.close()
        return redirect("/")


@app.route("/show_details/<int:id>")
def show_details(id):
    conn = sqlite3.connect('mytvshows.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM shows WHERE id = ?", (id,))
    show = cursor.fetchone()
    conn.close()
    return render_template("show_details.html", show=show)



    
@app.route("/delete_show/<int:id>")
def delete_show(id):
    conn, cursor = get_db()
    cursor.execute("DELETE FROM shows WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect("/")


@app.route("/filter_shows", methods=["POST"])
def filter_shows():
    genre = request.form.get('genre')
    user_rating = request.form.get('user_rating')
    status = request.form.get('status')
    start_date_min = request.form.get('start_date_min')
    start_date_max = request.form.get('start_date_max')
    end_date_min = request.form.get('end_date_min')
    end_date_max = request.form.get('end_date_max')

    conn, cursor = get_db()    
    query = "SELECT * FROM shows WHERE"
    params = []
    
    if genre != "all":
        query += " genre = ? AND"
        params.append(genre)

    if user_rating != "all":
        query += " user_rating = ? AND"
        params.append(user_rating)

    if status != "all":
        query += " status = ? AND"
        params.append(status)
        
    if start_date_min and start_date_max:
        query += " start_date BETWEEN ? AND ? AND"
        params.extend([start_date_min, start_date_max])

    if end_date_min and end_date_max:
        query += " end_date BETWEEN ? AND ? AND"
        params.extend([end_date_min, end_date_max])

    if params:
        query = query.rstrip(" AND")
    
    print(query)
    cursor.execute(query, params)
    filtered_shows = cursor.fetchall()
    conn.close()

    return jsonify(filtered_shows)
    


if __name__ == '__main__':
    init_db()
    app.run(debug=True)