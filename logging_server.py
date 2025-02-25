"""ZMQ-based logging server for centralized log collection.

This module implements a logging server that receives and processes log messages
over ZMQ sockets, supporting distributed logging infrastructure.
"""

import zmq
from loguru import logger

from config import LoggerConfig


def run_logging_server() -> None:
    """Run the ZMQ-based logging server.

    Listens for log messages on a ZMQ PULL socket and forwards them to loguru.
    Handles graceful shutdown on keyboard interrupt.
    """
    config = LoggerConfig()
    context = zmq.Context()
    socket = context.socket(zmq.PULL)
    socket.bind(config.log_address)
    logger.info("Logging server started")

    try:
        while True:
            message = socket.recv_json()
            record = message.get("record", {})
            logger.log(
                record.get("level", "INFO"),
                record.get("message", ""),
                **record.get("extra", {}),
            )
    except KeyboardInterrupt:
        logger.info("Logging server stopped")
    except (zmq.ZMQError, ValueError) as e:
        logger.exception(f"Logging server error: {e}")
    finally:
        socket.close()
        context.term()


if __name__ == "__main__":
    run_logging_server()
