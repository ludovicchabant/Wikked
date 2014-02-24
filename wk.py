#!/usr/local/bin/python
import sys
import logging
import colorama
from wikked.witch import ColoredFormatter, main


# Configure logging.
colorama.init()
root_logger = logging.getLogger()
handler = logging.StreamHandler(stream=sys.stdout)
handler.setFormatter(ColoredFormatter('%(message)s'))
root_logger.addHandler(handler)


if __name__ == "__main__":
    main()

