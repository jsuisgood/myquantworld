import abc
import pandas as pd
import time
from typing import Dict, List, Optional, Any
import logging

# 导入自定义日志工具
from utils.logger_config import get_logger, log_error, log_with_context

# 获取logger
logger = get_logger(__name__)


class BaseDataClient(abc.ABC):
    """数据接口抽象基类，定义所有数据源必须实现的接口"""
    
    def __init__(self):
        self._max_retries = 3
        self._retry_delay = 2  # 重试间隔时间（秒）
        self._logger = get_logger(f"{__name__}.{self.__class__.__name__}")
        self._last_error = None
        self._last_error_time = None
        self._logger.info(f"{self.__class__.__name__} 客户端已初始化")
    
    @log_error
    def get_stock_basic_info(self) -> pd.DataFrame:
        """获取股票基本信息
        
        Returns:
            包含股票代码、名称等基本信息的DataFrame
        """
        try:
            result = self._retry_with_backoff(self._get_stock_basic_info_impl)
            self._log_dataframe_info(result, "股票基本信息")
            return result
        except Exception as e:
            return self._handle_request_error(e, "get_stock_basic_info")
    
    @abc.abstractmethod
    def _get_stock_basic_info_impl(self) -> pd.DataFrame:
        """获取股票基本信息的具体实现"""
        pass
    
    @log_error
    def get_stock_daily_data(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """获取股票日线数据
        
        Args:
            stock_code: 股票代码
            start_date: 开始日期，格式为'YYYYMMDD'
            end_date: 结束日期，格式为'YYYYMMDD'
            
        Returns:
            包含开盘价、收盘价、最高价、最低价、成交量等数据的DataFrame
        """
        try:
            context = {"stock_code": stock_code, "start_date": start_date, "end_date": end_date}
            result = self._retry_with_backoff(
                self._get_stock_daily_data_impl,
                stock_code, start_date, end_date
            )
            self._log_dataframe_info(result, "股票日线数据", **context)
            return result
        except Exception as e:
            return self._handle_request_error(
                e, "get_stock_daily_data",
                stock_code=stock_code, 
                start_date=start_date, 
                end_date=end_date
            )
    
    @abc.abstractmethod
    def _get_stock_daily_data_impl(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """获取股票日线数据的具体实现"""
        pass
    
    @log_error
    def get_stock_financial_indicators(self, stock_code: str) -> pd.DataFrame:
        """获取股票财务指标数据
        
        Args:
            stock_code: 股票代码
            
        Returns:
            包含财务指标数据的DataFrame
        """
        try:
            context = {"stock_code": stock_code}
            result = self._retry_with_backoff(
                self._get_stock_financial_indicators_impl,
                stock_code
            )
            self._log_dataframe_info(result, "股票财务指标", **context)
            return result
        except Exception as e:
            return self._handle_request_error(
                e, "get_stock_financial_indicators",
                stock_code=stock_code
            )
    
    @abc.abstractmethod
    def _get_stock_financial_indicators_impl(self, stock_code: str) -> pd.DataFrame:
        """获取股票财务指标数据的具体实现"""
        pass
    
    @log_error
    def get_hot_sectors(self) -> pd.DataFrame:
        """获取热点行业板块数据
        
        Returns:
            包含板块名称、涨幅、领涨股等信息的DataFrame
        """
        try:
            result = self._retry_with_backoff(self._get_hot_sectors_impl)
            self._log_dataframe_info(result, "热点板块数据")
            return result
        except Exception as e:
            return self._handle_request_error(e, "get_hot_sectors")
    
    @abc.abstractmethod
    def _get_hot_sectors_impl(self) -> pd.DataFrame:
        """获取热点行业板块数据的具体实现"""
        pass
    
    @log_error
    def get_concept_sectors(self) -> pd.DataFrame:
        """获取概念板块数据
        
        Returns:
            包含概念板块名称、代码等信息的DataFrame
        """
        try:
            result = self._retry_with_backoff(self._get_concept_sectors_impl)
            self._log_dataframe_info(result, "概念板块数据")
            return result
        except Exception as e:
            return self._handle_request_error(e, "get_concept_sectors")
    
    @abc.abstractmethod
    def _get_concept_sectors_impl(self) -> pd.DataFrame:
        """获取概念板块数据的具体实现"""
        pass
    
    @log_error
    def get_sector_stocks(self, sector_code: str) -> pd.DataFrame:
        """获取指定板块的股票列表
        
        Args:
            sector_code: 板块代码
            
        Returns:
            包含板块内股票信息的DataFrame
        """
        try:
            context = {"sector_code": sector_code}
            result = self._retry_with_backoff(
                self._get_sector_stocks_impl,
                sector_code
            )
            self._log_dataframe_info(result, "板块股票列表", **context)
            return result
        except Exception as e:
            return self._handle_request_error(
                e, "get_sector_stocks",
                sector_code=sector_code
            )
    
    @abc.abstractmethod
    def _get_sector_stocks_impl(self, sector_code: str) -> pd.DataFrame:
        """获取指定板块的股票列表的具体实现"""
        pass
    
    def _handle_request_error(self, error: Exception, func_name: str, **context) -> pd.DataFrame:
        """处理请求错误的通用方法，返回空DataFrame
        
        Args:
            error: 捕获到的异常
            func_name: 调用出错的函数名
            **context: 上下文信息
            
        Returns:
            空的DataFrame作为默认值
        """
        error_msg = f"{self.__class__.__name__}.{func_name} 执行失败: {str(error)}"
        self._logger.error(error_msg, exc_info=True, extra=context)
        self._record_error(error_msg, error, context=context)
        return pd.DataFrame()
    
    def _record_error(self, message, exception, context=None):
        """记录错误信息
        
        Args:
            message: 错误消息
            exception: 异常对象
            context: 上下文信息
        """
        self._last_error = {
            'message': message,
            'exception_type': exception.__class__.__name__ if exception else 'Unknown',
            'context': context or {}
        }
        self._last_error_time = time.time()
    
    def _retry_with_backoff(self, func, *args, **kwargs):
        """带重试机制的函数执行器
        
        Args:
            func: 要执行的函数
            *args: 函数位置参数
            **kwargs: 函数关键字参数
            
        Returns:
            函数执行结果
        """
        for retry in range(self._max_retries):
            try:
                self._logger.debug(f"执行函数，尝试 {retry+1}/{self._max_retries}")
                result = func(*args, **kwargs)
                self._logger.debug(f"函数执行成功")
                return result
            except (ConnectionError, TimeoutError) as network_error:
                if retry < self._max_retries - 1:
                    backoff_delay = self._retry_delay * (2 ** retry)  # 指数退避
                    self._logger.warning(
                        f"网络连接错误，{retry+1}/{self._max_retries} 重试中，延迟 {backoff_delay}s: {str(network_error)}"
                    )
                    time.sleep(backoff_delay)
                else:
                    error_msg = f"网络连接失败，已重试{self._max_retries}次: {str(network_error)}"
                    self._logger.error(error_msg)
                    self._record_error(error_msg, network_error)
                    raise
            except Exception as e:
                error_msg = f"执行失败: {str(e)}"
                self._logger.error(error_msg, exc_info=True)
                self._record_error(error_msg, e)
                raise
    
    def get_last_error(self):
        """获取最后一次错误信息
        
        Returns:
            包含错误信息的字典，或None
        """
        return self._last_error
    
    def is_healthy(self, check_api=False):
        """
        检查客户端是否健康
        
        Args:
            check_api: 是否检查API可用性（执行简单API调用）
            
        Returns:
            bool: 客户端是否健康
        """
        # 如果有错误，且错误发生在最近5分钟内，则认为不健康
        if self._last_error_time and time.time() - self._last_error_time < 300:
            self._logger.warning(f"客户端不健康: 最近5分钟内有错误记录")
            return False
        
        # 如果需要检查API可用性
        if check_api:
            try:
                # 尝试获取少量基本数据进行健康检查
                df = self.get_stock_basic_info()
                health = isinstance(df, pd.DataFrame)
                if not health:
                    self._logger.warning(f"API健康检查失败: 返回数据类型不正确")
                return health
            except Exception as e:
                self._logger.warning(f"API健康检查异常: {str(e)}")
                return False
        
        self._logger.debug(f"客户端健康检查通过")
        return True
    
    def _log_dataframe_info(self, df, method_name, **context):
        """记录DataFrame信息
        
        Args:
            df: 要记录的DataFrame
            method_name: 方法名称
            **context: 上下文信息
        """
        if isinstance(df, pd.DataFrame):
            log_with_context(
                self._logger,
                "debug",
                f"获取{method_name}返回数据",
                rows=len(df),
                columns=len(df.columns),
                empty=df.empty,
                **context
            )
            if not df.empty and self._logger.isEnabledFor(logging.DEBUG):
                self._logger.debug(f"DataFrame列: {list(df.columns)}")
                # 只记录前3行以避免日志过大
                self._logger.debug(f"DataFrame前3行:\n{df.head(3)}")