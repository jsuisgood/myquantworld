import os
import logging
from logging.handlers import TimedRotatingFileHandler

"""
日志配置模块

负责设置应用程序的日志系统，提供统一的日志记录机制。
主要功能：
- 配置控制台和文件双重输出
- 实现按日期的日志轮转
- 设置详细的日志格式，包含时间戳、模块名、行号等信息
- 支持不同级别的日志记录（DEBUG, INFO, WARNING, ERROR, CRITICAL）
"""

def setup_logger(name='stock_api', log_level=logging.INFO):
    """
    设置日志配置，包含日志轮转机制和错误处理
    
    Args:
        name (str): 日志记录器名称，默认为'stock_api'
        log_level (int): 日志级别，默认为logging.INFO
        
    Returns:
        logging.Logger: 配置好的日志记录器实例
        
    Raises:
        Exception: 如果日志配置过程中发生异常
    """
    try:
        # 创建logger实例
        logger = logging.getLogger(name)
        logger.setLevel(log_level)  # 设置日志级别
        
        # 检查是否已有处理器，如果有则不再添加（避免重复）
        if logger.handlers:
            return logger
        
        # 创建formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(module)s.%(funcName)s:%(lineno)d] - %(message)s'
        )
        
        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # 确保logs目录存在
        try:
            # 确保日志目录存在
            LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
            os.makedirs(LOG_DIR, exist_ok=True)
            
            # 创建日志文件路径
            LOG_FILE = os.path.join(LOG_DIR, 'stock_api.log')
            
            # 创建按日期轮转的文件处理器
            file_handler = TimedRotatingFileHandler(
                filename=LOG_FILE,
                when='D',        # 每天轮转一次
                interval=1,       # 间隔为1
                backupCount=7,    # 保留7个日志文件（最近7天）
                encoding='utf-8'
            )
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            
            # 记录日志配置成功的信息（使用更低级别的日志，避免日志风暴）
            logger.debug(f"日志系统已成功配置，日志文件位置: {LOG_FILE}")
            
        except Exception as e:
            # 如果文件日志配置失败，记录错误并只使用控制台日志
            logger.error(f"配置文件日志处理器失败: {str(e)}")
        
        return logger
        
    except Exception as e:
        # 确保即使日志配置失败，也不会影响应用程序启动
        print(f"严重错误：日志系统配置失败: {str(e)}")
        # 返回一个简单的控制台日志记录器作为备用
        fallback_logger = logging.getLogger(name + '_fallback')
        fallback_logger.setLevel(logging.INFO)
        fallback_handler = logging.StreamHandler()
        fallback_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        fallback_logger.addHandler(fallback_handler)
        return fallback_logger

# 创建默认logger实例
default_logger = setup_logger()

# 提供日志级别快捷访问
DEBUG = logging.DEBUG
INFO = logging.INFO
WARNING = logging.WARNING
ERROR = logging.ERROR
CRITICAL = logging.CRITICAL

__all__ = ['setup_logger', 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']