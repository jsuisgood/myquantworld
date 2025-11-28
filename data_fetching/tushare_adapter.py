import os
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging
import time

# Predefine TS_TOKEN variable to ensure it always exists
TS_TOKEN = os.environ.get('TS_TOKEN', '')

from data_fetching.base_client import BaseDataClient
from utils.logger_config import get_logger, log_error, log_with_context
from data_storage.db_storage import DBStorage

# Configure logger
logger = get_logger(__name__)

# Try to import tushare, use mock data if failed
try:
    import tushare as ts
    # Use the defined TS_TOKEN variable
    ts.set_token(TS_TOKEN)  # Allow empty token, will be handled later
    TUSHARE_AVAILABLE = True
except ImportError:
    TUSHARE_AVAILABLE = False
    logger.warning("tushare library not installed, will use mock data")
except Exception as e:
    TUSHARE_AVAILABLE = True  # Library installed but initialization failed
    logger.warning(f"tushare initialization encountered an issue: {str(e)}")


class TuShareClient(BaseDataClient):
    """TuShare adapter, implementing BaseDataClient interface"""
    
    def __init__(self, token: Optional[str] = None):
        """
        Initialize Tushare client
        
        Args:
            token: Tushare API token, if None, will try to use token from environment variable or configuration file
        """
        super().__init__()
        self.name = "Tushare"
        self.pro = None
        self.token = token or TS_TOKEN
        
        # Initialize error tracking
        self._last_error = None
        self._error_count = 0
        self._last_health_check = None
        
        # Initialize database storage object
        self.db_storage = DBStorage()
        
        # Try to initialize Tushare API client
        if TUSHARE_AVAILABLE:
            try:
                # Try initialization regardless of token presence
                if self.token:
                    ts.set_token(self.token)
                    self.pro = ts.pro_api()
                    logger.info("TuShare client initialized - tushare API available")
                else:
                    logger.warning("No API token provided for TuShare, some functions may not be available")
                    self.pro = None
            except Exception as e:
                logger.warning(f"TuShare initialization failed: {str(e)}")
                self.pro = None
        else:
            logger.info("TuShare library not available, some functions may not be available")
    
    def _get_stock_basic_info_impl(self) -> pd.DataFrame:
        """Implementation for getting basic stock information"""
        if not (TUSHARE_AVAILABLE and self.pro):
            # Throw exception when tushare is not available
            error_msg = "tushare not available: cannot get basic stock information"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        # Use tushare to get basic stock information
        df = self.pro.stock_basic(exchange='', list_status='L', fields='ts_code,symbol,name,area,industry,market')
        
        # Check returned data
        if df is None or df.empty:
            error_msg = "Failed to get basic stock information: returned empty data"
            logger.error(error_msg)
            raise Exception(error_msg)
            
        # Convert column names to be compatible with the system
        if 'symbol' in df.columns and 'name' in df.columns:
            # Rename columns to comply with system naming conventions
            column_mapping = {
                'symbol': 'code',
                'name': 'name'
            }
            df.rename(columns=column_mapping, inplace=True)
            return df[['code', 'name']]
        return df
    
    def _get_all_a_stocks_impl(self) -> pd.DataFrame:
        """Implementation for getting all A-share stocks list"""
        if not (TUSHARE_AVAILABLE and self.pro):
            # Throw exception when tushare is not available
            error_msg = "tushare not available: cannot get A-share stocks list"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        # Use tushare to get all A-share stocks list (only get stocks from Shanghai and Shenzhen exchanges)
        df = self.pro.stock_basic(
            exchange='', 
            list_status='L', 
            market='',
            fields='ts_code,symbol,name,area,industry,market,list_date'
        )
        
        # Filter out A-share stocks (Shanghai and Shenzhen exchanges)
        if not df.empty:
            # Ensure market column exists
            if 'market' in df.columns:
                # Only keep A-shares (stocks from Shanghai and Shenzhen exchanges)
                df = df[df['market'].isin(['Main Board', 'Small and Medium Board', 'GEM', 'STAR Market', 'STAR Market CDR'])]
            
            # Rename columns to comply with system naming conventions
            column_mapping = {
                'symbol': 'code',
                'name': 'name',
                'area': 'area',
                'industry': 'industry',
                'list_date': 'list_date'
            }
            
            for ts_col, sys_col in column_mapping.items():
                if ts_col in df.columns:
                    df.rename(columns={ts_col: sys_col}, inplace=True)
        
        # Check returned data
        if df is None or df.empty:
            error_msg = "Failed to get A-share stocks list: returned empty data"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        logger.info(f"Successfully retrieved {len(df)} A-share stocks")
        return df[['code', 'name', 'area', 'industry', 'list_date']]
    
    def _get_stock_daily_data_impl(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Implementation for getting stock daily data"""
        logger.info(f"Start getting stock {stock_code} data, date range: {start_date} to {end_date}")
        
        if not (TUSHARE_AVAILABLE and self.pro):
            # Throw exception when tushare is not available
            error_msg = f"tushare not available: cannot get stock {stock_code} daily data"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        # Convert stock code format to tushare required format
        if stock_code.startswith('6'):
            ts_code = f"{stock_code}.SH"  # Shanghai Stock Exchange
        else:
            ts_code = f"{stock_code}.SZ"  # Shenzhen Stock Exchange
        
        # Use tushare to get stock historical data
        df = self.pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
        
        if not (isinstance(df, pd.DataFrame) and not df.empty):
            error_msg = f"Failed to get stock {stock_code} daily data: returned empty data or non-DataFrame object"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        # Rename columns to comply with system naming conventions
        column_mapping = {
            'trade_date': 'trade_date',
            'open': 'open_price',
            'high': 'high_price',
            'low': 'low_price',
            'close': 'close_price',
            'vol': 'volume',
            'amount': 'amount'
        }
        
        for ts_col, sys_col in column_mapping.items():
            if ts_col in df.columns:
                df.rename(columns={ts_col: sys_col}, inplace=True)
        
        # Add stock code column
        df['stock_code'] = stock_code
        
        # Sort by date (from oldest to newest)
        if 'trade_date' in df.columns:
            df.sort_values('trade_date', inplace=True)
        
        return df
    
    def _get_stock_financial_indicators_impl(self, stock_code: str) -> pd.DataFrame:
        """Implementation for getting stock financial indicators data"""
        if not (TUSHARE_AVAILABLE and self.pro):
            # Throw exception when tushare is not available
            error_msg = f"tushare not available: cannot get stock {stock_code} financial indicators data"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        # Convert stock code format to tushare required format
        if stock_code.startswith('6'):
            ts_code = f"{stock_code}.SH"  # Shanghai Stock Exchange
        else:
            ts_code = f"{stock_code}.SZ"  # Shenzhen Stock Exchange
        
        # Use tushare to get financial indicators
        try:
            # Get latest financial indicators
            df = self.pro.fina_indicator(ts_code=ts_code, fields='ts_code,end_date,eps,roe,gross_margin,net_profit_margin')
            
            # Check returned data
            if df is None or df.empty:
                error_msg = f"Failed to get stock {stock_code} financial indicators data: returned empty data"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            # Convert column names and add stock code
            # Rename columns to comply with system naming conventions
            column_mapping = {
                'eps': 'earnings_per_share',
                'roe': 'return_on_equity',
                'gross_margin': 'gross_profit_margin',
                'net_profit_margin': 'net_profit_margin'
            }
            
            for ts_col, sys_col in column_mapping.items():
                if ts_col in df.columns:
                    df.rename(columns={ts_col: sys_col}, inplace=True)
            
            # Add stock code column
            df['stock_code'] = stock_code
            
            return df
        except Exception as e:
            logger.error(f"Failed to get stock {stock_code} financial indicators data: {str(e)}")
            raise
    
    def _get_hot_sectors_impl(self) -> pd.DataFrame:
        """Implementation for getting hot industry sector data"""
        if not (TUSHARE_AVAILABLE and self.pro):
            # Throw exception when tushare is not available
            error_msg = "tushare not available: cannot get hot industry sector data"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        # Use tushare to get industry sector data
        try:
            # Get Shenwan Level-1 industry indices
            df = self.pro.index_dailybasic(ts_code='', market='CSI', fields='ts_code,name,close,change,volume,amount')
            
            # Check returned data
            if not (isinstance(df, pd.DataFrame) and not df.empty):
                error_msg = "Failed to get industry sector data: returned empty data or non-DataFrame object"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            # Sort by price change, descending order
            if 'change' in df.columns:
                df = df.sort_values('change', ascending=False)
            
            # Rename columns to comply with system naming conventions
            column_mapping = {
                'name': 'sector_name',
                'change': 'change_percent',
                'close': 'latest_price',
                'volume': 'volume',
                'amount': 'amount'
            }
            
            for ts_col, sys_col in column_mapping.items():
                if ts_col in df.columns:
                    df.rename(columns={ts_col: sys_col}, inplace=True)
            
            # Add simulated leading stock information
            if not df.empty:
                df['leading_stock'] = ['Leading Stock 1', 'Leading Stock 2', 'Leading Stock 3', 'Leading Stock 4', 'Leading Stock 5'][:len(df)]
            
            return df
        except Exception as e:
            logger.error(f"Failed to get industry sector data: {str(e)}")
            raise
    
    def _get_concept_sectors_impl(self) -> pd.DataFrame:
        """Implementation for getting concept sector data"""
        if not (TUSHARE_AVAILABLE and self.pro):
            # Throw exception when tushare is not available
            error_msg = "tushare not available: cannot get concept sector data"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        # Use retry mechanism to get concept sector data
        def fetch_concept_data():
            # Get concept sector information
            df = self.pro.concept()
            if isinstance(df, pd.DataFrame) and not df.empty:
                # Rename columns to comply with system naming conventions
                column_mapping = {
                    'code': 'sector_code',
                    'name': 'sector_name'
                }
                
                for ts_col, sys_col in column_mapping.items():
                    if ts_col in df.columns:
                        df.rename(columns={ts_col: sys_col}, inplace=True)
                
                return df
            else:
                raise ValueError("Failed to get concept sector data: returned empty data")
        
        try:
            return self._retry_with_backoff(fetch_concept_data)
        except Exception as e:
            logger.error(f"Failed to get concept sector data: {str(e)}")
            raise
    
    def _get_sector_stocks_impl(self, sector_code: str) -> pd.DataFrame:
        """Implementation for getting stock list of specified sector"""
        if not (TUSHARE_AVAILABLE and self.pro):
            # Throw exception when tushare is not available
            error_msg = "tushare not available: cannot get sector stock data"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        # Use tushare to get stock list in sector
        try:
            # Get concept sector constituent stocks
            df = self.pro.concept_detail(id=sector_code, fields='ts_code,name')
            
            # Check data validity
            if not (isinstance(df, pd.DataFrame) and not df.empty):
                # If getting concept sector fails, try to get industry constituent stocks
                try:
                    df = self.pro.index_member(index_code=sector_code, fields='ts_code,name')
                    if not (isinstance(df, pd.DataFrame) and not df.empty):
                        error_msg = f"Failed to get stock list under sector {sector_code}: returned empty data or non-DataFrame object"
                        logger.error(error_msg)
                        raise Exception(error_msg)
                except Exception as inner_e:
                    logger.error(f"Failed to get industry constituent stocks: {str(inner_e)}")
                    error_msg = f"Failed to get stock list under sector {sector_code}"
                    raise Exception(error_msg)
            
            # Rename columns to comply with system naming conventions
            column_mapping = {
                'ts_code': 'code',
                'name': 'name'
            }
            
            for ts_col, sys_col in column_mapping.items():
                if ts_col in df.columns:
                    df.rename(columns={ts_col: sys_col}, inplace=True)
            
            return df
        except Exception as e:
            if isinstance(e, Exception) and str(e) == f"Failed to get stock list under sector {sector_code}":
                raise
            logger.error(f"Failed to get stock list under sector {sector_code}: {str(e)}")
            raise Exception(f"Failed to get stock list under sector {sector_code}: {str(e)}")
    
    @log_error
    def get_all_a_stocks(self) -> pd.DataFrame:
        """Get all A-share stocks list
        
        Returns:
            DataFrame containing all A-share stocks' code, name, area, industry, listing date and other information
        """
        try:
            result = self._retry_with_backoff(self._get_all_a_stocks_impl)
            self._log_dataframe_info(result, "A股股票列表")
            return result
        except Exception as e:
            return self._handle_request_error(e, "get_all_a_stocks")
    
    def save_stock_basic_info_to_db(self) -> bool:
        """
        Get and save basic stock information to tushare-specific database table
        
        Returns:
            bool: whether the operation was successful
        """
        try:
            # Get basic stock information
            df = self._get_stock_basic_info_impl()
            if df.empty:
                logger.warning("No basic stock information obtained, skipping save")
                return False
            
            # Save to database
            success = self.db_storage.save_tushare_stock_basic_info(df)
            if success:
                logger.info(f"Successfully saved {len(df)} basic stock information records to tushare-specific database table")
            else:
                logger.error("Failed to save basic stock information")
            
            return success
        except Exception as e:
            logger.error(f"保存股票基本信息过程中发生错误: {str(e)}")
            return False
    
    def save_stock_daily_data_to_db(self, stock_code: str, start_date: str, end_date: str) -> bool:
        """
        Get and save stock daily data to tushare-specific database table
        
        Args:
            stock_code: stock code
            start_date: start date, format as YYYYMMDD
            end_date: end date, format as YYYYMMDD
            
        Returns:
            bool: whether the operation was successful
        """
        try:
            # Get stock daily data
            df = self._get_stock_daily_data_impl(stock_code, start_date, end_date)
            if df.empty:
                logger.warning(f"No daily data obtained for stock {stock_code}, skipping save")
                return False
            
            # Save to database
            success = self.db_storage.save_tushare_stock_daily_data(df)
            if success:
                logger.info(f"Successfully saved {len(df)} daily data records for stock {stock_code} to tushare-specific database table")
            else:
                logger.error(f"Failed to save daily data for stock {stock_code}")
            
            return success
        except Exception as e:
            logger.error(f"保存股票{stock_code}的日线数据过程中发生错误: {str(e)}")
            return False
    
    def save_stock_financial_indicators_to_db(self, stock_code: str) -> bool:
        """
        Get and save stock financial indicators data to tushare-specific database table
        
        Args:
            stock_code: stock code
            
        Returns:
            bool: whether the operation was successful
        """
        try:
            # Get stock financial indicators data
            df = self._get_stock_financial_indicators_impl(stock_code)
            if df.empty:
                logger.warning(f"No financial indicators data obtained for stock {stock_code}, skipping save")
                return False
            
            # Save to database
            success = self.db_storage.save_tushare_stock_financial_indicators(df)
            if success:
                logger.info(f"Successfully saved financial indicators data for stock {stock_code} to tushare-specific database table")
            else:
                logger.error(f"Failed to save financial indicators data for stock {stock_code}")
            
            return success
        except Exception as e:
            logger.error(f"保存股票{stock_code}的财务指标数据过程中发生错误: {str(e)}")
            return False
    
    def batch_save_stock_data_to_db(self, stock_codes: List[str], start_date: str, end_date: str) -> Dict[str, bool]:
        """
        Batch get and save data for multiple stocks to tushare-specific database table
        
        Args:
            stock_codes: list of stock codes
            start_date: start date, format as YYYYMMDD
            end_date: end date, format as YYYYMMDD
            
        Returns:
            Dict[str, bool]: save result for each stock
        """
        results = {}
        
        for stock_code in stock_codes:
            logger.info(f"Start processing stock: {stock_code}")
            
            # Save daily data
            daily_success = self.save_stock_daily_data_to_db(stock_code, start_date, end_date)
            
            # Save financial indicators data
            financial_success = self.save_stock_financial_indicators_to_db(stock_code)
            
            # Overall result: considered successful if either save succeeds
            results[stock_code] = daily_success or financial_success
            
            # Avoid frequent API requests
            if TUSHARE_AVAILABLE and self.pro:
                time.sleep(0.5)  # Sleep for 0.5 seconds
        
        return results