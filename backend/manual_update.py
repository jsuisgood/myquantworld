#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
股票数据更新工具
通过调用后端API更新数据（需要后端服务运行）
"""

import requests
import time
import json
import sys
import os
from typing import Dict, Any, Optional, List

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 后端API基础URL
BASE_URL = "http://localhost:8000"


def update_all_stocks(add_sample_stocks: bool = True) -> Dict[str, Any]:
    """
    调用 /api/stocks/update 接口，更新所有已请求过的股票数据
    
    Args:
        add_sample_stocks: 是否添加所有A股股票代码到跟踪列表
        
    Returns:
        Dict: API响应结果
    """
    # 如果设置为添加股票，通过后端API获取所有A股股票代码
    if add_sample_stocks:
        print("正在获取所有A股股票代码...")
        
        try:
            # 调用后端API获取所有A股股票基本信息
            stocks_url = f"{BASE_URL}/api/stocks/basic"
            print(f"正在调用股票列表接口: {stocks_url}")
            response = requests.get(stocks_url)
            
            if response.status_code == 200:
                all_stocks = response.json()
                print(f"成功获取 {len(all_stocks)} 只A股股票信息")
                
                # 提取股票代码列表
                stock_codes = [stock['code'] for stock in all_stocks if 'code' in stock]
                print(f"提取到 {len(stock_codes)} 只股票代码")
                print(f"前5只股票示例: {stock_codes[:5]}")
                
                # 添加股票到跟踪列表
                added_count = 0
                error_count = 0
                total_stocks = len(stock_codes)
                
                print(f"开始添加股票到跟踪列表 (共 {total_stocks} 只)...")
                
                for i, stock_code in enumerate(stock_codes):
                    try:
                        stock_url = f"{BASE_URL}/api/stocks/{stock_code}/update"
                        # 每50只股票显示一次进度
                        if i % 50 == 0 or i == total_stocks - 1:
                            print(f"处理进度: {i+1}/{total_stocks} ({((i+1)/total_stocks)*100:.1f}%)")
                        
                        requests.post(stock_url, timeout=5)
                        added_count += 1
                    except Exception as e:
                        error_count += 1
                        # 只记录部分错误，避免输出过多
                        if error_count <= 10 or i == total_stocks - 1:
                            print(f"添加股票 {stock_code} 时出错: {str(e)}")
                    
                    # 控制请求频率，避免API限流
                    # 0.1秒已经是一个相对较小的值，保持不变以平衡性能和API限制
                    time.sleep(0.1)
                
                print(f"\n添加完成: 成功 {added_count} 只, 失败 {error_count} 只")
            else:
                print(f"获取股票列表失败，状态码: {response.status_code}")
                print(f"错误信息: {response.text}")
                
                # 失败时使用默认的样本股票作为备选
                print("\n使用默认样本股票作为备选...")
                sample_stocks = ["000001", "600036", "601318", "000858", "002415"]
                for stock_code in sample_stocks:
                    try:
                        stock_url = f"{BASE_URL}/api/stocks/{stock_code}/update"
                        print(f"添加股票 {stock_code} 到跟踪列表...")
                        requests.post(stock_url, timeout=5)
                    except Exception as e:
                        print(f"添加股票 {stock_code} 时出错: {str(e)}")
                    # 减少错误处理部分的等待时间，从0.5秒减少到0.2秒
                    time.sleep(0.2)
        except Exception as e:
            print(f"获取所有A股股票代码时发生错误: {str(e)}")
            
            # 错误时使用默认的样本股票
            print("使用默认样本股票作为备选...")
            sample_stocks = ["000001", "600036", "601318", "000858", "002415"]
            for stock_code in sample_stocks:
                try:
                    stock_url = f"{BASE_URL}/api/stocks/{stock_code}/update"
                    print(f"添加股票 {stock_code} 到跟踪列表...")
                    requests.post(stock_url, timeout=5)
                except Exception as inner_e:
                    print(f"添加股票 {stock_code} 时出错: {str(inner_e)}")
                # 减少错误处理部分的等待时间，从0.5秒减少到0.2秒
                time.sleep(0.2)
    
    # 现在调用更新接口
    url = f"{BASE_URL}/api/stocks/update"
    print(f"\n正在调用批量更新接口: {url}")
    
    try:
        # 发送POST请求，无需请求体
        response = requests.post(url)
        
        # 检查响应状态码
        if response.status_code == 200:
            result = response.json()
            print(f"更新任务已启动: {result['message']}")
            print(f"计划更新股票数量: {result['stocks_count']}")
            
            # 如果计划更新的股票数量为0，给出提示
            if result['stocks_count'] == 0:
                print("警告: 没有股票需要更新，请确保股票代码已添加到跟踪列表")
                
            return result
        else:
            print(f"请求失败，状态码: {response.status_code}")
            print(f"错误信息: {response.text}")
            return {"status": "error", "code": response.status_code, "message": response.text}
    except Exception as e:
        print(f"调用接口时发生错误: {str(e)}")
        return {"status": "error", "message": str(e)}


def update_single_stock(stock_code: str) -> Dict[str, Any]:
    """
    调用 /api/stocks/{stock_code}/update 接口，更新单只股票数据
    
    Args:
        stock_code: 股票代码
        
    Returns:
        Dict: API响应结果
    """
    url = f"{BASE_URL}/api/stocks/{stock_code}/update"
    print(f"正在调用单只股票更新接口: {url}")
    
    try:
        # 发送POST请求，无需请求体
        response = requests.post(url)
        
        # 检查响应状态码
        if response.status_code == 200:
            result = response.json()
            print(f"单只股票更新结果: {result['message']}")
            return result
        else:
            print(f"请求失败，状态码: {response.status_code}")
            print(f"错误信息: {response.text}")
            return {"status": "error", "code": response.status_code, "message": response.text}
    except Exception as e:
        print(f"调用接口时发生错误: {str(e)}")
        return {"status": "error", "message": str(e)}


def check_data_status() -> Dict[str, Any]:
    """
    调用 /api/data/status 接口，检查数据状态
    
    Returns:
        Dict: API响应结果
    """
    url = f"{BASE_URL}/api/data/status"
    print(f"正在检查数据状态: {url}")
    
    try:
        response = requests.get(url)
        
        if response.status_code == 200:
            result = response.json()
            print(f"已请求股票数量: {result['requested_stocks_count']}")
            
            if result['last_update']:
                print(f"最后更新时间: {result['last_update']['last_full_update']}")
                print(f"距上次更新时间(秒): {result['last_update']['time_since_update_seconds']}")
            
            if result['sample_stocks_status']:
                print("样本股票状态:")
                for stock_code, status in result['sample_stocks_status'].items():
                    print(f"  - {stock_code}: {'最新' if status == 'up_to_date' else '需要更新'}")
            
            return result
        else:
            print(f"请求失败，状态码: {response.status_code}")
            return {"status": "error", "code": response.status_code}
    except Exception as e:
        print(f"调用接口时发生错误: {str(e)}")
        return {"status": "error", "message": str(e)}


def get_health_status() -> Dict[str, Any]:
    """
    调用 /api/health 接口，检查系统健康状态
    
    Returns:
        Dict: API响应结果
    """
    url = f"{BASE_URL}/api/health"
    print(f"正在检查系统健康状态: {url}")
    
    try:
        response = requests.get(url)
        
        if response.status_code == 200:
            result = response.json()
            print(f"系统状态: {'健康' if result['status'] == 'healthy' else '异常'}")
            print(f"服务状态:")
            print(f"  - akshare: {'可用' if result['services']['akshare'] == 'available' else '不可用'}")
            print(f"  - 数据库: {'已连接' if result['services']['database'] else '未连接'}")
            print(f"  - 分析器: {'可用' if result['services']['analyzer'] == 'available' else '不可用'}")
            print(f"  - 数据状态: {'最新' if result['services']['data_status'] == 'up_to_date' else '需要更新'}")
            
            if result['last_full_update']:
                print(f"最后完整更新时间: {result['last_full_update']}")
            
            print(f"跟踪股票数量: {result['tracked_stocks']}")
            return result
        else:
            print(f"请求失败，状态码: {response.status_code}")
            return {"status": "error", "code": response.status_code}
    except Exception as e:
        print(f"调用接口时发生错误: {str(e)}")
        return {"status": "error", "message": str(e)}


def wait_for_update_completion(poll_interval: int = 30, timeout: int = 300) -> bool:
    """
    轮询检查数据更新是否完成
    
    Args:
        poll_interval: 轮询间隔（秒）
        timeout: 超时时间（秒）
        
    Returns:
        bool: 更新是否完成
    """
    start_time = time.time()
    
    print(f"开始轮询检查更新状态，间隔 {poll_interval} 秒，超时 {timeout} 秒")
    
    while time.time() - start_time < timeout:
        status = check_data_status()
        
        # 检查数据状态
        if status.get('sample_stocks_status'):
            all_up_to_date = all(s == 'up_to_date' for s in status['sample_stocks_status'].values())
            if all_up_to_date:
                print("所有样本股票数据已更新为最新状态")
                return True
        
        elapsed = int(time.time() - start_time)
        print(f"已等待 {elapsed}/{timeout} 秒，继续等待...")
        time.sleep(poll_interval)
    
    print("更新超时")
    return False


# 移除了直接更新数据模式相关的函数定义


def main():
    """
    主函数，包含API模式的基本操作功能
    """
    print("=== 股票数据更新工具 ===")
    print("1. API模式 - 检查系统健康状态")
    print("2. API模式 - 检查数据状态")
    print("3. API模式 - 更新所有股票数据")
    print("4. API模式 - 更新单只股票数据")
    print("q. 退出")
    
    while True:
        choice = input("请选择操作 (1-4/q): ")
        
        if choice == '1':
            get_health_status()
        elif choice == '2':
            check_data_status()
        elif choice == '3':
            # API模式：更新所有股票
            update_all_stocks()
            # 询问是否等待更新完成
            wait = input("是否等待更新完成？(y/n): ")
            if wait.lower() == 'y':
                wait_for_update_completion()
        elif choice == '4':
            # API模式：更新单只股票
            stock_code = input("请输入股票代码: ")
            update_single_stock(stock_code)
        elif choice.lower() == 'q':
            print("感谢使用，再见！")
            break
        else:
            print("无效的选择，请输入1-4或q")
        
        print("\n" + "="*50 + "\n")


# 简单调用示例
if __name__ == "__main__":
    # 运行交互式界面
    main()
    
    # 或者可以直接使用以下代码调用特定功能:
    # 示例1: 更新所有股票并等待完成
    # result = update_all_stocks()
    # wait_for_update_completion()
    
    # 示例2: 更新单只股票
    # update_single_stock("000001")  # 平安银行
    
    # 示例3: 只检查状态
    # check_data_status()