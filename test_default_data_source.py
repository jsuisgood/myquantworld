import os
import sys

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_fetching.data_source_factory import DataSourceFactory, DATA_SOURCE_AKSHARE, DATA_SOURCE_TUSHARE

def test_default_data_source_from_env():
    """
    测试从环境变量设置默认数据源
    """
    print("===== 测试默认数据源设置功能 =====")
    
    # 首先测试默认情况下的数据源（不设置环境变量）
    print("\n1. 测试默认情况（不设置环境变量）:")
    # 清除可能存在的环境变量，确保测试的纯净性
    if 'DATA_SOURCE_DEFAULT' in os.environ:
        del os.environ['DATA_SOURCE_DEFAULT']
    
    # 创建工厂实例
    factory1 = DataSourceFactory()
    default_source1 = factory1.get_default_source()
    print(f"   默认数据源: {default_source1}")
    print(f"   是默认的AKShare: {default_source1 == DATA_SOURCE_AKSHARE}")
    
    # 测试设置为tushare的情况
    print("\n2. 测试设置为TuShare的情况:")
    os.environ['DATA_SOURCE_DEFAULT'] = DATA_SOURCE_TUSHARE
    
    # 创建新的工厂实例以触发环境变量读取
    factory2 = DataSourceFactory()
    default_source2 = factory2.get_default_source()
    print(f"   设置环境变量 DATA_SOURCE_DEFAULT={DATA_SOURCE_TUSHARE}")
    print(f"   默认数据源: {default_source2}")
    print(f"   成功切换到TuShare: {default_source2 == DATA_SOURCE_TUSHARE}")
    
    # 测试设置为akshare的情况
    print("\n3. 测试设置为AKShare的情况:")
    os.environ['DATA_SOURCE_DEFAULT'] = DATA_SOURCE_AKSHARE
    
    # 创建新的工厂实例
    factory3 = DataSourceFactory()
    default_source3 = factory3.get_default_source()
    print(f"   设置环境变量 DATA_SOURCE_DEFAULT={DATA_SOURCE_AKSHARE}")
    print(f"   默认数据源: {default_source3}")
    print(f"   设置为AKShare: {default_source3 == DATA_SOURCE_AKSHARE}")
    
    # 清理环境变量
    if 'DATA_SOURCE_DEFAULT' in os.environ:
        del os.environ['DATA_SOURCE_DEFAULT']
    
    print("\n===== 测试完成 =====")
    
if __name__ == "__main__":
    test_default_data_source_from_env()