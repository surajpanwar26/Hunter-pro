from modules.dashboard import log_handler


def test_subscribe_publish(tmp_path, capsys):
    received = []
    def cb(msg):
        received.append(msg)

    log_handler.subscribe(cb)
    log_handler.publish("hello world")
    log_handler.publish("ai chunk", tag="AI")
    log_handler.unsubscribe(cb)
    assert any("hello world" in r for r in received)
    assert any(r.startswith("[AI]") for r in received)
