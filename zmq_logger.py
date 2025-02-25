import zmq


class ZMQLogger:
    def __init__(self, zmq_address="tcp://127.0.0.1:5555"):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PUSH)
        self.socket.connect(zmq_address)

    def log(self, level, message, **kwargs):
        log_message = {"record": {"level": level, "message": message, "extra": kwargs}}
        # Send log message to ZeroMQ socket
        self.socket.send_json(log_message)
        # Optionally print to console for debugging
        print(f"[{level}] {message}")


# Instantiate the custom logger
zmq_logger = ZMQLogger()
