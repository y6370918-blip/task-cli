import logging

from task_cli.cli import run_cli
from task_cli.database import (
    SessionLocal,
)
from task_cli.logger import (
    configure_logging,
)

logger = logging.getLogger(__name__)


def main() -> None:

    configure_logging()

    logger.info("Task CLI started")

    with SessionLocal() as session:
        run_cli(session)


if __name__ == "__main__":
    main()
