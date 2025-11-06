import pandas as pd
import numpy as np
from typing import Dict, List, Any
from database.models import TechnicalAnalysisResult
from datetime import datetime

class TechnicalAnalyzer:
    """技术分析器，用于计算各种技术指标"""
    
    def __init__(self):
        pass
    
    def calculate_all_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算所有技术指标"""
        if df.empty:
            return df
        
        df_copy = df.copy()
        
        # 计算移动平均线
        self._calculate_moving_averages(df_copy)
        
        # 计算MACD
        self._calculate_macd(df_copy)
        
        # 计算RSI
        self._calculate_rsi(df_copy)
        
        # 计算布林带
        self._calculate_bollinger_bands(df_copy)
        
        # 计算KDJ
        self._calculate_kdj(df_copy)
        
        # 计算成交量指标
        self._calculate_volume_indicators(df_copy)
        
        # 计算动量指标
        self._calculate_momentum(df_copy)
        
        # 计算波动率指标
        self._calculate_volatility(df_copy)
        
        return df_copy
    
    def generate_signals(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """根据技术指标生成交易信号"""
        if df.empty:
            return []
        
        signals = []
        latest_data = df.iloc[-1]
        
        # 移动平均线交叉信号
        ma_signal = self._generate_ma_crossover_signal(df)
        if ma_signal:
            signals.append({
                'indicator_name': 'MA_Crossover',
                'indicator_value': ma_signal['value'],
                'signal': ma_signal['signal'],
                'strength': ma_signal['strength']
            })
        
        # MACD信号
        macd_signal = self._generate_macd_signal(df)
        if macd_signal:
            signals.append({
                'indicator_name': 'MACD',
                'indicator_value': latest_data.get('MACD_Hist', 0),
                'signal': macd_signal['signal'],
                'strength': macd_signal['strength']
            })
        
        # RSI信号
        rsi_signal = self._generate_rsi_signal(latest_data)
        if rsi_signal:
            signals.append({
                'indicator_name': 'RSI',
                'indicator_value': latest_data.get('RSI', 50),
                'signal': rsi_signal['signal'],
                'strength': rsi_signal['strength']
            })
        
        # 布林带信号
        bb_signal = self._generate_bollinger_band_signal(latest_data)
        if bb_signal:
            signals.append({
                'indicator_name': 'Bollinger_Bands',
                'indicator_value': latest_data.get('close_price', 0),
                'signal': bb_signal['signal'],
                'strength': bb_signal['strength']
            })
        
        # KDJ信号
        kdj_signal = self._generate_kdj_signal(latest_data)
        if kdj_signal:
            signals.append({
                'indicator_name': 'KDJ',
                'indicator_value': latest_data.get('K', 50),
                'signal': kdj_signal['signal'],
                'strength': kdj_signal['strength']
            })
        
        return signals
    
    def convert_to_db_models(self, stock_code: str, signals: List[Dict[str, Any]]) -> List[TechnicalAnalysisResult]:
        """将信号转换为数据库模型"""
        results = []
        analysis_date = datetime.now().date()
        
        for signal in signals:
            result = TechnicalAnalysisResult(
                stock_code=stock_code,
                analysis_date=analysis_date,
                indicator_name=signal['indicator_name'],
                indicator_value=signal['indicator_value'],
                signal=signal['signal']
            )
            results.append(result)
        
        return results
    
    # 以下是各种技术指标的计算方法
    def _calculate_moving_averages(self, df: pd.DataFrame):
        """计算各种移动平均线"""
        df['MA5'] = df['close_price'].rolling(window=5).mean()
        df['MA10'] = df['close_price'].rolling(window=10).mean()
        df['MA20'] = df['close_price'].rolling(window=20).mean()
        df['MA30'] = df['close_price'].rolling(window=30).mean()
        df['MA60'] = df['close_price'].rolling(window=60).mean()
        df['MA120'] = df['close_price'].rolling(window=120).mean()
        df['MA250'] = df['close_price'].rolling(window=250).mean()
        
        # 计算指数移动平均线
        df['EMA12'] = df['close_price'].ewm(span=12, adjust=False).mean()
        df['EMA26'] = df['close_price'].ewm(span=26, adjust=False).mean()
    
    def _calculate_macd(self, df: pd.DataFrame):
        """计算MACD指标"""
        # 确保已计算EMA
        if 'EMA12' not in df.columns or 'EMA26' not in df.columns:
            self._calculate_moving_averages(df)
        
        df['MACD'] = df['EMA12'] - df['EMA26']
        df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_Hist'] = df['MACD'] - df['Signal_Line']
    
    def _calculate_rsi(self, df: pd.DataFrame, window: int = 14):
        """计算RSI指标"""
        delta = df['close_price'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
    
    def _calculate_bollinger_bands(self, df: pd.DataFrame, window: int = 20, num_std: float = 2):
        """计算布林带"""
        df['SMA20'] = df['close_price'].rolling(window=window).mean()
        df['STD20'] = df['close_price'].rolling(window=window).std()
        df['Upper_Band'] = df['SMA20'] + (df['STD20'] * num_std)
        df['Lower_Band'] = df['SMA20'] - (df['STD20'] * num_std)
        # 计算布林带宽度
        df['BB_Width'] = (df['Upper_Band'] - df['Lower_Band']) / df['SMA20']
    
    def _calculate_kdj(self, df: pd.DataFrame, n: int = 9, m1: int = 3, m2: int = 3):
        """计算KDJ指标"""
        # 计算RSV值
        low_n = df['low_price'].rolling(window=n).min()
        high_n = df['high_price'].rolling(window=n).max()
        df['RSV'] = (df['close_price'] - low_n) / (high_n - low_n) * 100
        
        # 计算K、D、J值
        df['K'] = df['RSV'].ewm(com=m1-1, adjust=False).mean()
        df['D'] = df['K'].ewm(com=m2-1, adjust=False).mean()
        df['J'] = 3 * df['K'] - 2 * df['D']
    
    def _calculate_volume_indicators(self, df: pd.DataFrame):
        """计算成交量指标"""
        # 成交量移动平均线
        df['MA_Volume5'] = df['volume'].rolling(window=5).mean()
        df['MA_Volume10'] = df['volume'].rolling(window=10).mean()
        
        # 成交量比率
        df['Volume_Ratio'] = df['volume'] / df['volume'].shift(1)
    
    def _calculate_momentum(self, df: pd.DataFrame):
        """计算动量指标"""
        # 动量
        df['Momentum'] = df['close_price'] - df['close_price'].shift(10)
        
        # 变化率
        df['ROC'] = (df['close_price'] - df['close_price'].shift(10)) / df['close_price'].shift(10) * 100
    
    def _calculate_volatility(self, df: pd.DataFrame):
        """计算波动率指标"""
        # 日收益率
        df['Daily_Return'] = df['close_price'].pct_change()
        
        # 历史波动率（20日）
        df['Volatility'] = df['Daily_Return'].rolling(window=20).std() * np.sqrt(252)  # 年化
    
    # 以下是信号生成方法
    def _generate_ma_crossover_signal(self, df: pd.DataFrame):
        """生成均线交叉信号"""
        if len(df) < 30:
            return None
        
        # 检查MA5和MA20交叉
        if df['MA5'].iloc[-2] < df['MA20'].iloc[-2] and df['MA5'].iloc[-1] > df['MA20'].iloc[-1]:
            return {
                'signal': 'BUY',
                'value': df['MA5'].iloc[-1] - df['MA20'].iloc[-1],
                'strength': 'strong' if abs(df['MA5'].iloc[-1] - df['MA20'].iloc[-1]) > df['close_price'].iloc[-1] * 0.02 else 'weak'
            }
        elif df['MA5'].iloc[-2] > df['MA20'].iloc[-2] and df['MA5'].iloc[-1] < df['MA20'].iloc[-1]:
            return {
                'signal': 'SELL',
                'value': df['MA5'].iloc[-1] - df['MA20'].iloc[-1],
                'strength': 'strong' if abs(df['MA5'].iloc[-1] - df['MA20'].iloc[-1]) > df['close_price'].iloc[-1] * 0.02 else 'weak'
            }
        
        return None
    
    def _generate_macd_signal(self, df: pd.DataFrame):
        """生成MACD信号"""
        if len(df) < 30 or 'MACD_Hist' not in df.columns:
            return None
        
        # 检查MACD柱状图穿越零点
        if df['MACD_Hist'].iloc[-2] < 0 and df['MACD_Hist'].iloc[-1] > 0:
            return {
                'signal': 'BUY',
                'strength': 'strong' if df['MACD_Hist'].iloc[-1] > abs(df['MACD_Hist'].iloc[-2]) else 'weak'
            }
        elif df['MACD_Hist'].iloc[-2] > 0 and df['MACD_Hist'].iloc[-1] < 0:
            return {
                'signal': 'SELL',
                'strength': 'strong' if abs(df['MACD_Hist'].iloc[-1]) > df['MACD_Hist'].iloc[-2] else 'weak'
            }
        
        return None
    
    def _generate_rsi_signal(self, data):
        """生成RSI信号"""
        if 'RSI' not in data:
            return None
        
        rsi = data['RSI']
        
        if rsi < 30:
            return {
                'signal': 'BUY',
                'strength': 'strong' if rsi < 20 else 'weak'
            }
        elif rsi > 70:
            return {
                'signal': 'SELL',
                'strength': 'strong' if rsi > 80 else 'weak'
            }
        
        return None
    
    def _generate_bollinger_band_signal(self, data):
        """生成布林带信号"""
        if 'Upper_Band' not in data or 'Lower_Band' not in data:
            return None
        
        close = data['close_price']
        upper = data['Upper_Band']
        lower = data['Lower_Band']
        
        if close > upper:
            return {
                'signal': 'SELL',
                'strength': 'strong' if (close - upper) / upper > 0.02 else 'weak'
            }
        elif close < lower:
            return {
                'signal': 'BUY',
                'strength': 'strong' if (lower - close) / lower > 0.02 else 'weak'
            }
        
        return None
    
    def _generate_kdj_signal(self, data):
        """生成KDJ信号"""
        if 'K' not in data or 'D' not in data or 'J' not in data:
            return None
        
        k = data['K']
        d = data['D']
        
        # K线从下向上穿越D线
        if k > d and k > 20:
            return {
                'signal': 'BUY',
                'strength': 'strong' if k < 50 else 'weak'
            }
        # K线从上向下穿越D线
        elif k < d and k < 80:
            return {
                'signal': 'SELL',
                'strength': 'strong' if k > 50 else 'weak'
            }
        
        return None