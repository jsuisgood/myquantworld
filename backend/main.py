import os
import sys
import asyncio
import schedule
import time
from datetime import datetime, timedelta

# 确保项目根目录在Python路径中
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 导入日志配置（使用相对导入或绝对导入）
try:
    # 尝试相对导入
    from logging_config import setup_logger
except ImportError:
    # 如果相对导入失败，尝试绝对导入
    from backend.logging_config import setup_logger

logger = setup_logger(__name__)

# 打印路径信息以便调试
logger.info(f"Project root directory: {project_root}")
logger.info(f"Project root is in Python path: {project_root in sys.path}")

import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import pandas as pd
from typing import List, Dict, Any, Optional, Set

# 导入服务层和工具类
try:
    # 尝试相对导入方式
    from data_fetching.tushare_adapter import TuShareClient
    from data_storage.db_storage import DBStorage
    from analysis.technical_analyzer import TechnicalAnalyzer
    # 导入数据库会话
    from database.connection import SessionLocal
except ImportError:
    # 如果相对导入失败，尝试使用项目根目录的导入方式
    logger.warning("Standard imports failed, trying alternative import paths...")
    try:
        from myquantworld.data_fetching.tushare_adapter import TuShareClient
        from myquantworld.data_storage.db_storage import DBStorage
        from myquantworld.analysis.technical_analyzer import TechnicalAnalyzer
        from myquantworld.database.connection import SessionLocal
    except ImportError as e:
        logger.error(f"Failed to import required modules: {str(e)}", exc_info=True)
        # 尝试最后的导入方式
        import sys
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        from data_fetching.tushare_adapter import TuShareClient
        from data_storage.db_storage import DBStorage
        from analysis.technical_analyzer import TechnicalAnalyzer
        from database.connection import SessionLocal

# 创建FastAPI应用
app = FastAPI(
    title="股票数据分析API",
    description="提供股票数据获取、存储和分析的RESTful API，包含自动更新机制确保数据最新",
    version="1.0.1"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该设置具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化客户端和服务
db_storage = DBStorage()
analyzer = TechnicalAnalyzer()

# 初始化tushare客户端
tushare_client = TuShareClient()

# 跟踪哪些股票代码已被请求，用于增量更新
requested_stock_codes: Set[str] = set()

# 最后一次完整更新的时间
last_full_update_time = None

# 数据更新锁，避免并发更新
update_lock = asyncio.Lock()

# Pydantic模型定义
class StockDataRequest(BaseModel):
    stock_codes: List[str]
    start_date: str
    end_date: str

class AnalysisRequest(BaseModel):
    stock_code: str
    days_ahead: int = 5

class StockBasic(BaseModel):
    code: str
    name: str

# Tushare数据更新函数
async def update_tushare_stock_data_incrementally(stock_codes: List[str]):
    """
    增量更新tushare股票数据
    
    Args:
        stock_codes: 股票代码列表
    """
    try:
        logger.info(f"开始增量更新tushare股票数据，共{len(stock_codes)}只股票")
        
        for stock_code in stock_codes:
            try:
                logger.info(f"更新tushare股票{stock_code}的数据")
                
                # 获取最后更新日期（tushare专用表）
                last_update_date = db_storage.get_last_tushare_stock_update_date(stock_code)
                
                # 确定更新的日期范围
                if last_update_date:
                    start_date = (datetime.strptime(last_update_date, '%Y%m%d') + timedelta(days=1)).strftime('%Y%m%d')
                else:
                    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
                
                end_date = datetime.now().strftime('%Y%m%d')
                
                # 如果开始日期晚于结束日期，跳过更新
                if start_date <= end_date:
                    # 保存日线数据
                    tushare_client.save_stock_daily_data_to_db(stock_code, start_date, end_date)
                    
                    # 保存财务指标数据
                    tushare_client.save_stock_financial_indicators_to_db(stock_code)
                
                # 避免频繁请求API
                time.sleep(0.5)
            except Exception as e:
                logger.error(f"更新tushare股票{stock_code}的数据时出错: {str(e)}", exc_info=True)
        
        logger.info("tushare股票数据增量更新完成")
    except Exception as e:
        logger.error(f"增量更新tushare股票数据时出错: {str(e)}", exc_info=True)

async def update_all_tushare_stocks_data():
    """更新所有tushare股票数据"""
    global last_full_update_time
    
    try:
        logger.info("开始更新所有tushare股票数据")
        
        # 记录开始时间
        start_time = datetime.now()
        
        # 获取所有股票代码
        stock_df = tushare_client.get_stock_basic_info()
        if stock_df.empty:
            logger.error("未获取到tushare股票基本信息，更新失败")
            return
        
        all_stock_codes = stock_df['code'].tolist()
        logger.info(f"获取到{tushare_client.name}的{len(all_stock_codes)}只股票代码")
        
        # 更新记录
        last_full_update_time = datetime.now()
        
        # 定义批次大小
        batch_size = 100
        total_stocks = len(all_stock_codes)
        success_count = 0
        
        # 分批处理股票数据
        for i in range(0, total_stocks, batch_size):
            batch = all_stock_codes[i:i+batch_size]
            logger.info(f"处理批次 {i//batch_size + 1}/{(total_stocks + batch_size - 1)//batch_size}")
            
            # 调用增量更新函数
            await update_tushare_stock_data_incrementally(batch)
            success_count += len(batch)
            
            # 批次之间添加延迟，避免API限流
            if i + batch_size < total_stocks:
                logger.info("批次处理完成，等待10秒后继续...")
                time.sleep(10)
        
        # 记录完成时间
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info(f"所有tushare股票数据更新完成！")
        logger.info(f"更新股票数量: {success_count}/{total_stocks}")
        logger.info(f"总耗时: {duration:.2f}秒")
        
    except Exception as e:
        logger.error(f"更新所有tushare股票数据时出错: {str(e)}", exc_info=True)

# Tushare相关API端点
@app.get("/api/tushare/stocks/basic")
async def get_tushare_stock_basic():
    """获取tushare股票基本信息"""
    try:
        logger.info("获取tushare股票基本信息")
        
        # 从tushare获取数据
        df = tushare_client.get_stock_basic_info()
        
        if not df.empty:
            # 转换为字典列表
            data = df.to_dict('records')
            
            # 保存到数据库
            tushare_client.save_stock_basic_info_to_db()
            
            return {
                "code": 200,
                "message": "success",
                "data": data
            }
        else:
            return {
                "code": 404,
                "message": "未获取到tushare股票基本信息"
            }
    except Exception as e:
        logger.error(f"获取tushare股票基本信息时出错: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取tushare股票基本信息失败: {str(e)}")

@app.get("/api/tushare/stocks/a_list")
async def get_all_a_stocks():
    """获取所有A股股票列表"""
    try:
        logger.info("获取所有A股股票列表")
        
        # 从tushare获取所有A股股票数据
        df = tushare_client.get_all_a_stocks()
        
        if not df.empty:
            # 转换为字典列表
            data = df.to_dict('records')
            
            return {
                "code": 200,
                "message": "success",
                "data": data,
                "total_count": len(data)
            }
        else:
            return {
                "code": 404,
                "message": "未获取到A股股票列表"
            }
    except Exception as e:
        logger.error(f"获取A股股票列表时出错: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取A股股票列表失败: {str(e)}")

@app.get("/api/tushare/stocks/{stock_code}/daily")
async def get_tushare_stock_daily(stock_code: str, start_date: Optional[str] = None, end_date: Optional[str] = None):
    """获取tushare股票日线数据"""
    try:
        # 如果没有指定日期范围，默认获取最近30天的数据
        if not end_date:
            end_date = datetime.now().strftime('%Y%m%d')
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
        
        logger.info(f"获取tushare股票{stock_code}的日线数据，日期范围: {start_date} 到 {end_date}")
        
        # 从tushare获取数据
        df = tushare_client.get_stock_daily_data(stock_code, start_date, end_date)
        
        if not df.empty:
            # 转换为字典列表
            data = df.to_dict('records')
            
            return {
                "code": 200,
                "message": "success",
                "data": data
            }
        else:
            return {
                "code": 404,
                "message": f"未获取到股票{stock_code}的日线数据"
            }
    except Exception as e:
        logger.error(f"获取tushare股票日线数据时出错: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取tushare股票日线数据失败: {str(e)}")

@app.get("/api/tushare/stocks/{stock_code}/financial")
async def get_tushare_stock_financial(stock_code: str):
    """获取tushare股票财务指标"""
    try:
        logger.info(f"获取tushare股票{stock_code}的财务指标数据")
        
        # 从tushare获取数据
        df = tushare_client.get_stock_financial_indicators(stock_code)
        
        if not df.empty:
            # 转换为字典列表
            data = df.to_dict('records')
            
            return {
                "code": 200,
                "message": "success",
                "data": data
            }
        else:
            return {
                "code": 404,
                "message": f"未获取到股票{stock_code}的财务指标数据"
            }
    except Exception as e:
        logger.error(f"获取tushare股票财务指标时出错: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取tushare股票财务指标失败: {str(e)}")

@app.post("/api/stocks/{stock_code}/update")
async def update_stock_data(stock_code: str, background_tasks: BackgroundTasks = BackgroundTasks()):
    """将股票添加到跟踪列表并更新数据"""
    try:
        logger.info(f"添加股票{stock_code}到跟踪列表并更新数据")
        
        # 将股票代码添加到跟踪列表
        requested_stock_codes.add(stock_code)
        
        # 在后台任务中更新股票数据
        background_tasks.add_task(update_tushare_stock_data_incrementally, [stock_code])
        
        return {
            "status": "success",
            "message": f"股票{stock_code}已添加到跟踪列表，数据更新正在后台进行",
            "stock_code": stock_code
        }
    except Exception as e:
        logger.error(f"添加股票{stock_code}到跟踪列表时出错: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"添加股票到跟踪列表失败: {str(e)}")

@app.post("/api/tushare/stocks/save")
async def save_tushare_stock_data(request: StockDataRequest, background_tasks: BackgroundTasks = BackgroundTasks()):
    """保存tushare股票数据到数据库"""
    try:
        stock_codes = request.stock_codes
        start_date = request.start_date
        end_date = request.end_date
        
        logger.info(f"保存tushare股票数据到数据库，股票代码: {stock_codes}，日期范围: {start_date} 到 {end_date}")
        
        # 使用tushare_client批量保存股票数据
        results = tushare_client.batch_save_stock_data_to_db(stock_codes, start_date, end_date)
        
        # 统计成功和失败的数量
        success_count = sum(1 for success in results.values() if success)
        
        return {
            "code": 200,
            "message": "success",
            "data": {
                "total": len(stock_codes),
                "success": success_count,
                "failure": len(stock_codes) - success_count,
                "results": results
            }
        }
    except Exception as e:
        logger.error(f"保存tushare股票数据时出错: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"保存tushare股票数据失败: {str(e)}")

@app.get("/api/schedule/test/tushare")
async def test_tushare_scheduled_task():
    """
    测试tushare定时任务功能的接口
    立即执行一次update_all_tushare_stocks_data函数，用于触发tushare数据全量加载
    """
    try:
        logger.info(f"[{datetime.now()}] 开始测试tushare定时任务功能，立即执行tushare数据全量加载...")
        
        # 立即在后台执行tushare数据全量加载任务
        import threading
        def run_tushare_update_task():
            try:
                asyncio.run(update_all_tushare_stocks_data())
                logger.info(f"[{datetime.now()}] tushare数据全量加载执行完成")
            except Exception as e:
                logger.error(f"[{datetime.now()}] tushare数据全量加载执行失败: {str(e)}", exc_info=True)
        
        # 在新线程中执行异步任务
        task_thread = threading.Thread(target=run_tushare_update_task, daemon=True)
        task_thread.start()
        
        return {
            "status": "success",
            "message": "tushare数据全量加载任务已启动，将在后台执行",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"启动tushare数据全量加载失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"启动tushare数据全量加载失败: {str(e)}")

# 启动定时更新任务
def start_scheduled_updates():
    """启动后台定时更新任务"""
    logger.info("配置股票数据定时更新任务...")
    
    # Tushare数据更新任务
    logger.info("配置Tushare数据更新任务:")
    # 每天开盘前更新数据（9:15）
    schedule.every().day.at("09:15").do(lambda: asyncio.run(update_all_tushare_stocks_data()))
    logger.info("- 已配置：每天09:15（开盘前）更新所有A股股票数据（tushare）")
    
    # 交易时段每2小时更新一次（10:45, 13:45）
    schedule.every().day.at("10:45").do(lambda: asyncio.run(update_all_tushare_stocks_data()))
    schedule.every().day.at("13:45").do(lambda: asyncio.run(update_all_tushare_stocks_data()))
    logger.info("- 已配置：交易时段每2小时更新一次所有A股股票数据（tushare）")
    
    # 每天交易结束后更新数据（16:00）
    schedule.every().day.at("16:00").do(lambda: asyncio.run(update_all_tushare_stocks_data()))
    logger.info("- 已配置：每天16:00（收盘后）更新所有A股股票数据（tushare）")
    
    # 运行定时任务的函数
    def run_scheduler():
        logger.info("定时任务调度器已启动")
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)  # 每分钟检查一次
            except Exception as e:
                logger.error(f"定时任务调度器发生错误: {str(e)}", exc_info=True)
                # 发生错误后继续运行
                time.sleep(60)
    
    # 在后台线程中运行定时任务
    import threading
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    print("定时数据更新任务已成功启动")

# 添加缺失的pandas导入
try:
    import pandas as pd
except ImportError:
    pd = None
    logger.warning("pandas未安装，某些功能可能不可用")

@app.get("/api/data/status")
async def get_data_status():
    """获取数据状态信息"""
    global last_full_update_time
    
    # 检查最近更新时间
    update_info = {}
    if last_full_update_time:
        time_since_update = (datetime.now() - last_full_update_time).total_seconds()
        update_info = {
            "last_full_update": last_full_update_time.strftime('%Y-%m-%d %H:%M:%S'),
            "time_since_update_seconds": int(time_since_update)
        }
    
    return {
        "requested_stocks_count": len(requested_stock_codes),
        "last_update": update_info,
        "sample_stocks_status": {}
    }

@app.get("/api/health")
async def health_check():
    """健康检查端点"""
    # 检查数据库连接
    db_connected = db_storage.check_connection()
    
    # 检查tushare是否可用
    tushare_available = True
    try:
        # 尝试一个简单的tushare调用检查可用性
        tushare_client.get_stock_basic_info()
    except:
        tushare_available = False
    
    return {
        "status": "healthy" if db_connected and tushare_available else "degraded",
        "services": {
            "tushare": "available" if tushare_available else "unavailable",
            "database": db_connected,
            "analyzer": "available" if hasattr(analyzer, 'available') and analyzer.available else "available"
        },
        "last_full_update": last_full_update_time.strftime('%Y-%m-%d %H:%M:%S') if last_full_update_time else None,
        "tracked_stocks": len(requested_stock_codes)
    }

# 启动时更新任务
@app.on_event("startup")
async def startup_event():
    """应用启动时执行的任务"""
    logger.info("股票分析API服务启动中...")
    
    # 初始化时获取并加载所有A股股票代码（tushare）
    try:
        logger.info("正在初始化加载所有A股股票代码（tushare）...")
        stock_df = tushare_client.get_stock_basic_info()
        
        if not stock_df.empty:
            all_stock_codes = stock_df['code'].tolist()
            requested_stock_codes.update(all_stock_codes)
            logger.info(f"成功加载 {len(all_stock_codes)} 只A股股票代码（tushare）")
            
            # 保存tushare股票基本信息到数据库
            tushare_client.save_stock_basic_info_to_db()
        else:
            logger.warning("未能加载A股股票代码（tushare），将在首次更新时尝试获取")
    except Exception as e:
        logger.error(f"加载A股股票代码（tushare）时出错: {str(e)}", exc_info=True)
    
    # 启动定时更新任务
    start_scheduled_updates()
    
    # 默认全量加载tushare数据
    logger.info("开始默认全量加载tushare数据...")
    try:
        await update_all_tushare_stocks_data()
        logger.info("tushare数据全量加载完成")
    except Exception as e:
        logger.error(f"全量加载tushare数据时出错: {str(e)}", exc_info=True)
    
    logger.info("股票分析API服务启动完成")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)