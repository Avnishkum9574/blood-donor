from flask import Flask, render_template, request, jsonify
import sqlite3
import os
import base64
import uuid
import cv2
import numpy as np


# =========================================================
# FLASK APP
# =========================================================

app = Flask(__name__)


# =========================================================
# PATHS
# =========================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATABASE = os.path.join(
    BASE_DIR,
    "databases",
    "donors.db"
)

FACE_FOLDER = os.path.join(
    BASE_DIR,
    "faces"
)

MODEL_FOLDER = os.path.join(
    BASE_DIR,
    "models"
)

os.makedirs(
    os.path.dirname(DATABASE),
    exist_ok=True
)

os.makedirs(
    FACE_FOLDER,
    exist_ok=True
)


# =========================================================
# FACE CASCADE
# =========================================================

CASCADE_PATH = os.path.join(
    MODEL_FOLDER,
    "haarcascade_frontalface_default.xml"
)

# If cascade is not present in models folder,
# use OpenCV's built-in cascade.

if not os.path.exists(CASCADE_PATH):

    CASCADE_PATH = os.path.join(
        cv2.data.haarcascades,
        "haarcascade_frontalface_default.xml"
    )

print("Cascade path:", CASCADE_PATH)
print("Cascade exists:", os.path.exists(CASCADE_PATH))


# Load face detector
face_cascade = cv2.CascadeClassifier(
    CASCADE_PATH
)


if face_cascade.empty():

    print("ERROR: Face cascade could not be loaded!")

else:

    print("Face cascade loaded successfully!")


# =========================================================
# DATABASE INITIALIZATION
# =========================================================

def init_database():

    connection = sqlite3.connect(
        DATABASE
    )

    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS donors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL UNIQUE,
            blood_group TEXT NOT NULL,
            face_file TEXT NOT NULL
        )
    """)

    connection.commit()

    connection.close()


init_database()


# =========================================================
# HOME PAGE
# =========================================================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# =========================================================
# SCAN PAGE
# =========================================================

@app.route("/scan")
def scan():

    return render_template(
        "scan.html"
    )


# =========================================================
# REGISTER PAGE
# =========================================================

@app.route("/register", methods=["GET"])
def register_page():

    return render_template(
        "register.html"
    )


# =========================================================
# REGISTER DONOR
# =========================================================

@app.route("/register", methods=["POST"])
def register_donor():

    filepath = None

    try:
        # -------------------------------------------------
        # Get JSON data
        # -------------------------------------------------
        data = request.get_json()

        if not data:
            return jsonify({
                "success": False,
                "message": "No data received."
            })

        name = str(data.get("name", "")).strip()
        phone = str(data.get("phone", "")).strip()
        blood_group = str(data.get("blood_group", "")).strip().upper()
        face_image = data.get("face_image")

        # -------------------------------------------------
        # Name, phone and blood group are required.
        # Face image is OPTIONAL.
        # -------------------------------------------------
        if not name or not phone or not blood_group:
            return jsonify({
                "success": False,
                "message": "Name, phone and blood group are required."
            })

        # -------------------------------------------------
        # Check duplicate phone number
        # -------------------------------------------------
        connection = sqlite3.connect(DATABASE)
        cursor = connection.cursor()

        cursor.execute(
            "SELECT id FROM donors WHERE phone = ?",
            (phone,)
        )

        existing_donor = cursor.fetchone()
        connection.close()

        if existing_donor:
            return jsonify({
                "success": False,
                "message": "This mobile number is already registered."
            })

        # -------------------------------------------------
        # Face image is optional
        # -------------------------------------------------
        filename = ""

        if face_image:
            # Remove Base64 header
            if "," in face_image:
                image_data = face_image.split(",", 1)[1]
            else:
                image_data = face_image

            # Decode image
            try:
                image_bytes = base64.b64decode(image_data)
            except Exception:
                return jsonify({
                    "success": False,
                    "message": "Invalid image data."
                })

            # Create unique filename
            filename = str(uuid.uuid4()) + ".jpg"
            filepath = os.path.join(FACE_FOLDER, filename)

            # Save image
            with open(filepath, "wb") as file:
                file.write(image_bytes)

            print("Face image saved:", filepath)

            # Read image
            image = cv2.imread(filepath)

            if image is None:
                if os.path.exists(filepath):
                    os.remove(filepath)
                return jsonify({
                    "success": False,
                    "message": "Could not read captured face image."
                })

            # Convert image to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            # Detect face
            faces = face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(80, 80)
            )

            if len(faces) == 0:
                if os.path.exists(filepath):
                    os.remove(filepath)
                return jsonify({
                    "success": False,
                    "message": "No face detected. Please capture your face again."
                })

        # -------------------------------------------------
        # Save donor information
        # -------------------------------------------------
        connection = sqlite3.connect(DATABASE)
        cursor = connection.cursor()

        try:
            cursor.execute("""
                INSERT INTO donors
                (name, phone, blood_group, face_file)
                VALUES (?, ?, ?, ?)
            """, (
                name,
                phone,
                blood_group,
                filename
            ))

            connection.commit()

        except sqlite3.IntegrityError:
            connection.rollback()

            if filepath and os.path.exists(filepath):
                os.remove(filepath)

            return jsonify({
                "success": False,
                "message": "This mobile number is already registered."
            })

        finally:
            connection.close()

        print("Donor registered:", name)
        print("Face registration:", "YES" if filename else "NO")

        return jsonify({
            "success": True,
            "message": "Donor registered successfully!"
        })

    except Exception as error:
        print("REGISTRATION ERROR:", error)

        if filepath and os.path.exists(filepath):
            try:
                os.remove(filepath)
            except Exception:
                pass

        return jsonify({
            "success": False,
            "message": "Error while registering donor."
        })


# =========================================================
# RECOGNIZE FACE
# =========================================================

@app.route(
    "/recognize",
    methods=["POST"]
)
def recognize_face():

    try:

        # -------------------------------------------------
        # Check face cascade
        # -------------------------------------------------

        if face_cascade.empty():

            print(
                "ERROR: Face cascade is empty."
            )


            return jsonify({
                "success": False,
                "message":
                    "Face detector could not be loaded."
            })


        # -------------------------------------------------
        # Get JSON data
        # -------------------------------------------------

        data = request.get_json()


        if not data:

            return jsonify({
                "success": False,
                "message":
                    "No image received."
            })


        face_image = data.get(
            "face_image"
        )


        if not face_image:

            return jsonify({
                "success": False,
                "message":
                    "Face image is required."
            })


        # -------------------------------------------------
        # Remove Base64 header
        # -------------------------------------------------

        if "," in face_image:

            image_data = face_image.split(
                ",",
                1
            )[1]

        else:

            image_data = face_image


        # -------------------------------------------------
        # Decode captured image
        # -------------------------------------------------

        try:

            image_bytes = base64.b64decode(
                image_data
            )

        except Exception:

            return jsonify({
                "success": False,
                "message":
                    "Invalid image data."
            })


        # -------------------------------------------------
        # Convert bytes to OpenCV image
        # -------------------------------------------------

        image_array = np.frombuffer(
            image_bytes,
            dtype=np.uint8
        )


        image = cv2.imdecode(
            image_array,
            cv2.IMREAD_COLOR
        )


        if image is None:

            return jsonify({
                "success": False,
                "message":
                    "Invalid captured image."
            })


        # -------------------------------------------------
        # Detect face in captured image
        # -------------------------------------------------

        gray = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY
        )


        detected_faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(80, 80)
        )


        if len(detected_faces) == 0:

            return jsonify({
                "success": False,
                "message":
                    "No face detected. Please try again."
            })


        # -------------------------------------------------
        # Get donors from database
        # -------------------------------------------------

        connection = sqlite3.connect(
            DATABASE
        )

        cursor = connection.cursor()


        cursor.execute("""
            SELECT
                id,
                name,
                phone,
                blood_group,
                face_file
            FROM donors
        """)


        donors = cursor.fetchall()


        connection.close()


        if not donors:

            return jsonify({
                "success": False,
                "message":
                    "No donors registered yet."
            })


        # -------------------------------------------------
        # Check OpenCV face recognition module
        # -------------------------------------------------

        if not hasattr(
            cv2,
            "face"
        ):

            return jsonify({
                "success": False,
                "message":
                    "OpenCV face recognition module "
                    "is not available. "
                    "Install opencv-contrib-python."
            })


        # -------------------------------------------------
        # Create LBPH recognizer
        # -------------------------------------------------

        recognizer = (
            cv2.face
            .LBPHFaceRecognizer_create()
        )


        training_images = []

        training_labels = []

        donor_information = {}

        label_number = 0


        # -------------------------------------------------
        # Prepare training images
        # -------------------------------------------------

        for donor in donors:

            donor_id = donor[0]

            donor_name = donor[1]

            donor_phone = donor[2]

            donor_blood_group = donor[3]

            donor_face_file = donor[4]

            # Donor may have registered without a face.
            # Such donors cannot participate in face recognition.
            if not donor_face_file:
                continue

            filepath = os.path.join(
                FACE_FOLDER,
                donor_face_file
            )


            if not os.path.exists(
                filepath
            ):

                continue


            donor_image = cv2.imread(
                filepath
            )


            if donor_image is None:

                continue


            donor_gray = cv2.cvtColor(
                donor_image,
                cv2.COLOR_BGR2GRAY
            )


            donor_faces = face_cascade.detectMultiScale(
                donor_gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(80, 80)
            )


            if len(donor_faces) == 0:

                continue


            # -------------------------------------------------
            # Use first detected face
            # -------------------------------------------------

            x, y, w, h = donor_faces[0]


            face_crop = donor_gray[
                y:y + h,
                x:x + w
            ]


            if face_crop.size == 0:

                continue


            # Keep image size same
            face_crop = cv2.resize(
                face_crop,
                (200, 200)
            )


            training_images.append(
                face_crop
            )


            training_labels.append(
                label_number
            )


            donor_information[
                label_number
            ] = {

                "id": donor_id,

                "name": donor_name,

                "phone": donor_phone,

                "blood_group":
                    donor_blood_group
            }


            label_number += 1


        # -------------------------------------------------
        # Check training data
        # -------------------------------------------------

        if len(training_images) == 0:

            return jsonify({
                "success": False,
                "message":
                    "No valid donor face images found."
            })


        # -------------------------------------------------
        # Train recognizer
        # -------------------------------------------------

        recognizer.train(
            training_images,
            np.array(
                training_labels
            )
        )


        # -------------------------------------------------
        # Recognize captured face
        # -------------------------------------------------

        best_match = None

        best_confidence = 999


        for x, y, w, h in detected_faces:

            captured_face = gray[
                y:y + h,
                x:x + w
            ]


            if captured_face.size == 0:

                continue


            captured_face = cv2.resize(
                captured_face,
                (200, 200)
            )


            label, confidence = (
                recognizer.predict(
                    captured_face
                )
            )


            print(
                "Prediction:",
                label,
                "Confidence:",
                confidence
            )


            if confidence < best_confidence:

                best_confidence = confidence

                best_match = label


        # -------------------------------------------------
        # Recognition threshold
        # -------------------------------------------------

        # Lower LBPH confidence = better match
        #
        # 0   = very good match
        # 50  = good
        # 70  = acceptable
        # 100+ = generally poor
        #
        # Current threshold = 70

        if (
            best_match is not None
            and best_match in donor_information
            and best_confidence <= 70
        ):

            donor = donor_information[
                best_match
            ]


            return jsonify({

                "success": True,

                "message":
                    "Donor recognized successfully!",

                "donor": donor,

                "confidence":
                    round(
                        best_confidence,
                        2
                    )
            })


        # -------------------------------------------------
        # Face not recognized
        # -------------------------------------------------

        return jsonify({

            "success": False,

            "message":
                "Face not recognized. Please try again."
        })


    except Exception as error:

        print(
            "RECOGNITION ERROR:",
            error
        )


        return jsonify({

            "success": False,

            "message":
                "Error while recognizing face."
        })


# =========================================================
# SEARCH BLOOD DONORS
# =========================================================
@app.route("/search_donors")
def search_donors():

    try:

        # Get blood group from request
        blood_group = request.args.get("blood_group", "").strip()

        # Fix + issue
        if blood_group in ["A", "B", "AB", "O"]:
            blood_group += "+"

        # Check selection
        if not blood_group:
            return jsonify({
                "success": False,
                "message": "Please select a blood group."
            })

        # Connect database
        connection = sqlite3.connect(DATABASE)
        cursor = connection.cursor()

        # Search donor
        cursor.execute("""
            SELECT name, phone, blood_group
            FROM donors
            WHERE TRIM(UPPER(blood_group))=TRIM(UPPER(?))
        """, (blood_group,))

        rows = cursor.fetchall()

        connection.close()

        # No donor found
        if not rows:
            return jsonify({
                "success": False,
                "message": "No donor found for " + blood_group
            })

        # Prepare donor list
        donors = []

        for row in rows:

            donors.append({
                "name": row[0],
                "phone": row[1],
                "blood_group": row[2]
            })

        # Return results
        return jsonify({
            "success": True,
            "donors": donors
        })

    except Exception as error:

        print("SEARCH ERROR:", error)

        return jsonify({
            "success": False,
            "message": "Error while searching donors."
        })
@app.route("/search")
def search_page():
        return render_template("search.html")
    



# =========================================================
# RUN FLASK
# =========================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )