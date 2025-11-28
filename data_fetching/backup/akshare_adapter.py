import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging

from data_fetching.base_client import BaseDataClient

# 配置日志
logger = logging.getLogger(__name__)

# 尝试导入akshare，如果失败则使用模拟数据
try:
    import akshare as ak
    AK_SHARE_AVAILABLE = True
except ImportError:
    AK_SHARE_AVAILABLE = False
    logger.warning("akshare库未安装，将使用模拟数据")


class AKShareClient(BaseDataClient):
    """AKShare适配器，实现BaseDataClient接口"""
    
    def __init__(self):
        super().__init__()
        logger.info(f"AKShare客户端已初始化 - akshare可用: {AK_SHARE_AVAILABLE}")
    
    def _get_stock_basic_info_impl(self) -> pd.DataFrame:
        """获取股票基本信息的具体实现"""
        if AK_SHARE_AVAILABLE:
            # 使用akshare获取股票基本信息
            stock_info = ak.stock_info_a_code_name()
            
            # 检查数据格式并转换为pandas DataFrame
            if isinstance(stock_info, pd.DataFrame):
                return stock_info
            else:
                # 如果不是DataFrame，尝试转换
                return pd.DataFrame(stock_info)
        else:
            # 返回模拟数据
            logger.info("使用模拟股票基本信息数据")
            return self._get_mock_stock_basic_info()
    
    def _get_stock_daily_data_impl(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """获取股票日线数据的具体实现"""
        logger.info(f"开始获取股票{stock_code}数据，日期范围: {start_date} 到 {end_date}")
        if AK_SHARE_AVAILABLE:
            # 转换股票代码格式（如果需要）
            if stock_code.startswith('6'):
                adjusted_code = stock_code + '.SH'  # 上海证券交易所
            else:
                adjusted_code = stock_code + '.SZ'  # 深圳证券交易所
            
            # 使用akshare获取股票历史数据
            try:
                df = ak.stock_zh_a_hist(
                    symbol=stock_code,
                    period="daily",
                    start_date=start_date,
                    end_date=end_date,
                    adjust="qfq"  # 前复权
                )
            except Exception as ak_error:
                logger.error(f"akshare.stock_zh_a_hist调用失败: {str(ak_error)}")
                # 尝试使用不同的接口获取数据
                try:
                    logger.info("尝试使用stock_zh_a_daily接口...")
                    df = ak.stock_zh_a_daily(
                        symbol=adjusted_code,
                        start_date=start_date,
                        end_date=end_date
                    )
                except Exception as ak_error2:
                    logger.error(f"stock_zh_a_daily调用失败: {str(ak_error2)}")
                    # 返回空DataFrame并继续使用模拟数据
                    return self._get_mock_stock_daily_data(stock_code, start_date, end_date)
            
            # 重命名列以符合我们的系统命名规范
            if isinstance(df, pd.DataFrame) and not df.empty:
                # 处理不同版本的akshare返回的不同列名
                column_mapping = {
                    '日期': 'trade_date',
                    '开盘': 'open_price',
                    '最高': 'high_price',
                    '最低': 'low_price',
                    '收盘': 'close_price',
                    '成交量': 'volume',
                    '成交额': 'amount',
                    '换手率': 'turnover_rate',
                    'open': 'open_price',
                    'high': 'high_price',
                    'low': 'low_price',
                    'close': 'close_price',
                    'volume': 'volume',
                    'amount': 'amount'
                }
                
                # 重命名存在的列
                for cn_col, en_col in column_mapping.items():
                    if cn_col in df.columns:
                        df.rename(columns={cn_col: en_col}, inplace=True)
                
                # 添加股票代码列
                df['stock_code'] = stock_code
                
                # 转换日期格式
                date_columns = ['trade_date', '日期', 'date']
                for col in date_columns:
                    if col in df.columns:
                        if col != 'trade_date':
                            df.rename(columns={col: 'trade_date'}, inplace=True)
                        break
                
                # 如果没有找到日期列，尝试将索引转换为日期列
                if 'trade_date' not in df.columns and isinstance(df.index, pd.DatetimeIndex):
                    df['trade_date'] = df.index
                
                # 确保trade_date列存在并转换格式
                if 'trade_date' in df.columns:
                    df['trade_date'] = pd.to_datetime(df['trade_date'])
                    df['trade_date'] = df['trade_date'].dt.strftime('%Y%m%d')
                
                # 按日期排序（从旧到新）
                if 'trade_date' in df.columns:
                    df.sort_values('trade_date', inplace=True)
                
                return df
            else:
                logger.warning("akshare返回空数据或非DataFrame对象")
                return self._get_mock_stock_daily_data(stock_code, start_date, end_date)
        else:
            # 返回模拟数据
            logger.info(f"akshare不可用，使用模拟股票{stock_code}日线数据")
            return self._get_mock_stock_daily_data(stock_code, start_date, end_date)
    
    def _get_stock_financial_indicators_impl(self, stock_code: str) -> pd.DataFrame:
        """获取股票财务指标数据的具体实现"""
        if AK_SHARE_AVAILABLE:
            # 转换股票代码格式
            if stock_code.startswith('6'):
                adjusted_code = 'sh' + stock_code  # 上海证券交易所
            else:
                adjusted_code = 'sz' + stock_code  # 深圳证券交易所
            
            # 使用akshare获取财务指标
            try:
                df = ak.stock_financial_analysis_indicator(stock=adjusted_code)
                return df
            except Exception as e:
                logger.error(f"获取财务指标失败: {str(e)}")
                return pd.DataFrame()
        else:
            # 返回模拟数据
            logger.info("akshare不可用，使用模拟财务指标数据")
            return pd.DataFrame()
    
    def _get_hot_sectors_impl(self) -> pd.DataFrame:
        """获取热点行业板块数据的具体实现"""
        if AK_SHARE_AVAILABLE:
            # 使用akshare获取行业板块实时数据
            # 尝试使用stock_sector_spot函数
            try:
                df = ak.stock_sector_spot()
            except AttributeError:
                # 如果stock_sector_spot也不存在，尝试其他可能的函数名
                try:
                    df = ak.stock_board_industry_name_em()
                except AttributeError:
                    # 如果仍然失败，使用模拟数据
                    logger.warning("akshare中找不到合适的行业板块数据函数，使用模拟数据")
                    return self._get_mock_hot_sectors()
            
            if isinstance(df, pd.DataFrame) and not df.empty:
                # 按涨幅排序，降序排列
                if '涨跌幅' in df.columns:
                    df = df.sort_values('涨跌幅', ascending=False)
                # 重命名列以符合系统命名规范
                column_mapping = {
                    '板块名称': 'sector_name',
                    '涨跌幅': 'change_percent',
                    '领涨股': 'leading_stock',
                    '最新价': 'latest_price',
                    '开盘价': 'open_price',
                    '最高价': 'high_price',
                    '最低价': 'low_price',
                    '成交量': 'volume',
                    '成交额': 'amount'
                }
                
                for cn_col, en_col in column_mapping.items():
                    if cn_col in df.columns:
                        df.rename(columns={cn_col: en_col}, inplace=True)
                
                return df
            else:
                logger.warning("获取行业板块数据失败：返回空数据")
                return self._get_mock_hot_sectors()
        else:
            # 返回模拟热点板块数据
            logger.info("akshare不可用，使用模拟热点板块数据")
            return self._get_mock_hot_sectors()
    
    def _get_concept_sectors_impl(self) -> pd.DataFrame:
        """获取概念板块数据的具体实现"""
        if AK_SHARE_AVAILABLE:
            # 使用重试机制获取概念板块数据
            def fetch_concept_data():
                df = ak.stock_board_concept_name_em()
                if isinstance(df, pd.DataFrame) and not df.empty:
                    return df
                else:
                    raise ValueError("获取概念板块数据失败：返回空数据")
            
            try:
                return self._retry_with_backoff(fetch_concept_data)
            except Exception as e:
                logger.error(f"获取概念板块数据失败: {str(e)}")
                return self._get_mock_concept_sectors()
        else:
            # akshare不可用时返回模拟数据
            logger.info("akshare不可用，使用模拟概念板块数据")
            return self._get_mock_concept_sectors()
    
    def _get_sector_stocks_impl(self, sector_code: str) -> pd.DataFrame:
        """获取指定板块的股票列表的具体实现"""
        if AK_SHARE_AVAILABLE:
            # 使用akshare获取板块内股票列表
            # 不同版本的akshare可能有不同的接口，尝试使用常见的接口
            try:
                df = ak.stock_board_concept_cons_em(symbol=sector_code)
            except:
                # 尝试另一种接口
                try:
                    df = ak.stock_board_industry_cons_ths(symbol=sector_code)
                except:
                    return self._get_mock_sector_stocks()
            
            if isinstance(df, pd.DataFrame) and not df.empty:
                return df
            else:
                return self._get_mock_sector_stocks()
        else:
            # 返回模拟板块股票数据
            logger.info("akshare不可用，使用模拟板块股票数据")
            return self._get_mock_sector_stocks()
    
    # 模拟数据方法
    def _get_mock_stock_basic_info(self) -> pd.DataFrame:
        """提供模拟的股票基本信息数据"""
        mock_data = {
            'code': ['000001', '000002', '600000', '600036'],
            'name': ['平安银行', '万科A', '浦发银行', '招商银行']
        }
        return pd.DataFrame(mock_data)
    
    def _get_mock_stock_daily_data(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """提供模拟的股票日线数据"""
        # 生成一些模拟的日期数据
        dates = pd.date_range(start=start_date, end=end_date, freq='B')
        mock_data = {
            'trade_date': dates.strftime('%Y%m%d'),
            'open_price': [10.0 + i*0.1 for i in range(len(dates))],
            'high_price': [10.2 + i*0.1 for i in range(len(dates))],
            'low_price': [9.9 + i*0.1 for i in range(len(dates))],
            'close_price': [10.1 + i*0.1 for i in range(len(dates))],
            'volume': [1000000 + i*10000 for i in range(len(dates))],
            'amount': [10000000 + i*100000 for i in range(len(dates))],
            'stock_code': [stock_code] * len(dates)
        }
        return pd.DataFrame(mock_data)
    
    def _get_mock_hot_sectors(self) -> pd.DataFrame:
        """提供模拟的热点板块数据"""
        mock_data = {
            'sector_name': ['人工智能', '新能源', '医药生物', '半导体', '金融服务'],
            'change_percent': [3.2, 2.8, 1.5, 4.1, 0.9],
            'leading_stock': ['科大讯飞', '宁德时代', '恒瑞医药', '中芯国际', '招商银行'],
            'latest_price': [65.21, 189.56, 45.78, 52.34, 38.91],
            'volume': [123456789, 98765432, 76543210, 87654321, 65432109],
            'amount': [8145678901, 18695678901, 3502789012, 4584567890, 2545678901]
        }
        return pd.DataFrame(mock_data)
    
    def _get_mock_concept_sectors(self) -> pd.DataFrame:
        """提供模拟的概念板块数据"""
        mock_data = {
            '板块代码': ['BK0577', 'BK0980', 'BK0636', 'BK1024', 'BK0642'],
            '板块名称': ['新能源汽车', '光伏概念', '数字货币', 'ChatGPT', '医疗器械']
        }
        return pd.DataFrame(mock_data)
    
    def _get_mock_sector_stocks(self) -> pd.DataFrame:
        """提供模拟的板块股票数据"""
        mock_data = {
            '代码': ['000001', '000002', '600000', '600036', '000858'],
            '名称': ['平安银行', '万科A', '浦发银行', '招商银行', '五粮液']
        }
        return pd.DataFrame(mock_data)