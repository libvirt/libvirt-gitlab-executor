import logging
import os
import sys

from provisioner.application import Application
from provisioner.cmdline import CmdLine
from provisioner.logger import LevelFormatter


def logInit():
    log_level_formats = {
        logging.DEBUG: "[%(levelname)s] %(module)s:%(funcName)s:%(lineno)d: %(message)s",
        logging.ERROR: "[%(levelname)s]: %(message)s",
    }

    custom_formatter = LevelFormatter(log_level_formats)
    custom_handler = logging.StreamHandler(stream=sys.stderr)
    custom_handler.setFormatter(custom_formatter)

    log = logging.getLogger()
    log.addHandler(custom_handler)

    return log


def err_code():
    return os.environ.get("BUILD_FAILURE_EXIT_CODE", 1)


def main():
    log = logInit()
    args = CmdLine().parse()

    if args.debug:
        log.setLevel(logging.DEBUG)

    cli_args = vars(args)
    log.debug(f"Cmdline args={cli_args}")

    try:
        ret = 0
        if Application(cli_args).run() < 0:
            ret = err_code()
    except Exception as ex:
        ret = err_code()
        if args.debug:
            log.exception(ex)
        else:
            log.error(ex)
    sys.exit(ret)
