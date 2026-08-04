import logging
from task_cli.database import create_tables
from task_cli.logger import configure_logging

logger = logging.getLogger(__name__)


def main() -> None:
    configure_logging()
    create_tables()
    logger.info("Task CLI started")


if __name__ == "__main__":
    main()
