"""Ollama local model wrapper with streaming support"""
import subprocess
import shlex
import time
from typing import Optional, Iterator

OLLAMA_BINARY = "ollama"  # assumes `ollama` is on PATH
try:
    from config.secrets import ollama_model as _OLLAMA_MODEL
except Exception:
    _OLLAMA_MODEL = "llama2:13b"

MODEL_NAME = _OLLAMA_MODEL


def set_model(model_name: str) -> None:
    """Set the default Ollama model name for this process."""
    global MODEL_NAME
    if model_name:
        MODEL_NAME = model_name


def _read_process_stream(proc: subprocess.Popen) -> Iterator[str]:
    """Yield stdout incremental chunks from the process."""
    try:
        while True:
            chunk = proc.stdout.readline()
            if chunk == '' and proc.poll() is not None:
                break
            if chunk:
                yield chunk
    finally:
        # drain remaining
        rest = proc.stdout.read()
        if rest:
            yield rest


def stream_generate(prompt: str, timeout: int = 60, cmd_extra: Optional[str] = None) -> Iterator[str]:
    """Generator yielding incremental text from local `ollama` call."""
    cmd = [OLLAMA_BINARY, 'run', MODEL_NAME]
    if cmd_extra:
        cmd.extend(shlex.split(cmd_extra))
    try:
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace')
        if proc.stdin:
            proc.stdin.write(prompt)
            proc.stdin.close()
    except FileNotFoundError:
        yield "[Ollama Error] ollama binary not found on PATH"
        return
    except Exception as e:
        yield f"[Ollama Error] {e}"
        return

    start = time.perf_counter()
    try:
        for piece in _read_process_stream(proc):
            yield piece
    finally:
        duration = time.perf_counter() - start
        try:
            from modules.dashboard import metrics as _m
            _m.inc('ollama_calls')
            _m.append_sample('ollama_response_time', duration)
        except Exception:
            pass


def generate(prompt: str, timeout: int = 60, stream: bool = False) -> str | Iterator[str]:
    """Call ollama synchronously or return a generator for streaming.

    - If stream=True, returns an iterator yielding chunks (use: for chunk in generate(..., stream=True))
    - Otherwise, returns full response string
    """
    if stream:
        return stream_generate(prompt, timeout)

    cmd = [OLLAMA_BINARY, 'run', MODEL_NAME]
    try:
        proc = subprocess.run(cmd, input=prompt, capture_output=True, text=True, timeout=timeout, encoding='utf-8', errors='replace')
        if proc.returncode == 0:
            text = proc.stdout.strip()
            try:
                from modules.dashboard import metrics as _m
                _m.inc('ollama_calls')
                _m.append_sample('ollama_response_time', 0)
            except Exception:
                pass
            return text
        else:
            return f"[Ollama Error] {proc.stderr.strip()}"
    except subprocess.TimeoutExpired:
        return "[Ollama Error] Timeout"
    except FileNotFoundError:
        return "[Ollama Error] ollama binary not found on PATH"
    except Exception as e:
        return f"[Ollama Error] {e}"
