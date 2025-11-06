#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志功能测试脚本
用于验证日志配置是否正常工作
"""

import os
import sys

# 确保项目根目录在Python路径中
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 导入日志配置
from backend.logging_config import setup_logger

# 设置日志记录器
logger = setup_logger(__name__)

def test_logging():
    """测试不同级别的日志记录"""
    print("开始测试日志记录功能...")
    
    # 记录不同级别的日志
    logger.debug("这是一条DEBUG级别的日志")
    logger.info("这是一条INFO级别的日志")
    logger.warning("这是一条WARNING级别的日志")
    logger.error("这是一条ERROR级别的日志")
    
    # 测试异常日志记录
    try:
        1 / 0
    except Exception as e:
        logger.error("测试异常日志记录", exc_info=True)
    
    print("日志测试完成！请检查控制台输出和日志文件。")
    print(f"日志文件位置: {os.path.join(project_root, 'logs')}")

if __name__ == "__main__":
    test_logging()