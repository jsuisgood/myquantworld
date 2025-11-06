import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Any
from database.models import PolarAnalysisResult


class PolarAnalyzer:
    """基于pandas的分析器，用于股票模式识别和预测"""
    
    def __init__(self):
        # 确认pandas库可用
        try:
            import pandas as pd
            self.available = True
            print("数据分析器已成功初始化")
        except ImportError:
            print("警告: pandas库未安装，某些功能可能不可用")
            self.available = False
    
    def recognize_patterns(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """识别股票价格模式，仅支持pandas DataFrame"""
        if not self.available:
            return []
        
        # 检查DataFrame是否为空
        if df.empty or len(df) < 20:  # 需要足够的数据点来识别模式
            return []
        
        patterns = []
        
        # 检测头肩顶形态
        if self._detect_head_shoulder_top(df):
            patterns.append({
                'pattern_name': '头肩顶',
                'confidence': 0.75,
                'prediction': '看跌',
                'details': '检测到潜在的头肩顶形态，通常是反转信号'
            })
        
        # 检测双底形态
        if self._detect_double_bottom(df):
            patterns.append({
                'pattern_name': '双底',
                'confidence': 0.80,
                'prediction': '看涨',
                'details': '检测到潜在的双底形态，通常是反转信号'
            })
        
        # 检测上升三角形
        if self._detect_ascending_triangle(df):
            patterns.append({
                'pattern_name': '上升三角形',
                'confidence': 0.85,
                'prediction': '看涨',
                'details': '检测到上升三角形形态，通常是延续信号'
            })
        
        return patterns
    
    def predict_price_movement(self, df: pd.DataFrame, days_ahead: int = 5) -> Dict[str, Any]:
        """预测未来价格走势"""
        if not self.available:
            return {
                'prediction': '中性',
                'confidence': 0.5,
                'reason': '数据分析器不可用'
            }
        
        # 检查数据量
        if df.empty or len(df) < 2 * days_ahead:
            return {
                'prediction': '中性',
                'confidence': 0.5,
                'reason': '数据不足'
            }
        
        # 使用pandas计算最近的价格变化趋势
        # 提取最近的收盘价数据
        close_series = df['close_price'].values
        
        # 确保有足够的数据
        if len(close_series) < 2 * days_ahead:
            return {
                'prediction': '中性',
                'confidence': 0.5,
                'reason': '数据不足'
            }
        
        # 计算最近和之前的平均价格
        recent_close = close_series[-days_ahead:]
        previous_close = close_series[-2*days_ahead:-days_ahead]
        
        # 计算平均值
        recent_avg = recent_close.mean()
        previous_avg = previous_close.mean()
        
        # 计算变化率
        change_rate = (recent_avg - previous_avg) / previous_avg
        
        # 根据变化率做出预测
        if change_rate > 0.05:
            prediction = '看涨'
            confidence = min(0.5 + change_rate * 5, 0.9)
        elif change_rate < -0.05:
            prediction = '看跌'
            confidence = min(0.5 + abs(change_rate) * 5, 0.9)
        else:
            prediction = '中性'
            confidence = 0.5
        
        return {
            'prediction': prediction,
            'confidence': confidence,
            'reason': f'基于最近{days_ahead}天的价格变化趋势'
        }
    
    def generate_analysis_report(self, stock_code: str, df: pd.DataFrame) -> List[PolarAnalysisResult]:
        """生成分析报告并转换为数据库模型"""
        if df.empty:
            return []
        
        # 获取模式识别结果
        patterns = self.recognize_patterns(df)
        
        # 获取预测结果
        prediction = self.predict_price_movement(df)
        
        results = []
        analysis_date = datetime.now().date()
        
        # 保存模式识别结果
        for pattern in patterns:
            result = PolarAnalysisResult(
                stock_code=stock_code,
                analysis_date=analysis_date,
                pattern_name=pattern['pattern_name'],
                confidence=pattern['confidence'],
                prediction=pattern['prediction'],
                details=pattern['details']
            )
            results.append(result)
        
        # 保存总体预测结果
        if results:
            # 如果已有模式识别结果，更新第一个结果的预测为总体预测
            results[0].prediction = prediction['prediction']
            results[0].details += f"\n总体预测: {prediction['prediction']}\n"
            results[0].details += f"置信度: {prediction['confidence']:.2f}\n"
            results[0].details += f"原因: {prediction['reason']}"
        
        return results
    
    def _detect_head_shoulder_top(self, df: pd.DataFrame) -> bool:
        """检测头肩顶形态"""
        # 简化的头肩顶形态检测算法
        # 实际实现需要更复杂的逻辑
        if len(df) < 20:
            return False
        
        # 获取价格序列
        prices = df['close_price'].values
        
        # 寻找潜在的头肩顶形态
        # 这里使用简化实现，实际应用中需要更复杂的算法
        window_size = min(5, len(df) // 4)
        
        # 计算局部最大值
        max_indices = []
        for i in range(1, len(prices) - 1):
            if prices[i] > prices[i-1] and prices[i] > prices[i+1]:
                max_indices.append(i)
        
        # 检查是否有足够的局部最大值来形成头肩顶
        if len(max_indices) < 3:
            return False
        
        return False  # 简化实现总是返回False，实际应用中需要更复杂的算法
    
    def _detect_double_bottom(self, df: pd.DataFrame) -> bool:
        """检测双底形态"""
        # 简化的双底形态检测算法
        if len(df) < 20:
            return False
        
        # 获取价格序列
        prices = df['close_price'].values
        
        # 寻找潜在的双底形态
        # 这里使用简化实现，实际应用中需要更复杂的算法
        window_size = min(5, len(df) // 4)
        
        # 计算局部最小值
        min_indices = []
        for i in range(1, len(prices) - 1):
            if prices[i] < prices[i-1] and prices[i] < prices[i+1]:
                min_indices.append(i)
        
        # 检查是否有足够的局部最小值来形成双底
        if len(min_indices) < 2:
            return False
        
        return False  # 简化实现总是返回False，实际应用中需要更复杂的算法
    
    def _detect_ascending_triangle(self, df: pd.DataFrame) -> bool:
        """检测上升三角形形态"""
        # 简化的上升三角形形态检测算法
        if len(df) < 20:
            return False
        
        # 获取价格序列
        highs = df['high_price'].values
        lows = df['low_price'].values
        
        # 简化实现
        # 实际应用中需要检查高点是否形成水平阻力线
        # 低点是否形成上升趋势线
        
        # 计算高低点的趋势
        high_trend = np.polyfit(range(len(highs)), highs, 1)[0]
        low_trend = np.polyfit(range(len(lows)), lows, 1)[0]
        
        # 上升三角形通常表现为高点趋势平缓，低点趋势上升
        return low_trend > 0 and abs(high_trend) < low_trend