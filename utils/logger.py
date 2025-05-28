# logger.py
from loguru import logger
import sys
import os

def init_logger(service_name: str):
    logger.remove()
    logger.add(sys.stdout, format=(
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level}</level> | " +
        service_name +
        " | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    ), level="INFO", enqueue=True)
    return logger
