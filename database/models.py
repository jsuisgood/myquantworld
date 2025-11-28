from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class StockBasicInfo(Base):
    """股票基本信息表"""
    __tablename__ = 'stock_basic_info'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String(20), unique=True, nullable=False, index=True)
    stock_name = Column(String(100), nullable=False)
    industry = Column(String(100))
    area = Column(String(50))
    market = Column(String(20))  # 主板、创业板、科创板等
    list_date = Column(Date)     # 上市日期
    status = Column(String(20), default='正常')
    
    # 关系
    daily_data = relationship("StockDailyData", back_populates="stock_info")
    financial_indicators = relationship("StockFinancialIndicators", back_populates="stock_info")
    
    def __repr__(self):
        return f"<StockBasicInfo(stock_code={self.stock_code}, stock_name={self.stock_name})>"


# 兼容旧代码的Stock类 - 直接使用现有的StockBasicInfo
class Stock(StockBasicInfo):
    """股票基本信息表 - 兼容旧代码使用，继承自StockBasicInfo"""
    # 不需要重新定义列，直接继承StockBasicInfo的所有属性和方法
    pass


class StockDailyData(Base):
    """股票日线数据表"""
    __tablename__ = 'stock_daily_data'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String(20), ForeignKey('stock_basic_info.stock_code'), nullable=False, index=True)
    trade_date = Column(Date, nullable=False, index=True)
    open_price = Column(Float)
    high_price = Column(Float)
    low_price = Column(Float)
    close_price = Column(Float)
    volume = Column(Float)
    amount = Column(Float)
    change_percent = Column(Float)
    turnover_rate = Column(Float)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关系
    stock_info = relationship("StockBasicInfo", back_populates="daily_data")
    
    def __repr__(self):
        return f"<StockDailyData(stock_code={self.stock_code}, trade_date={self.trade_date}, close_price={self.close_price})>"


class StockFinancialIndicators(Base):
    """股票财务指标表"""
    __tablename__ = 'stock_financial_indicators'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String(20), ForeignKey('stock_basic_info.stock_code'), nullable=False, index=True)
    report_date = Column(Date, nullable=False, index=True)
    pe = Column(Float)          # 市盈率
    pb = Column(Float)          # 市净率
    ps = Column(Float)          # 市销率
    roe = Column(Float)         # 净资产收益率
    revenue = Column(Float)     # 营业收入
    profit = Column(Float)      # 净利润
    profit_growth_rate = Column(Float)  # 净利润增长率
    revenue_growth_rate = Column(Float)  # 营业收入增长率
    debt_ratio = Column(Float)  # 资产负债率
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关系
    stock_info = relationship("StockBasicInfo", back_populates="financial_indicators")
    
    def __repr__(self):
        return f"<StockFinancialIndicators(stock_code={self.stock_code}, report_date={self.report_date}, pe={self.pe})>"


class TradingStrategy(Base):
    """交易策略表"""
    __tablename__ = 'trading_strategies'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关系
    trading_signals = relationship("TradingSignal", back_populates="strategy")
    
    def __repr__(self):
        return f"<TradingStrategy(name={self.name}, is_active={self.is_active})>"


class TechnicalAnalysisResult(Base):
    """技术分析结果表"""
    __tablename__ = 'technical_analysis_results'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String(20), nullable=False, index=True)
    analysis_date = Column(Date, nullable=False, index=True)
    indicator_name = Column(String(100), nullable=False)
    indicator_value = Column(Float)
    signal = Column(String(20))  # 买入、卖出、持有等信号
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f"<TechnicalAnalysisResult(stock_code={self.stock_code}, indicator={self.indicator_name}, signal={self.signal})>"


class TradingSignal(Base):
    """交易信号表"""
    __tablename__ = 'trading_signals'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    strategy_id = Column(Integer, ForeignKey('trading_strategies.id'))
    stock_code = Column(String(20), nullable=False, index=True)
    signal_type = Column(String(20), nullable=False)  # 买入、卖出、持有
    signal_date = Column(Date, nullable=False, index=True)
    price = Column(Float)
    reason = Column(Text)
    strength = Column(String(20))  # 弱、中、强
    is_executed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    
    # 关系
    strategy = relationship("TradingStrategy", back_populates="trading_signals")
    
    def __repr__(self):
        return f"<TradingSignal(stock_code={self.stock_code}, signal_type={self.signal_type}, signal_date={self.signal_date})>"


class User(Base):
    """用户表"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f"<User(username={self.username}, email={self.email})>"


class AnalysisTask(Base):
    """分析任务表"""
    __tablename__ = 'analysis_tasks'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_name = Column(String(100), nullable=False)
    task_type = Column(String(50), nullable=False)  # 日度分析、周度分析、自定义分析等
    status = Column(String(20), default='pending')  # pending, running, completed, failed
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    
    def __repr__(self):
        return f"<AnalysisTask(task_name={self.task_name}, status={self.status})>"


class MarketIndex(Base):
    """市场指数表"""
    __tablename__ = 'market_indices'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    index_code = Column(String(20), unique=True, nullable=False, index=True)
    index_name = Column(String(100), nullable=False)
    trade_date = Column(Date, nullable=False, index=True)
    open_price = Column(Float)
    high_price = Column(Float)
    low_price = Column(Float)
    close_price = Column(Float)
    volume = Column(Float)
    amount = Column(Float)
    change_percent = Column(Float)
    created_at = Column(DateTime, default=datetime.now)
    
    def __repr__(self):
        return f"<MarketIndex(index_code={self.index_code}, trade_date={self.trade_date}, close_price={self.close_price})>"


# TuShare专用数据表
class TushareStockBasicInfo(Base):
    """TuShare股票基本信息表"""
    __tablename__ = 'tushare_stock_basic_info'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String(20), unique=True, nullable=False, index=True)
    stock_name = Column(String(100), nullable=False)
    industry = Column(String(100))
    area = Column(String(50))
    market = Column(String(20))  # 主板、创业板、科创板等
    list_date = Column(Date)     # 上市日期
    status = Column(String(20), default='正常')
    source = Column(String(20), default='tushare')  # 数据源标记
    
    # 关系
    daily_data = relationship("TushareStockDailyData", back_populates="stock_info")
    financial_indicators = relationship("TushareStockFinancialIndicators", back_populates="stock_info")
    
    def __repr__(self):
        return f"<TushareStockBasicInfo(stock_code={self.stock_code}, stock_name={self.stock_name})>"


class TushareStockDailyData(Base):
    """TuShare股票日线数据表"""
    __tablename__ = 'tushare_stock_daily_data'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String(20), ForeignKey('tushare_stock_basic_info.stock_code'), nullable=False, index=True)
    trade_date = Column(Date, nullable=False, index=True)
    open_price = Column(Float)
    high_price = Column(Float)
    low_price = Column(Float)
    close_price = Column(Float)
    volume = Column(Float)
    amount = Column(Float)
    change_percent = Column(Float)
    turnover_rate = Column(Float)
    pe = Column(Float)          # 市盈率
    pb = Column(Float)          # 市净率
    ps = Column(Float)          # 市销率
    dv_ratio = Column(Float)    # 股息率
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关系
    stock_info = relationship("TushareStockBasicInfo", back_populates="daily_data")
    
    def __repr__(self):
        return f"<TushareStockDailyData(stock_code={self.stock_code}, trade_date={self.trade_date}, close_price={self.close_price})>"


class TushareStockFinancialIndicators(Base):
    """TuShare股票财务指标表"""
    __tablename__ = 'tushare_stock_financial_indicators'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String(20), ForeignKey('tushare_stock_basic_info.stock_code'), nullable=False, index=True)
    report_date = Column(Date, nullable=False, index=True)
    pe = Column(Float)          # 市盈率
    pb = Column(Float)          # 市净率
    ps = Column(Float)          # 市销率
    roe = Column(Float)         # 净资产收益率
    revenue = Column(Float)     # 营业收入
    profit = Column(Float)      # 净利润
    profit_growth_rate = Column(Float)  # 净利润增长率
    revenue_growth_rate = Column(Float)  # 营业收入增长率
    debt_ratio = Column(Float)  # 资产负债率
    operating_cash_flow = Column(Float)  # 经营现金流
    total_assets = Column(Float)  # 总资产
    total_liabilities = Column(Float)  # 总负债
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关系
    stock_info = relationship("TushareStockBasicInfo", back_populates="financial_indicators")
    
    def __repr__(self):
        return f"<TushareStockFinancialIndicators(stock_code={self.stock_code}, report_date={self.report_date}, pe={self.pe})>"
