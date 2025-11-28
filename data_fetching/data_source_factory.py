import json
import os
import logging
from typing import Optional, Type, Dict, Any

from data_fetching.base_client import BaseDataClient
from data_fetching.tushare_adapter import TuShareClient
from utils.logger_config import get_logger, log_error, log_with_context

# 导入环境变量处理
from dotenv import load_dotenv
# 加载.env文件
load_dotenv()

# 配置日志
logger = get_logger(__name__)

# 数据源类型常量
DATA_SOURCE_TUSHARE = 'tushare'

# 默认配置文件路径
CONFIG_FILE_PATH = os.path.join(os.path.dirname(__file__), 'data_source_config.json')


class DataSourceConfig:
    """数据源配置类，负责管理数据源配置"""
    
    def __init__(self, config_file: str = CONFIG_FILE_PATH):
        self.config_file = config_file
        self._config = self._load_config()
        # 从环境变量加载默认数据源（如果存在）
        self._load_default_source_from_env()
        # 从环境变量加载TuShare Token（如果存在）
        self._load_token_from_env()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # 返回默认配置
                default_config = {
                    'default_source': DATA_SOURCE_TUSHARE,
                    'tushare': {
                        'timeout': 10,
                        'retry_count': 3
                    },
                    'logging': {
                        'level': 'INFO',
                        'file': None
                    }
                }
                # 保存默认配置
                self._save_config(default_config)
                return default_config
        except Exception as e:
            logger.error(f"加载配置文件失败: {str(e)}")
            return {'default_source': DATA_SOURCE_TUSHARE}
    
    def _load_token_from_env(self) -> None:
        """从环境变量加载TuShare Token"""
        env_token = os.getenv('TUSHARE_TOKEN')
        if env_token:
            # 获取当前TuShare配置
            tushare_config = self.get_source_config(DATA_SOURCE_TUSHARE)
            # 更新Token
            tushare_config['token'] = env_token
            # 保存更新后的配置
            self.update_source_config(DATA_SOURCE_TUSHARE, tushare_config)
            logger.info(f"从环境变量加载TuShare Token")
    
    def _load_default_source_from_env(self) -> None:
        """从环境变量加载默认数据源设置
        
        环境变量 DATA_SOURCE_DEFAULT 可以设置为 'tushare'
        如果设置了有效的值，则覆盖配置文件中的默认数据源设置
        """
        env_default_source = os.getenv('DATA_SOURCE_DEFAULT')
        if env_default_source == DATA_SOURCE_TUSHARE:
            current_default = self._config.get('default_source', DATA_SOURCE_TUSHARE)
            if current_default != env_default_source:
                self._config['default_source'] = env_default_source
                # 这里不保存到配置文件，只是临时覆盖当前实例的配置
                logger.info(f"从环境变量覆盖默认数据源为: {env_default_source}")
    
    def _save_config(self, config: Dict[str, Any]) -> None:
        """保存配置到文件"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
                
            logger.info(f"配置已保存到 {self.config_file}")
        except Exception as e:
            logger.error(f"保存配置文件失败: {str(e)}")
    
    @property
    def default_source(self) -> str:
        """获取默认数据源"""
        return self._config.get('default_source', DATA_SOURCE_TUSHARE)
    
    def set_default_source(self, source: str) -> None:
        """设置默认数据源"""
        if source == DATA_SOURCE_TUSHARE:
            self._config['default_source'] = source
            self._save_config(self._config)
            logger.info(f"默认数据源已设置为 {source}")
        else:
            raise ValueError(f"无效的数据源类型: {source}")
    
    def get_source_config(self, source: str) -> Dict[str, Any]:
        """获取特定数据源的配置"""
        return self._config.get(source, {})
    
    def update_source_config(self, source: str, config: Dict[str, Any]) -> None:
        """更新特定数据源的配置"""
        if source == DATA_SOURCE_TUSHARE:
            self._config[source] = config
            self._save_config(self._config)
            logger.info(f"数据源 {source} 的配置已更新")
        else:
            raise ValueError(f"无效的数据源类型: {source}")


class DataSourceFactory:
    """数据源工厂类，负责创建和管理数据源客户端"""
    
    def __init__(self, config: Optional[DataSourceConfig] = None):
        self.config = config or DataSourceConfig()
        self._clients: Dict[str, BaseDataClient] = {}
        self._current_client: Optional[BaseDataClient] = None
    
    def get_client(self, source: Optional[str] = None, token: Optional[str] = None) -> BaseDataClient:
        """获取指定数据源的客户端
        
        Args:
            source: 数据源类型，默认使用tushare
            token: 可选的API密钥
            
        Returns:
            数据源客户端实例
        """
        # 强制使用tushare数据源
        source = DATA_SOURCE_TUSHARE
        
        # 对于需要token的数据源，使用token作为缓存键的一部分
        cache_key = f"{source}_{token[:8] if token else 'default'}"
        
        # 如果客户端已存在，则直接返回
        if cache_key not in self._clients:
            self._clients[cache_key] = self._create_client(source, token)
            logger.info(f"已创建 {source} 客户端")
        
        return self._clients[cache_key]
    
    def _create_client(self, source: str, token: Optional[str] = None) -> BaseDataClient:
        """创建数据源客户端实例
        
        Args:
            source: 数据源类型
            token: 可选的API密钥
        """
        source_config = self.config.get_source_config(source)
        
        if source == DATA_SOURCE_TUSHARE:
            logger.info("创建TuShare客户端实例")
            # 如果提供了token，保存到配置中
            if token:
                # 更新配置中的token信息
                tushare_config = source_config.copy()
                tushare_config['token'] = token
                self.config.update_source_config(DATA_SOURCE_TUSHARE, tushare_config)
            # 从配置获取token或使用提供的token
            config_token = source_config.get('token')
            final_token = token or config_token
            return TuShareClient(token=final_token)
        else:
            raise ValueError(f"不支持的数据源类型: {source}")
    
    def switch_data_source(self, source: str, token: Optional[str] = None) -> BaseDataClient:
        """切换到指定的数据源
        
        Args:
            source: 要切换到的数据源类型，只能是'tushare'
            token: 可选的API密钥
            
        Returns:
            切换后的数据源客户端实例
            
        Raises:
            ValueError: 如果数据源类型不支持
        """
        if source != DATA_SOURCE_TUSHARE:
            raise ValueError(f"不支持的数据源类型: {source}，仅支持 {DATA_SOURCE_TUSHARE}")
        
        try:
            # 更新默认数据源
            self.config.set_default_source(source)
            
            # 获取并保存当前客户端
            self._current_client = self.get_client(source, token)
            
            # 记录切换事件
            client_info = f"{source}"
            if token and source == DATA_SOURCE_TUSHARE:
                client_info += f" (Token: {token[:8]}...)"
            logger.info(f"数据源已设置为 {client_info}")
            
            return self._current_client
        except Exception as e:
            logger.error(f"设置数据源失败: {str(e)}")
            # 尝试回滚到之前的客户端
            if self._current_client is not None:
                logger.warning("回滚到之前的数据源客户端")
                return self._current_client
            # 如果没有之前的客户端，尝试使用默认数据源
            self._current_client = self.get_client()
            logger.warning(f"使用默认数据源: {self.config.default_source}")
            raise
    
    def get_current_client(self) -> BaseDataClient:
        """获取当前使用的数据源客户端
        
        Returns:
            当前数据源客户端实例
        """
        if self._current_client is None:
            # 如果当前客户端不存在，则初始化默认数据源客户端
            self._current_client = self.get_client()
        
        return self._current_client
    
    def is_tushare_available(self) -> bool:
        """检查TuShare数据源是否可用"""
        try:
            # 获取配置中的token（如果有）
            tushare_config = self.config.get_source_config(DATA_SOURCE_TUSHARE)
            token = tushare_config.get('token')
            
            client = self.get_client(DATA_SOURCE_TUSHARE, token=token)
            
            # 检查客户端的健康状态
            if hasattr(client, 'is_healthy'):
                return client.is_healthy()
            
            # 获取少量基本数据进行测试
            data = client.get_stock_basic_info()
            return isinstance(data, pd.DataFrame) and not data.empty
        except Exception as e:
            logger.error(f"TuShare可用性检查失败: {str(e)}")
            return False
    
    def clear_client_cache(self, source: Optional[str] = None) -> None:
        """清除指定数据源的客户端缓存
        
        Args:
            source: 数据源类型，如果为None则清除所有缓存
        """
        if source is None:
            # 清除所有缓存
            self._clients.clear()
            logger.info("已清除所有数据源客户端缓存")
        else:
            # 清除指定数据源的缓存
            keys_to_remove = []
            for key in self._clients:
                if key.startswith(source):
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self._clients[key]
            
            logger.info(f"已清除 {source} 数据源客户端缓存")
        
        # 如果当前客户端被清除，重置它
        if self._current_client is not None:
            current_source = self.config.default_source
            if source is None or self._current_client.name.lower() == source.lower():
                self._current_client = None
                logger.info("已重置当前客户端")
    
    def get_available_sources(self) -> Dict[str, bool]:
        """获取所有可用数据源的状态
        
        Returns:
            字典，键为数据源类型，值为是否可用
        """
        return {
            DATA_SOURCE_TUSHARE: self.is_tushare_available()
        }


# 创建全局工厂实例，方便在整个应用中使用
data_source_factory = DataSourceFactory()

# 为了避免循环导入，这里尝试导入pandas
# 注意：仅用于可用性检查
import pandas as pd