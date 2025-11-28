#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
股票数据更新工具 - 非交互式版本
直接调用更新功能
"""

import sys
import os
import time

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from manual_update import update_all_stocks, wait_for_update_completion

def main():
    print("开始更新所有股票数据...")
    
    # 调用更新函数
    result = update_all_stocks(add_sample_stocks=False)  # 不添加新股票，只更新已有股票
    
    if result.get('status') != 'error':
        print(f"更新任务已启动，计划更新 {result.get('stocks_count', 0)} 只股票")
        print("开始等待更新完成...")
        
        # 等待更新完成，轮询间隔30秒，超时600秒
        success = wait_for_update_completion(poll_interval=30, timeout=600)
        
        if success:
            print("✅ 所有股票数据更新完成！")
        else:
            print("❌ 更新超时，请检查系统状态")
    else:
        print(f"❌ 更新失败: {result.get('message', '未知错误')}")

if __name__ == "__main__":
    main()