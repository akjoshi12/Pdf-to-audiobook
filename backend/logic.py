
import edge_tts
from pydub import AudioSegment
import io
import pdfplumber
import re

DEFAULT_VOICES = [
    'en-US-AriaNeural',
    'en-US-GuyNeural',
    'en-GB-SoniaNeural',
    'en-GB-RyanNeural',
    'en-AU-NatashaNeural',
    'en-IN-NeerjaNeural',
]

def clean_text(text):
    """Cleans text by removing URLs and extra whitespace."""
    # Remove URLs
    url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    text = re.sub(url_pattern, '', text)
    # Remove extra whitespace and newlines
    text = text.replace('\n', ' ').strip()
    text = re.sub(r'\s+', ' ', text)
    return text

async def get_voices():
    """Fetches the list of available voices from edge-tts with a fallback."""
    try:
        voices = await edge_tts.list_voices()
        return [voice["ShortName"] for voice in voices]
    except Exception as e:
        print(f"Could not retrieve voices, using fallback list: {e}")
        return DEFAULT_VOICES

def extract_text_from_pdf(pdf_file):
    """Extracts text from an uploaded PDF file."""
    with pdfplumber.open(pdf_file) as pdf:
        return "".join(page.extract_text() for page in pdf.pages if page.extract_text())

def chunk_text(text, chunk_size=4000):
    """Splits text into smaller chunks."""
    return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]

async def convert_chunk_to_speech(chunk, voice, output_path):
    """Converts a single text chunk to speech and saves it."""
    communicate = edge_tts.Communicate(chunk, voice)
    await communicate.save(output_path)

def merge_audio_files(file_list):
    """Merges a list of audio files into a single audio segment."""
    combined_audio = AudioSegment.empty()
    for audio_file in file_list:
        combined_audio += AudioSegment.from_mp3(audio_file)
    return combined_audio

def export_audio_to_bytes(audio_segment):
    """Exports an audio segment to an in-memory bytes buffer."""
    audio_bytes = io.BytesIO()
    audio_segment.export(audio_bytes, format="mp3")
    audio_bytes.seek(0)
    return audio_bytes
