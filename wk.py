#!/usr/local/bin/python
import logging
from wikked.witch import main


# Configure logging.
logging.basicConfig(level=logging.DEBUG,
        format="[%(levelname)s]: %(message)s")


if __name__ == "__main__":
    main()

