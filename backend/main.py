
from fastapi import FastAPI, File, UploadFile, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
import uuid
import logic
import time
import random
import io
import asyncio
import shutil
import edge_tts

app = FastAPI()

class PreviewRequest(BaseModel):
    text: str
    voice: str

# --- State & Storage ---
conversion_tasks = {}
output_dir = "output"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# --- Concurrent Conversion Logic ---

async def convert_chunk_with_retry(task_id: str, chunk: str, voice: str, chunk_index: int, temp_dir: str, semaphore: asyncio.Semaphore, tasks_state: dict, total_chunks: int):
    """Converts a single chunk with retry logic, designed for concurrency."""
    async with semaphore:
        MAX_RETRIES = 5
        retries = 0
        chunk_filename = os.path.join(temp_dir, f"chunk_{chunk_index:04d}.mp3")
        
        while retries < MAX_RETRIES:
            try:
                await logic.convert_chunk_to_speech(chunk, voice, chunk_filename)
                # On success, update progress and return the path
                tasks_state["completed_chunks"] = tasks_state.get("completed_chunks", 0) + 1
                # Scale progress to be between 10% and 85%
                progress = 10 + int((tasks_state["completed_chunks"] / total_chunks) * 75)
                tasks_state["progress"] = progress
                return chunk_filename
            except Exception as e:
                retries += 1
                error_str = str(e).lower()
                if "401" in error_str or "invalid response status" in error_str or "no audio was received" in error_str:
                    print(f"WARNING: Rate limit on task {task_id}, chunk {chunk_index}. Attempt {retries}/{MAX_RETRIES}.")
                    if retries < MAX_RETRIES:
                        wait_time = retries * 30 + random.randint(5, 15)
                        print(f"Waiting for {wait_time} seconds before retrying chunk {chunk_index}...")
                        await asyncio.sleep(wait_time)
                    else:
                        print(f"FATAL: Failed chunk {chunk_index} after {MAX_RETRIES} attempts.")
                        return None # Failed to convert this chunk
                else:
                    print(f"ERROR: An unexpected error occurred on chunk {chunk_index}: {e}.")
                    return None # Failed due to unexpected error
        return None

async def run_conversion_async(task_id: str, file_path: str, voice: str):
    """The main async worker for processing the PDF conversion."""
    temp_dir = os.path.join(output_dir, task_id + "_temp") # Define temp_dir early for cleanup
    try:
        tasks_state = conversion_tasks[task_id]
        tasks_state["status"] = "processing"

        with open(file_path, "rb") as f:
            raw_text = logic.extract_text_from_pdf(f)
        
        if not raw_text.strip():
            raise ValueError("Could not extract any text from the PDF.")

        cleaned_text = logic.clean_text(raw_text)
        chunks = logic.chunk_text(cleaned_text)
        tasks_state["total_chunks"] = len(chunks)
        tasks_state["completed_chunks"] = 0
        os.makedirs(temp_dir)

        # Create a semaphore to limit concurrency
        CONCURRENCY_LIMIT = 4
        semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)

        # Create concurrent tasks for each chunk
        conversion_coroutines = []
        for i, chunk in enumerate(chunks):
            conversion_coroutines.append(convert_chunk_with_retry(task_id, chunk, voice, i, temp_dir, semaphore, tasks_state, len(chunks)))
        
        # Run all chunk conversions concurrently (respecting the semaphore limit)
        tasks_state["progress"] = 10 # Start with a bit of progress
        results = await asyncio.gather(*conversion_coroutines)
        
        temp_audio_files = [res for res in results if res is not None]
        tasks_state["successful_chunks"] = len(temp_audio_files)
        tasks_state["progress"] = 85 # Done with conversion

        if not temp_audio_files:
            raise ValueError("No audio chunks were successfully created.")

        # Sort files to ensure correct order before merging
        temp_audio_files.sort()

        combined_audio = logic.merge_audio_files(temp_audio_files)
        final_audio_path = os.path.join(output_dir, f"{task_id}.mp3")
        combined_audio.export(final_audio_path, format="mp3")
        tasks_state["audio_path"] = final_audio_path

        tasks_state["status"] = "complete"
        tasks_state["progress"] = 100

    except Exception as e:
        print(f"Error during conversion for task {task_id}: {e}")
        tasks_state["status"] = "failed"
        tasks_state["error"] = str(e)
    finally:
        # Robust cleanup
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        if os.path.exists(file_path):
            os.remove(file_path)

def run_conversion_task(task_id: str, file_path: str, voice: str):
    """Synchronous entrypoint for the background task."""
    asyncio.run(run_conversion_async(task_id, file_path, voice))

# --- API Endpoints ---
@app.post("/api/preview")
async def preview_voice(request: PreviewRequest):
    MAX_RETRIES = 3
    for attempt in range(MAX_RETRIES):
        try:
            communicate = edge_tts.Communicate(request.text, request.voice)
            audio_buffer = io.BytesIO()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_buffer.write(chunk["data"])
            
            audio_buffer.seek(0)
            return StreamingResponse(audio_buffer, media_type="audio/mpeg")
        except Exception as e:
            print(f"Preview failed on attempt {attempt + 1}: {e}")
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(2) # Wait 2 seconds before retrying
            else:
                # If all retries fail, raise the HTTP exception
                raise HTTPException(status_code=500, detail=f"Failed to generate preview after {MAX_RETRIES} attempts.")

@app.get("/api/voices")
async def get_voices():
    voices = await logic.get_voices()
    return JSONResponse(content=voices)

@app.post("/api/convert")
async def convert_pdf(background_tasks: BackgroundTasks, 
                      pdf_file: UploadFile = File(...), 
                      voice: str = File(...) ):
    task_id = str(uuid.uuid4())
    file_extension = os.path.splitext(pdf_file.filename)[1]
    temp_pdf_path = os.path.join(output_dir, f"{task_id}{file_extension}")

    # Save the uploaded PDF temporarily
    with open(temp_pdf_path, "wb") as f:
        f.write(await pdf_file.read())

    # Create and store task state
    conversion_tasks[task_id] = {
        "status": "pending",
        "progress": 0,
        "audio_path": None,
        "error": None
    }

    # Start the conversion in the background
    background_tasks.add_task(run_conversion_task, task_id, temp_pdf_path, voice)

    return JSONResponse(content={"task_id": task_id})

@app.get("/api/status/{task_id}")
async def get_status(task_id: str):
    task = conversion_tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return JSONResponse(content=task)

@app.get("/api/download/{task_id}")
async def download_audio(task_id: str):
    task = conversion_tasks.get(task_id)
    if not task or task["status"] != "complete":
        raise HTTPException(status_code=404, detail="Audio not ready or task not found")
    
    file_path = task.get("audio_path")
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Audio file not found")

    return FileResponse(path=file_path, media_type='audio/mpeg', filename='audiobook.mp3')

# --- Frontend Serving ---
# Mount static files
app.mount("/", StaticFiles(directory="../frontend", html=True), name="static")

@app.get("/")
async def read_index():
    return FileResponse('../frontend/index.html')
