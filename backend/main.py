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
    from data_fetching.akshare_client import AkshareClient
    from data_storage.db_storage import DBStorage
    from analysis.technical_analyzer import TechnicalAnalyzer
    # 导入数据库会话
    from database.connection import SessionLocal
except ImportError:
    # 如果相对导入失败，尝试使用项目根目录的导入方式
    logger.warning("Standard imports failed, trying alternative import paths...")
    try:
        from myquantworld.data_fetching.akshare_client import AkshareClient
        from myquantworld.data_storage.db_storage import DBStorage
        from myquantworld.analysis.technical_analyzer import TechnicalAnalyzer
        from myquantworld.database.connection import SessionLocal
    except ImportError as e:
        logger.error(f"Failed to import required modules: {str(e)}", exc_info=True)
        # 尝试最后的导入方式
        import sys
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        from data_fetching.akshare_client import AkshareClient
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
ak_client = AkshareClient()
db_storage = DBStorage()
analyzer = TechnicalAnalyzer()

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

# API端点定义
@app.get("/api/stocks/basic", response_model=List[Dict[str, Any]])
async def get_stock_basic_info():
    """获取股票基本信息列表"""
    try:
        # 使用akshare_client获取股票基本信息
        stock_df = ak_client.get_stock_basic_info()
        
        if stock_df.empty:
            return []
        
        # 将DataFrame转换为字典列表
        return stock_df.to_dict('records')
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取股票基本信息失败: {str(e)}")

@app.post("/api/stocks/daily")
async def get_stock_daily_data(request: StockDataRequest):
    """批量获取股票日线数据"""
    try:
        # 使用akshare_client批量获取股票数据
        results = ak_client.batch_get_stock_daily_data(
            stock_codes=request.stock_codes,
            start_date=request.start_date,
            end_date=request.end_date
        )
        
        # 转换结果为可JSON序列化的格式
        response_data = {}
        for stock_code, df in results.items():
            if not df.empty:
                # 处理日期列以确保可序列化
                df_serializable = df.copy()
                for col in df_serializable.columns:
                    if pd.api.types.is_datetime64_any_dtype(df_serializable[col]):
                        df_serializable[col] = df_serializable[col].astype(str)
                response_data[stock_code] = df_serializable.to_dict('records')
            else:
                response_data[stock_code] = []
        
        return response_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取股票日线数据失败: {str(e)}")

@app.get("/api/stocks/{stock_code}/daily")
async def get_single_stock_daily(stock_code: str, start_date: str, end_date: str, background_tasks: BackgroundTasks = None):
    """
    获取单个股票的日线数据，确保返回最新数据
    """
    try:
        # 获取数据库会话
        db = SessionLocal()
        
        try:
            # 将股票代码添加到已请求集合
            requested_stock_codes.add(stock_code)
            
            # 检查数据是否过时，如果过时则在后台更新
            if await is_data_outdated(stock_code):
                if background_tasks:
                    background_tasks.add_task(update_stock_data_incrementally, stock_code)
                    
            # 尝试从数据库获取数据，正确传递数据库会话
            df = db_storage.get_stock_daily_data(db, stock_code, start_date, end_date)
            
            # 如果数据库中没有数据或数据不足，从API获取
            if df.empty:
                df = ak_client.get_stock_daily_data(stock_code, start_date, end_date)
                
                # 保存到数据库，正确传递参数
                if not df.empty:
                    db_storage.save_stock_daily_data(db, stock_code, df)
            
            if df.empty:
                return {"data": [], "message": "未找到数据"}
            
            # 处理日期列以确保可序列化
            df_serializable = df.copy()
            for col in df_serializable.columns:
                if pd.api.types.is_datetime64_any_dtype(df_serializable[col]):
                    df_serializable[col] = df_serializable[col].astype(str)
            
            # 检查数据是否是最新的
            latest_data_date = df['trade_date'].max()
            is_latest = (datetime.now().date() - latest_data_date.date()).days <= 1
            
            return {
                "data": df_serializable.to_dict('records'), 
                "message": "success",
                "is_latest": is_latest,
                "latest_date": latest_data_date.strftime('%Y%m%d') if hasattr(latest_data_date, 'strftime') else str(latest_data_date)
            }
        finally:
            # 确保数据库会话关闭
            db.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取股票数据失败: {str(e)}")

async def is_data_outdated(stock_code: str, days_threshold: int = 1) -> bool:
    """
    检查股票数据是否过时
    """
    try:
        # 获取数据库会话
        db = SessionLocal()
        
        try:
            # 获取最新的数据日期，函数内部已处理数据库会话
            latest_date = db_storage.get_latest_stock_date(stock_code)
            
            if not latest_date:
                return True  # 没有数据，视为过时
            
            # 计算与当前日期的差异
            today = datetime.now().date()
            days_diff = (today - latest_date).days
            
            # 考虑交易日和非交易日
            if days_diff > days_threshold:
                # 获取交易日历，检查是否有遗漏的交易日
                end_date = today.strftime('%Y%m%d')
                start_date = (latest_date + timedelta(days=1)).strftime('%Y%m%d')
                
                # 尝试获取交易日历，如果失败则默认认为数据需要更新
                try:
                    trade_dates = ak_client.get_trade_dates(start_date, end_date)
                    # 如果有交易日未更新，则数据过时
                    return len(trade_dates) > 0
                except:
                    return True
            
            return False
        finally:
            # 确保数据库会话关闭
            db.close()
    except:
        # 发生错误时默认认为数据需要更新
        return True

async def update_stock_data_incrementally(stock_code: str):
    """
    增量更新单只股票的数据
    """
    try:
        # 获取数据库会话
        db = SessionLocal()
        
        try:
            # 获取最新的数据日期，函数内部已处理数据库会话
            latest_date = db_storage.get_latest_stock_date(stock_code)
            
            if latest_date:
                # 从最新日期的下一天开始获取数据
                start_date = (latest_date + timedelta(days=1)).strftime('%Y%m%d')
            else:
                # 如果没有数据，获取最近1000天的数据
                start_date = (datetime.now() - timedelta(days=1000)).strftime('%Y%m%d')
            
            end_date = datetime.now().strftime('%Y%m%d')
            
            # 只在日期有效时获取数据
            if start_date <= end_date:
                df = ak_client.get_stock_daily_data(stock_code, start_date, end_date)
                if not df.empty:
                    # 正确传递参数：db会话、stock_code、数据
                    success = db_storage.save_stock_daily_data(db, stock_code, df)
                    print(f"增量更新股票 {stock_code} 数据成功，新增 {len(df)} 条记录")
                    return success
                else:
                    print(f"股票 {stock_code} 数据已是最新，无需更新")
                    return True  # 数据已是最新，返回True表示状态正常
            else:
                print(f"股票 {stock_code} 数据已是最新，无需更新 (start_date > end_date)")
                return True  # 数据已是最新，返回True表示状态正常
        finally:
            # 确保数据库会话关闭
            db.close()
    except Exception as e:
        print(f"增量更新股票 {stock_code} 数据失败: {str(e)}")
        return False

async def update_all_stocks_data():
    """更新所有A股股票数据"""
    global last_full_update_time
    
    async with update_lock:
        try:
            logger.info("开始获取所有A股股票代码...")
            
            # 获取所有A股股票基本信息
            stock_df = ak_client.get_stock_basic_info()
            
            if stock_df.empty:
                logger.warning("未获取到任何A股股票信息，无法进行全量更新")
                return {}
            
            # 提取股票代码列表
            all_stock_codes = stock_df['code'].tolist()
            logger.info(f"成功获取 {len(all_stock_codes)} 只A股股票代码，开始进行全量更新")
            
            # 将所有股票代码添加到已请求集合中
            requested_stock_codes.update(all_stock_codes)
            
            update_results = {}
            total_stocks = len(all_stock_codes)
            
            # 遍历每个股票代码并更新数据
            for idx, stock_code in enumerate(all_stock_codes):
                try:
                    if idx % 100 == 0:
                        logger.info(f"更新进度: {idx+1}/{total_stocks} ({(idx+1)/total_stocks*100:.1f}%)")
                        
                    success = await update_stock_data_incrementally(stock_code)
                    update_results[stock_code] = success
                    logger.debug(f"股票 {stock_code} 更新{'成功' if success else '失败'}")
                except Exception as e:
                    logger.error(f"更新股票 {stock_code} 数据时出错: {str(e)}", exc_info=True)
                    update_results[stock_code] = False
                # 添加短暂延迟避免API限流
                # 已从0.5秒减少到0.2秒以提高性能，同时仍保持一定的限流保护
                await asyncio.sleep(0.2)
            
            last_full_update_time = datetime.now()
            
            successful_updates = sum(1 for success in update_results.values() if success)
            logger.info(f"股票数据全量更新完成，成功更新 {successful_updates}/{len(update_results)} 只股票")
            
            return update_results
        except Exception as e:
            logger.error(f"更新所有A股股票数据时出错: {str(e)}", exc_info=True)
            return {}
            return {}

@app.post("/api/stocks/save")
async def save_stock_data(request: StockDataRequest, background_tasks: BackgroundTasks):
    """
    获取并保存股票数据到数据库
    """
    try:
        # 获取数据库会话
        db = SessionLocal()
        
        try:
            # 将请求的股票代码添加到已请求集合
            for stock_code in request.stock_codes:
                requested_stock_codes.add(stock_code)
            
            results = ak_client.batch_get_stock_daily_data(
                stock_codes=request.stock_codes,
                start_date=request.start_date,
                end_date=request.end_date
            )
            
            save_results = {}
            for stock_code, df in results.items():
                if not df.empty:
                    # 保存数据到数据库，正确传递数据库会话
                    success = db_storage.save_stock_daily_data(db, stock_code, df)
                    save_results[stock_code] = {"success": success, "rows": len(df)}
                    
                    # 如果数据可能过时，在后台更新
                    if await is_data_outdated(stock_code):
                        background_tasks.add_task(update_stock_data_incrementally, stock_code)
                else:
                    save_results[stock_code] = {"success": False, "rows": 0, "message": "无数据"}
            
            return save_results
        finally:
            # 确保数据库会话关闭
            db.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存股票数据失败: {str(e)}")

@app.get("/api/analysis/{stock_code}/patterns")
async def analyze_stock_patterns(stock_code: str, days: int = 100):
    """分析股票价格模式"""
    try:
        # 从数据库获取历史数据
        df = db_storage.get_stock_daily_data(stock_code)
        
        # 如果数据库中没有，尝试从API获取
        if df.empty:
            # 计算日期范围
            import datetime
            end_date = datetime.datetime.now().strftime('%Y%m%d')
            start_date = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime('%Y%m%d')
            df = ak_client.get_stock_daily_data(stock_code, start_date, end_date)
        
        if df.empty:
            raise HTTPException(status_code=404, detail="无法获取股票数据")
        
        # 使用analyzer进行模式识别
        patterns = analyzer.recognize_patterns(df)
        
        return {"stock_code": stock_code, "patterns": patterns}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")

@app.post("/api/analysis/predict")
async def predict_stock_movement(request: AnalysisRequest):
    """预测股票未来走势"""
    try:
        # 从数据库获取历史数据
        df = db_storage.get_stock_daily_data(request.stock_code)
        
        # 如果数据库中没有，尝试从API获取
        if df.empty:
            # 计算日期范围（获取足够的数据）
            import datetime
            end_date = datetime.datetime.now().strftime('%Y%m%d')
            start_date = (datetime.datetime.now() - datetime.timedelta(days=request.days_ahead * 10)).strftime('%Y%m%d')
            df = ak_client.get_stock_daily_data(request.stock_code, start_date, end_date)
        
        if df.empty:
            raise HTTPException(status_code=404, detail="无法获取股票数据")
        
        # 使用analyzer进行预测
        prediction = analyzer.predict_price_movement(df, request.days_ahead)
        
        return {"stock_code": request.stock_code, "prediction": prediction}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"预测失败: {str(e)}")

@app.get("/api/stocks/{stock_code}/financial")
async def get_stock_financial(stock_code: str):
    """获取股票财务指标"""
    try:
        # 尝试从数据库获取
        df = db_storage.get_stock_financial_indicators(stock_code)
        
        # 如果数据库中没有，尝试从API获取
        if df.empty:
            df = ak_client.get_stock_financial_indicators(stock_code)
        
        if df.empty:
            return {"data": [], "message": "未找到财务数据"}
        
        # 处理日期列以确保可序列化
        df_serializable = df.copy()
        for col in df_serializable.columns:
            if pd.api.types.is_datetime64_any_dtype(df_serializable[col]):
                df_serializable[col] = df_serializable[col].astype(str)
        
        return {"data": df_serializable.to_dict('records'), "message": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取财务指标失败: {str(e)}")

@app.get("/api/trade-dates")
async def get_trade_dates(start_date: str, end_date: str):
    """获取交易日历"""
    try:
        dates = ak_client.get_trade_dates(start_date, end_date)
        return {"dates": dates}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取交易日历失败: {str(e)}")

@app.post("/api/stocks/update")
async def force_update_stocks(background_tasks: BackgroundTasks):
    """强制更新所有已请求过的股票数据"""
    background_tasks.add_task(update_all_stocks_data)
    return {
        "status": "started",
        "message": f"已开始后台更新 {len(requested_stock_codes)} 只股票数据",
        "stocks_count": len(requested_stock_codes)
    }

@app.post("/api/stocks/{stock_code}/update")
async def update_single_stock(stock_code: str):
    """
    更新单只股票数据
    """
    try:
        # 添加到请求过的股票列表
        requested_stock_codes.add(stock_code)
        # 调用update_stock_data_incrementally，该函数现在已正确处理数据库会话
        await update_stock_data_incrementally(stock_code)
        return {"status": "success", "message": f"股票 {stock_code} 数据更新成功"}
    except Exception as e:
        print(f"更新股票 {stock_code} 失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"股票 {stock_code} 数据更新失败: {str(e)}")

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
    
    # 检查一些关键股票的数据时效性
    sample_stocks = list(requested_stock_codes)[:5]  # 最多检查5只股票
    stock_status = {}
    for stock_code in sample_stocks:
        is_outdated = await is_data_outdated(stock_code)
        stock_status[stock_code] = "up_to_date" if not is_outdated else "needs_update"
    
    return {
        "requested_stocks_count": len(requested_stock_codes),
        "last_update": update_info,
        "sample_stocks_status": stock_status
    }

@app.get("/api/health")
async def health_check():
    """健康检查端点"""
    # 检查数据库连接
    db_connected = db_storage.check_connection()
    
    # 检查akshare是否可用
    ak_available = True
    try:
        # 尝试一个简单的akshare调用检查可用性
        ak_client.get_trade_dates(datetime.now().strftime('%Y%m%d'), datetime.now().strftime('%Y%m%d'))
    except:
        ak_available = False
    
    # 检查数据更新状态
    data_status = "up_to_date"
    if requested_stock_codes:
        # 检查第一只股票的数据是否过时
        first_stock = next(iter(requested_stock_codes))
        if await is_data_outdated(first_stock):
            data_status = "needs_update"
    
    return {
        "status": "healthy" if db_connected and ak_available else "degraded",
        "services": {
            "akshare": "available" if ak_available else "unavailable",
            "database": db_connected,
            "analyzer": "available" if hasattr(analyzer, 'available') and analyzer.available else "available",
            "data_status": data_status
        },
        "last_full_update": last_full_update_time.strftime('%Y-%m-%d %H:%M:%S') if last_full_update_time else None,
        "tracked_stocks": len(requested_stock_codes)
    }

@app.get("/api/schedule/test")
async def test_scheduled_task():
    """
    测试定时任务功能的接口
    立即执行一次update_all_stocks_data函数，用于验证定时任务机制是否正常工作
    """
    try:
        logger.info(f"[{datetime.now()}] 开始测试定时任务功能，立即执行数据更新...")
        
        # 立即在后台执行数据更新任务
        import threading
        def run_update_task():
            try:
                asyncio.run(update_all_stocks_data())
                logger.info(f"[{datetime.now()}] 测试定时任务执行完成")
            except Exception as e:
                logger.error(f"[{datetime.now()}] 测试定时任务执行失败: {str(e)}", exc_info=True)
        
        # 在新线程中执行异步任务
        task_thread = threading.Thread(target=run_update_task, daemon=True)
        task_thread.start()
        
        return {
            "status": "success",
            "message": "测试定时任务已启动，将在后台执行数据更新",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"测试定时任务失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"测试定时任务失败: {str(e)}")


# 启动定时更新任务
def start_scheduled_updates():
    """启动后台定时更新任务"""
    logger.info("配置股票数据定时更新任务...")
    
    # 每天开盘前更新数据（9:00）
    schedule.every().day.at("09:00").do(lambda: asyncio.run(update_all_stocks_data()))
    logger.info("- 已配置：每天09:00（开盘前）更新所有A股股票数据")
    
    # 交易时段每2小时更新一次（10:30, 13:30）
    schedule.every().day.at("10:30").do(lambda: asyncio.run(update_all_stocks_data()))
    schedule.every().day.at("13:30").do(lambda: asyncio.run(update_all_stocks_data()))
    logger.info("- 已配置：交易时段每2小时更新一次所有A股股票数据")
    
    # 每天交易结束后更新数据（15:45）
    schedule.every().day.at("15:45").do(lambda: asyncio.run(update_all_stocks_data()))
    logger.info("- 已配置：每天15:45（收盘后）更新所有A股股票数据")
    
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

# 启动时更新任务
@app.on_event("startup")
async def startup_event():
    """应用启动时执行的任务"""
    logger.info("股票分析API服务启动中...")
    
    # 初始化时获取并加载所有A股股票代码
    try:
        logger.info("正在初始化加载所有A股股票代码...")
        stock_df = ak_client.get_stock_basic_info()
        
        if not stock_df.empty:
            all_stock_codes = stock_df['code'].tolist()
            requested_stock_codes.update(all_stock_codes)
            logger.info(f"成功加载 {len(all_stock_codes)} 只A股股票代码")
        else:
            logger.warning("未能加载A股股票代码，将在首次更新时尝试获取")
    except Exception as e:
        logger.error(f"加载A股股票代码时出错: {str(e)}", exc_info=True)
    
    # 启动定时更新任务
    start_scheduled_updates()
    
    logger.info("股票分析API服务启动完成")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)