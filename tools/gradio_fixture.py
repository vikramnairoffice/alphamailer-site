"""Local-only API fixture. No Alphamailer source, account, or delivery access."""
import argparse
import os
import time
from pathlib import Path
os.environ["GRADIO_ANALYTICS_ENABLED"] = "False"
import gradio as gr

parser = argparse.ArgumentParser()
parser.add_argument("--port", type=int, required=True)
args = parser.parse_args()

def echo(value, state):
    yield "preparing:" + value, state
    time.sleep(0.1)
    yield "complete:" + value, state + 1

def count(state):
    return str(state), state

with gr.Blocks() as demo:
    state = gr.State(0)
    value = gr.Textbox()
    output = gr.Textbox()
    gr.Button("Echo").click(echo, inputs=[value, state], outputs=[output, state], api_name="echo")
    gr.Button("Count").click(count, inputs=[state], outputs=[output, state], api_name="count")
    file = gr.File()
    gr.Button("Read upload").click(lambda path: Path(path).read_text(), inputs=file, outputs=output, api_name="read_upload")
demo.queue().launch(server_name="127.0.0.1", server_port=args.port, share=False, inbrowser=False)
