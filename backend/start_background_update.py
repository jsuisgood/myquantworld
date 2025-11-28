#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
股票数据更新工具 - 后台启动版本
只启动更新任务，不等待完成
"""

import sys
import os
import requests

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

BASE_URL = "http://localhost:8000"

def start_background_update():
    print("🔄 正在启动后台数据更新任务...")
    
    # 调用批量更新接口
    url = f"{BASE_URL}/api/stocks/update"
    print(f"正在调用批量更新接口: {url}")
    
    try:
        # 发送POST请求
        response = requests.post(url)
        
        # 检查响应状态码
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 更新任务已成功启动!")
            print(f"   - 消息: {result['message']}")
            print(f"   - 计划更新股票数量: {result['stocks_count']}")
            print("\nℹ️  更新任务已在后台运行，请稍后通过系统状态检查更新进度")
            print("ℹ️  可以通过 /api/data/status 接口查看更新状态")
            return True
        else:
            print(f"❌ 请求失败，状态码: {response.status_code}")
            print(f"   错误信息: {response.text}")
            return False
    except Exception as e:
        print(f"❌ 调用接口时发生错误: {str(e)}")
        print("请确保后端服务正在运行 (http://localhost:8000)")
        return False

if __name__ == "__main__":
    start_background_update()