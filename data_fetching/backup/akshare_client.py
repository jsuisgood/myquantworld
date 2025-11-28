import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 尝试导入akshare，如果失败则使用模拟数据
try:
    import akshare as ak
    AK_SHARE_AVAILABLE = True
except ImportError:
    AK_SHARE_AVAILABLE = False
    logger.warning("akshare库未安装，将使用模拟数据")


class AkshareClient:
    """Akshare API客户端，用于获取股票数据"""
    
    def __init__(self):
        self._max_retries = 3
        self._retry_delay = 2  # 重试间隔时间（秒）
        print(f"Akshare客户端已初始化 - akshare可用: {AK_SHARE_AVAILABLE}")
    
    def get_stock_basic_info(self) -> pd.DataFrame:
        """获取股票基本信息，仅支持pandas DataFrame返回"""
        try:
            if AK_SHARE_AVAILABLE:
                # 使用akshare获取股票基本信息
                stock_info = ak.stock_info_a_code_name()
                
                # 检查数据格式并转换为pandas DataFrame（akshare默认返回pandas DataFrame）
                if isinstance(stock_info, pd.DataFrame):
                    return stock_info
                else:
                    # 如果不是DataFrame，尝试转换
                    return pd.DataFrame(stock_info)
            else:
                # 返回模拟数据
                logger.info("使用模拟股票基本信息数据")
                mock_data = {
                    'code': ['000001', '000002', '600000', '600036'],
                    'name': ['平安银行', '万科A', '浦发银行', '招商银行']
                }
                return pd.DataFrame(mock_data)
        except Exception as e:
            logger.error(f"获取股票基本信息失败: {str(e)}")
            # 返回模拟数据作为备选
            mock_data = {
                'code': ['000001', '000002', '600000', '600036'],
                'name': ['平安银行', '万科A', '浦发银行', '招商银行']
            }
            return pd.DataFrame(mock_data)
    
    def get_stock_daily_data(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """获取股票日线数据，仅返回pandas DataFrame"""
        print(f"开始获取股票{stock_code}数据，日期范围: {start_date} 到 {end_date}")
        try:
            if AK_SHARE_AVAILABLE:
                # 转换股票代码格式（如果需要）
                if stock_code.startswith('6'):
                    adjusted_code = stock_code + '.SH'  # 上海证券交易所
                else:
                    adjusted_code = stock_code + '.SZ'  # 深圳证券交易所
                
                print(f"使用akshare获取数据，调整后的代码: {adjusted_code}")
                print(f"使用akshare获取数据，使用的代码: {stock_code}")
                # 使用akshare获取股票历史数据
                try:
                    df = ak.stock_zh_a_hist(
                        symbol=stock_code,
                        period="daily",
                        start_date=start_date,
                        end_date=end_date,
                        adjust="qfq"  # 前复权
                    )
                    print(f"akshare返回数据形状: {df.shape if isinstance(df, pd.DataFrame) else '非DataFrame'}")
                except Exception as ak_error:
                    print(f"akshare.stock_zh_a_hist调用失败: {str(ak_error)}")
                    # 尝试使用不同的接口获取数据
                    try:
                        print("尝试使用stock_zh_a_daily接口...")
                        df = ak.stock_zh_a_daily(
                            symbol=adjusted_code,
                            start_date=start_date,
                            end_date=end_date
                        )
                        print(f"stock_zh_a_daily返回数据形状: {df.shape if isinstance(df, pd.DataFrame) else '非DataFrame'}")
                    except Exception as ak_error2:
                        print(f"stock_zh_a_daily调用失败: {str(ak_error2)}")
                        # 返回空DataFrame并继续使用模拟数据
                        return pd.DataFrame()
                
                # 重命名列以符合我们的系统命名规范
                if isinstance(df, pd.DataFrame) and not df.empty:
                    print(f"原始数据列名: {df.columns.tolist()}")
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
                            print(f"找到日期列: {col}")
                            if col != 'trade_date':
                                df.rename(columns={col: 'trade_date'}, inplace=True)
                            break
                    
                    # 如果没有找到日期列，尝试将索引转换为日期列（对于某些接口）
                    if 'trade_date' not in df.columns and isinstance(df.index, pd.DatetimeIndex):
                        print("使用索引作为trade_date列")
                        df['trade_date'] = df.index
                    
                    # 确保trade_date列存在并转换格式
                    if 'trade_date' in df.columns:
                        df['trade_date'] = pd.to_datetime(df['trade_date'])
                        df['trade_date'] = df['trade_date'].dt.strftime('%Y%m%d')
                    
                    # 按日期排序（从旧到新）
                    if 'trade_date' in df.columns:
                        df.sort_values('trade_date', inplace=True)
                    
                    print(f"处理后的数据形状: {df.shape}")
                    print(f"处理后的数据列名: {df.columns.tolist()}")
                    if not df.empty:
                        print("处理后的数据前3行:")
                        print(df.head(3))
                    
                    return df
                else:
                    print("akshare返回空数据或非DataFrame对象")
                    return pd.DataFrame()
            else:
                # 返回模拟数据
                print(f"akshare不可用，使用模拟股票{stock_code}日线数据")
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
        except Exception as e:
            print(f"获取股票{stock_code}日线数据失败: {str(e)}")
            logger.error(f"获取股票{stock_code}日线数据失败: {str(e)}")
            # 返回模拟数据作为备选
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
    
    def get_stock_financial_indicators(self, stock_code: str) -> pd.DataFrame:
        """获取股票财务指标数据，仅返回pandas DataFrame"""
        try:
            if AK_SHARE_AVAILABLE:
                # 转换股票代码格式
                if stock_code.startswith('6'):
                    adjusted_code = 'sh' + stock_code  # 上海证券交易所
                else:
                    adjusted_code = 'sz' + stock_code  # 深圳证券交易所
                
                # 使用akshare获取财务指标
                df = ak.stock_financial_analysis_indicator(stock=adjusted_code)
                
                if isinstance(df, pd.DataFrame) and not df.empty:
                    # 处理数据格式
                    # 假设df已经是符合要求的格式
                    # 添加股票代码列
                    df['stock_code'] = stock_code
                    return df
                else:
                    return pd.DataFrame()
            else:
                # 返回模拟财务数据
                logger.info(f"使用模拟股票{stock_code}财务指标数据")
                mock_data = {
                    'code': [stock_code] * 4,
                    'name': ['模拟财务数据'] * 4,
                    '指标': ['每股收益', '净资产收益率', '资产负债率', '毛利率'],
                    '2023': [1.2, 0.08, 0.45, 0.3],
                    '2022': [1.0, 0.07, 0.43, 0.28],
                    '2021': [0.9, 0.06, 0.41, 0.26],
                    '2020': [0.8, 0.05, 0.40, 0.25]
                }
                return pd.DataFrame(mock_data)
        except Exception as e:
            logger.error(f"获取股票{stock_code}财务指标失败: {str(e)}")
            # 返回模拟财务数据作为备选
            mock_data = {
                'code': [stock_code] * 4,
                'name': ['模拟财务数据'] * 4,
                '指标': ['每股收益', '净资产收益率', '资产负债率', '毛利率'],
                '2023': [1.2, 0.08, 0.45, 0.3],
                '2022': [1.0, 0.07, 0.43, 0.28],
                '2021': [0.9, 0.06, 0.41, 0.26],
                '2020': [0.8, 0.05, 0.40, 0.25]
            }
            return pd.DataFrame(mock_data)
    
    def batch_get_stock_daily_data(self, stock_codes: List[str], start_date: str, end_date: str) -> Dict[str, pd.DataFrame]:
        """批量获取多个股票的日线数据
        
        Args:
            stock_codes: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
        
        Returns:
            字典，键为股票代码，值为对应的日线数据DataFrame
        """
        results = {}
        for stock_code in stock_codes:
            try:
                print(f"正在获取股票{stock_code}的数据...")
                # 获取单只股票数据
                df = self.get_stock_daily_data(stock_code, start_date, end_date)
                results[stock_code] = df
                # 避免请求过快
                # 已从0.1秒减少到0.05秒以提高性能，同时仍保持基本的限流保护
                import time
                time.sleep(0.05)
            except Exception as e:
                print(f"获取股票{stock_code}数据失败: {str(e)}")
                results[stock_code] = pd.DataFrame()
        return results
        
    def get_trade_dates(self, start_date: str, end_date: str) -> List[str]:
        """获取指定日期范围内的交易日历
        
        Args:
            start_date: 开始日期，格式'YYYY-MM-DD'
            end_date: 结束日期，格式'YYYY-MM-DD'
        
        Returns:
            交易日列表，每个元素为日期字符串
        """
        try:
            if AK_SHARE_AVAILABLE:
                import akshare as ak
                # 使用akshare获取交易日历
                # 上海证券交易所交易日历
                df = ak.tool_trade_date_hist_sina()
                
                # 将日期列转换为datetime类型
                df['trade_date'] = pd.to_datetime(df['trade_date'])
                
                # 过滤指定日期范围
                start = pd.to_datetime(start_date)
                end = pd.to_datetime(end_date)
                filtered_df = df[(df['trade_date'] >= start) & (df['trade_date'] <= end)]
                
                # 返回日期字符串列表
                return filtered_df['trade_date'].dt.strftime('%Y%m%d').tolist()
            else:
                # 模拟数据：生成工作日列表作为交易日
                start = pd.to_datetime(start_date)
                end = pd.to_datetime(end_date)
                date_range = pd.date_range(start=start, end=end)
                
                # 过滤工作日（周一到周五）
                weekdays = date_range[date_range.weekday < 5]
                
                # 返回日期字符串列表
                return weekdays.strftime('%Y%m%d').tolist()
        except Exception as e:
            print(f"获取交易日历失败: {str(e)}")
            # 出错时返回空列表
            return []
    
    def get_index_data(self, index_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """获取指数数据，仅返回pandas DataFrame"""
        try:
            # 根据指数代码获取对应的akshare接口
            if index_code.startswith('000'):
                adjusted_code = 'sh' + index_code  # 上证指数系列
            elif index_code.startswith('399'):
                adjusted_code = 'sz' + index_code  # 深圳指数系列
            else:
                adjusted_code = index_code  # 默认情况
            
            # 使用akshare获取指数数据
            df = ak.stock_zh_index_daily(symbol=adjusted_code)
            
            if isinstance(df, pd.DataFrame) and not df.empty:
                # 过滤日期范围
                df['date'] = pd.to_datetime(df['date'])
                mask = (df['date'] >= start_date) & (df['date'] <= end_date)
                df = df[mask]
                
                # 重命名列以符合我们的系统命名规范
                column_mapping = {
                    'date': 'trade_date',
                    'open': 'open_price',
                    'high': 'high_price',
                    'low': 'low_price',
                    'close': 'close_price',
                    'volume': 'volume',
                    'amount': 'amount'
                }
                
                for cn_col, en_col in column_mapping.items():
                    if cn_col in df.columns:
                        df.rename(columns={cn_col: en_col}, inplace=True)
                
                # 添加指数代码列
                df['index_code'] = index_code
                
                # 转换日期格式
                if 'trade_date' in df.columns:
                    df['trade_date'] = df['trade_date'].dt.strftime('%Y%m%d')
                
                # 按日期排序
                if 'trade_date' in df.columns:
                    df.sort_values('trade_date', inplace=True)
                
                return df
            else:
                return pd.DataFrame()
        except Exception as e:
            print(f"获取指数{index_code}数据失败: {str(e)}")
            return pd.DataFrame()
    
    def get_trade_dates(self, start_date: str, end_date: str) -> List[str]:
        """获取指定日期范围内的交易日历"""
        try:
            # 使用上证指数的数据来获取交易日历
            df = self.get_index_data('000001', start_date, end_date)
            
            if isinstance(df, pd.DataFrame) and not df.empty and 'trade_date' in df.columns:
                return sorted(df['trade_date'].tolist())
            else:
                return []
        except Exception as e:
            print(f"获取交易日历失败: {str(e)}")
            return []
    
    def get_stock_sector(self) -> pd.DataFrame:
        """获取股票行业分类数据"""
        try:
            # 使用akshare获取股票行业分类
            df = ak.stock_board_industry_name_ths()
            
            if isinstance(df, pd.DataFrame) and not df.empty:
                return df
            else:
                return pd.DataFrame()
        except Exception as e:
            print(f"获取股票行业分类失败: {str(e)}")
            return pd.DataFrame()
    
    def get_hot_sectors(self) -> pd.DataFrame:
        """获取热点行业板块数据，根据涨幅排序
        
        Returns:
            包含板块名称、涨幅、领涨股等信息的DataFrame
        """
        try:
            if AK_SHARE_AVAILABLE:
                # 使用akshare获取行业板块实时数据
                # 尝试使用stock_sector_spot函数代替不存在的stock_board_industry_spot
                try:
                    df = ak.stock_sector_spot()
                except AttributeError:
                    # 如果stock_sector_spot也不存在，尝试其他可能的函数名
                    try:
                        df = ak.stock_board_industry_name_em()
                    except AttributeError:
                        # 如果仍然失败，使用模拟数据
                        print("akshare中找不到合适的行业板块数据函数，使用模拟数据")
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
                    print("获取行业板块数据失败：返回空数据")
                    return pd.DataFrame()
            else:
                # 返回模拟热点板块数据
                print("akshare不可用，使用模拟热点板块数据")
                return self._get_mock_hot_sectors()
        except Exception as e:
            print(f"获取热点行业板块失败: {str(e)}")
            # 返回模拟数据作为备选
            return self._get_mock_hot_sectors()
    
    def get_concept_sectors(self) -> pd.DataFrame:
        """获取概念板块数据
        
        Returns:
            包含概念板块名称、代码等信息的DataFrame
        """
        try:
            if AK_SHARE_AVAILABLE:
                max_retries = 3
                retry_count = 0
                
                while retry_count < max_retries:
                    try:
                        # 使用akshare获取东方财富概念板块数据
                        df = ak.stock_board_concept_name_em()
                        if isinstance(df, pd.DataFrame) and not df.empty:
                            return df
                        else:
                            print("获取概念板块数据失败：返回空数据")
                            break
                    except (ConnectionError, TimeoutError) as network_error:
                        retry_count += 1
                        if retry_count < max_retries:
                            print(f"网络连接错误，{retry_count}/3 重试中: {str(network_error)}")
                            import time
                            time.sleep(1)  # 等待1秒后重试
                        else:
                            print(f"获取概念板块数据失败，已重试{max_retries}次: {str(network_error)}")
                    except Exception as e:
                        print(f"获取概念板块数据失败: {str(e)}")
                        break
                
                # 返回模拟概念板块数据
                print("使用模拟概念板块数据")
                return self._get_mock_concept_sectors()
            else:
                # akshare不可用时返回模拟数据
                print("akshare不可用，使用模拟概念板块数据")
                return self._get_mock_concept_sectors()
        except Exception as e:
            print(f"获取概念板块数据失败: {str(e)}")
            # 返回模拟数据作为备选
            return self._get_mock_concept_sectors()
    
    def _get_mock_concept_sectors(self) -> pd.DataFrame:
        """提供模拟的概念板块数据
        
        Returns:
            包含模拟概念板块数据的DataFrame
        """
        mock_data = {
            '板块代码': ['BK0577', 'BK0980', 'BK0636', 'BK1024', 'BK0642'],
            '板块名称': ['新能源汽车', '光伏概念', '数字货币', 'ChatGPT', '医疗器械']
        }
        return pd.DataFrame(mock_data)
    
    def _get_mock_hot_sectors(self) -> pd.DataFrame:
        """提供模拟的热点板块数据
        
        Returns:
            包含模拟热点板块数据的DataFrame
        """
        mock_data = {
            'sector_name': ['人工智能', '新能源', '医药生物', '半导体', '金融服务'],
            'change_percent': [3.2, 2.8, 1.5, 4.1, 0.9],
            'leading_stock': ['科大讯飞', '宁德时代', '恒瑞医药', '中芯国际', '招商银行'],
            'latest_price': [65.21, 189.56, 45.78, 52.34, 38.91],
            'volume': [123456789, 98765432, 76543210, 87654321, 65432109],
            'amount': [8145678901, 18695678901, 3502789012, 4584567890, 2545678901]
        }
        return pd.DataFrame(mock_data)
    
    def get_sector_stocks(self, sector_code: str) -> pd.DataFrame:
        """获取指定板块的股票列表
        
        Args:
            sector_code: 板块代码
            
        Returns:
            包含板块内股票信息的DataFrame
        """
        try:
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
                        return pd.DataFrame()
                
                if isinstance(df, pd.DataFrame) and not df.empty:
                    return df
                else:
                    return pd.DataFrame()
            else:
                # 返回模拟板块股票数据
                print("akshare不可用，使用模拟板块股票数据")
                mock_data = {
                    '代码': ['000001', '000002', '600000', '600036', '000858'],
                    '名称': ['平安银行', '万科A', '浦发银行', '招商银行', '五粮液']
                }
                return pd.DataFrame(mock_data)
        except Exception as e:
            print(f"获取板块股票列表失败: {str(e)}")
            # 返回模拟数据作为备选
            mock_data = {
                '代码': ['000001', '000002', '600000', '600036', '000858'],
                '名称': ['平安银行', '万科A', '浦发银行', '招商银行', '五粮液']
            }
            return pd.DataFrame(mock_data)