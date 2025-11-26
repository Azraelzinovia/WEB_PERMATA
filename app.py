from flask import Flask, render_template, request, redirect, session, send_file
from pymongo import MongoClient
from bson.objectid import ObjectId
import os
import base64
import uuid
import pandas as pd
from datetime import datetime

app = Flask(__name__)
app.secret_key = "permata-session-key"

# Maksimal upload 50MB
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024

# Anti 413
@app.before_request
def block_large_requests():
    cl = request.content_length
    if cl is not None and cl > app.config["MAX_CONTENT_LENGTH"]:
        return "Request terlalu besar", 413

# MongoDB
MONGO_URI = "mongodb+srv://permata_user:Permata12345@cluster0.0aooruh.mongodb.net/?appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client["permata_db"]
absensi_collection = db["absensi"]

# Folder foto
UPLOAD_FOLDER = "static/registered_photos"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ===============================
# HALAMAN UTAMA
# ===============================
@app.route("/")
def index():
    return render_template("index.html")

# ===============================
# KIRIM ABSENSI
# ===============================
@app.route("/absen", methods=["POST"])
def absen():
    name = request.form.get("name")
    kegiatan = request.form.get("kegiatan")
    kegiatanLain = request.form.get("kegiatanLain") or ""
    imageData = request.form.get("imageData")

    if not name or not kegiatan or not imageData:
        return redirect("/")

    # Simpan foto
    filename = f"{name.replace(' ', '_')}_{uuid.uuid4().hex}.jpg"
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    try:
        img = imageData.split(",")[1]
        with open(filepath, "wb") as f:
            f.write(base64.b64decode(img))
    except Exception as e:
        return f"Error saat menyimpan foto: {e}"

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Simpan database
    absensi_collection.insert_one({
        "name": name,
        "kegiatan": kegiatan,
        "kegiatanLain": kegiatanLain,
        "photo": filename,
        "timestamp": timestamp
    })

    return redirect("/success")

@app.route("/success")
def success():
    return render_template("success.html")

# ===============================
# LOGIN ADMIN
# ===============================
@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        password = request.form.get("password")

        if password == "adminPermatagacorRnya3":
            session["is_admin"] = True
            return redirect("/admin")

        return render_template("admin_login.html", error="Password salah!")

    return render_template("admin_login.html")

# ===============================
# DASHBOARD ADMIN
# ===============================
@app.route("/admin")
def admin():
    if not session.get("is_admin"):
        return redirect("/admin-login")

    data = list(absensi_collection.find())
    for item in data:
        item["_id"] = str(item["_id"])

    return render_template("admin.html", absensi=data)

# ===============================
# HAPUS DATA
# ===============================
@app.route("/delete/<id>")
def delete(id):
    if not session.get("is_admin"):
        return redirect("/admin-login")

    try:
        absensi_collection.delete_one({"_id": ObjectId(id)})
    except:
        pass

    return redirect("/admin")

# ===============================
# EXPORT EXCEL
# ===============================
@app.route("/export-excel")
def export_excel():
    if not session.get("is_admin"):
        return redirect("/admin-login")

    data = list(absensi_collection.find())

    rows = [{
        "Nama": item.get("name"),
        "Kegiatan": item.get("kegiatan"),
        "Keterangan Lainnya": item.get("kegiatanLain"),
        "Foto": item.get("photo"),
        "Waktu": item.get("timestamp")
    } for item in data]

    df = pd.DataFrame(rows)
    file_path = "absensi.xlsx"
    df.to_excel(file_path, index=False)

    return send_file(file_path, as_attachment=True)

# ===============================
# LOGOUT
# ===============================
@app.route("/admin-logout")
def admin_logout():
    session.pop("is_admin", None)
    return redirect("/admin-login")

# ===============================
# RUN APP
# ===============================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
@app.route("/rekap")
def rekap():
    if not session.get("is_admin"):
        return redirect("/admin-login")

    data = list(absensi_collection.find())

    rekap_dict = {}

    for item in data:
        name = item.get("name")

        if name not in rekap_dict:
            rekap_dict[name] = {
                "total": 0,
                "last": item.get("timestamp"),
                "kegiatan": item.get("kegiatan")
            }

        rekap_dict[name]["total"] += 1

        # update waktu terakhir hadir
        if item.get("timestamp") > rekap_dict[name]["last"]:
            rekap_dict[name]["last"] = item.get("timestamp")
            rekap_dict[name]["kegiatan"] = item.get("kegiatan")

    # ubah ke list agar bisa di-render
    hasil = []
    for nama, info in rekap_dict.items():
        hasil.append({
            "name": nama,
            "total": info["total"],
            "last": info["last"],
            "kegiatan": info["kegiatan"]
        })

    return render_template("rekap.html", hasil=hasil)
