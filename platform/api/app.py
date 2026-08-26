import gradio as gr
import uvicorn
import threading
from main import app

def run_fastapi():
    uvicorn.run(app, host="0.0.0.0", port=7860)

# Start FastAPI in a background thread
thread = threading.Thread(target=run_fastapi, daemon=True)
thread.start()

# Keep Gradio alive so HF doesn't kill the Space
demo = gr.Interface(
    fn=lambda: "ZestQA Platform API is running.",
    inputs=[],
    outputs="text",
    title="ZestQA Platform API"
)
demo.launch(server_port=7861)
