import logging
from task_cli.logger import configure_logging

logger = logging.getLogger(__name__)


def main() -> None:
    configure_logging()
    logger.info("Task CLI started")


if __name__ == "__main__":
    main()
