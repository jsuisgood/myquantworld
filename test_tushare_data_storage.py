#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试tushare数据存储功能
"""

import os
import sys
import logging
from datetime import datetime, timedelta
import time

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 配置日志
from utils.logger_config import get_logger, log_error, log_with_context
logger = get_logger(__name__)

# 导入必要的模块
from data_fetching.tushare_adapter import TuShareClient
from database.models import TushareStockBasicInfo, TushareStockDailyData, TushareStockFinancialIndicators
from database.db_manager import DBManager

def test_init_database():
    """初始化数据库，确保表结构存在"""
    try:
        logger.info("初始化数据库...")
        # 先检查是否存在初始化数据库的脚本
        if os.path.exists('init_db.py'):
            # 执行初始化数据库的脚本
            with open('init_db.py', 'r', encoding='utf-8') as f:
                exec(f.read())
            logger.info("数据库初始化完成")
        else:
            logger.warning("未找到init_db.py，跳过自动初始化")
        return True
    except Exception as e:
        logger.error(f"数据库初始化失败: {str(e)}")
        return False

def test_save_stock_basic_info(client):
    """测试保存股票基本信息到数据库"""
    try:
        logger.info("测试保存股票基本信息...")
        success = client.save_stock_basic_info_to_db()
        
        if success:
            # 验证数据库中是否有数据
            db_manager = DBManager()
            with db_manager.get_session() as session:
                count = session.query(TushareStockBasicInfo).count()
                logger.info(f"tushare_stock_basic_info表中记录数: {count}")
                # 获取前5条记录作为示例
                records = session.query(TushareStockBasicInfo).limit(5).all()
                for record in records:
                    logger.info(f"股票基本信息示例: 代码={record.code}, 名称={record.name}")
            return True
        else:
            logger.error("保存股票基本信息失败")
            return False
    except Exception as e:
        logger.error(f"测试保存股票基本信息失败: {str(e)}")
        return False

def test_save_single_stock_data(client, stock_code):
    """测试保存单只股票数据到数据库"""
    try:
        logger.info(f"测试保存股票{stock_code}数据...")
        
        # 计算日期范围（最近30天）
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
        
        # 保存日线数据
        daily_success = client.save_stock_daily_data_to_db(stock_code, start_date, end_date)
        
        # 保存财务指标数据
        financial_success = client.save_stock_financial_indicators_to_db(stock_code)
        
        # 验证数据库中是否有数据
        db_manager = DBManager()
        with db_manager.get_session() as session:
            # 验证日线数据
            if daily_success:
                daily_count = session.query(TushareStockDailyData).filter(
                    TushareStockDailyData.stock_code == stock_code
                ).count()
                logger.info(f"股票{stock_code}的日线数据记录数: {daily_count}")
                # 获取最新的日线数据
                latest_daily = session.query(TushareStockDailyData).filter(
                    TushareStockDailyData.stock_code == stock_code
                ).order_by(TushareStockDailyData.trade_date.desc()).first()
                if latest_daily:
                    logger.info(f"最新日线数据: 日期={latest_daily.trade_date}, 收盘价={latest_daily.close_price}")
            
            # 验证财务指标数据
            if financial_success:
                financial_count = session.query(TushareStockFinancialIndicators).filter(
                    TushareStockFinancialIndicators.stock_code == stock_code
                ).count()
                logger.info(f"股票{stock_code}的财务指标记录数: {financial_count}")
                # 获取最新的财务指标
                latest_financial = session.query(TushareStockFinancialIndicators).filter(
                    TushareStockFinancialIndicators.stock_code == stock_code
                ).order_by(TushareStockFinancialIndicators.end_date.desc()).first()
                if latest_financial:
                    logger.info(f"最新财务指标: 日期={latest_financial.end_date}, EPS={latest_financial.earnings_per_share}")
        
        return daily_success or financial_success
    except Exception as e:
        logger.error(f"测试保存股票{stock_code}数据失败: {str(e)}")
        return False

def test_batch_save_stock_data(client, stock_codes):
    """测试批量保存多只股票数据到数据库"""
    try:
        logger.info(f"测试批量保存{len(stock_codes)}只股票数据...")
        
        # 计算日期范围（最近10天）
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=10)).strftime('%Y%m%d')
        
        # 批量保存数据
        results = client.batch_save_stock_data_to_db(stock_codes, start_date, end_date)
        
        # 统计结果
        success_count = sum(1 for success in results.values() if success)
        logger.info(f"批量保存完成: 成功{success_count}只，失败{len(results) - success_count}只")
        
        # 打印每只股票的保存结果
        for stock_code, success in results.items():
            status = "成功" if success else "失败"
            logger.info(f"股票{stock_code}: {status}")
        
        # 验证数据库中是否有数据
        db_manager = DBManager()
        with db_manager.get_session() as session:
            # 验证所有测试股票的日线数据总数
            total_daily_count = session.query(TushareStockDailyData).filter(
                TushareStockDailyData.stock_code.in_(stock_codes)
            ).count()
            logger.info(f"所有测试股票的日线数据总记录数: {total_daily_count}")
        
        return success_count > 0
    except Exception as e:
        logger.error(f"测试批量保存股票数据失败: {str(e)}")
        return False

def main():
    """主函数"""
    logger.info("开始测试tushare数据存储功能...")
    
    # 初始化数据库
    if not test_init_database():
        logger.error("数据库初始化失败，无法继续测试")
        return
    
    # 初始化TuShareClient
    client = TuShareClient()
    logger.info(f"TuShare客户端初始化完成: {'可用' if client.pro else '不可用，将使用模拟数据'}")
    
    # 定义测试股票列表
    test_stocks = ['000001', '000002', '600000']  # 平安银行、万科A、浦发银行
    
    # 运行各项测试
    tests = [
        ("保存股票基本信息", lambda: test_save_stock_basic_info(client)),
        (f"保存单只股票数据 ({test_stocks[0]})", lambda: test_save_single_stock_data(client, test_stocks[0])),
        ("批量保存股票数据", lambda: test_batch_save_stock_data(client, test_stocks))
    ]
    
    # 运行测试
    success_count = 0
    for test_name, test_func in tests:
        logger.info(f"\n=== {test_name} ===")
        if test_func():
            success_count += 1
            logger.info(f"✅ {test_name} 测试通过")
        else:
            logger.error(f"❌ {test_name} 测试失败")
        
        # 测试之间添加间隔，避免API调用过于频繁
        time.sleep(1)
    
    # 输出测试总结
    logger.info(f"\n=== 测试总结 ===")
    logger.info(f"总测试数: {len(tests)}")
    logger.info(f"通过测试数: {success_count}")
    logger.info(f"失败测试数: {len(tests) - success_count}")
    
    if success_count == len(tests):
        logger.info("✅ 所有测试通过！")
        return 0
    else:
        logger.error("❌ 有测试失败，请检查错误信息")
        return 1

if __name__ == "__main__":
    sys.exit(main())