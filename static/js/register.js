const video = document.getElementById("video");
const canvas = document.getElementById("canvas");

const startButton = document.getElementById("startCamera");
const captureButton = document.getElementById("captureButton");

const form = document.getElementById("registerForm");
const message = document.getElementById("cameraMessage");

let cameraStream = null;
let capturedImage = null;


// =====================================================
// START CAMERA
// =====================================================

startButton.addEventListener("click", async function () {

    try {

        cameraStream = await navigator.mediaDevices.getUserMedia({
            video: true,
            audio: false
        });

        video.srcObject = cameraStream;

        message.innerText =
            "Camera started. Position your face.";

    } catch (error) {

        console.error(error);

        message.innerText =
            "Unable to access camera.";
    }
});


// =====================================================
// CAPTURE FACE
// =====================================================

captureButton.addEventListener("click", function () {

    if (!cameraStream) {

        message.innerText =
            "Please start the camera first.";

        return;
    }

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    const context = canvas.getContext("2d");

    context.drawImage(
        video,
        0,
        0,
        canvas.width,
        canvas.height
    );

    // Convert captured image to Base64
    capturedImage = canvas.toDataURL("image/jpeg");

    message.innerText =
        "Face captured successfully!";
});


// =====================================================
// REGISTER DONOR
// =====================================================

form.addEventListener("submit", async function (event) {

    event.preventDefault();

    const name = document.getElementById("name").value.trim();
    const phone = document.getElementById("phone").value.trim();
    const bloodGroup =
        document.getElementById("blood_group").value.trim();

    // ONLY these 3 fields are required
    if (!name || !phone || !bloodGroup) {

        message.innerText =
            "Name, phone and blood group are required.";

        return;
    }

    // Face image is OPTIONAL
    const donorData = {

        name: name,
        phone: phone,
        blood_group: bloodGroup,
        face_image: capturedImage || null
    };

    console.log("Sending donor data:", donorData);

    try {

        const response = await fetch("/register", {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify(donorData)
        });

        const result = await response.json();

        console.log("Server response:", result);

        if (result.success) {

            message.innerText =
                "Donor registered successfully!";

            form.reset();

            capturedImage = null;

        } else {

            message.innerText =
                result.message;
        }

    } catch (error) {

        console.error(error);

        message.innerText =
            "Registration failed.";
    }
});