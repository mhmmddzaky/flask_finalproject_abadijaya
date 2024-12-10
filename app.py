import os
from os.path import join, dirname
from dotenv import load_dotenv
from flask import Flask, render_template, jsonify, request, redirect, url_for, flash, session
from bson import ObjectId
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

MONGODB_URI = os.environ.get("MONGODB_URI")
DB_NAME = os.environ.get("DB_NAME")

client = MongoClient(MONGODB_URI)
db = client[DB_NAME]

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

# REGISTER ROUTE
@app.route('/register',methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # Ambil data dari form
        username = request.form.get("username")
        fullname = request.form.get("fullname")
        email = request.form.get("email")
        password = request.form.get("password")

        # Validasi data (contoh sederhana)
        if not username or not fullname or not email or not password:
            flash("Semua field wajib diisi!", "error")
            return redirect(url_for("register"))

        # Cek apakah email sudah digunakan
        existing_user = db.users.find_one({"email": email})
        if existing_user:
            flash("Email sudah terdaftar. Gunakan email lain.", "error")
            return redirect(url_for("register"))

        # Hash password dan simpan ke database
         # Hash password dan simpan ke database
        hashed_password = generate_password_hash(password)  

        # Foto profil default
        default_profile_picture = "static/foto_profile/profile.png"

        db.users.insert_one({
            "username": username,
            "fullname": fullname,
            "email": email,
            "password": hashed_password,
            "role": "user",
            "profile_picture": default_profile_picture
        })

        flash("Registrasi berhasil! Silakan login.", "success")
        return redirect(url_for("register"))

    return render_template('register.html')

# LOGIN ROUTE
@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        if not email or not password:
            flash("Email dan password wajib diisi!", "error")
            return redirect(url_for("login"))

        # Cari pengguna berdasarkan email
        user = db.users.find_one({"email": email})
        if user and check_password_hash(user["password"], password):
            # Login berhasil, simpan data ke sesi
            session["user_id"] = str(user["_id"])
            session["username"] = user["username"]
            session["profile_picture"] = user.get("profile_picture", "static/images/profile .png")
            session["role"] = user.get("role", "user")

            flash(f"Selamat datang, {user['username']}!", "success")

            # Redirect berdasarkan role
            if session["role"] == "admin":
                return redirect(url_for("dashboard"))
            else:
                return redirect(url_for("home"))
        else:
            flash("Email atau password salah.", "error")
            return redirect(url_for("login"))
    return render_template('login.html')

# LOGIN DECORATOR
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:  # Cek apakah pengguna sudah login
            flash("Anda harus login terlebih dahulu!", "error")
            return redirect(url_for("login", next=request.endpoint))  # Redirect ke login
        return f(*args, **kwargs)
    return decorated_function

# LOGOUT ROUTE
@app.route("/logout")
def logout():
    session.clear()
    flash("Anda berhasil logout.", "success")
    return redirect(url_for("home"))

# HOME ROUTE
@app.route('/')
def home():
    # ambil path foto profile   
    profile_picture = session.get("profile_picture", "static/foto_profile/profile.png")
    return render_template(
        'home.html',
         username=session.get("username"),
         profile_picture=profile_picture)

# ABOUT ROUTE
@app.route('/about')
def about():
    profile_picture = session.get("profile_picture", "static/foto_profile/profile.png")
    return render_template(
    'about.html',
    username=session.get("username"),
    profile_picture=profile_picture)

# CONTACT ROUTE
@app.route('/contact', methods=["GET", "POST"])
def contact():
    profile_picture = session.get("profile_picture", "static/foto_profile/profile.png")

    if request.method == "POST":
        try:
            # Ambil data dari form
            fullname = request.form.get("fullname")
            email = request.form.get("email")
            message = request.form.get("message")

            # Validasi sederhana
            if not fullname or not email or not message:
                flash("Semua field wajib diisi!", "error")
                return redirect(url_for("contact"))

            # Data yang akan disimpan ke database
            feedback_data = {
                "fullname": fullname,
                "email": email,
                "message": message,
                "date": datetime.now()
            }
            
            # Simpan pesan ke database
            db.feedback.insert_one(feedback_data)

            flash("Pesan berhasil dikirim. Terima kasih telah menghubungi kami!", "success")
            return redirect(url_for("contact"))
        except Exception as e:
            flash(f"Terjadi kesalahan: {str(e)}", "error")
            return redirect(url_for("contact"))

    return render_template(
        'contact.html',
        username=session.get("username"),
        profile_picture=profile_picture
    )

# PROFILE ROUTE
@app.route('/profile')
@login_required
def profile():
    profile_picture = session.get("profile_picture", "static/foto_profile/profile.png")
    # Ambil data pengguna dari database berdasarkan session user_id
    user_id = session.get("user_id")
    user = db.users.find_one({"_id": ObjectId(user_id)})

    return render_template('profile.html',
                           user=user,
                           profile_picture=profile_picture)

# PROFILE UPDATE ROUTE
@app.route('/update', methods=["GET", "POST"])
def update_profile():

    # ambil path foto profile   
    profile_picture = session.get("profile_picture", "static/foto_profile/profile.png")

    if request.method == "POST":
        new_name = request.form["new_username"]
        new_fullname = request.form["new_fullname"]
        new_email = request.form["new_email"]
        current_password = request.form["current_password"]
        new_password = request.form["new_password"]
        confirm_password = request.form["confirm_password"]
        profile_picture = request.files.get("profile_picture")

        user_id = session.get("user_id")
        user = db.users.find_one({"_id": ObjectId(user_id)})

        # Cek apakah email sudah digunakan oleh pengguna lain
        existing_user = db.users.find_one({"email": new_email})
        if existing_user and str(existing_user["_id"]) != str(user["_id"]):
            flash("Email sudah terdaftar oleh pengguna lain. Gunakan email lain.", "error")
            return redirect(url_for("update_profile"))

         # Verifikasi password lama
        if not check_password_hash(user["password"], current_password):
            flash("Password lama salah.", "error")
            return redirect(url_for("update_profile"))
        
         # Confirm password baru
        if new_password != confirm_password:
            flash("Password baru tidak cocok.", "error")
            return redirect(url_for("update_profile"))
        
        # Proses foto profil
        today = datetime.now()
        mytime = today.strftime('%Y-%m-%d-%H-%M-%S')
        upload_folder = os.path.join("static", "foto_profile")  # Path ke folder foto_profile
        if profile_picture and profile_picture.filename != "":
            # Jika file diunggah, simpan ke folder
            extension = profile_picture.filename.split('.')[-1]
            filename = f'profile-{mytime}.{extension}'
            file_path = os.path.join(upload_folder, filename)
            profile_picture.save(file_path)
            file_path = f'static/foto_profile/{filename}' # Path untuk database
        else:
            # Jika tidak ada file yang diunggah, gunakan foto profil yang sudah ada atau default
            file_path = user.get("profile_picture", "static/foto_profile/profile.png")
        
        # Update jika password valid
        db.users.update_one({"_id": ObjectId(user_id)}, {
            "$set": {
                "username": new_name,
                "fullname": new_fullname,
                "email": new_email,
                "profile_picture": file_path,
            }
        })

        # Jika ada password baru, hash dan simpan
        if new_password:
            hashed_password = generate_password_hash(new_password)
            db.users.update_one({"_id": ObjectId(user_id)}, {
                "$set": {
                    "password": hashed_password
                }
            })

        # Update session username
        session["username"] = new_name
        session["profile_picture"] = file_path
        
        flash("Data Kamu berhasil diperbarui.", "success")
        return redirect(url_for("profile"))

    return render_template('update.html',
        profile_picture=profile_picture,
        username=session.get("username"))

# PRODUCT ROUTE
@app.route('/product')
def product():
    profile_picture = session.get("profile_picture", "static/foto_profile/profile.png")

     # Ambil semua data produk dari koleksi product
    products = list(db.product.find())
    
    # Ubah ObjectId ke string
    for product in products:
        product["_id"] = str(product["_id"])


    return render_template(
    'product.html',
    username=session.get("username"),
    profile_picture=profile_picture,
    products=products)

# PRODUCT DETAIL ROUTE
@app.route('/detail_produk')
def detail_produk():
    profile_picture = session.get("profile_picture", "static/foto_profile/profile.png")
    return render_template(
    'detail_produk.html',
    username=session.get("username"),
    profile_picture=profile_picture)

# DASHBOARD ROUTE
@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

# PRODUCT ADD ROUTE
@app.route('/add_produk', methods=['GET', 'POST'])
def add_produk():
    if request.method == 'POST':
        try:
            # Menerima data dari form
            product_name = request.form.get('product_name')
            product_category = request.form.get('product_category')
            product_brand = request.form.get('product_brand')
            product_desc = request.form.get('product_desc')
            product_price = request.form.get('product_price')

            # Validasi sederhana
            if not product_name or not product_category or not product_brand or not product_desc or not product_price:
                flash('Semua field wajib diisi!', 'error')
                return redirect(url_for('add_produk'))

            # Mengelola file gambar
            file = request.files.get('product_image')
            if file:
                # Ekstensi file
                extension = file.filename.split('.')[-1]
                # Nama file berdasarkan timestamp
                timestamp = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
                filename = f'product-{timestamp}.{extension}'
                # Path penyimpanan file
                file_path = os.path.join('static', 'product_images', filename)
                file.save(file_path)  # Simpan file ke folder lokal
            else:
                flash('Gambar produk harus diunggah!', 'error')
                return redirect(url_for('add_produk'))

            # Data yang akan disimpan ke MongoDB
            product_data = {
                'product_name': product_name,
                'product_image': filename,
                'product_category': product_category,
                'product_brand': product_brand,
                'product_desc': product_desc,
                'product_price': product_price
            }
            # Simpan ke collection 'product'
            db.product.insert_one(product_data)

            flash('Produk berhasil ditambahkan!', 'success')
            return redirect(url_for('add_produk'))
        except Exception as e:
            flash(f'Error: {str(e)}', 'error')
            return redirect(url_for('add_produk'))

    return render_template('dsb_addproduk.html')

# PRODUCT TABLE ROUTE
@app.route('/tabel_produk')
def tabel_produk():
    # Ambil semua data produk dari koleksi product
    products = list(db.product.find())
    
    # Ubah ObjectId ke string
    for product in products:
        product["_id"] = str(product["_id"])

    return render_template('dsb_tabelproduk.html', products=products)

# PRODUCT EDIT ROUTE
@app.route('/edit_produk', methods=["GET", "POST"])
def edit_produk():
    product_id = request.args.get("id")
    
    # Mendapatkan data produk berdasarkan ID
    product = db.product.find_one({"_id": ObjectId(product_id)}, {
        "product_name": 1,
        "product_category": 1,
        "product_brand": 1,
        "product_desc": 1,
        "product_price": 1
    })

    if not product:
        flash("Produk tidak ditemukan.", "error")
        return redirect(url_for("tabel_produk"))

    if request.method == "POST":
        new_name = request.form["product_name"]
        new_category = request.form["product_category"]
        new_brand = request.form["product_brand"]
        new_desc = request.form["product_desc"]
        new_price = request.form["product_price"]

        # Data yang akan diupdate
        update_data = {
            "product_name": new_name,
            "product_category": new_category,
            "product_brand": new_brand,
            "product_desc": new_desc,
            "product_price": new_price
        }

        # Cek apakah ada gambar baru yang diunggah
        file = request.files.get("product_image")
        if file and file.filename != "":
            extension = file.filename.split('.')[-1]
            timestamp = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
            filename = f'product-{timestamp}.{extension}'
            file_path = os.path.join('static', 'product_images', filename)
            file.save(file_path)

            # Tambahkan nama file gambar baru ke data update
            update_data["product_image"] = filename

        # Update data produk di database
        db.product.update_one({"_id": ObjectId(product_id)}, {"$set": update_data})

        flash("Produk berhasil diperbarui.", "success")
        return redirect(url_for("tabel_produk"))

    return render_template('dsb_editproduk.html', product=product)

# PRODUCT DELETE ROUTE
@app.route('/delete_produk/<product_id>', methods=["POST"])
def delete_produk(product_id):
    try:
        # Hapus produk berdasarkan ID
        result = db.product.delete_one({"_id": ObjectId(product_id)})

        # Cek apakah ada data yang dihapus
        if result.deleted_count > 0:
            flash("Produk berhasil dihapus.", "success")
        else:
            flash("Produk tidak ditemukan.", "error")
    except Exception as e:
        flash(f"Terjadi kesalahan: {str(e)}", "error")
    
    return redirect(url_for("tabel_produk"))

# USER ADD ROUTE
@app.route('/add_admin', methods=["GET", "POST"])
def add_admin():
    if request.method == "POST":
        # Ambil data dari form
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        fullname = request.form.get("fullname")
        role = request.form.get("role")

        # Validasi data (contoh sederhana)
        if not username or not email or not fullname or not role or not password:
            flash("Semua field wajib diisi!", "error")
            return redirect(url_for("add_admin"))

        # Cek apakah email sudah digunakan
        existing_user = db.users.find_one({"email": email})
        if existing_user:
            flash("Email sudah terdaftar. Gunakan email lain.", "error")
            return redirect(url_for("add_admin"))

        # Hash password dan simpan ke database
        hashed_password = generate_password_hash(password)  

        # Foto profil default
        default_profile_picture = "static/foto_profile/profile.png"

        db.users.insert_one({
            "username": username,
            "email": email,
            "password": hashed_password,
            "role": role,
            "fullname": fullname,
            "profile_picture": default_profile_picture
        })

        flash("User Berhasil Ditambahkan", "success")
        return redirect(url_for("add_admin"))
    return render_template('dsb_adduser.html') 

# USER TABLE ROUTE
@app.route('/tabel_user')
def tabel_user():
    # Ambil semua data pengguna dari koleksi users
    users = list(db.users.find())
    
    # Ubah ObjectId ke string 
    for user in users:
        user["_id"] = str(user["_id"])

    return render_template('dsb_tabeluser.html', users=users)

# USER EDIT ROUTE
@app.route('/edit_user', methods=["GET", "POST"])
def edit_user():
    user_id = request.args.get("id")
    
    user = db.users.find_one({"_id": ObjectId(user_id)})

    if request.method == "POST":
        new_name = request.form["new_username"]
        new_fullname = request.form["new_fullname"]
        new_email = request.form["new_email"]
        new_password = request.form["new_password"]
        new_role = request.form["new_role"]

        # Cek apakah email sudah digunakan oleh pengguna lain
        existing_user = db.users.find_one({"email": new_email})
        if existing_user and str(existing_user["_id"]) != str(user["_id"]):
            flash("Email sudah terdaftar oleh pengguna lain. Gunakan email lain.", "error")
            return redirect(url_for("edit_user"))
        
        # Update data
        db.users.update_one({"_id": ObjectId(user_id)}, {
            "$set": {
                "username": new_name,
                "fullname": new_fullname,
                "email": new_email,
                "role": new_role,
            }
        })

         # password baru, hash dan simpan
        if new_password:
            hashed_password = generate_password_hash(new_password)
            db.users.update_one({"_id": ObjectId(user_id)}, {
                "$set": {
                    "password": hashed_password
                }
            })
        
        flash("Data Kamu berhasil diperbarui.", "success")
        return redirect(url_for("tabel_user"))

    return render_template('dsb_edituser.html', user=user)

#USER DELETE ROUTE
@app.route('/delete_user/<user_id>',  methods=["POST"])
def delete_user(user_id):

    # Hapus pengguna berdasarkan ID
    result = db.users.delete_one({"_id": ObjectId(user_id)})

    # Cek apakah ada data yang dihapus
    if result.deleted_count > 0:
        flash("Pengguna berhasil dihapus.", "success")
    else:
        flash("Pengguna tidak ditemukan.", "error")

    return redirect(url_for("tabel_user"))

# FEEDBACK TABLE ROUTE
@app.route('/tabel_feedback', methods=['GET'])
def tabel_feedback():
    # Ambil semua data feedback dari koleksi feedback
    feedbacks = list(db.feedback.find())

    # Ubah ObjectId menjadi string
    for feedback in feedbacks:
        feedback["_id"] = str(feedback["_id"])

    return render_template('dsb_tabelfeedback.html', feedbacks=feedbacks)

# FEEDBACK VIEW ROUTE
@app.route('/view_feedback', methods=["GET"])
def view_feedback():
    feedback_id = request.args.get("id")
    
    # Mendapatkan data feedback berdasarkan ID
    feedback = db.feedback.find_one({"_id": ObjectId(feedback_id)}, {
        "fullname": 1,
        "email": 1,
        "message": 1
    })

    if not feedback:
        flash("Feedback tidak ditemukan.", "error")
        return redirect(url_for("tabel_feedback"))

    return render_template('dsb_viewfeedback.html', feedback=feedback)

# FEEDBACK DELETE ROUTE
@app.route('/delete_feedback/<feedback_id>', methods=["POST"])
def delete_feedback(feedback_id):
    try:
        # Hapus feedback berdasarkan ID
        result = db.feedback.delete_one({"_id": ObjectId(feedback_id)})

        # Cek apakah ada data yang dihapus
        if result.deleted_count > 0:
            flash("Feedback berhasil dihapus.", "success")
        else:
            flash("Feedback tidak ditemukan.", "error")
    except Exception as e:
        flash(f"Terjadi kesalahan: {str(e)}", "error")
    
    return redirect(url_for("tabel_feedback"))

# ADMIN PROFILE ROUTE
@app.route('/profile_admin')
def profile_admin():
    return render_template('profile_admin.html') 

# ADMIN PROFILE EDIT ROUTE
@app.route('/updateprofile_admin')
def updateprofile_admin():
    return render_template('update_profileadmin.html') 

if __name__ == '__main__':
    app.run('0.0.0.0', port=5009, debug=True)
