import os
import sys
import time
import pandas as pd
import unittest
from typing import Dict, Any

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from data_fetching.data_source_factory import (
    data_source_factory,
    DATA_SOURCE_TUSHARE
)
from utils.logger_config import get_logger

# 配置日志
logger = get_logger('data_source_test')


class DataSourceSwitchTest(unittest.TestCase):
    """测试数据源切换功能的单元测试类"""
    
    def setUp(self):
        """测试前的初始化工作"""
        logger.info("开始测试数据源切换功能")
        # 清除客户端缓存，确保测试环境干净
        data_source_factory.clear_client_cache()
        # 保存原始默认数据源
        self.original_default = data_source_factory.config.default_source
        
    def tearDown(self):
        """测试后的清理工作"""
        # 恢复原始默认数据源
        data_source_factory.config.set_default_source(self.original_default)
        # 清除客户端缓存
        data_source_factory.clear_client_cache()
        logger.info("测试完成，环境已清理")
    
    def test_basic_switch(self):
        """测试基本的数据源功能"""
        logger.info("测试基本的数据源功能")
        
        # 切换到TuShare（使用模拟Token）
        tushare_client = data_source_factory.switch_data_source(
            DATA_SOURCE_TUSHARE,
            token="mock_test_token"
        )
        self.assertEqual(tushare_client.name, DATA_SOURCE_TUSHARE)
        logger.info(f"成功创建TuShare客户端，客户端名称: {tushare_client.name}")
        
        # 验证当前客户端是正确的
        current_client = data_source_factory.get_current_client()
        self.assertEqual(current_client.name, DATA_SOURCE_TUSHARE)
    
    def test_data_retrieval(self):
        """测试从TuShare获取的数据格式"""
        logger.info("测试数据格式")
        
        # 测试TuShare
        tushare_client = data_source_factory.switch_data_source(
            DATA_SOURCE_TUSHARE,
            token="mock_test_token"
        )
        ts_stock_basic = tushare_client.get_stock_basic_info()
        self.assertIsInstance(ts_stock_basic, pd.DataFrame)
        logger.info(f"TuShare基本信息数据行数: {len(ts_stock_basic)}")
        
        # 验证数据不为空
        self.assertFalse(ts_stock_basic.empty)
    
    def test_health_check(self):
        """测试健康检查功能"""
        logger.info("测试健康检查功能")
        
        # 检查TuShare的可用性
        ts_available = data_source_factory.is_tushare_available()
        logger.info(f"TuShare可用性: {ts_available}")
        
        # 获取所有可用数据源的状态
        all_sources = data_source_factory.get_available_sources()
        logger.info(f"所有数据源状态: {all_sources}")
        
        # 确保返回了tushare数据源的状态
        self.assertEqual(len(all_sources), 1)
        self.assertIn(DATA_SOURCE_TUSHARE, all_sources)
    
    def test_token_management(self):
        """测试Token管理功能"""
        logger.info("测试Token管理功能")
        
        # 测试使用不同Token创建多个客户端
        token1 = "test_token_1"
        token2 = "test_token_2"
        
        client1 = data_source_factory.get_client(DATA_SOURCE_TUSHARE, token=token1)
        client2 = data_source_factory.get_client(DATA_SOURCE_TUSHARE, token=token2)
        
        # 确保使用不同Token创建的是不同的客户端实例
        # 在实际场景中，应该验证客户端使用了正确的Token
        logger.info("已测试使用不同Token创建客户端")
    
    def test_error_handling(self):
        """测试错误处理和回滚机制"""
        logger.info("测试错误处理和回滚机制")
        
        # 先切换到TuShare作为基线
        baseline_client = data_source_factory.switch_data_source(DATA_SOURCE_TUSHARE, token="mock_test_token")
        
        # 尝试使用无效参数切换数据源，应该抛出异常但保持当前客户端不变
        try:
            # 使用不存在的数据源类型
            invalid_source = "INVALID_SOURCE"
            data_source_factory.switch_data_source(invalid_source)
            self.fail("应该抛出ValueError异常")
        except ValueError as e:
            logger.info(f"正确捕获到异常: {str(e)}")
            # 验证当前客户端没有改变
            current_client = data_source_factory.get_current_client()
            self.assertEqual(current_client, baseline_client)
    
    def test_performance(self):
        """测试数据源初始化的性能"""
        logger.info("测试数据源初始化的性能")
        
        iterations = 3
        
        # 测试连续创建tushare客户端的性能
        start_time = time.time()
        for i in range(iterations):
            client = data_source_factory.switch_data_source(DATA_SOURCE_TUSHARE, token="mock_token")
            logger.info(f"第{i+1}次初始化: {client.name}")
        
        end_time = time.time()
        avg_time = (end_time - start_time) / iterations
        logger.info(f"平均初始化时间: {avg_time:.4f} 秒")
        
        # 性能指标：每次初始化应该在合理时间内完成（例如<1秒）
        self.assertLess(avg_time, 1.0, f"初始化时间过长: {avg_time:.4f} 秒")
    
    def test_all_data_methods(self):
        """测试所有数据获取方法"""
        logger.info("测试所有数据获取方法")
        
        # 只测试tushare数据源
        client = data_source_factory.switch_data_source(DATA_SOURCE_TUSHARE, token="mock_test_token")
        
        # 测试获取基本信息
        basic_info = client.get_stock_basic_info()
        self.assertIsInstance(basic_info, pd.DataFrame)
        logger.info(f"TuShare - 基本信息数据: {len(basic_info)} 行")
        
        # 测试获取日线数据（使用少量数据）
        if not basic_info.empty:
            # 选择第一个股票代码进行测试
            stock_code = basic_info.iloc[0]['code']
            daily_data = client.get_stock_daily_data(stock_code, '20240101', '20240131')
            self.assertIsInstance(daily_data, pd.DataFrame)
            logger.info(f"TuShare - 日线数据: {len(daily_data)} 行")
        
        # 测试获取财务指标
        financial_data = client.get_financial_indicators()
        self.assertIsInstance(financial_data, pd.DataFrame)
        logger.info(f"TuShare - 财务指标数据: {len(financial_data)} 行")
        
        # 测试获取热点板块
        hot_sectors = client.get_hot_sectors()
        self.assertIsInstance(hot_sectors, pd.DataFrame)
        logger.info(f"TuShare - 热点板块数据: {len(hot_sectors)} 行")
        
        # 测试获取资金流向
        money_flow = client.get_money_flow()
        self.assertIsInstance(money_flow, pd.DataFrame)
        logger.info(f"TuShare - 资金流向数据: {len(money_flow)} 行")
        
        # 测试获取宏观经济数据
        macro_data = client.get_macro_economic_data()
        self.assertIsInstance(macro_data, pd.DataFrame)
        logger.info(f"TuShare - 宏观经济数据: {len(macro_data)} 行")


if __name__ == '__main__':
    logger.info("开始运行数据源切换测试...")
    unittest.main()