"""
日志系统
"""
import logging
import colorlog
from pathlib import Path
from typing import Optional


def setup_logger(
    name: str = "auto_farming",
    level: str = "INFO",
    log_file: Optional[str] = None,
    console: bool = True
) -> logging.Logger:
    """
    设置日志系统
    
    Args:
        name: 日志名称
        level: 日志级别
        log_file: 日志文件路径
        console: 是否输出到控制台
    
    Returns:
        Logger实例
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # 清除已有的处理器
    logger.handlers.clear()
    
    # 日志格式
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # 控制台输出（带颜色）
    if console:
        console_handler = colorlog.StreamHandler()
        console_handler.setFormatter(
            colorlog.ColoredFormatter(
                '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt=date_format,
                log_colors={
                    'DEBUG': 'cyan',
                    'INFO': 'green',
                    'WARNING': 'yellow',
                    'ERROR': 'red',
                    'CRITICAL': 'red,bg_white',
                }
            )
        )
        logger.addHandler(console_handler)
    
    # 文件输出
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(
            logging.Formatter(log_format, datefmt=date_format)
        )
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str = "auto_farming") -> logging.Logger:
    """
    获取日志实例
    
    Args:
        name: 日志名称
    
    Returns:
        Logger实例
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        # 如果没有配置，使用默认配置
        return setup_logger(name)
    return logger
