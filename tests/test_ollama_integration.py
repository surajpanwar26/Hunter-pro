import subprocess
from modules.ai import ollama_integration as oi


class DummyProc:
    def __init__(self, outputs):
        self._outputs = outputs
        self.stdout = self
        self._i = 0

    def readline(self):
        if self._i < len(self._outputs):
            out = self._outputs[self._i]
            self._i += 1
            return out
        return ''

    def poll(self):
        return 0 if self._i >= len(self._outputs) else None

    def read(self):
        return ''.join(self._outputs[self._i:])


def test_stream_generate(monkeypatch):
    dummy = DummyProc(['Hello ', 'world', '\n'])

    def fake_popen(cmd, stdout, stderr, text):
        return dummy

    monkeypatch.setattr(subprocess, 'Popen', fake_popen)
    gen = oi.stream_generate('hi')
    out = ''.join(list(gen))
    assert 'Hello' in out
