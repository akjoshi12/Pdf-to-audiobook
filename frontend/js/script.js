
document.addEventListener('DOMContentLoaded', () => {
    const uploadForm = document.getElementById('upload-form');
    const pdfFile = document.getElementById('pdf-file');
    const voiceSelect = document.getElementById('voice-select');
    const previewText = document.getElementById('preview-text');
    const previewBtn = document.getElementById('preview-btn');
    const convertBtn = document.getElementById('convert-btn');
    const btnText = document.getElementById('btn-text');
    const btnSpinner = document.getElementById('btn-spinner');

    const initialMessage = document.getElementById('initial-message');
    const progressContainer = document.getElementById('progress-container');
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');
    const resultContainer = document.getElementById('result-container');
    const warningContainer = document.getElementById('warning-container');
    const audioPlayer = document.getElementById('audio-player');
    const downloadBtn = document.getElementById('download-btn');
    const errorContainer = document.getElementById('error-container');

    // --- Initial State Setup ---
    const fetchVoices = async () => {
        try {
            const response = await fetch('/api/voices');
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            const voices = await response.json();
            voiceSelect.innerHTML = ''; // Clear loading message
            voices.forEach(voice => {
                const option = document.createElement('option');
                option.value = voice;
                option.textContent = voice;
                voiceSelect.appendChild(option);
            });
            voiceSelect.disabled = false;
        } catch (error) {
            console.error('Failed to fetch voices:', error);
            voiceSelect.innerHTML = '<option>Could not load voices</option>';
            errorContainer.textContent = 'Failed to load voice list. Please try refreshing.';
            errorContainer.style.display = 'block';
        }
    };

    fetchVoices();

    // --- Event Listeners ---
    pdfFile.addEventListener('change', () => {
        if (pdfFile.files.length > 0) {
            convertBtn.disabled = false;
        } else {
            convertBtn.disabled = true;
        }
    });

    previewBtn.addEventListener('click', async () => {
        const text = previewText.value;
        const voice = voiceSelect.value;
        if (!text || !voice) return;

        const originalBtnContent = previewBtn.innerHTML;
        previewBtn.disabled = true;
        previewBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Generating...';

        try {
            const response = await fetch('/api/preview', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ text, voice }),
            });

            if (!response.ok) {
                throw new Error('Failed to generate preview.');
            }

            const audioBlob = await response.blob();
            const audioUrl = URL.createObjectURL(audioBlob);
            const audio = new Audio(audioUrl);
            audio.play();

        } catch (error) {
            showError(error.message);
        } finally {
            previewBtn.disabled = false;
            previewBtn.innerHTML = originalBtnContent;
        }
    });

    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (!pdfFile.files[0]) return;

        resetUI();
        setLoadingState(true);

        const formData = new FormData();
        formData.append('pdf_file', pdfFile.files[0]);
        formData.append('voice', voiceSelect.value);

        try {
            const response = await fetch('/api/convert', {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || 'Conversion failed to start.');
            }

            const { task_id } = await response.json();
            progressContainer.style.display = 'block';
            pollStatus(task_id);

        } catch (error) {
            showError(error.message);
            setLoadingState(false);
        }
    });

    // --- UI Helper Functions ---
    const setLoadingState = (isLoading) => {
        if (isLoading) {
            btnText.textContent = 'Converting...';
            btnSpinner.style.display = 'inline-block';
            convertBtn.disabled = true;
        } else {
            btnText.textContent = 'Convert';
            btnSpinner.style.display = 'none';
            convertBtn.disabled = false;
        }
    };

    const resetUI = () => {
        initialMessage.style.display = 'none';
        progressContainer.style.display = 'none';
        resultContainer.style.display = 'none';
        errorContainer.style.display = 'none';
        warningContainer.style.display = 'none';
        progressBar.style.width = '0%';
        progressText.textContent = 'Starting conversion...';
    };

    const showError = (message) => {
        errorContainer.textContent = message;
        errorContainer.style.display = 'block';
    };

    // --- Polling Logic ---
    const pollStatus = (taskId) => {
        const interval = setInterval(async () => {
            try {
                const response = await fetch(`/api/status/${taskId}`);
                if (!response.ok) {
                    throw new Error('Could not get status.');
                }
                const data = await response.json();

                progressBar.style.width = `${data.progress}%`;
                progressText.textContent = `Processing... (${data.progress}%)`;

                if (data.status === 'complete') {
                    clearInterval(interval);
                    
                    // Check for and display warnings about incomplete conversions
                    if (data.total_chunks && data.successful_chunks < data.total_chunks) {
                        warningContainer.textContent = `Warning: Conversion finished, but ${data.total_chunks - data.successful_chunks} out of ${data.total_chunks} text chunks failed to convert. The audiobook may be incomplete.`
                        warningContainer.style.display = 'block';
                    }

                    progressContainer.style.display = 'none';
                    resultContainer.style.display = 'block';
                    audioPlayer.src = `/api/download/${taskId}`;
                    downloadBtn.href = `/api/download/${taskId}`;
                    setLoadingState(false);
                } else if (data.status === 'failed') {
                    clearInterval(interval);
                    showError(`Conversion failed: ${data.error}`);
                    setLoadingState(false);
                }
            } catch (error) {
                clearInterval(interval);
                showError('Error checking conversion status.');
                setLoadingState(false);
            }
        }, 2000); // Poll every 2 seconds
    };
});
