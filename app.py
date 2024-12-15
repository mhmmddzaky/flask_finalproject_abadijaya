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

# Fungsi untuk format Rupiah
def format_rupiah(amount):
    amount = int(amount)
    return f"Rp {amount:,.0f}".replace(",", ".")

# Mendaftarkan fungsi sebagai filter Jinja2
app.jinja_env.filters['rupiah'] = format_rupiah

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
        if "user_id" not in session: 
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

    # mengambil product unggulan
    featured_products = list(db.product.find({"featured_prod": "unggulan"}))

    # Ambil semua kategori dari koleksi `categories`
    categories = list(db.category.find())

    return render_template(
        'home.html',
         username=session.get("username"),
         profile_picture=profile_picture,
         categories= categories,
         products=featured_products)

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
        # Cek apakah user sudah login
        if not session.get("user_id"):  # Jika tidak ada user_id di session, artinya user belum login
            flash("Anda harus login terlebih dahulu untuk mengirim pesan.", "error")
            return redirect(url_for("login"))  # Redirect ke halaman login

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
                           profile_picture=profile_picture,
                           username=session.get("username"))

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
@app.route('/product', methods=['GET'])
def product():
    profile_picture = session.get("profile_picture", "static/foto_profile/profile.png")

    # Ambil semua kategori dari koleksi `categories`
    categories = list(db.category.find())

    # code untuk menghitung jumlah produk sesuai dengan kategorinya
    for category in categories:
        product_count = db.product.count_documents({"product_category": category["category_name"]})
        category["product_count"] = product_count  # Menambahkan jumlah produk ke kategori

    # Ambil kategori yang dipilih dari query string
    selected_category = request.args.get("category", "Semua")
    # Mendapatkan parameter pencarian dari URL
    search_query = request.args.get('search', '')  # Jika tidak ada pencarian, default ke string kosong

    # Bangun query untuk MongoDB secara dinamis
    query = {}

    # Tambahkan filter kategori jika kategori yang dipilih bukan "Semua"
    if selected_category != "Semua":
        query["product_category"] = selected_category

    # Tambahkan filter pencarian jika ada query pencarian
    if search_query:
        query["product_name"] = {'$regex': search_query, '$options': 'i'}

    # Ambil produk berdasarkan query
    products = list(db.product.find(query))    

    # Ubah ObjectId menjadi string untuk keperluan tampilan
    for product in products:
        product["_id"] = str(product["_id"])

    no_results = len(products) == 0  # Cek apakah tidak ada hasil pencarian

    return render_template(
        'product.html',
        username=session.get("username"),
        profile_picture=profile_picture,
        categories=categories,
         selected_category=selected_category,
        products=products,
        no_results=no_results,  # Menyertakan variabel untuk menampilkan pesan jika tidak ada hasil
        search_query=search_query  # Kirimkan query pencarian untuk menampilkan kembali di input
    )

# PRODUCT DETAIL ROUTE
@app.route('/detail_produk')
@login_required
def detail_produk():
    profile_picture = session.get("profile_picture", "static/foto_profile/profile.png")

    # mendapatkan id produknya
    product_id = request.args.get("id")

    # mencari data sesuai id nya
    get_product = db.product.find_one({"_id": ObjectId(product_id)})

    # Ambil kategori produk
    category = get_product.get("product_category")

    # Mencari produk lain dengan kategori yang sama
    related_products = db.product.find({"product_category": category, "_id": {"$ne": ObjectId(product_id)}})

    return render_template(
    'detail_produk.html',
    username=session.get("username"),
    profile_picture=profile_picture,
    get_product=get_product,
    related_products=related_products)

# DASHBOARD ROUTE
@app.route('/dashboard')
def dashboard():
    # Periksa apakah pengguna sudah login
    if "user_id" not in session:
        flash("Anda harus login terlebih dahulu!", "error")
        return redirect(url_for("login"))

    # Ambil data pengguna berdasarkan sesi user_id
    user_id = session["user_id"]
    user = db.users.find_one({"_id": ObjectId(user_id)})

    if not user:
        flash("Pengguna tidak ditemukan.", "error")
        return redirect(url_for("login"))

    # Periksa apakah pengguna memiliki peran admin
    if user.get("role") != "admin":
        flash("Anda tidak memiliki izin untuk mengakses halaman ini.", "error")
        return redirect(url_for("home"))  # Ganti 'home' dengan halaman lain untuk user biasa

    return render_template(
        'dashboard.html',
        username=session.get("username"))

# CATEGORY ADD ROUTE
@app.route('/add_kategori', methods=['GET', 'POST'])
def add_kategori():
    if request.method == 'POST':
        try:
            # Menerima data dari form
            category_name = request.form.get('category_name')

            # Validasi sederhana
            if not category_name:
                flash('Nama kategori wajib diisi!', 'error')
                return redirect(url_for('add_kategori'))

            # Mengelola file gambar
            file = request.files.get('category_image')
            if file:
                # Ekstensi file
                extension = file.filename.split('.')[-1]
                # Nama file berdasarkan timestamp
                timestamp = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
                filename = f'category-{timestamp}.{extension}'
                # Path penyimpanan file
                file_path = os.path.join('static', 'category_images', filename)
                file.save(file_path)  # Simpan file ke folder lokal
            else:
                flash('Gambar kategori harus diunggah!', 'error')
                return redirect(url_for('add_kategori'))

            # Data yang akan disimpan ke MongoDB
            category_data = {
                'category_name': category_name,
                'category_image': filename,
            }
            # Simpan ke collection 'categories'
            db.category.insert_one(category_data)

            flash('Kategori berhasil ditambahkan!', 'success')
            return redirect(url_for('add_kategori'))
        except Exception as e:
            flash(f'Error: {str(e)}', 'error')
            return redirect(url_for('add_kategori'))

    return render_template('dsb_addkategori.html',
        username=session.get("username"))

# CATEGORY TABLE ROUTE
@app.route('/tabel_kategori')
def tabel_kategori():
    # Ambil semua data kategori dari koleksi category
    categories = list(db.category.find())
    
    # Ubah ObjectId ke string
    for category in categories:
        category["_id"] = str(category["_id"])

    return render_template('dsb_tabelkategori.html', categories=categories,
        username=session.get("username"))

# CATEGORY EDIT ROUTE
@app.route('/edit_kategori', methods=["GET", "POST"])
def edit_kategori():
    category_id = request.args.get("id")
    
    # Mendapatkan data kategori berdasarkan ID
    category = db.category.find_one({"_id": ObjectId(category_id)}, {
        "category_name": 1
    })

    if not category:
        flash("Kategori tidak ditemukan.", "error")
        return redirect(url_for("tabel_kategori"))

    if request.method == "POST":
        new_name = request.form["category_name"]

        # Data yang akan diupdate
        update_data = {"category_name": new_name}

        # Cek apakah ada gambar baru yang diunggah
        file = request.files.get("category_image")
        if file and file.filename != "":
            extension = file.filename.split('.')[-1]
            timestamp = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
            filename = f'category-{timestamp}.{extension}'
            file_path = os.path.join('static', 'category_images', filename)
            file.save(file_path)

            # Tambahkan nama file gambar baru ke data update
            update_data["category_image"] = filename

        # Update data kategori di database
        db.category.update_one({"_id": ObjectId(category_id)}, {"$set": update_data})

        flash("Kategori berhasil diperbarui.", "success")
        return redirect(url_for("tabel_kategori"))

    return render_template('dsb_editkategori.html', category=category,
        username=session.get("username"))

# CATEGORY DELETE ROUTE
@app.route('/delete_kategori/<category_id>', methods=["POST"])
def delete_kategori(category_id):
    try:
        # Hapus kategori berdasarkan ID
        result = db.category.delete_one({"_id": ObjectId(category_id)})

        # Cek apakah ada data yang dihapus
        if result.deleted_count > 0:
            flash("Kategori berhasil dihapus.", "success")
        else:
            flash("Kategori tidak ditemukan.", "error")
    except Exception as e:
        flash(f"Terjadi kesalahan: {str(e)}", "error")
    
    return redirect(url_for("tabel_kategori"))

# PRODUCT ADD ROUTE
@app.route('/add_produk', methods=['GET', 'POST'])
def add_produk():
    if request.method == 'POST':
        try:
            # Menerima data dari form
            product_name = request.form.get('product_name')
            product_category = request.form.get('product_category')
            product_brand = request.form.get('product_brand')
            featured_prod = request.form.get('featured_prod')
            product_desc = request.form.get('product_desc')
            product_price = request.form.get('product_price')

            # Validasi sederhana
            if not product_name or not product_category or not product_brand or not product_desc or not product_price:
                flash('Semua field wajib diisi!', 'error')
                return redirect(url_for('add_produk'))

            # Mengelola file gambar
            file = request.files.getlist('product_image')
            image_paths = []
            for index, file in enumerate(file):
                if file:
                    # Ekstensi file
                    extension = file.filename.split('.')[-1]
                    # Nama file berdasarkan timestamp
                    timestamp = datetime.now().strftime('%Y-%m-%d-%H-%M-%S-%f')
                    filename = f'product-{timestamp}-{index}.{extension}'
                    # Path penyimpanan file
                    file_path = os.path.join('static', 'product_images', filename)
                    file.save(file_path)  # Simpan file ke folder lokal
                    image_paths.append(file_path)
                else:
                    flash('Gambar produk harus diunggah!', 'error')
                    return redirect(url_for('add_produk'))

            # Data yang akan disimpan ke MongoDB
            product_data = {
                'product_name': product_name,
                'product_image': image_paths,
                'product_category': product_category,
                'product_brand': product_brand,
                'featured_prod': featured_prod,
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

    # Ambil data kategori untuk disertakan di form
    categories = list(db.category.find())
    for category in categories:
        category["_id"] = str(category["_id"])

    return render_template('dsb_addproduk.html', categories=categories,
        username=session.get("username"))

# PRODUCT TABLE ROUTE
@app.route('/tabel_produk')
def tabel_produk():
    # Ambil semua data produk dari koleksi product
    products = list(db.product.find())
    
    # Ubah ObjectId ke string
    for product in products:
        product["_id"] = str(product["_id"])

    return render_template('dsb_tabelproduk.html', products=products,
        username=session.get("username"))

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
        "product_price": 1,
        "featured_prod": 1
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
        new_featured = request.form.get("featured_prod")

        # Data yang akan diupdate
        update_data = {
            "product_name": new_name,
            "product_category": new_category,
            "product_brand": new_brand,
            "product_desc": new_desc,
            "product_price": new_price,
            "featured_prod": new_featured
        }

        # Cek apakah ada gambar baru yang diunggah
        files = request.files.getlist("product_image")
        if files and files[0].filename != "":  # Pastikan setidaknya ada satu file yang diunggah
            image_paths = []
            
            for index, file in enumerate(files):
                if file:
                    # Ekstensi file
                    extension = file.filename.split('.')[-1]
                    # Nama file berdasarkan timestamp
                    timestamp = datetime.now().strftime('%Y-%m-%d-%H-%M-%S-%f')
                    filename = f'product-{timestamp}-{index}.{extension}'
                    # Path penyimpanan file
                    file_path = os.path.join('static', 'product_images', filename)
                    file.save(file_path)  # Simpan file ke folder lokal
                    image_paths.append(file_path)

            # Tambahkan array nama file gambar baru ke data update
            update_data["product_image"] = image_paths

        # Update data produk di database
        db.product.update_one({"_id": ObjectId(product_id)}, {"$set": update_data})

        flash("Produk berhasil diperbarui.", "success")
        return redirect(url_for("tabel_produk"))

    # Ambil data kategori untuk disertakan di form
    categories = list(db.category.find())
    for category in categories:
        category["_id"] = str(category["_id"])

    return render_template('dsb_editproduk.html', product=product, categories=categories,
        username=session.get("username"))


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
    return render_template('dsb_adduser.html',
        username=session.get("username")) 

# USER TABLE ROUTE
@app.route('/tabel_user')
def tabel_user():
    # Ambil semua data pengguna dari koleksi users
    users = list(db.users.find())
    
    # Ubah ObjectId ke string 
    for user in users:
        user["_id"] = str(user["_id"])

    return render_template('dsb_tabeluser.html', users=users,
        username=session.get("username"))

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

    return render_template('dsb_edituser.html', user=user,
        username=session.get("username"))

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

    return render_template('dsb_tabelfeedback.html', feedbacks=feedbacks,
        username=session.get("username"))

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

    return render_template('dsb_viewfeedback.html', feedback=feedback,
        username=session.get("username"))

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
    # Periksa apakah pengguna sudah login
    if "user_id" not in session:
        flash("Anda harus login terlebih dahulu!", "error")
        return redirect(url_for("login"))

    # Ambil data pengguna berdasarkan sesi user_id
    user_id = session["user_id"]
    user = db.users.find_one({"_id": ObjectId(user_id)})

    if not user:
        flash("Pengguna tidak ditemukan.", "error")
        return redirect(url_for("login"))

    # Periksa apakah pengguna memiliki peran admin
    if user.get("role") != "admin":
        flash("Anda tidak memiliki izin untuk mengakses halaman ini.", "error")
        return redirect(url_for("home"))  

    # Kirim data ke template
    profile_data = {
        "username": user.get("username", "Tidak Diketahui"),
        "full_name": user.get("fullname", "Tidak Diketahui"),
        "email": user.get("email", "Tidak Diketahui"),
        "profile_picture": user.get("profile_picture", "/static/images/default_profile.png")
    }

    return render_template('profile_admin.html', profile_data=profile_data)

# ADMIN PROFILE EDIT ROUTE
@app.route('/updateprofile_admin')
def updateprofile_admin():
    return render_template('update_profileadmin.html') 

if __name__ == '__main__':
    app.run('0.0.0.0', port=5009, debug=True)
