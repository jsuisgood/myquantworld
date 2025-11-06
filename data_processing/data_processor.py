import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple, Optional, Union


class DataProcessor:
    """数据处理类，用于清洗、转换和处理股票数据"""
    
    def __init__(self):
        print("数据处理器已初始化")
    
    def clean_stock_daily_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """清洗股票日线数据，仅支持pandas DataFrame"""
        if df.empty:
            return df
        
        # 创建副本以避免修改原始数据
        cleaned_df = df.copy()
        
        # 1. 处理列名 - 确保使用标准的英文列名
        column_mapping = {
            '日期': 'trade_date',
            'trading_date': 'trade_date',
            '开盘': 'open_price',
            '开盘价': 'open_price',
            '最高': 'high_price',
            '最高价': 'high_price',
            '最低': 'low_price',
            '最低价': 'low_price',
            '收盘': 'close_price',
            '收盘价': 'close_price',
            '成交量': 'volume',
            '成交额': 'amount',
            '换手率': 'turnover_rate',
            '涨跌幅': 'change_percent'
        }
        
        # 重命名列
        for cn_col, en_col in column_mapping.items():
            if cn_col in cleaned_df.columns:
                cleaned_df.rename(columns={cn_col: en_col}, inplace=True)
        
        # 2. 处理日期列 - 确保日期格式一致
        if 'trade_date' in cleaned_df.columns:
            try:
                # 尝试转换为日期类型
                if not pd.api.types.is_datetime64_any_dtype(cleaned_df['trade_date']):
                    cleaned_df['trade_date'] = pd.to_datetime(cleaned_df['trade_date'])
                # 格式化为字符串格式
                cleaned_df['trade_date'] = cleaned_df['trade_date'].dt.strftime('%Y%m%d')
            except Exception as e:
                print(f"处理日期列时出错: {str(e)}")
        
        # 3. 处理数值列 - 确保数值格式正确
        numeric_columns = ['open_price', 'high_price', 'low_price', 'close_price', 'volume', 'amount', 'turnover_rate', 'change_percent']
        for col in numeric_columns:
            if col in cleaned_df.columns:
                try:
                    # 移除可能的非数字字符（如%）
                    if cleaned_df[col].dtype == 'object':
                        cleaned_df[col] = cleaned_df[col].astype(str).str.replace('%', '').str.replace(',', '')
                    # 转换为浮点数
                    cleaned_df[col] = pd.to_numeric(cleaned_df[col], errors='coerce')
                except Exception as e:
                    print(f"处理数值列 {col} 时出错: {str(e)}")
        
        # 4. 处理缺失值 - 填充或删除
        # 删除完全为空的行
        cleaned_df.dropna(how='all', inplace=True)
        
        # 对于价格数据，使用前向填充
        price_columns = ['open_price', 'high_price', 'low_price', 'close_price']
        for col in price_columns:
            if col in cleaned_df.columns:
                cleaned_df[col].fillna(method='ffill', inplace=True)
        
        # 对于成交量和成交额，填充为0
        volume_columns = ['volume', 'amount']
        for col in volume_columns:
            if col in cleaned_df.columns:
                cleaned_df[col].fillna(0, inplace=True)
        
        # 5. 排序 - 按日期排序
        if 'trade_date' in cleaned_df.columns:
            cleaned_df.sort_values('trade_date', inplace=True)
        
        # 6. 重置索引
        cleaned_df.reset_index(drop=True, inplace=True)
        
        return cleaned_df
    
    def calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算常用技术指标"""
        if df.empty or len(df) < 20:  # 需要足够的数据点
            return df
        
        # 创建副本以避免修改原始数据
        tech_df = df.copy()
        
        # 确保必要的列存在
        required_columns = ['open_price', 'high_price', 'low_price', 'close_price', 'volume']
        for col in required_columns:
            if col not in tech_df.columns:
                print(f"警告: 缺少必要的列 {col}，无法计算所有技术指标")
                return df
        
        # 1. 移动平均线 (MA)
        tech_df['ma5'] = tech_df['close_price'].rolling(window=5).mean()
        tech_df['ma10'] = tech_df['close_price'].rolling(window=10).mean()
        tech_df['ma20'] = tech_df['close_price'].rolling(window=20).mean()
        tech_df['ma60'] = tech_df['close_price'].rolling(window=60).mean()
        
        # 2. 相对强弱指标 (RSI)
        delta = tech_df['close_price'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        rs = avg_gain / avg_loss
        tech_df['rsi14'] = 100 - (100 / (1 + rs))
        
        # 3. 移动平均线收敛/发散 (MACD)
        exp1 = tech_df['close_price'].ewm(span=12, adjust=False).mean()
        exp2 = tech_df['close_price'].ewm(span=26, adjust=False).mean()
        tech_df['macd'] = exp1 - exp2
        tech_df['signal_line'] = tech_df['macd'].ewm(span=9, adjust=False).mean()
        tech_df['macd_hist'] = tech_df['macd'] - tech_df['signal_line']
        
        # 4. 布林带 (Bollinger Bands)
        tech_df['bollinger_mid'] = tech_df['close_price'].rolling(window=20).mean()
        tech_df['bollinger_std'] = tech_df['close_price'].rolling(window=20).std()
        tech_df['bollinger_upper'] = tech_df['bollinger_mid'] + (tech_df['bollinger_std'] * 2)
        tech_df['bollinger_lower'] = tech_df['bollinger_mid'] - (tech_df['bollinger_std'] * 2)
        
        # 5. 成交量移动平均线
        tech_df['vol_ma5'] = tech_df['volume'].rolling(window=5).mean()
        tech_df['vol_ma20'] = tech_df['volume'].rolling(window=20).mean()
        
        # 6. 计算价格变化率
        tech_df['price_change'] = tech_df['close_price'].pct_change() * 100
        
        return tech_df
    
    def generate_trading_signals(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """根据技术指标生成交易信号"""
        if df.empty or len(df) < 20:
            return []
        
        signals = []
        
        # 创建副本以避免修改原始数据
        signal_df = df.copy()
        
        # 确保必要的列存在，如果不存在则计算
        if 'ma5' not in signal_df.columns or 'ma10' not in signal_df.columns:
            signal_df = self.calculate_technical_indicators(signal_df)
        
        # 1. 均线金叉死叉信号
        if 'ma5' in signal_df.columns and 'ma10' in signal_df.columns:
            # 计算均线交叉点
            signal_df['ma_cross'] = 0
            signal_df.loc[signal_df['ma5'] > signal_df['ma10'], 'ma_cross'] = 1
            signal_df['ma_cross_signal'] = signal_df['ma_cross'].diff()
            
            # 找出金叉点
            golden_crosses = signal_df[signal_df['ma_cross_signal'] == 1]
            for _, row in golden_crosses.iterrows():
                signals.append({
                    'date': row.get('trade_date', ''),
                    'signal_type': '买入',
                    'reason': 'MA5上穿MA10（金叉）',
                    'strength': '中等',
                    'price': row.get('close_price', 0)
                })
            
            # 找出死叉点
            death_crosses = signal_df[signal_df['ma_cross_signal'] == -1]
            for _, row in death_crosses.iterrows():
                signals.append({
                    'date': row.get('trade_date', ''),
                    'signal_type': '卖出',
                    'reason': 'MA5下穿MA10（死叉）',
                    'strength': '中等',
                    'price': row.get('close_price', 0)
                })
        
        # 2. RSI超买超卖信号
        if 'rsi14' in signal_df.columns:
            # RSI低于30视为超卖，高于70视为超买
            oversold = signal_df[signal_df['rsi14'] < 30]
            for _, row in oversold.iterrows():
                signals.append({
                    'date': row.get('trade_date', ''),
                    'signal_type': '买入',
                    'reason': f'RSI超卖: {row["rsi14"]:.2f}',
                    'strength': '弱',
                    'price': row.get('close_price', 0)
                })
            
            overbought = signal_df[signal_df['rsi14'] > 70]
            for _, row in overbought.iterrows():
                signals.append({
                    'date': row.get('trade_date', ''),
                    'signal_type': '卖出',
                    'reason': f'RSI超买: {row["rsi14"]:.2f}',
                    'strength': '弱',
                    'price': row.get('close_price', 0)
                })
        
        # 3. MACD信号
        if 'macd' in signal_df.columns and 'signal_line' in signal_df.columns:
            signal_df['macd_cross'] = 0
            signal_df.loc[signal_df['macd'] > signal_df['signal_line'], 'macd_cross'] = 1
            signal_df['macd_signal'] = signal_df['macd_cross'].diff()
            
            # MACD金叉（买入信号）
            macd_buy_signals = signal_df[signal_df['macd_signal'] == 1]
            for _, row in macd_buy_signals.iterrows():
                signals.append({
                    'date': row.get('trade_date', ''),
                    'signal_type': '买入',
                    'reason': 'MACD金叉',
                    'strength': '中等',
                    'price': row.get('close_price', 0)
                })
            
            # MACD死叉（卖出信号）
            macd_sell_signals = signal_df[signal_df['macd_signal'] == -1]
            for _, row in macd_sell_signals.iterrows():
                signals.append({
                    'date': row.get('trade_date', ''),
                    'signal_type': '卖出',
                    'reason': 'MACD死叉',
                    'strength': '中等',
                    'price': row.get('close_price', 0)
                })
        
        # 按日期排序信号
        signals.sort(key=lambda x: x['date'])
        
        return signals
    
    def prepare_data_for_analysis(self, df: pd.DataFrame) -> pd.DataFrame:
        """准备用于分析的数据格式"""
        if df.empty:
            return df
        
        # 清洗数据
        prepared_df = self.clean_stock_daily_data(df)
        
        # 计算技术指标
        prepared_df = self.calculate_technical_indicators(prepared_df)
        
        # 确保必要的列存在
        required_columns = ['trade_date', 'open_price', 'high_price', 'low_price', 'close_price', 'volume']
        for col in required_columns:
            if col not in prepared_df.columns:
                print(f"警告: 缺少必要的列 {col}")
        
        return prepared_df
    
    def normalize_price_data(self, df: pd.DataFrame, column: str = 'close_price') -> pd.DataFrame:
        """价格数据标准化"""
        if df.empty or column not in df.columns:
            return df
        
        norm_df = df.copy()
        
        # 标准化为相对于起始价格的百分比变化
        first_price = norm_df[column].iloc[0]
        if first_price != 0:
            norm_df[f'{column}_normalized'] = (norm_df[column] / first_price) * 100
        
        return norm_df
    
    def calculate_returns(self, df: pd.DataFrame, periods: List[int] = [1, 5, 10, 20]) -> pd.DataFrame:
        """计算不同时间周期的收益率"""
        if df.empty or 'close_price' not in df.columns:
            return df
        
        returns_df = df.copy()
        
        for period in periods:
            returns_df[f'return_{period}d'] = returns_df['close_price'].pct_change(periods=period) * 100
        
        return returns_df
    
    def aggregate_daily_to_weekly(self, df: pd.DataFrame) -> pd.DataFrame:
        """将日线数据聚合为周线数据"""
        if df.empty or 'trade_date' not in df.columns:
            return df
        
        # 确保日期列是datetime类型
        agg_df = df.copy()
        if not pd.api.types.is_datetime64_any_dtype(agg_df['trade_date']):
            agg_df['trade_date'] = pd.to_datetime(agg_df['trade_date'])
        
        # 设置日期为索引
        agg_df.set_index('trade_date', inplace=True)
        
        # 按周聚合，使用OHLCV格式
        weekly_df = agg_df.resample('W').agg({
            'open_price': 'first',
            'high_price': 'max',
            'low_price': 'min',
            'close_price': 'last',
            'volume': 'sum',
            'amount': 'sum' if 'amount' in agg_df.columns else 'sum'
        })
        
        # 重置索引并确保没有空周
        weekly_df.reset_index(inplace=True)
        weekly_df.dropna(subset=['close_price'], inplace=True)
        
        return weekly_df
    
    def filter_outliers(self, df: pd.DataFrame, columns: List[str], method: str = 'iqr') -> pd.DataFrame:
        """过滤异常值"""
        if df.empty:
            return df
        
        filtered_df = df.copy()
        
        for col in columns:
            if col not in filtered_df.columns:
                continue
                
            if method == 'iqr':
                # 使用IQR方法
                Q1 = filtered_df[col].quantile(0.25)
                Q3 = filtered_df[col].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                
                # 保留在范围内的值
                filtered_df = filtered_df[(filtered_df[col] >= lower_bound) & (filtered_df[col] <= upper_bound)]
            
            elif method == 'zscore':
                # 使用Z-Score方法
                z_scores = np.abs((filtered_df[col] - filtered_df[col].mean()) / filtered_df[col].std())
                filtered_df = filtered_df[z_scores < 3]  # 保留Z-Score小于3的值
        
        return filtered_df
    
    def prepare_stock_for_db(self, df: pd.DataFrame, stock_code: str) -> List[Dict[str, Any]]:
        """准备股票数据用于数据库存储
        
        Args:
            df: 清洗后的股票数据DataFrame
            stock_code: 股票代码
            
        Returns:
            字典列表，适合直接保存到数据库
        """
        if df.empty:
            return []
        
        # 确保必要的列存在
        required_columns = ['trade_date', 'open_price', 'high_price', 'low_price', 'close_price', 'volume']
        for col in required_columns:
            if col not in df.columns:
                print(f"警告: 缺少必要的列 {col}，无法准备数据")
                return []
        
        # 转换为字典列表
        records = []
        for _, row in df.iterrows():
            record = {
                'trade_date': row['trade_date'],
                'open_price': row.get('open_price', 0),
                'high_price': row.get('high_price', 0),
                'low_price': row.get('low_price', 0),
                'close_price': row.get('close_price', 0),
                'volume': row.get('volume', 0),
                'amount': row.get('amount', 0),
                'change_percent': row.get('change_percent', 0),
                'turnover_rate': row.get('turnover_rate', 0)
            }
            records.append(record)
        
        return records