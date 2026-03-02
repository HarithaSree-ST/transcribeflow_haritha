import os
import whisper
import json
from transformers import pipeline
from flask import Flask, render_template, request, redirect, flash, session, send_from_directory, jsonify
import mysql.connector
from werkzeug.utils import secure_filename

# -------------------- APP SETUP -------------------- #

app = Flask(__name__)
app.secret_key = "secretkey"

# -------------------- LOAD MODELS -------------------- #

whisper_model = whisper.load_model("base")
summarizer = pipeline("summarization", model="t5-small")

# -------------------- FOLDER CONFIG -------------------- #

UPLOAD_FOLDER = "uploads"
TRANSCRIPT_FOLDER = "transcripts"
SUMMARY_FOLDER = "summaries"
COMBINED_FOLDER = "combined"
JSON_FOLDER = "json_outputs"

ALLOWED_EXTENSIONS = {"mp3", "wav"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(TRANSCRIPT_FOLDER, exist_ok=True)
os.makedirs(SUMMARY_FOLDER, exist_ok=True)
os.makedirs(COMBINED_FOLDER, exist_ok=True)
os.makedirs(JSON_FOLDER, exist_ok=True)

# -------------------- DATABASE CONNECTION -------------------- #

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="haritha@0402",
    database="transcribeflow"
)
cursor = db.cursor()

# -------------------- HELPER FUNCTIONS -------------------- #

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def generate_summary(text):
    try:
        input_text = "summarize: " + text
        result = summarizer(
            input_text,
            max_length=120,
            min_length=30,
            do_sample=False
        )
        return result[0]["summary_text"]
    except Exception as e:
        print("Summarization Error:", e)
        return "Summary generation failed."

# -------------------- LOGIN & REGISTER -------------------- #

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        cursor.execute(
            "SELECT * FROM users WHERE email=%s AND password=%s",
            (email, password)
        )
        user = cursor.fetchone()

        if user:
            session["user"] = email
            return redirect("/upload")
        else:
            flash("Invalid credentials")

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        cursor.execute(
            "INSERT INTO users (email, password) VALUES (%s, %s)",
            (email, password)
        )
        db.commit()

        flash("Registered successfully! Please login.")
        return redirect("/")

    return render_template("register.html")

# -------------------- MAIN UPLOAD -------------------- #

@app.route("/upload", methods=["GET", "POST"])
def upload():
    if "user" not in session:
        return redirect("/")

    transcription = None
    summary = None
    transcript_filename = None
    summary_filename = None
    combined_filename = None
    json_filename = None

    if request.method == "POST":

        if "file" not in request.files:
            flash("No file selected")
            return redirect(request.url)

        file = request.files["file"]

        if file.filename == "":
            flash("No file selected")
            return redirect(request.url)

        if file and allowed_file(file.filename):

            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(filepath)

            try:
                # 1️⃣ Transcription
                result = whisper_model.transcribe(filepath, fp16=False)
                transcription = result["text"]

                # 2️⃣ Summary
                summary = generate_summary(transcription)

                base_name = filename.rsplit(".", 1)[0]

                # 3️⃣ Save Transcript
                transcript_filename = base_name + "_transcript.txt"
                with open(os.path.join(TRANSCRIPT_FOLDER, transcript_filename), "w", encoding="utf-8") as f:
                    f.write(transcription)

                # 4️⃣ Save Summary
                summary_filename = base_name + "_summary.txt"
                with open(os.path.join(SUMMARY_FOLDER, summary_filename), "w", encoding="utf-8") as f:
                    f.write(summary)

                # 5️⃣ Save Combined File
                combined_filename = base_name + "_full.txt"
                with open(os.path.join(COMBINED_FOLDER, combined_filename), "w", encoding="utf-8") as f:
                    f.write("TRANSCRIPTION:\n\n")
                    f.write(transcription)
                    f.write("\n\nSUMMARY:\n\n")
                    f.write(summary)

                # 6️⃣ Save JSON File
                json_filename = base_name + ".json"
                json_data = {
                    "transcript": transcription,
                    "summary": summary
                }
                with open(os.path.join(JSON_FOLDER, json_filename), "w", encoding="utf-8") as f:
                    json.dump(json_data, f, indent=4)

                flash("File processed successfully!")

            except Exception as e:
                flash("Error processing file.")
                print("Processing Error:", e)

        else:
            flash("Invalid file format. Upload MP3 or WAV only.")

    return render_template(
        "upload.html",
        transcription=transcription,
        summary=summary,
        txt_filename=transcript_filename,
        summary_filename=summary_filename,
        combined_filename=combined_filename,
        json_filename=json_filename
    )

# -------------------- API FOR LIVE RECORDING -------------------- #

@app.route("/api/upload", methods=["POST"])
def api_upload():

    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]

    if file and allowed_file(file.filename):

        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)

        # 1️⃣ Transcribe
        result = whisper_model.transcribe(filepath, fp16=False)
        transcription = result["text"]

        # 2️⃣ Summarize
        summary = generate_summary(transcription)

        base_name = filename.rsplit(".", 1)[0]

        # 3️⃣ Save Transcript
        transcript_filename = base_name + "_transcript.txt"
        with open(os.path.join(TRANSCRIPT_FOLDER, transcript_filename), "w", encoding="utf-8") as f:
            f.write(transcription)

        # 4️⃣ Save Summary
        summary_filename = base_name + "_summary.txt"
        with open(os.path.join(SUMMARY_FOLDER, summary_filename), "w", encoding="utf-8") as f:
            f.write(summary)

        # 5️⃣ Save Combined
        combined_filename = base_name + "_full.txt"
        with open(os.path.join(COMBINED_FOLDER, combined_filename), "w", encoding="utf-8") as f:
            f.write("TRANSCRIPTION:\n\n")
            f.write(transcription)
            f.write("\n\nSUMMARY:\n\n")
            f.write(summary)

        # 6️⃣ Save JSON
        json_filename = base_name + ".json"
        with open(os.path.join(JSON_FOLDER, json_filename), "w", encoding="utf-8") as f:
            json.dump({
                "transcript": transcription,
                "summary": summary
            }, f, indent=4)

        # 🔥 IMPORTANT: Return filenames also
        return jsonify({
            "transcript": transcription,
            "summary": summary,
            "combined_filename": combined_filename,
            "json_filename": json_filename,
            "transcript_filename": transcript_filename,
            "summary_filename": summary_filename
        })

    return jsonify({"error": "Invalid file format"}), 400
# -------------------- DOWNLOAD ROUTES -------------------- #

@app.route("/download/transcript/<filename>")
def download_transcript(filename):
    return send_from_directory(TRANSCRIPT_FOLDER, filename, as_attachment=True)


@app.route("/download/summary/<filename>")
def download_summary(filename):
    return send_from_directory(SUMMARY_FOLDER, filename, as_attachment=True)


@app.route("/download/combined/<filename>")
def download_combined(filename):
    return send_from_directory(COMBINED_FOLDER, filename, as_attachment=True)


@app.route("/download/json/<filename>")
def download_json(filename):
    return send_from_directory(JSON_FOLDER, filename, as_attachment=True)


@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/")

# -------------------- RUN -------------------- #

if __name__ == "__main__":
    app.run(debug=True)