#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
股票数据更新状态检查工具
用于查询 /api/data/status 接口获取数据更新进度
"""

import sys
import os
import requests
import json
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

BASE_URL = "http://localhost:8000"

def check_update_status():
    print("🔍 正在检查数据更新状态...")
    
    # 调用状态查询接口
    url = f"{BASE_URL}/api/data/status"
    print(f"正在调用状态接口: {url}")
    
    try:
        # 发送GET请求
        response = requests.get(url)
        
        # 检查响应状态码
        if response.status_code == 200:
            result = response.json()
            
            # 打印状态信息
            print("\n📊 数据更新状态报告")
            print("=" * 50)
            print(f"已请求股票数量: {result.get('total_stocks', 0)}")
            print(f"已更新股票数量: {result.get('updated_stocks', 0)}")
            print(f"未更新股票数量: {result.get('pending_stocks', 0)}")
            print(f"最后更新时间: {result.get('last_update_time', 'N/A')}")
            
            # 计算更新百分比
            total = result.get('total_stocks', 0)
            updated = result.get('updated_stocks', 0)
            if total > 0:
                percent = (updated / total) * 100
                print(f"更新进度: {percent:.1f}%")
                
                # 显示进度条
                bar_length = 40
                filled_length = int(bar_length * updated // total)
                bar = '█' * filled_length + '-' * (bar_length - filled_length)
                print(f"[{bar}] {percent:.1f}%")
            
            # 打印样本股票状态
            sample_status = result.get('sample_stocks_status', [])
            if sample_status:
                print("\n📈 样本股票状态:")
                for stock_info in sample_status:
                    # 处理可能的不同格式
                    if isinstance(stock_info, dict):
                        code = stock_info.get('code', 'unknown')
                        status = stock_info.get('status', 'unknown')
                        print(f"  - {code}: {status}")
                    else:
                        # 假设是格式如 "002892: 需要更新" 的字符串
                        print(f"  - {stock_info}")
            
            # 检查更新是否完成
            if updated >= total and total > 0:
                print("\n✅ 更新已完成！")
            else:
                print("\n⏳ 更新正在进行中...")
            
            return True
        else:
            print(f"❌ 请求失败，状态码: {response.status_code}")
            print(f"   错误信息: {response.text}")
            return False
    except Exception as e:
        print(f"❌ 调用接口时发生错误: {str(e)}")
        print("请确保后端服务正在运行 (http://localhost:8000)")
        return False

def check_with_retry(retries=3, interval=5):
    """带重试机制的状态检查"""
    for i in range(retries):
        if check_update_status():
            return True
        if i < retries - 1:
            print(f"\n将在 {interval} 秒后重试...")
            time.sleep(interval)
    return False

if __name__ == "__main__":
    import time
    
    # 解析命令行参数
    import argparse
    parser = argparse.ArgumentParser(description='股票数据更新状态检查工具')
    parser.add_argument('--retry', type=int, default=1, help='重试次数')
    parser.add_argument('--interval', type=int, default=5, help='重试间隔(秒)')
    args = parser.parse_args()
    
    if args.retry > 1:
        check_with_retry(args.retry, args.interval)
    else:
        check_update_status()