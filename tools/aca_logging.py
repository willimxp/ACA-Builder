# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：ACA Builder 日志模块，提供统一的日志配置和管理功能
# 260210 从 __init__.py 中独立出来，支持可配置的日志级别和路径

import logging
import pathlib
import bpy
from logging.handlers import RotatingFileHandler

# 日志模块常量
LOGGER_NAME = "ACA"
DEFAULT_LOG_LEVEL = logging.INFO
DEFAULT_LOG_FILENAME = "aca_log.txt"
DEFAULT_MAX_BYTES = 5 * 1024 * 1024  # 5MB
DEFAULT_BACKUP_COUNT = 3

# 日志级别映射（用于UI显示和配置）
LOG_LEVELS = [
    ('DEBUG', '调试 (Debug)', '详细的调试信息', logging.DEBUG),
    ('INFO', '信息 (Info)', '一般信息', logging.INFO),
    ('WARNING', '警告 (Warning)', '警告信息', logging.WARNING),
    ('ERROR', '错误 (Error)', '错误信息', logging.ERROR),
]


def get_default_log_path() -> pathlib.Path:
    """
    获取默认日志路径
    
    Returns:
        pathlib.Path: 默认日志目录路径
    """
    addon_name = "ACA Builder"
    user_path = pathlib.Path(bpy.utils.resource_path('USER'))
    return user_path / "scripts/addons" / addon_name


def get_log_level_from_string(level_name: str) -> int:
    """
    将日志级别名称转换为 logging 级别
    
    Args:
        level_name: 日志级别名称 ('DEBUG', 'INFO', 'WARNING', 'ERROR')
        
    Returns:
        int: logging 模块定义的日志级别
    """
    level_map = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
    }
    return level_map.get(level_name, DEFAULT_LOG_LEVEL)


def get_logger() -> logging.Logger:
    """
    获取 ACA 日志记录器
    
    Returns:
        logging.Logger: ACA 日志记录器实例
    """
    return logging.getLogger(LOGGER_NAME)


def init_logger(
    log_level: int = None,
    log_path: pathlib.Path = None,
    log_filename: str = None,
    use_rotating: bool = True,
    max_bytes: int = DEFAULT_MAX_BYTES,
    backup_count: int = DEFAULT_BACKUP_COUNT
) -> logging.Logger:
    """
    初始化 ACA 日志记录器
    
    使用示例:
        from .tools import aca_logging
        logger = aca_logging.init_logger(
            log_level=logging.INFO,
            use_rotating=True
        )
    
    Args:
        log_level: 日志级别，默认为 INFO
        log_path: 日志文件目录路径，默认为 Blender 用户目录下的 ACA Builder 文件夹
        log_filename: 日志文件名，默认为 aca_log.txt
        use_rotating: 是否使用日志轮转，默认为 True
        max_bytes: 单个日志文件最大字节数，默认为 5MB
        backup_count: 保留的备份文件数量，默认为 3
        
    Returns:
        logging.Logger: 配置好的日志记录器
    """
    logger = logging.getLogger(LOGGER_NAME)
    
    # 设置日志级别
    if log_level is None:
        log_level = DEFAULT_LOG_LEVEL
    logger.setLevel(log_level)
    
    # 清除已有的 handlers
    if logger.hasHandlers():
        logger.handlers.clear()
    
    # 日志格式
    formatter = logging.Formatter(
        fmt='%(asctime)s [%(levelname)s] : %(message)s',
        datefmt='%y/%m/%d %H:%M:%S',
    )
    
    # 添加控制台日志处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 添加文件日志处理器
    if log_path is None:
        log_path = get_default_log_path()
    
    if log_filename is None:
        log_filename = DEFAULT_LOG_FILENAME
    
    # 确保日志目录存在
    log_path.mkdir(parents=True, exist_ok=True)
    log_file_path = log_path / log_filename
    
    # 创建或检查日志文件
    if not log_file_path.exists():
        log_file_path.touch()
    
    # 选择日志处理器类型
    if use_rotating:
        file_handler = RotatingFileHandler(
            filename=log_file_path,
            mode='a',  # 追加模式
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
    else:
        file_handler = logging.FileHandler(
            filename=log_file_path,
            mode='w',  # 每次清空上一次的日志（兼容旧行为）
            encoding='utf-8'
        )
    
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger


def remove_logger() -> None:
    """
    移除 ACA 日志记录器的所有处理器
    
    使用示例:
        from .tools import aca_logging
        aca_logging.remove_logger()
    """
    logger = logging.getLogger(LOGGER_NAME)
    if logger.hasHandlers():
        logger.handlers.clear()


def update_log_level(log_level: int) -> None:
    """
    更新日志级别（运行时动态调整）
    
    使用示例:
        from .tools import aca_logging
        aca_logging.update_log_level(logging.DEBUG)
    
    Args:
        log_level: 新的日志级别
    """
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(log_level)
    for handler in logger.handlers:
        handler.setLevel(log_level)


def log_system_info(logger: logging.Logger = None) -> None:
    """
    记录系统信息到日志
    
    使用示例:
        from .tools import aca_logging
        aca_logging.log_system_info()
    
    Args:
        logger: 日志记录器，默认使用 ACA 日志记录器
    """
    if logger is None:
        logger = get_logger()
    
    import platform
    
    logger.info("=" * 50)
    logger.info("ACA Builder 日志系统启动")
    logger.info(f"操作系统: {platform.system()} {platform.release()}")
    logger.info(f"Python 版本: {platform.python_version()}")
    logger.info(f"Blender 版本: {bpy.app.version_string}")
    logger.info("=" * 50)
