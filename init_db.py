#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据库初始化脚本
用于创建所有数据库表
"""

import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 从环境变量加载配置
load_dotenv()

# 导入数据库模型和连接配置
from database.config import SQLALCHEMY_DATABASE_URL
from database.models import Base, StockBasicInfo, Stock, StockDailyData, StockFinancialIndicators
from database.models import TradingStrategy, TechnicalAnalysisResult, TradingSignal, User
from database.models import AnalysisTask, MarketIndex

def init_database():
    """初始化数据库，创建所有表"""
    try:
        print(f"正在连接数据库: {SQLALCHEMY_DATABASE_URL}")
        
        # 创建数据库引擎
        engine = create_engine(SQLALCHEMY_DATABASE_URL)
        
        # 创建会话工厂
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        print("开始创建数据库表...")
        
        # 创建所有表
        Base.metadata.create_all(bind=engine)
        
        print("数据库表创建成功！")
        print(f"创建的表: {', '.join(Base.metadata.tables.keys())}")
        
        # 测试数据库连接
        db = SessionLocal()
        try:
            # 执行简单查询以验证连接
            result = db.execute("SELECT 1")
            print("数据库连接测试成功!")
            return True
        except Exception as e:
            print(f"数据库连接测试失败: {e}")
            return False
        finally:
            db.close()
            
    except Exception as e:
        print(f"数据库初始化失败: {e}")
        print("请检查数据库配置和连接信息是否正确。")
        return False

def drop_tables():
    """删除所有表（慎用！）"""
    try:
        confirm = input("警告：此操作将删除所有数据库表，是否继续？(y/N): ")
        if confirm.lower() != 'y':
            print("操作已取消。")
            return False
        
        engine = create_engine(SQLALCHEMY_DATABASE_URL)
        Base.metadata.drop_all(bind=engine)
        print("所有表已删除。")
        return True
    except Exception as e:
        print(f"删除表失败: {e}")
        return False

def main():
    """主函数"""
    print("==== 数据库初始化工具 ====")
    print("1. 创建所有数据库表")
    print("2. 删除所有数据库表（慎用！）")
    print("0. 退出")
    
    choice = input("请选择操作 (1/2/0): ")
    
    if choice == '1':
        init_database()
    elif choice == '2':
        drop_tables()
    elif choice == '0':
        print("程序已退出。")
    else:
        print("无效的选择，请重新运行程序。")

if __name__ == "__main__":
    main()