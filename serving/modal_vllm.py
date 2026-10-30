"""Serve an open-weight model on Modal with vLLM's OpenAI-compatible API.

The harness talks to it like any other provider:
  EVAL_BASE_URL=https://<workspace>--ministack-eval-vllm-serve.modal.run/v1
  EVAL_API_KEY=<the VLLM_API_KEY used at deploy time>
  EVAL_MODEL=openai/gpt-oss-120b

  modal run serving/modal_vllm.py::download     # weights -> Volume, CPU only
  VLLM_API_KEY=... modal deploy serving/modal_vllm.py
  modal app stop ministack-eval-vllm            # stop billing when done

Cost guards: one container max, scale to zero after 2 idle minutes.
"""
import os
import subprocess

import modal

MODEL_ID = "openai/gpt-oss-120b"
MODEL_REVISION = "b5c939de8f754692c1647ca79fbf85e8c1e70f8a"
VLLM_VERSION = "0.32.0"
MODEL_DIR = "/models/gpt-oss-120b"

app = modal.App("ministack-eval-vllm")
weights = modal.Volume.from_name("ministack-eval-weights", create_if_missing=True)

download_image = modal.Image.debian_slim(python_version="3.12").pip_install("huggingface_hub[hf_xet]==2.4.0")


@app.function(image=download_image, volumes={"/models": weights}, cpu=4, memory=8192, timeout=30 * 60)
def download():
    from huggingface_hub import snapshot_download

    # Root files only: original/ and metal/ are duplicate copies of the weights.
    snapshot_download(MODEL_ID, revision=MODEL_REVISION, local_dir=MODEL_DIR,
                      allow_patterns=["*.json", "*.safetensors", "*.jinja"],
                      ignore_patterns=["original/*", "metal/*"])
    weights.commit()
    print(subprocess.run(["du", "-sh", MODEL_DIR], capture_output=True, text=True).stdout)


serve_image = (
    modal.Image.from_registry("nvidia/cuda:12.8.1-devel-ubuntu22.04", add_python="3.12")
    .entrypoint([])
    .uv_pip_install(f"vllm=={VLLM_VERSION}")
)


@app.function(
    image=serve_image,
    gpu="H100",
    volumes={"/models": weights},
    secrets=[modal.Secret.from_dict({"VLLM_API_KEY": os.environ.get("VLLM_API_KEY", "")})],
    max_containers=1,
    scaledown_window=120,
    timeout=20 * 60,
)
@modal.concurrent(max_inputs=8)
@modal.web_server(port=8000, startup_timeout=20 * 60)
def serve():
    if not os.environ.get("VLLM_API_KEY"):
        raise RuntimeError("deploy with VLLM_API_KEY set; the endpoint is public otherwise")
    subprocess.Popen([
        "vllm", "serve", MODEL_DIR,
        "--served-model-name", MODEL_ID,
        "--host", "0.0.0.0", "--port", "8000",
        "--max-model-len", "65536",
        "--api-key", os.environ["VLLM_API_KEY"],
        "--enable-auto-tool-choice", "--tool-call-parser", "openai",
    ])
