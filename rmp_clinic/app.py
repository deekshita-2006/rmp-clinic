from flask import Flask, render_template, request, redirect, session, url_for, flash
import sqlite3
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table
from reportlab.lib.styles import getSampleStyleSheet
from flask import send_file
import io

app = Flask(__name__)
app.secret_key = "secret_key"

DATABASE = "database.db"

# ---------------- DATABASE ----------------
def init_db():
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()

    cur.execute('''CREATE TABLE IF NOT EXISTS doctor(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT,
                    password TEXT)''')

    cur.execute('''CREATE TABLE IF NOT EXISTS patients(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    age INTEGER,
                    gender TEXT,
                    phone TEXT)''')

    cur.execute('''CREATE TABLE IF NOT EXISTS appointments(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    patient_id INTEGER,
                    date TEXT,
                    time TEXT,
                    status TEXT DEFAULT 'Pending',
                    FOREIGN KEY(patient_id) REFERENCES patients(id))''')

    cur.execute('''CREATE TABLE IF NOT EXISTS records(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    patient_id INTEGER,
                    diagnosis TEXT,
                    prescription TEXT,
                    file_path TEXT,
                    FOREIGN KEY(patient_id) REFERENCES patients(id))''')

    conn.commit()
    conn.close()
# ---------------- LOGIN ----------------
@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect(DATABASE)
        cur = conn.cursor()
        cur.execute("SELECT * FROM doctor WHERE username=? AND password=?",(username,password))
        user = cur.fetchone()
        conn.close()

        if user:
            session["doctor"] = username
            return redirect("/dashboard")
        else:
            flash("Invalid Credentials")

    return render_template("login.html")
 
@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect(DATABASE)
        cur = conn.cursor()
        cur.execute("INSERT INTO doctor(username,password) VALUES(?,?)",
                    (username,password))
        conn.commit()
        conn.close()

        return redirect("/")

    return render_template("register.html")

# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM patients")
    total_patients = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM appointments")
    total_appointments = cur.fetchone()[0]

    conn.close()

    return render_template("dashboard.html",
                           total_patients=total_patients,
                           total_appointments=total_appointments)

# ---------------- ADD PATIENT ----------------
@app.route("/add_patient", methods=["GET","POST"])
def add_patient():
    if request.method == "POST":
        name = request.form["name"]
        age = request.form["age"]
        gender = request.form["gender"]
        phone = request.form["phone"]

        conn = sqlite3.connect(DATABASE)
        cur = conn.cursor()
        cur.execute("INSERT INTO patients(name,age,gender,phone) VALUES(?,?,?,?)",
                    (name,age,gender,phone))
        conn.commit()
        conn.close()

        return redirect("/patients")

    return render_template("add_patient.html")

@app.route("/history/<int:patient_id>")
def history(patient_id):
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()

    cur.execute("""
        SELECT id, diagnosis, prescription, file_path
        FROM records
        WHERE patient_id=?
    """, (patient_id,))

    records = cur.fetchall()
    conn.close()

    return render_template("history.html", records=records)


# ---------------- ADD APPOINTMENT ----------------
@app.route("/add_appointment", methods=["GET","POST"])
def add_appointment():
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    cur.execute("SELECT * FROM patients")
    patients = cur.fetchall()

    if request.method == "POST":
        patient_id = request.form["patient_id"]
        date = request.form["date"]
        time = request.form["time"]

        cur.execute("INSERT INTO appointments(patient_id,date,time) VALUES(?,?,?)",
                    (patient_id,date,time))
        conn.commit()
        conn.close()

        return redirect("/appointments")

    conn.close()
    return render_template("add_appointment.html", patients=patients)

# ---------------- VIEW APPOINTMENTS ----------------
@app.route("/appointments")
def appointments():
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    cur.execute('''SELECT appointments.id, patients.name, date, time
                   FROM appointments
                   JOIN patients ON appointments.patient_id = patients.id''')
    data = cur.fetchall()
    conn.close()
    return render_template("appointments.html", appointments=data)
    
@app.route("/update_status/<int:id>/<status>")
def update_status(id, status):
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()

    cur.execute("UPDATE appointments SET status=? WHERE id=?", (status, id))
    conn.commit()
    conn.close()

    return redirect("/appointments")

# ---------------- ADD RECORD ----------------
@app.route("/add_record/<int:patient_id>", methods=["GET", "POST"])
def add_record(patient_id):
    if request.method == "POST":
        diagnosis = request.form["diagnosis"]
        prescription = request.form["prescription"]

        file = request.files.get("file")
        file_path = None

        if file and file.filename:
            upload_folder = "static/uploads"

            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)

            file_path = f"{upload_folder}/{file.filename}"
            file.save(file_path)

        conn = sqlite3.connect(DATABASE)
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO records(patient_id, diagnosis, prescription, file_path)
            VALUES(?, ?, ?, ?)
        """, (patient_id, diagnosis, prescription, file_path))

        conn.commit()
        conn.close()

        return redirect("/patients")

    return render_template("add_record.html", patient_id=patient_id)
    
# ---------------- SEARCH & VIEW PATIENTS ----------------
@app.route("/patients", methods=["GET"])
def patients():
    search = request.args.get("search", "")

    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()

    if search:
        cur.execute("SELECT * FROM patients WHERE name LIKE ?", ('%' + search + '%',))
    else:
        cur.execute("SELECT * FROM patients")

    data = cur.fetchall()
    conn.close()

    return render_template("patients.html", patients=data)


# ---------------- EDIT PATIENT ----------------
@app.route("/edit_patient/<int:id>", methods=["GET", "POST"])
def edit_patient(id):
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()

    if request.method == "POST":
        name = request.form["name"]
        age = request.form["age"]
        gender = request.form["gender"]
        phone = request.form["phone"]

        cur.execute("UPDATE patients SET name=?, age=?, gender=?, phone=? WHERE id=?",
                    (name, age, gender, phone, id))
        conn.commit()
        conn.close()

        return redirect("/patients")

    cur.execute("SELECT * FROM patients WHERE id=?", (id,))
    patient = cur.fetchone()
    conn.close()

    return render_template("edit_patient.html", patient=patient)


# ---------------- DELETE PATIENT ----------------
@app.route("/delete_patient/<int:id>")
def delete_patient(id):
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()

    cur.execute("DELETE FROM patients WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return redirect("/patients")
 
@app.route("/download_history/<int:patient_id>")
def download_history(patient_id):
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()

    # Get patient name
    cur.execute("SELECT name FROM patients WHERE id=?", (patient_id,))
    patient = cur.fetchone()

    # Get medical history
    cur.execute("""
        SELECT id, diagnosis, prescription
        FROM records
        WHERE patient_id=?
    """, (patient_id,))

    records = cur.fetchall()
    conn.close()

    if not patient:
        return "Patient not found"

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer)

    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph(f"Medical History of {patient[0]}", styles["Title"]))

    table_data = [["ID", "Diagnosis", "Prescription"]]

    for r in records:
        table_data.append([r[0], r[1], r[2]])

    table = Table(table_data)
    elements.append(table)

    doc.build(elements)
    buffer.seek(0)

    return send_file(buffer, as_attachment=True,
                     download_name="medical_history.pdf",
                     mimetype="application/pdf")

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.pop("doctor", None)
    return redirect("/")


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0",port=10000)