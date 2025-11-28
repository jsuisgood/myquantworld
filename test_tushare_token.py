import os
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from data_fetching.data_source_factory import data_source_factory, DATA_SOURCE_TUSHARE
from utils.logger_config import get_logger

# 配置日志
logger = get_logger('tushare_token_test')


def test_tushare_token():
    """测试TuShare Token是否正确加载并可用"""
    logger.info("开始测试TuShare Token加载...")
    
    try:
        # 检查是否从环境变量加载了Token
        tushare_config = data_source_factory.config.get_source_config(DATA_SOURCE_TUSHARE)
        token = tushare_config.get('token')
        
        if token:
            logger.info(f"成功从配置中获取Token，长度: {len(token)} 字符")
            logger.info(f"Token前缀: {token[:8]}...")
        else:
            logger.error("未找到TuShare Token")
            return False
        
        # 尝试切换到TuShare数据源
        logger.info("尝试切换到TuShare数据源...")
        client = data_source_factory.switch_data_source(DATA_SOURCE_TUSHARE)
        logger.info(f"成功切换到数据源: {client.name}")
        
        # 检查数据源是否可用
        logger.info("检查数据源可用性...")
        is_available = data_source_factory.is_tushare_available()
        
        if is_available:
            logger.info("TuShare数据源可用")
            # 尝试获取一小部分数据进行验证
            logger.info("尝试获取股票基本信息...")
            basic_info = client.get_stock_basic_info()
            if basic_info is not None and not basic_info.empty:
                logger.info(f"成功获取数据，返回 {len(basic_info)} 条记录")
                logger.info("前5条记录:")
                logger.info(basic_info.head().to_string())
                return True
            else:
                logger.warning("获取的数据为空")
                return False
        else:
            logger.error("TuShare数据源不可用")
            # 查看最后一个错误
            if hasattr(client, 'get_last_error'):
                last_error = client.get_last_error()
                logger.error(f"错误详情: {last_error}")
            return False
            
    except Exception as e:
        logger.error(f"测试过程中发生错误: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False


if __name__ == '__main__':
    logger.info("开始运行TuShare Token测试...")
    success = test_tushare_token()
    
    if success:
        logger.info("测试成功完成！TuShare Token已正确配置并可用。")
        sys.exit(0)
    else:
        logger.error("测试失败。请检查Token配置和网络连接。")
        sys.exit(1)