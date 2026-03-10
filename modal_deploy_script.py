# © 2022-2026 Protopia AI, Inc. All rights reserved.
"""Runs a vLLM server with Stained Glass Output Protection enabled on Modal.

```
uv pip install modal
MODAL_LOG_LEVEL=DEBUG modal deploy scripts/modal_deploy_output_protection.py
```
"""

import base64
import socket
import subprocess
from typing import Final

import modal

# --------------- Deployment Constants ---------------

OUTPUT_PROTECTION_IMAGE: Final[str] = ( # UPDATE THIS TO YOUR IMAGE
    "protopia/stainedglass-inference-server:0.15.1-2.9.3"
)

MODEL_NAME: Final[str] = "Qwen/Qwen3-32B"
SERVED_MODEL_NAME: Final[str] = MODEL_NAME
MAX_MODEL_LEN: Final[int] = 32768

GPU_TYPE: Final[str] = "H200"
N_GPU: Final[int] = 1

VLLM_PORT: Final[int] = 8000
# Set to False to enable Torch compilation
# and CUDA graph capture.
FAST_BOOT: Final[bool] = False

MINUTES: Final[int] = 60  # seconds in a minute
# ----------------------------------------------------

container_pull_secret = modal.Secret.from_name("container-secret")
vllm_image = (
    modal.Image.from_aws_ecr(
        OUTPUT_PROTECTION_IMAGE,
        secret=container_pull_secret,
    )
    .env(
        {
            "HF_XET_HIGH_PERFORMANCE": "1",
            "VLLM_SERVER_DEV_MODE": "1",  # allows the use of "Sleep Mode"
            "TORCHINDUCTOR_COMPILE_THREADS": "1",  # improve compatibility with snapshots
            "HF_HUB_CACHE": "/home/stainedglass/.cache/huggingface",
            "TRITON_CACHE_DIR": "/home/stainedglass/.cache/torch/triton",
            "TORCHINDUCTOR_CACHE_DIR": "/home/stainedglass/.cache/torch/inductor",
        }
    )
    .run_commands("ln -s /usr/bin/python3 /usr/bin/python")
    .entrypoint([])
)

with vllm_image.imports():
    import time

    import requests
    from cryptography.hazmat.primitives.asymmetric import x25519

# Modal volumes
hf_cache_vol = modal.Volume.from_name("huggingface-cache", create_if_missing=True)
vllm_cache_vol = modal.Volume.from_name("vllm-cache", create_if_missing=True)
torch_cache_vol = modal.Volume.from_name("torch-cache", create_if_missing=True)

app = modal.App(f"{MODEL_NAME.lower().replace('/', '-')}-output-protection-vllm")


def sleep(level: int = 1) -> None:
    """Put the server into sleep mode to reduce costs during idle periods.

    Args:
        level: The level of sleep mode to enter.
    """
    requests.post(f"http://localhost:{VLLM_PORT}/sleep?level={level}").raise_for_status()  # noqa: S113


def wake_up() -> None:
    """Wake up the server from sleep mode."""
    requests.post(f"http://localhost:{VLLM_PORT}/wake_up").raise_for_status()  # noqa: S113


def wait_ready(proc: subprocess.Popen) -> None:
    """Wait for the vLLM server to be ready for connections.

    Args:
        proc: The vLLM process.

    Raises:
        RuntimeError: If the process exits before becoming ready.
    """
    while True:
        if proc.poll() is not None:
            raise RuntimeError(f"vLLM exited with {proc.returncode}") from None
        try:
            socket.create_connection(("localhost", VLLM_PORT), timeout=1).close()
            return
        except OSError:
            time.sleep(1.0)  # Yield to the event loop to allow heartbeat checks and prevent timeouts during long startups.


def warmup(n_requests: int) -> None:
    """Send a few requests to warm up the model and trigger any lazy initialization.

    Args:
        n_requests: The number of warmup requests to send.
    """
    private_key = x25519.X25519PrivateKey.generate()
    client_public_key = private_key.public_key()
    headers = {"x-client-public-key": base64.b64encode(client_public_key.public_bytes_raw()).decode("utf-8")}
    payload = {
        "model": "llm",
        "messages": [{"role": "user", "content": "Who are you?"}],
        "max_tokens": 16,
    }

    for _ in range(n_requests):
        requests.post(
            f"http://localhost:{VLLM_PORT}/v1/chat/completions",
            json=payload,
            headers=headers,
            timeout=300,
        ).raise_for_status()


@app.cls(
    image=vllm_image,
    gpu=f"{GPU_TYPE}:{N_GPU}",
    scaledown_window=60 * MINUTES,  # how long should we stay up with no requests?
    timeout=40 * MINUTES,  # how long should we wait for container start?
    volumes={
        "/home/stainedglass/.cache/huggingface": hf_cache_vol,
        "/home/stainedglass/.cache/vllm": vllm_cache_vol,  # vLLM's torch.compile cache
        "/home/stainedglass/.cache/torch": torch_cache_vol,
    },
    enable_memory_snapshot=True,
    experimental_options={"enable_gpu_snapshot": False},
    max_containers=1,
    secrets=[modal.Secret.from_name("huggingface-secret")],
)
@modal.concurrent(  # How many requests can one replica handle? tune carefully!
    max_inputs=32
)
class OutputProtectedvLLMServer:
    """Launch the vLLM inference server for the base model with Stained Glass Output Protection."""

    @modal.enter(snap=True)
    def start(self) -> None:
        """Start the vLLM server process with Stained Glass Output Protection."""
        cmd = [
            "python3",
            "-m",
            "stainedglass_output_protection.vllm.entrypoint",
            "--uvicorn-log-level=info",
            "--model",
            MODEL_NAME,
            "--served-model-name",
            MODEL_NAME,
            "llm",
            "--host",
            "0.0.0.0",  # noqa: S104
            "--port",
            str(VLLM_PORT),
            "--gpu_memory_utilization",
            str(0.95),
            "--enable-prompt-embeds",
            "--download-dir",
            "/home/stainedglass/.cache/huggingface",
            "--tensor-parallel-size",
            str(N_GPU),
            "--enable-auto-tool-choice",
            "--tool-call-parser",
            "hermes",
            "--enable-sleep-mode",
            # config for snapshotting
            # make KV cache predictable / small
            "--max-num-seqs",
            "32",
            "--max-model-len",
            str(MAX_MODEL_LEN),
            "--max-num-batched-tokens",
            str(MAX_MODEL_LEN),
        ]

        # enforce-eager disables both Torch compilation and CUDA graph capture
        # default is no-enforce-eager. see the --compilation-config flag for tighter control
        cmd += ["--enforce-eager" if FAST_BOOT else "--no-enforce-eager"]

        print("Launching Output Protected vLLM with command:")
        print(*cmd)
        self.vllm_proc = subprocess.Popen(cmd)  # noqa: S603

        wait_ready(self.vllm_proc)
        warmup(n_requests=2)

    @modal.enter(snap=False)
    def wake_up(self) -> None:
        wake_up()
        wait_ready(self.vllm_proc)
        warmup(1)

    @modal.web_server(port=VLLM_PORT, startup_timeout=40 * MINUTES, requires_proxy_auth=True)
    def serve(self) -> None:
        pass

    @modal.exit()
    def stop(self) -> None:
        self.vllm_proc.terminate()
