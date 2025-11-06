from typing import List, Dict, Any, Union
import pandas as pd
from datetime import datetime
from sqlalchemy.orm import Session
from database.models import StockBasicInfo, StockDailyData, StockFinancialIndicators, Stock
from database.connection import engine, Base


class DBStorage:
    """数据库存储类，用于处理与数据库相关的操作"""
    
    def __init__(self):
        """初始化数据库存储类"""
        # 确保数据库表已创建
        Base.metadata.create_all(bind=engine)
    
    def save_stock_basic_info(self, db: Session, stock_data: Union[List[Dict[str, Any]], pd.DataFrame]):
        """保存股票基本信息
        
        Args:
            db: 数据库会话
            stock_data: 股票基本信息，可以是字典列表或pandas DataFrame
            
        Returns:
            保存是否成功
        """
        try:
            # 确保表已创建
            Base.metadata.create_all(bind=engine)
            
            # 处理不同类型的输入数据
            items = []
            if isinstance(stock_data, pd.DataFrame):
                # 检查DataFrame是否为空
                if stock_data.empty:
                    return True
                df = stock_data
                # 转换DataFrame为字典列表
                items = df.to_dict('records')
            else:
                # 直接使用列表
                items = stock_data
            
            # 批量保存股票基本信息
            for item in items:
                # 尝试查找现有记录
                existing_stock = db.query(Stock).filter(Stock.stock_code == item['code']).first()
                
                if existing_stock:
                    # 更新现有记录
                    existing_stock.stock_name = item.get('name', existing_stock.stock_name)
                    existing_stock.market = item.get('market', existing_stock.market)
                    existing_stock.industry = item.get('industry', existing_stock.industry)
                    existing_stock.area = item.get('area', existing_stock.area)
                    existing_stock.list_date = item.get('list_date', existing_stock.list_date)
                else:
                    # 创建新记录
                    stock = Stock(
                        stock_code=item['code'],
                        stock_name=item.get('name', ''),
                        market=item.get('market', ''),
                        industry=item.get('industry', ''),
                        area=item.get('area', ''),
                        list_date=item.get('list_date', None)
                    )
                    db.add(stock)
            
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            print(f"保存股票基本信息失败: {e}")
            return False
    
    def save_stock_daily_data(self, db: Session, stock_code: str, daily_data: Union[List[Dict[str, Any]], pd.DataFrame]):
        """保存股票日线数据
        
        Args:
            db: 数据库会话
            stock_code: 股票代码
            daily_data: 日线数据，可以是字典列表或pandas DataFrame
            
        Returns:
            保存是否成功
        """
        try:
            # 处理不同类型的输入数据
            items = []
            if isinstance(daily_data, pd.DataFrame):
                # 检查DataFrame是否为空
                if daily_data.empty:
                    return True
                df = daily_data
                # 转换DataFrame为字典列表
                items = df.to_dict('records')
            else:
                # 直接使用列表
                items = daily_data
            
            # 批量保存日线数据
            for item in items:
                # 确保日期格式正确
                trade_date = item['trade_date']
                if isinstance(trade_date, str):
                    trade_date = datetime.strptime(trade_date, '%Y%m%d').date()
                
                # 尝试查找现有记录
                existing_data = db.query(StockDailyData).filter(
                    StockDailyData.stock_code == stock_code,
                    StockDailyData.trade_date == trade_date
                ).first()
                
                if existing_data:
                    # 更新现有记录
                    existing_data.open_price = float(item.get('open_price', existing_data.open_price))
                    existing_data.high_price = float(item.get('high_price', existing_data.high_price))
                    existing_data.low_price = float(item.get('low_price', existing_data.low_price))
                    existing_data.close_price = float(item.get('close_price', existing_data.close_price))
                    existing_data.volume = float(item.get('volume', existing_data.volume))
                    existing_data.amount = float(item.get('amount', existing_data.amount))
                    existing_data.change_percent = float(item.get('change_percent', existing_data.change_percent))
                    existing_data.turnover_rate = float(item.get('turnover_rate', existing_data.turnover_rate))
                else:
                    # 创建新记录
                    daily = StockDailyData(
                        stock_code=stock_code,
                        trade_date=trade_date,
                        open_price=float(item.get('open_price', 0)),
                        high_price=float(item.get('high_price', 0)),
                        low_price=float(item.get('low_price', 0)),
                        close_price=float(item.get('close_price', 0)),
                        volume=float(item.get('volume', 0)),
                        amount=float(item.get('amount', 0)),
                        change_percent=float(item.get('change_percent', 0)),
                        turnover_rate=float(item.get('turnover_rate', 0))
                    )
                    db.add(daily)
            
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            print(f"保存股票{stock_code}日线数据失败: {e}")
            return False
    
    def save_stock_financial_indicators(self, db: Session, stock_code: str, financial_data: Union[Dict[str, Any], Dict[str, pd.DataFrame]]):
        """保存股票财务指标
        
        Args:
            db: 数据库会话
            stock_code: 股票代码
            financial_data: 财务指标数据，可以是字典或包含DataFrame的字典
            
        Returns:
            保存是否成功
        """
        try:
            # 处理不同类型的输入数据
            indicators = {}
            
            # 如果是包含DataFrame的字典（来自akshare_client）
            if 'valuation' in financial_data and isinstance(financial_data['valuation'], pd.DataFrame):
                valuation_df = financial_data['valuation']
                
                # 处理pandas DataFrame
                if valuation_df.empty:
                    return True
                df = valuation_df
                
                # 提取第一个记录（假设只有一条记录对应指定股票）
                if not df.empty:
                    row = df.iloc[0]
                    # 映射常见的列名
                    indicators['pe'] = float(row.get('市盈率-动态', row.get('pe', 0)))
                    indicators['pe_ttm'] = float(row.get('市盈率-TTM', row.get('pe_ttm', 0)))
                    indicators['pb'] = float(row.get('市净率', row.get('pb', 0)))
                    indicators['ps'] = float(row.get('市销率', row.get('ps', 0)))
                    indicators['ps_ttm'] = float(row.get('市销率-TTM', row.get('ps_ttm', 0)))
                    indicators['pcf'] = float(row.get('市现率', row.get('pcf', 0)))
                    indicators['pcf_ttm'] = float(row.get('市现率-TTM', row.get('pcf_ttm', 0)))
            else:
                # 直接使用字典数据
                indicators = financial_data
            
            # 创建或更新财务指标记录
            indicator = StockFinancialIndicators(
                stock_code=stock_code,
                valuation_date=datetime.now().date(),
                pe=indicators.get('pe', 0),
                pe_ttm=indicators.get('pe_ttm', 0),
                pb=indicators.get('pb', 0),
                ps=indicators.get('ps', 0),
                ps_ttm=indicators.get('ps_ttm', 0),
                pcf=indicators.get('pcf', 0),
                pcf_ttm=indicators.get('pcf_ttm', 0),
                roe=indicators.get('roe', 0),
                revenue=indicators.get('revenue', 0),
                profit=indicators.get('profit', 0)
            )
            
            db.add(indicator)
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            print(f"保存股票{stock_code}财务指标失败: {e}")
            return False
    
    def get_stock_list(self, db: Session):
        """获取所有股票列表"""
        try:
            stocks = db.query(Stock).all()
            return stocks
        except Exception as e:
            print(f"获取股票列表失败: {e}")
            return []
    
    def get_all_stock_codes(self, db: Session, return_dataframe: bool = False):
        """获取所有股票代码
        
        Args:
            db: 数据库会话
            return_dataframe: 是否返回DataFrame
            
        Returns:
            股票代码列表，默认为字典列表，也可返回pandas DataFrame
        """
        try:
            stocks = db.query(Stock).all()
            result = []
            for stock in stocks:
                result.append({
                    'code': stock.stock_code,
                    'name': stock.stock_name,
                    'market': stock.market,
                    'industry': stock.industry
                })
            
            # 根据参数返回不同格式
            if return_dataframe:
                return pd.DataFrame(result)
            
            return result
        except Exception as e:
            print(f"获取所有股票代码失败: {e}")
            if return_dataframe:
                return pd.DataFrame()
            return []
    
    def get_stock_daily_data(self, db_or_stock_code, stock_code=None, start_date=None, end_date=None, 
                           return_dataframe: bool = False):
        """获取股票日线数据
        
        支持两种调用方式：
        1. 传统方式: get_stock_daily_data(db, stock_code, start_date, end_date, return_dataframe)
        2. 简化方式: get_stock_daily_data(stock_code)  # 仅获取股票代码参数
        """
        # 处理参数，支持两种调用方式
        if stock_code is None:
            # 简化调用方式
            from database.connection import SessionLocal
            db = SessionLocal()
            stock_code = db_or_stock_code
            try:
                result = self._get_stock_daily_data_internal(db, stock_code, start_date, end_date, return_dataframe)
                return result
            finally:
                db.close()
        else:
            # 传统调用方式
            db = db_or_stock_code
            return self._get_stock_daily_data_internal(db, stock_code, start_date, end_date, return_dataframe)
            
    def _get_stock_daily_data_internal(self, db: Session, stock_code: str, start_date=None, end_date=None, 
                           return_dataframe: bool = False):
        """获取股票日线数据
        
        Args:
            db: 数据库会话
            stock_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            return_dataframe: 是否返回DataFrame
            
        Returns:
            股票日线数据，默认为字典列表，也可返回pandas DataFrame
        """
        try:
            query = db.query(StockDailyData).filter(StockDailyData.stock_code == stock_code)
            
            if start_date:
                query = query.filter(StockDailyData.trade_date >= start_date)
            if end_date:
                query = query.filter(StockDailyData.trade_date <= end_date)
            
            # 按日期排序
            query = query.order_by(StockDailyData.trade_date.asc())
            
            # 转换为字典列表
            result = []
            for data in query.all():
                result.append({
                    'trade_date': data.trade_date,
                    'open_price': data.open_price,
                    'high_price': data.high_price,
                    'low_price': data.low_price,
                    'close_price': data.close_price,
                    'volume': data.volume,
                    'amount': data.amount,
                    'change_percent': data.change_percent,
                    'turnover_rate': data.turnover_rate
                })
            
            # 根据参数返回不同格式
            if return_dataframe:
                return pd.DataFrame(result)
            
            return result
        except Exception as e:
            print(f"获取股票{stock_code}日线数据失败: {e}")
            if return_dataframe:
                return pd.DataFrame()
            return []
    
    def get_stock_financial_indicators(self, db: Session, stock_code: str, start_date=None, end_date=None, 
                                     return_dataframe: bool = False):
        """获取股票财务指标
        
        Args:
            db: 数据库会话
            stock_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            return_dataframe: 是否返回DataFrame
            
        Returns:
            股票财务指标，默认为字典列表，也可返回pandas DataFrame
        """
        try:
            query = db.query(StockFinancialIndicators).filter(
                StockFinancialIndicators.stock_code == stock_code
            )
            
            if start_date:
                query = query.filter(StockFinancialIndicators.valuation_date >= start_date)
            
            if end_date:
                query = query.filter(StockFinancialIndicators.valuation_date <= end_date)
            
            # 按日期倒序排序
            query = query.order_by(StockFinancialIndicators.valuation_date.desc())
            
            # 转换为字典列表
            result = []
            for data in query.all():
                result.append({
                    'valuation_date': data.valuation_date,
                    'pe': data.pe,
                    'pe_ttm': data.pe_ttm,
                    'pb': data.pb,
                    'ps': data.ps,
                    'ps_ttm': data.ps_ttm,
                    'pcf': data.pcf,
                    'pcf_ttm': data.pcf_ttm,
                    'roe': data.roe,
                    'revenue': data.revenue,
                    'profit': data.profit
                })
            
            # 根据参数返回不同格式
            if return_dataframe:
                return pd.DataFrame(result)
            
            return result
        except Exception as e:
            print(f"获取股票{stock_code}财务指标失败: {e}")
            if return_dataframe:
                return pd.DataFrame()
            return []
    
    def get_latest_stock_date(self, stock_code: str):
        """获取某只股票的最新数据日期
        
        Args:
            stock_code: 股票代码
            
        Returns:
            最新数据的日期对象，如果没有数据则返回None
        """
        from database.connection import SessionLocal
        db = SessionLocal()
        try:
            # 查询该股票的最新交易日期
            latest_data = db.query(StockDailyData).filter(
                StockDailyData.stock_code == stock_code
            ).order_by(StockDailyData.trade_date.desc()).first()
            
            if latest_data:
                return latest_data.trade_date
            return None
        except Exception as e:
            print(f"获取股票{stock_code}最新数据日期失败: {e}")
            return None
        finally:
            db.close()
    
    def check_connection(self):
        """检查数据库连接是否正常
        
        Returns:
            bool: 数据库连接是否正常
        """
        from database.connection import SessionLocal
        try:
            db = SessionLocal()
            # 执行简单查询测试连接
            db.query(Stock).limit(1).all()
            return "connected"
        except Exception as e:
            print(f"数据库连接检查失败: {e}")
            return "disconnected"
        finally:
            if 'db' in locals():
                db.close()
    
    def batch_save_daily_data(self, db: Session, daily_data_list: List[Dict[str, Any]]):
        """批量保存日线数据，提高性能"""
        try:
            # 使用bulk_save_objects批量插入
            db.bulk_save_objects([StockDailyData(**item) for item in daily_data_list])
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            print(f"批量保存日线数据失败: {e}")
            return False