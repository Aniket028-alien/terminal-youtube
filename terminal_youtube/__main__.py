from .app import TerminalYouTube
from .config import setup_logging


def main() -> None:
    setup_logging()
    TerminalYouTube().run()


if __name__ == "__main__":
    main()
