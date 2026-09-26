"""OpenAI-compatible chat client, including local Ollama's /v1 endpoint."""
import json
import urllib.error
import urllib.request
from urllib.parse import urlparse


def complete(messages: list[dict], base_url: str, model: str, api_key: str = "", timeout: int = 90) -> str:
    url = base_url.rstrip("/") + "/chat/completions"
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("Use an http(s) OpenAI-compatible base URL")
    if parsed.scheme == "http" and parsed.hostname not in ("localhost", "127.0.0.1", "::1"):
        raise ValueError("Remote providers must use HTTPS")
    if not model.strip():
        raise ValueError("Select a model")
    body = json.dumps({"model": model, "messages": messages, "temperature": 0.8, "max_tokens": 650}).encode()
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            result = json.load(response)
        return result["choices"][0]["message"]["content"] or "(empty response)"
    except urllib.error.HTTPError as error:
        detail = error.read(300).decode("utf-8", errors="replace")
        # Some API error bodies can echo request information; never surface the key.
        if api_key:
            detail = detail.replace(api_key, "[redacted]")
        raise RuntimeError(f"Provider returned HTTP {error.code}: {detail}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"Cannot reach model endpoint: {error.reason}") from error
    except (KeyError, IndexError, TypeError) as error:
        raise RuntimeError("Provider returned an unexpected chat response") from error
