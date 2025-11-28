#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试获取A股股票列表的功能
"""

import sys
sys.path.append('.')

from data_fetching.tushare_adapter import TuShareClient
import logging
# 简化日志配置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_get_all_a_stocks():
    """测试获取所有A股股票列表"""
    try:
        logger.info("开始测试获取所有A股股票列表功能")
        
        # 初始化tushare客户端
        client = TuShareClient()
        
        # 尝试获取A股股票列表
        df = client.get_all_a_stocks()
        
        if df is not None and not df.empty:
            logger.info(f"成功获取到 {len(df)} 只A股股票")
            logger.info(f"返回的数据列: {list(df.columns)}")
            # 打印前5行数据作为示例
            logger.info("\n前5行数据示例:")
            logger.info(df.head().to_string())
            return True
        else:
            logger.warning("未能获取到A股股票列表")
            return False
    except Exception as e:
        logger.error(f"测试获取A股股票列表时出错: {str(e)}", exc_info=True)
        return False

if __name__ == "__main__":
    test_get_all_a_stocks()