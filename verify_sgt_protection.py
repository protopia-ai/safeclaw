# © 2022-2026 Protopia AI, Inc. All rights reserved.
"""Terminal demo script to verify Protopia SGT protection behavior.

This script calls the SGT Proxy `/stainedglass` endpoint twice:

1) Request plaintext + transformed embeddings.
2) Request reconstructed prompt
"""

from __future__ import annotations

import torch
import argparse
import os
import sys
import textwrap
from typing import Any

import requests


# ---- SGT Proxy access defaults ----
DEFAULT_PROXY_URL = "http://localhost:32784/v1"
DEFAULT_MODEL_NAME = "Qwen/Qwen3-32B"
DEFAULT_TIMEOUT_SECONDS = 30


def _env_or_none(value: str | None) -> str | None:
    """Resolves environment-variable style placeholders.

    Args:
        value: Raw argument value.

    Returns:
        The resolved value or None.
    """
    if value is None:
        return None
    if value.startswith("$"):
        return os.getenv(value[1:])
    return value


def _print_header(title: str) -> None:
    width = 78
    print("=" * width)
    print(title.center(width))
    print("=" * width)


def _print_section(title: str, body: str) -> None:
    print(f"\n[{title}]")
    print("-" * (len(title) + 2))
    print(body)


def _shape_2d(values: Any) -> tuple[int, int] | None:
    """Returns shape for nested list-like 2D embeddings."""
    if not isinstance(values, list) or not values:
        return None
    if not isinstance(values[0], list):
        return None
    return (len(values), len(values[0]))


def _post_stainedglass(
    *,
    proxy_url: str,
    api_key: str | None,
    payload: dict[str, Any],
    timeout: int,
) -> dict[str, Any]:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    response = requests.post(
        f"{proxy_url.rstrip('/')}/stainedglass",
        headers=headers,
        json=payload,
        stream=False,
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()


def _preview(text: str, max_chars: int = 1024) -> str:
    clean = " ".join(text.split())
    if len(clean) <= max_chars:
        return clean
    return f"{clean[:max_chars].rstrip()}..."


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify SGT protection and print a terminal-friendly demo report."
    )
    parser.add_argument("--proxy-url", default=DEFAULT_PROXY_URL)
    parser.add_argument("--model", default=DEFAULT_MODEL_NAME)
    parser.add_argument(
        "--api-key",
        default="$SGP_API_KEY",
        help=(
            "Bearer key for proxy auth. Supports direct value or env form like "
            "$SGP_API_KEY"
        ),
    )
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument(
        "--message",
        default=(
            "Summarize why output protection is useful for sensitive enterprise "
            "data in exactly 4 bullet points."
        ),
    )
    args = parser.parse_args()

    api_key = _env_or_none(args.api_key)

    messages = [{"role": "user", "content": args.message}]
    base_payload: dict[str, Any] = {
        "model": args.model,
        "messages": messages,
    }

    _print_header("SAFECLAW SGT PROTECTION VERIFICATION")
    _print_section(
        "Run Config",
        textwrap.dedent(
            f"""\
            SGT Proxy URL  : {args.proxy_url}
            Model          : {args.model}
            Timeout        : {args.timeout}s
            Prompt         : {_preview(args.message, 120)}
            """
        ).strip(),
    )

    try:
        first_response = _post_stainedglass(
            proxy_url=args.proxy_url,
            api_key=api_key,
            timeout=args.timeout,
            payload=base_payload
            | {
                "return_plain_text_embeddings": True,
                "return_transformed_embeddings": True,
                "return_reconstructed_prompt": False,
            },
        )

        plain = torch.tensor(first_response.get("plain_text_embeddings"))
        transformed = torch.tensor(first_response.get("transformed_embeddings"))
        plain_text = "".join(first_response.get("tokenized_plain_text", []))

        _print_section(
            "Plain vs Protected Embeddings",
            textwrap.dedent(
                f"""\
            plain_text_embeddings preview: {plain}

            transformed_embeddings preview: {transformed}
                
            plaintext preview           : {_preview(plain_text)}
            """
            ).strip(),
        )

        second_response = _post_stainedglass(
            proxy_url=args.proxy_url,
            api_key=api_key,
            timeout=args.timeout,
            payload=base_payload
            | {
                "return_reconstructed_prompt": True,
                "return_obfuscation_score": False,
                "return_transformed_embeddings": True,
            },
        )

        reconstructed_prompt = str(second_response.get("reconstructed_prompt", ""))
        transformed_embeddings = torch.tensor(
            second_response.get("transformed_embeddings")
        )

        _print_section(
            "Request #2: 🔒 Transformed Embeddings 🔒",
            textwrap.dedent(
                f"""\
                Transformed Embeddings preview : {_preview(str(transformed_embeddings[:-5]))}
                """
            ).strip(),
        )

        _print_section(
            "Reconstruction Attempt Check 🕵️‍♂️",
            textwrap.dedent(
                f"""\
                reconstructed preview : {_preview(reconstructed_prompt)}
                """
            ).strip(),
        )

        print("\nDemo completed successfully.")
        return 0

    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "unknown"
        body = exc.response.text if exc.response is not None else "<no response body>"
        _print_section(
            "HTTP Error", f"status={status}\nbody={_preview(body, max_chars=1000)}"
        )
        return 1
    except requests.RequestException as exc:
        _print_section("Request Error", str(exc))
        return 1
    except Exception as exc:  # pragma: no cover - defensive path for demos
        _print_section("Unexpected Error", f"{type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
