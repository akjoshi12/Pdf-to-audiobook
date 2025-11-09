# PDF to Audiobook Converter

This project is a web-based application that converts PDF files into audiobooks. Users can upload a PDF, choose from a variety of voices, and generate an MP3 audio file of the document's content.

## Features

- **PDF to Audio Conversion:** Extracts text from uploaded PDF files and converts it into speech.
- **Voice Selection:** Allows users to choose from a wide range of voices for the audiobook generation, powered by Microsoft Edge's online text-to-speech service.
- **Voice Preview:** Users can type in custom text to preview how a selected voice sounds before starting the conversion.
- **Background Processing:** The conversion process runs in the background, allowing the user to track the progress without tying up the browser.
- **Real-time Progress:** The frontend displays a real-time progress bar, showing the status of the conversion.
- **Audio Playback and Download:** Once the audiobook is generated, it can be played directly in the browser or downloaded as an MP3 file.
- **Responsive UI:** The user interface is built with Bootstrap, making it responsive and easy to use on different devices.

## Technologies Used

### Backend

- **FastAPI:** A modern, fast (high-performance) web framework for building APIs with Python.
- **edge-tts:** A Python library that uses Microsoft Edge's online text-to-speech service to convert text to speech.
- **pydub:** A Python library to work with audio files.
- **pdfplumber:** A library to extract text from PDF files.
- **Uvicorn:** An ASGI server for running the FastAPI application.

### Frontend

- **HTML5, CSS3, JavaScript:** Standard web technologies for the user interface.
- **Bootstrap:** A popular CSS framework for building responsive and mobile-first websites.
- **Material Icons:** Used for icons throughout the application.

## Setup and Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/pdf_to_audiobook_fastapi.git
    cd pdf_to_audiobook_fastapi
    ```

2.  **Install backend dependencies:**
    Navigate to the `backend` directory and install the required Python packages.
    ```bash
    cd backend
    pip install -r requirements.txt
    ```

3.  **Run the backend server:**
    From the `backend` directory, start the FastAPI server using Uvicorn.
    ```bash
    uvicorn main:app --reload
    ```
    The backend server will be running at `http://127.0.0.1:8000`.

## Usage

1.  **Open the web interface:**
    Once the backend server is running, open the `frontend/index.html` file in your web browser, or navigate to `http://127.0.0.1:8000`.

2.  **Upload a PDF:**
    Click the "Upload PDF" button and select a PDF file from your computer.

3.  **Select a Voice:**
    Choose a voice from the dropdown menu. You can use the "Preview Voice" feature to test the selected voice.

4.  **Convert:**
    Click the "Convert" button to start the conversion process. The progress bar will show the status of the conversion.

5.  **Playback and Download:**
    Once the conversion is complete, an audio player will appear. You can play the audiobook directly or download it to your device using the "Download Audiobook" button.
