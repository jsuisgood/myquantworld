import logging
import os
import time
from logging.handlers import RotatingFileHandler

# 项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(PROJECT_ROOT, 'logs')

# 确保日志目录存在
os.makedirs(LOG_DIR, exist_ok=True)

# 默认日志配置
DEFAULT_LOG_CONFIG = {
    'level': 'INFO',
    'file': os.path.join(LOG_DIR, 'myquantworld.log'),
    'max_bytes': 10 * 1024 * 1024,  # 10MB
    'backup_count': 5
}


def setup_logger(name=None, log_config=None):
    """
    设置日志配置
    
    Args:
        name: 日志器名称
        log_config: 日志配置字典，如果为None则使用默认配置
    
    Returns:
        配置好的logger实例
    """
    # 使用默认配置或提供的配置
    config = log_config or DEFAULT_LOG_CONFIG
    
    # 创建logger
    logger = logging.getLogger(name) if name else logging.getLogger()
    logger.setLevel(getattr(logging, config['level']))
    
    # 防止重复添加处理器
    if logger.handlers:
        return logger
    
    # 创建格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    )
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, config['level']))
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 如果配置了文件日志，则添加文件处理器
    if config.get('file'):
        file_handler = RotatingFileHandler(
            config['file'],
            maxBytes=config['max_bytes'],
            backupCount=config['backup_count'],
            encoding='utf-8'
        )
        file_handler.setLevel(getattr(logging, config['level']))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name=None):
    """
    获取已配置的logger实例
    
    Args:
        name: 日志器名称
    
    Returns:
        logger实例
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        # 如果logger没有处理器，使用默认配置设置
        setup_logger(name)
    return logger


def log_error(func):
    """
    异常记录装饰器
    
    用于捕获函数执行过程中的异常并记录到日志中
    """
    def wrapper(*args, **kwargs):
        # 获取适当的logger，优先使用args[0]的__module__属性（如果是类方法）
        logger_name = None
        if args and hasattr(args[0], '__class__'):
            logger_name = args[0].__class__.__module__
        elif func.__module__:
            logger_name = func.__module__
        
        logger = get_logger(logger_name)
        
        try:
            start_time = time.time()
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            # 记录函数执行时间（仅记录超过阈值的，或DEBUG级别）
            if logger.isEnabledFor(logging.DEBUG) or execution_time > 0.5:
                logger.debug(f"Function {func.__name__} executed in {execution_time:.4f} seconds")
            
            return result
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}", exc_info=True)
            # 重新抛出异常以便调用者处理
            raise
    
    return wrapper


def log_with_context(logger, level, message, **context):
    """
    带上下文的日志记录
    
    Args:
        logger: logger实例
        level: 日志级别
        message: 日志消息
        **context: 上下文信息，将作为键值对添加到日志中
    """
    # 构建包含上下文的消息
    context_str = ' '.join([f'{k}={v}' for k, v in context.items()])
    full_message = f"{message} [{context_str}]"
    
    # 根据级别记录日志
    if level == 'debug':
        logger.debug(full_message)
    elif level == 'info':
        logger.info(full_message)
    elif level == 'warning':
        logger.warning(full_message)
    elif level == 'error':
        logger.error(full_message)
    elif level == 'critical':
        logger.critical(full_message)