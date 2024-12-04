import os
from os.path import join, dirname
from dotenv import load_dotenv
from flask import Flask, render_template, jsonify, request
from pymongo import MongoClient

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

# MONGODB_URI = os.environ.get("MONGODB_URI")
# DB_NAME = os.environ.get("DB_NAME")

# client = MongoClient(MONGODB_URI)
# db = client[DB_NAME]

app = Flask(__name__)

# Main Navbar #
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/profile')
def profile():
    return render_template('profile.html')

@app.route('/update')
def update_profile():
    return render_template('update.html')

@app.route('/product')
def product():
    return render_template('product.html')

@app.route('/detail_produk')
def detail_produk():
    return render_template('detail_produk.html')

# Admin Sidebar #
@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/tabel_produk')
def tabel_produk():
    return render_template('dsb_tabelproduk.html')

@app.route('/tabel_user')
def tabel_user():
    return render_template('dsb_tabeluser.html')

@app.route('/tabel_feedback')
def tabel_feedback():
    return render_template('dsb_tabelfeedback.html')

@app.route('/edit_produk')
def edit_produk():
    return render_template('dsb_editproduk.html')

@app.route('/edit_user')
def edit_user():
    return render_template('dsb_edituser.html')


@app.route('/add_admin')
def add_admin():
    return render_template('dsb_adduser.html') 

@app.route('/add_produk')
def add_produk():
    return render_template('dsb_addproduk.html') 

@app.route('/feedback')
def feedback():
    return render_template('feedback.html')

if __name__ == '__main__':
    app.run('0.0.0.0', port=5009, debug=True)
