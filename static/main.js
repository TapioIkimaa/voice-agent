const recordButton = document.getElementById('recordButton');
const audioPlayback = document.getElementById('audioPlayback');
const statusDiv = document.getElementById('status');

let mediaRecorder;
let audioChunks = [];

window.onload = () => {
    recordButton.disabled = false;
    statusDiv.textContent = 'Ready to record';
}

recordButton.addEventListener('click', () => {
    if (mediaRecorder && mediaRecorder.state === 'recording') {
        mediaRecorder.stop();
    } else {
        navigator.mediaDevices.getUserMedia({ audio: true })
            .then(stream => {
                console.log('Streaming');
                mediaRecorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
                recordButton.textContent = 'Stop';
                statusDiv.textContent = 'Recording...';
                audioChunks = [];
                mediaRecorder.ondataavailable = (event) => {
                    audioChunks.push(event.data);
                }
                mediaRecorder.onstop = () => {
                    recordButton.textContent = 'Record';
                    statusDiv.textContent = 'Processing...';

                    const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                    const file = new File([audioBlob], 'recording.webm', { type: 'audio/webm' });
                    const formData = new FormData();
                    formData.append('recording', file);

                    fetch('/process-recording', {
                        method: 'POST',
                        body: formData
                    })
                    .then(response => response.blob())
                    .then(blob => {
                        const audioUrl = URL.createObjectURL(blob);
                        audioPlayback.src = audioUrl;
                        statusDiv.textContent = 'Playing...';
                        audioPlayback.play();
                        statusDiv.textContent = '';
                    });
                }
                mediaRecorder.start();
            });
    }
});
