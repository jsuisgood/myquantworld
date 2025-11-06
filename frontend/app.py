import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入项目模块
from data_fetching.akshare_client import AkshareClient
from data_processing.data_processor import DataProcessor
from analysis.technical_analyzer import TechnicalAnalyzer

from database.connection import get_db, SessionLocal
from database.models import StockBasicInfo, StockDailyData
from data_storage.db_storage import DBStorage

class StockAnalysisApp:
    """股票分析应用"""
    
    def __init__(self):
        self.ak_client = AkshareClient()
        self.processor = DataProcessor()
        self.tech_analyzer = TechnicalAnalyzer()
        self.db_storage = DBStorage()
        self.db = next(get_db())
    
    def load_stock_list(self):
        """加载股票列表"""
        # 先尝试从数据库加载
        stocks = self.db_storage.get_stock_list(self.db)
        
        if not stocks:
            # 如果数据库为空，从akshare获取
            stock_df = self.ak_client.get_stock_basic_info()
            if not stock_df.empty:
                # 准备数据
                stock_data = []
                for _, row in stock_df.iterrows():
                    # 假设股票代码和名称是分开的两列
                    # 根据akshare返回的实际列名调整
                    if len(row) >= 2:
                        stock_data.append({
                            'code': row.iloc[0],
                            'name': row.iloc[1],
                            'market': 'SH' if str(row.iloc[0]).startswith('6') else 'SZ'
                        })
                
                # 保存到数据库
                self.db_storage.save_stock_basic_info(self.db, stock_data)
                
                # 重新加载
                stocks = self.db_storage.get_stock_list(self.db)
        
        return stocks
    
    def load_stock_data(self, stock_code, start_date, end_date):
        """加载股票数据"""
        # 确保日期格式为date类型
        if isinstance(start_date, datetime):
            start_date = start_date.date()
        if isinstance(end_date, datetime):
            end_date = end_date.date()
            
        # 先尝试从数据库加载
        db_data = self.db_storage.get_stock_daily_data(
            self.db, 
            stock_code, 
            start_date, 
            end_date
        )
        
        if not db_data:
            # 如果数据库中没有数据，从akshare获取
            df = self.ak_client.get_stock_daily_data(stock_code, start_date.strftime('%Y%m%d'), end_date.strftime('%Y%m%d'))
            
            if not df.empty:
                # 清洗数据
                cleaned_df = self.processor.clean_stock_daily_data(df)
                
                # 准备数据用于数据库存储
                records = self.processor.prepare_stock_for_db(cleaned_df, stock_code)
                
                # 保存到数据库
                self.db_storage.save_stock_daily_data(self.db, stock_code, records)
                
                # 重新加载，确保使用正确的日期类型
                db_data = self.db_storage.get_stock_daily_data(
                    self.db, 
                    stock_code, 
                    start_date, 
                    end_date
                )
        
        # 转换为DataFrame
        if db_data:
            data = []
            for record in db_data:
                data.append({
                    'trade_date': record['trade_date'],
                    'open_price': record['open_price'],
                    'high_price': record['high_price'],
                    'low_price': record['low_price'],
                    'close_price': record['close_price'],
                    'volume': record['volume'],
                    'amount': record['amount']
                })
            
            df = pd.DataFrame(data)
            df['trade_date'] = pd.to_datetime(df['trade_date'])
            df = df.sort_values('trade_date')
            
            # 计算技术指标
            df = self.tech_analyzer.calculate_all_indicators(df)
            
            return df
        
        return pd.DataFrame()
    
    def run(self):
        """运行应用"""
        st.set_page_config(
            page_title="MyQuantWorld - 股票分析系统",
            page_icon="📈",
            layout="wide"
        )
        
        st.title("📈 MyQuantWorld 股票分析系统")
        
        # 加载股票列表
        stocks = self.load_stock_list()
        
        if not stocks:
            st.error("无法加载股票列表，请检查网络连接或数据库配置")
            return
        
        # 侧边栏配置
        st.sidebar.header("股票选择")
        
        # 创建股票代码和名称的映射
        stock_options = {f"{stock.stock_code} - {stock.stock_name}": stock.stock_code for stock in stocks}
        
        # 股票选择
        selected_stock_display = st.sidebar.selectbox(
            "选择股票",
            options=list(stock_options.keys()),
            index=0
        )
        
        selected_stock_code = stock_options[selected_stock_display]
        
        # 时间范围选择
        st.sidebar.header("时间范围")
        
        default_end_date = datetime.now()
        default_start_date = default_end_date - timedelta(days=365)
        
        start_date = st.sidebar.date_input(
            "开始日期",
            default_start_date
        )
        
        end_date = st.sidebar.date_input(
            "结束日期",
            default_end_date
        )
        
        # 加载股票数据
        with st.spinner("加载数据中..."):
            df = self.load_stock_data(selected_stock_code, start_date, end_date)
        
        if df.empty:
            st.error("无法加载股票数据，请检查股票代码或时间范围")
            return
        
        # 显示基本信息
        st.subheader(f"{selected_stock_display} 分析")
        
        # 价格走势图
        st.header("价格走势")
        
        # 创建图表
        fig = make_subplots(rows=2, cols=1, 
                           shared_xaxes=True,
                           vertical_spacing=0.1,
                           subplot_titles=("价格与移动平均线", "成交量"),
                           row_heights=[0.7, 0.3])
        
        # 添加K线图
        fig.add_trace(
            go.Candlestick(x=df['trade_date'],
                          open=df['open_price'],
                          high=df['high_price'],
                          low=df['low_price'],
                          close=df['close_price'],
                          name="K线"),
            row=1, col=1
        )
        
        # 添加移动平均线
        for ma in ['MA5', 'MA20', 'MA60']:
            if ma in df.columns:
                fig.add_trace(
                    go.Scatter(x=df['trade_date'], y=df[ma], name=ma),
                    row=1, col=1
                )
        
        # 添加成交量
        fig.add_trace(
            go.Bar(x=df['trade_date'], y=df['volume'], name="成交量", marker_color='rgba(0, 0, 255, 0.5)'),
            row=2, col=1
        )
        
        # 更新布局
        fig.update_layout(
            title=f"{selected_stock_display} 价格走势",
            xaxis_title="日期",
            yaxis_title="价格",
            xaxis_rangeslider_visible=False,
            height=600
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # 技术指标分析
        st.header("技术指标分析")
        
        # 创建技术指标选项
        indicator_options = {
            "MACD": "MACD指标",
            "RSI": "RSI指标",
            "布林带": "布林带指标",
            "KDJ": "KDJ指标"
        }
        
        selected_indicators = st.multiselect(
            "选择技术指标",
            options=list(indicator_options.keys()),
            default=["MACD", "RSI"]
        )
        
        # 显示选择的技术指标
        for indicator in selected_indicators:
            if indicator == "MACD" and all(col in df.columns for col in ['MACD', 'Signal_Line', 'MACD_Hist']):
                fig_macd = go.Figure()
                fig_macd.add_trace(go.Scatter(x=df['trade_date'], y=df['MACD'], name='MACD'))
                fig_macd.add_trace(go.Scatter(x=df['trade_date'], y=df['Signal_Line'], name='信号线'))
                fig_macd.add_trace(go.Bar(x=df['trade_date'], y=df['MACD_Hist'], name='柱状图'))
                fig_macd.update_layout(title="MACD指标", xaxis_title="日期", yaxis_title="值")
                st.plotly_chart(fig_macd, use_container_width=True)
            
            elif indicator == "RSI" and "RSI" in df.columns:
                fig_rsi = go.Figure()
                fig_rsi.add_trace(go.Scatter(x=df['trade_date'], y=df['RSI'], name='RSI'))
                fig_rsi.add_hline(y=70, line_dash="dash", line_color="red", name="超买线")
                fig_rsi.add_hline(y=30, line_dash="dash", line_color="green", name="超卖线")
                fig_rsi.update_layout(title="RSI指标", xaxis_title="日期", yaxis_title="RSI值", yaxis_range=[0, 100])
                st.plotly_chart(fig_rsi, use_container_width=True)
            
            elif indicator == "布林带" and all(col in df.columns for col in ['close_price', 'Upper_Band', 'Lower_Band', 'SMA20']):
                fig_bb = go.Figure()
                fig_bb.add_trace(go.Scatter(x=df['trade_date'], y=df['close_price'], name='收盘价'))
                fig_bb.add_trace(go.Scatter(x=df['trade_date'], y=df['Upper_Band'], name='上轨'))
                fig_bb.add_trace(go.Scatter(x=df['trade_date'], y=df['Lower_Band'], name='下轨'))
                fig_bb.add_trace(go.Scatter(x=df['trade_date'], y=df['SMA20'], name='中轨'))
                fig_bb.update_layout(title="布林带指标", xaxis_title="日期", yaxis_title="价格")
                st.plotly_chart(fig_bb, use_container_width=True)
            
            elif indicator == "KDJ" and all(col in df.columns for col in ['K', 'D', 'J']):
                fig_kdj = go.Figure()
                fig_kdj.add_trace(go.Scatter(x=df['trade_date'], y=df['K'], name='K线'))
                fig_kdj.add_trace(go.Scatter(x=df['trade_date'], y=df['D'], name='D线'))
                fig_kdj.add_trace(go.Scatter(x=df['trade_date'], y=df['J'], name='J线'))
                fig_kdj.add_hline(y=80, line_dash="dash", line_color="red", name="超买线")
                fig_kdj.add_hline(y=20, line_dash="dash", line_color="green", name="超卖线")
                fig_kdj.update_layout(title="KDJ指标", xaxis_title="日期", yaxis_title="值", yaxis_range=[0, 100])
                st.plotly_chart(fig_kdj, use_container_width=True)
        

        
        # 技术指标信号
        st.header("技术指标信号")
        
        # 生成信号
        signals = self.tech_analyzer.generate_signals(df)
        
        if signals:
            # 创建信号表格
            signal_data = []
            for signal in signals:
                signal_data.append({
                    "指标": signal['indicator_name'],
                    "值": signal['indicator_value'],
                    "信号": signal['signal'],
                    "强度": signal['strength']
                })
            
            st.table(signal_data)
            
            # 计算总体信号
            buy_signals = sum(1 for s in signals if s['signal'] == 'BUY')
            sell_signals = sum(1 for s in signals if s['signal'] == 'SELL')
            
            if buy_signals > sell_signals:
                overall_signal = "看涨"
                color = "green"
            elif sell_signals > buy_signals:
                overall_signal = "看跌"
                color = "red"
            else:
                overall_signal = "中性"
                color = "gray"
            
            st.markdown(f"### 总体信号: <span style='color:{color}'>{overall_signal}</span>", unsafe_allow_html=True)
            st.markdown(f"买入信号: {buy_signals} | 卖出信号: {sell_signals}")
        else:
            st.info("暂无明显的技术指标信号")
        
        # 数据统计摘要
        st.header("数据统计摘要")
        
        # 计算统计指标
        stats = {
            "数据起始日期": df['trade_date'].min().strftime('%Y%m%d'),
            "数据结束日期": df['trade_date'].max().strftime('%Y%m%d'),
            "数据点数": len(df),
            "最新价格": df['close_price'].iloc[-1],
            "最高价": df['high_price'].max(),
            "最低价": df['low_price'].min(),
            "平均价格": df['close_price'].mean(),
            "价格波动率": df['close_price'].pct_change().std() * np.sqrt(252) * 100
        }
        
        # 显示统计信息
        for key, value in stats.items():
            if isinstance(value, float):
                st.write(f"**{key}**: {value:.2f}")
            else:
                st.write(f"**{key}**: {value}")

if __name__ == "__main__":
    app = StockAnalysisApp()
    app.run()