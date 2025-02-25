"""ZeroMQ-based logger for sending log messages over a network connection."""

import zmq


class ZMQLogger:
    """ZeroMQ-based logger for transmitting log messages across the network."""

    def __init__(self, zmq_address: str = "tcp://127.0.0.1:5555") -> None:
        """Initialize the ZMQ logger with a socket connection.

        Args:
            zmq_address: The address to connect to for sending logs, defaults
            to local ZMQ endpoint.

        """
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PUSH)
        self.socket.connect(zmq_address)

    def log(self, level: str, message: str, **kwargs: object) -> None:
        """Send a log message to the connected ZeroMQ socket.

        Args:
            level: The log level (INFO, WARNING, ERROR, etc.)
            message: The log message to send
            **kwargs: Additional data to include in the log record

        """
        log_message = {"record": {"level": level, "message": message, "extra": kwargs}}
        # Send log message to ZeroMQ socket
        self.socket.send_json(log_message)


# Instantiate the custom logger
zmq_logger = ZMQLogger()
