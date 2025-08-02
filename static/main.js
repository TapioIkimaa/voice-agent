const recordButton = document.getElementById('recordButton');
const audioPlayback = document.getElementById('audioPlayback');
const statusDiv = document.getElementById('status');

let mediaRecorder;
let audioChunks = [];

window.onload = () => {
    recordButton.disabled = false;
    statusDiv.textContent = 'Ready to record';
}

recordButton.addEventListener('click', async () => {
    if (mediaRecorder && mediaRecorder.state === 'recording') {
        mediaRecorder.stop();
    } else {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            console.log('Streaming');
            mediaRecorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
            recordButton.textContent = 'Stop';
            statusDiv.textContent = 'Recording...';
            audioChunks = [];
            mediaRecorder.ondataavailable = (event) => {
                audioChunks.push(event.data);
            };
            mediaRecorder.onstop = async () => {
                recordButton.textContent = 'Record';
                statusDiv.textContent = 'Processing...';

                const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                const file = new File([audioBlob], 'recording.webm', { type: 'audio/webm' });
                const formData = new FormData();
                formData.append('recording', file);

                try {
                    const response = await fetch('/process-recording', {
                        method: 'POST',
                        body: formData
                    });
                    const blob = await response.blob();
                    const audioUrl = URL.createObjectURL(blob);
                    audioPlayback.src = audioUrl;
                    statusDiv.textContent = 'Playing...';
                    audioPlayback.onended = () => {
                        statusDiv.textContent = 'Ready to record';
                    };
                    await audioPlayback.play();
                } catch (error) {
                    console.error('Error processing recording:', error);
                    statusDiv.textContent = 'Error processing recording.';
                }
            };
            mediaRecorder.start();
        } catch (error) {
            console.error('Error getting media:', error);
            statusDiv.textContent = 'Could not start recording. Please allow microphone access.';
        }
    }
});
