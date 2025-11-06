import sys
import os
import pandas as pd
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入需要的模块
try:
    import akshare as ak
    print("akshare库已安装")
    print(f"akshare版本: {ak.__version__}")
    AK_SHARE_AVAILABLE = True
except ImportError:
    print("警告: akshare库未安装")
    AK_SHARE_AVAILABLE = False

# 导入项目模块
from data_fetching.akshare_client import AkshareClient
from data_processing.data_processor import DataProcessor
from database.connection import get_db
from data_storage.db_storage import DBStorage

def test_akshare_directly():
    """直接测试akshare获取数据"""
    print("\n=== 直接测试akshare获取数据 ===")
    if not AK_SHARE_AVAILABLE:
        print("跳过直接测试，akshare不可用")
        return None
    
    try:
        # 测试获取单只股票数据

        stock_szse_area_summary_df = ak.stock_szse_area_summary(date="202412")
        print(stock_szse_area_summary_df)
        stock_code = "000001"
        adjusted_code = stock_code + ".SZ"
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
        end_date = datetime.now().strftime('%Y%m%d')


        
        print(f"测试获取股票 {stock_code} 数据，日期范围: {start_date} 到 {end_date}")
        df = ak.stock_zh_a_hist(
            symbol=stock_code,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust="qfq"
        )
        
        print(f"原始数据形状: {df.shape}")
        print("原始数据列名:", df.columns.tolist())
        if not df.empty:
            print("原始数据前5行:")
            print(df.head())
        
        return df
    except Exception as e:
        print(f"直接调用akshare出错: {e}")
        return None

def test_akshare_client():
    """测试AkshareClient类获取数据"""
    print("\n=== 测试AkshareClient类获取数据 ===")
    client = AkshareClient()
    
    # 测试获取股票基本信息
    print("\n测试获取股票基本信息:")
    stock_basic = client.get_stock_basic_info()
    print(f"基本信息数据形状: {stock_basic.shape}")
    print("基本信息前3行:")
    print(stock_basic.head(3))
    
    # 测试获取股票日线数据
    print("\n测试获取股票日线数据:")
    stock_code = "000001"
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
    end_date = datetime.now().strftime('%Y%m%d')
    
    daily_data = client.get_stock_daily_data(stock_code, start_date, end_date)
    print(f"日线数据形状: {daily_data.shape}")
    print("日线数据列名:", daily_data.columns.tolist())
    if not daily_data.empty:
        print("日线数据前5行:")
        print(daily_data.head())
    
    return daily_data

def test_data_processor(daily_data):
    """测试数据处理功能"""
    if daily_data is None or daily_data.empty:
        print("\n跳过数据处理测试，无数据可用")
        return None
    
    print("\n=== 测试数据处理功能 ===")
    processor = DataProcessor()
    
    # 测试清洗数据
    cleaned_data = processor.clean_stock_daily_data(daily_data)
    print(f"清洗后数据形状: {cleaned_data.shape}")
    print("清洗后数据列名:", cleaned_data.columns.tolist())
    if not cleaned_data.empty:
        print("清洗后数据前5行:")
        print(cleaned_data.head())
    
    # 测试准备数据库格式
    stock_code = "000001"
    db_records = processor.prepare_stock_for_db(cleaned_data, stock_code)
    print(f"准备的数据库记录数量: {len(db_records)}")
    if db_records:
        print("前2条记录示例:")
        for i, record in enumerate(db_records[:2]):
            print(f"记录 {i+1}: {record}")
    
    return db_records

def test_database_storage(records):
    """测试数据库存储功能"""
    if not records:
        print("\n跳过数据库存储测试，无记录可用")
        return False
    
    print("\n=== 测试数据库存储功能 ===")
    db_storage = DBStorage()
    db = next(get_db())
    
    try:
        stock_code = "000001"
        success = db_storage.save_stock_daily_data(db, stock_code, records)
        print(f"保存结果: {'成功' if success else '失败'}")
        
        # 验证数据是否保存成功
        from datetime import datetime, date
        start_date = (datetime.now() - timedelta(days=30)).date()
        end_date = datetime.now().date()
        
        saved_data = db_storage.get_stock_daily_data(db, stock_code, start_date, end_date)
        print(f"从数据库读取的记录数量: {len(saved_data) if saved_data else 0}")
        
        return success
    except Exception as e:
        print(f"数据库操作出错: {e}")
        return False
    finally:
        db.close()

def main():
    print("开始测试akshare数据获取和存储流程...")
    
    # 1. 直接测试akshare
    direct_df = test_akshare_directly()
    
    # 2. 测试AkshareClient
    client_df = test_akshare_client()
    
    # 3. 测试数据处理
    records = test_data_processor(client_df)
    
    # 4. 测试数据库存储
    db_success = test_database_storage(records)
    
    print("\n=== 测试完成 ===")
    print(f"akshare可用: {AK_SHARE_AVAILABLE}")
    print(f"数据获取: {'成功' if client_df is not None and not client_df.empty else '失败'}")
    print(f"数据处理: {'成功' if records else '失败'}")
    print(f"数据存储: {'成功' if db_success else '失败'}")

if __name__ == "__main__":
    main()