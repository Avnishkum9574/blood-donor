const video = document.getElementById("video");
const canvas = document.getElementById("canvas");

const startButton = document.getElementById("startCamera");
const captureButton = document.getElementById("captureButton");

const message = document.getElementById("cameraMessage");
const donorResult = document.getElementById("donorResult");

let cameraStream = null;


// =====================================
// START CAMERA
// =====================================

startButton.addEventListener("click", async function () {

    try {

        if (
            !navigator.mediaDevices ||
            !navigator.mediaDevices.getUserMedia
        ) {
            message.innerText =
                "Camera is not supported by this browser.";

            return;
        }

        message.innerText =
            "Requesting camera permission...";

        cameraStream =
            await navigator.mediaDevices.getUserMedia({
                video: {
                    facingMode: "user"
                },
                audio: false
            });

        video.srcObject = cameraStream;

        await video.play();

        message.innerText =
            "Camera started successfully. Position your face.";

    }

    catch (error) {

        console.error("Camera error:", error);

        message.innerText =
            "Camera error: " + error.message;
    }

});


// =====================================
// CAPTURE FACE
// =====================================

captureButton.addEventListener("click", async function () {

    if (!cameraStream) {

        message.innerText =
            "Please click Start Camera first.";

        return;
    }


    if (
        video.videoWidth === 0 ||
        video.videoHeight === 0
    ) {

        message.innerText =
            "Camera is not ready. Please wait.";

        return;
    }


    // Set canvas size

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;


    // Get canvas context

    const context = canvas.getContext("2d");


    // Capture current camera frame

    context.drawImage(
        video,
        0,
        0,
        canvas.width,
        canvas.height
    );


    // Convert image to Base64

    const faceImage =
        canvas.toDataURL("image/jpeg");


    message.innerText =
        "Checking face...";

    donorResult.innerHTML = "";


    try {

        // Send image to Flask

        const response = await fetch("/recognize", {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                face_image: faceImage
            })

        });


        const result = await response.json();


        // ============================
        // FACE FOUND
        // ============================

        if (result.success) {

            message.innerText =
                result.message;


            const donor = result.donor;


            donorResult.innerHTML = `
                <div class="donor-result">

                    <h2>Donor Found</h2>

                    <p>
                        <strong>Name:</strong>
                        ${donor.name}
                    </p>

                    <p>
                        <strong>Phone:</strong>
                        ${donor.phone}
                    </p>

                    <p>
                        <strong>Blood Group:</strong>
                        ${donor.blood_group}
                    </p>

                    <p>
                        <strong>Match Score:</strong>
                        ${result.confidence}
                    </p>

                </div>
            `;

        }

        // ============================
        // FACE NOT FOUND
        // ============================

        else {

            message.innerText =
                result.message;

        }

    }

    catch (error) {

        console.error(
            "Recognition error:",
            error
        );

        message.innerText =
            "Error connecting to server.";
    }

});


// =====================================
// STOP CAMERA WHEN LEAVING PAGE
// =====================================

window.addEventListener(
    "beforeunload",
    function () {

        if (cameraStream) {

            cameraStream
                .getTracks()
                .forEach(function (track) {
                    track.stop();
                });
        }

    }
);