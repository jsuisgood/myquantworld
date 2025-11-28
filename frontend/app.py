import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import sys
import os
import requests

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入项目模块
from data_fetching.data_source_factory import data_source_factory
from data_processing.data_processor import DataProcessor
from analysis.technical_analyzer import TechnicalAnalyzer

from database.connection import get_db, SessionLocal
from database.models import StockBasicInfo, StockDailyData
from data_storage.db_storage import DBStorage

class StockAnalysisApp:
    """股票分析应用"""
    
    def __init__(self):
        # 初始化应用状态
        if 'page' not in st.session_state:
            st.session_state.page = 'overview'
        
        # 初始化共享组件
        # 默认使用TuShare数据源
        token = st.session_state.get("tushare_token")
        self.data_client = data_source_factory.get_client("tushare", token=token)
        self.processor = DataProcessor()
        self.tech_analyzer = TechnicalAnalyzer()
        self.db_storage = DBStorage()
        self.db = next(get_db())
        
        # 添加数据源切换功能
        self._initialize_data_source_ui()
    
    def _initialize_data_source_ui(self):
        """初始化数据源UI组件"""
        # 在侧边栏添加数据源设置选项
        with st.sidebar.expander("🔄 数据源设置", expanded=False):
            st.markdown("### 数据源配置")
            config_container = st.container()
            
            # 只显示TuShare配置选项
            with config_container:
                # TuShare需要API密钥
                tushare_token = st.text_input(
                    "TuShare API Token:",
                    type="password",
                    help="输入您的TuShare API密钥以获取数据访问体验",
                    key="tushare_token"
                )
                
                # 保存Token的按钮
                if st.button("保存Token", key="save_tushare_token"):
                    if tushare_token:
                        # 保存Token到会话状态
                        st.session_state.tushare_token = tushare_token
                        
                        # 更新数据客户端
                        try:
                            self.data_client = data_source_factory.switch_data_source("tushare", token=tushare_token)
                            st.success("Token已保存并更新数据源")
                            # 刷新页面以应用新的配置
                            st.experimental_rerun()
                        except Exception as e:
                            st.error(f"更新数据源失败: {str(e)}")
                    else:
                        st.error("请输入有效的Token")
                
                # 数据源测试区域
                st.markdown("### 数据源测试")
                
                if st.button("测试数据源连接", key="test_data_source"):
                    with st.spinner("正在测试TuShare数据源..."):
                        try:
                            # 获取测试用的客户端
                            test_client = data_source_factory.get_client(
                                "tushare",
                                token=st.session_state.get("tushare_token")
                            )
                            
                            # 执行简单的测试请求
                            test_df = test_client.get_stock_basic_info()
                            
                            if not test_df.empty:
                                st.success("TuShare数据源连接成功！")
                                st.info(f"测试返回了{len(test_df)}条股票数据")
                            else:
                                st.warning("TuShare数据源连接成功，但返回空数据")
                        except Exception as e:
                            st.error(f"TuShare数据源连接失败: {str(e)}")
            
            # 显示数据源状态
            st.markdown("### 数据源状态")
            
            # 检查当前活动数据源的健康状态
            try:
                st.write("**当前数据源**: TuShare")
                
                # 显示健康状态
                health_status = "✅ 健康" if hasattr(self.data_client, 'is_healthy') and self.data_client.is_healthy() else "⚠️ 未知"
                st.write(f"**健康状态**: {health_status}")
                
                # 显示最近错误（如果有）
                if hasattr(self.data_client, 'get_last_error'):
                    last_error = self.data_client.get_last_error()
                    if last_error:
                        with st.expander("查看最近错误", expanded=False):
                            st.error(last_error)
            except Exception as e:
                st.warning(f"无法获取数据源状态: {str(e)}")
        
    
    def load_stock_list(self):
        """加载股票列表"""
        # 先尝试从数据库加载
        stocks = self.db_storage.get_stock_list(self.db)
        
        if not stocks:
            # 如果数据库为空，从当前数据源获取
            stock_df = self.data_client.get_stock_basic_info()
            if not stock_df.empty:
                # 准备数据
                stock_data = []
                for _, row in stock_df.iterrows():
                    # 假设股票代码和名称是分开的两列
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
    
    def load_stock_data(self, stock_code, start_date, end_date, force_refresh=False):
        """加载股票数据，支持强制刷新获取最新数据"""
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
        
        # 检查是否需要更新数据
        need_update = False
        
        # 如果强制刷新，或者数据库中没有数据，或者数据不是最新的，需要更新
        if force_refresh or not db_data:
            need_update = True
        else:
            # 检查数据库中的最新数据日期
            latest_date = self.db_storage.get_latest_stock_date(stock_code)
            if latest_date and latest_date < end_date:
                # 如果数据库中的最新数据日期早于请求的结束日期，需要更新
                need_update = True
                # 更新时间范围，只获取新的数据
                update_start_date = latest_date + timedelta(days=1)
            elif not latest_date:
                # 如果没有最新数据日期，也需要更新
                need_update = True
        
        if need_update:
            # 确定要获取的数据范围
            fetch_start_date = update_start_date if 'update_start_date' in locals() else start_date
            
            # 从当前数据源获取数据
            df = self.data_client.get_stock_daily_data(
                stock_code, 
                fetch_start_date.strftime('%Y%m%d'), 
                end_date.strftime('%Y%m%d')
            )
            
            if not df.empty:
                # 清洗数据
                cleaned_df = self.processor.clean_stock_daily_data(df)
                
                # 准备数据用于数据库存储
                records = self.processor.prepare_stock_for_db(cleaned_df, stock_code)
                
                # 保存到数据库
                self.db_storage.save_stock_daily_data(self.db, stock_code, records)
                
                # 重新加载
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
    
    def display_overview_page(self):
        """显示总览页面"""
        st.title("📈 MyQuantWorld 股票分析系统")
        st.header("欢迎使用股票分析平台")
        
        # 创建卡片式导航
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("### K线分析")
            st.markdown("详细的个股K线图和技术指标分析")
            if st.button("进入K线分析", width='stretch'):
                st.session_state.page = 'kline'
        
        with col2:
            st.markdown("### 热点板块")
            st.markdown("实时查看市场热点板块和行业表现")
            if st.button("查看热点板块", width='stretch'):
                st.session_state.page = 'sectors'
        
        with col3:
            st.markdown("### 强势股票")
            st.markdown("筛选市场中的强势股和潜在投资机会")
            if st.button("浏览强势股票", width='stretch'):
                st.session_state.page = 'strong_stocks'
        
        # 市场概览信息
        st.header("📊 市场概览")
        
        # 加载一些示例数据（如果有）
        st.info("点击上方卡片进入相应功能模块")
        
        # 系统信息
        st.header("ℹ️ 系统信息")
        st.write("版本: 1.0.0")
        st.write("更新时间: 2024年")
    
    def display_kline_page(self):
        """显示K线分析页面"""
        st.title("📈 K线分析")
        
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
        default_start_date = default_end_date - timedelta(days=365*3)  # 近3年数据
        
        start_date = st.sidebar.date_input(
            "开始日期",
            default_start_date
        )
        
        end_date = st.sidebar.date_input(
            "结束日期",
            default_end_date
        )
        
        # 数据操作按钮
        st.sidebar.header("数据操作")
        col_load1, col_load2 = st.sidebar.columns(2)
        with col_load1:
            load_data_button = st.button("加载数据", key="load_data_kline")
        with col_load2:
            # 添加刷新数据按钮，强制获取最新数据
            refresh_data_button = st.button("🔄 刷新数据", key="refresh_data_kline")
        
        # 初始化变量
        df = pd.DataFrame()
        
        # 当用户点击加载数据或刷新数据按钮时执行
        if load_data_button or refresh_data_button:
            # 判断是否需要强制刷新
            force_refresh = refresh_data_button
            
            # 确保时间范围是近3年
            load_end_date = default_end_date
            load_start_date = load_end_date - timedelta(days=365*3)
            
            # 当点击加载数据按钮时，先通过API更新股票数据
            if load_data_button:
                with st.spinner(f"正在更新 {selected_stock_display} 的最新数据..."):
                    try:
                        # 调用后端API更新单只股票数据
                        api_url = f"http://localhost:8000/api/stocks/{selected_stock_code}/update"
                        response = requests.post(api_url, timeout=10)
                        
                        if response.status_code == 200:
                            result = response.json()
                            st.success(f"数据更新成功: {result.get('message', '股票数据已更新')}")
                        else:
                            st.warning(f"数据更新可能不完整，状态码: {response.status_code}")
                    except requests.exceptions.RequestException as e:
                        st.warning(f"无法连接到后端服务: {str(e)}. 将尝试直接加载数据。")
                    except Exception as e:
                        st.warning(f"更新数据时出错: {str(e)}. 将尝试直接加载数据。")
            
            # 加载股票数据
            with st.spinner(f"正在加载 {selected_stock_display} 的近3年数据..."):
                # 调用数据加载方法
                df = self.load_stock_data(selected_stock_code, load_start_date, load_end_date, force_refresh=force_refresh)
        
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
        
        st.plotly_chart(fig, width='stretch')
        
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
                st.plotly_chart(fig_macd, width='stretch')
            
            elif indicator == "RSI" and "RSI" in df.columns:
                fig_rsi = go.Figure()
                fig_rsi.add_trace(go.Scatter(x=df['trade_date'], y=df['RSI'], name='RSI'))
                fig_rsi.add_hline(y=70, line_dash="dash", line_color="red", name="超买线")
                fig_rsi.add_hline(y=30, line_dash="dash", line_color="green", name="超卖线")
                fig_rsi.update_layout(title="RSI指标", xaxis_title="日期", yaxis_title="RSI值", yaxis_range=[0, 100])
                st.plotly_chart(fig_rsi, width='stretch')
            
            elif indicator == "布林带" and all(col in df.columns for col in ['close_price', 'Upper_Band', 'Lower_Band', 'SMA20']):
                fig_bb = go.Figure()
                fig_bb.add_trace(go.Scatter(x=df['trade_date'], y=df['close_price'], name='收盘价'))
                fig_bb.add_trace(go.Scatter(x=df['trade_date'], y=df['Upper_Band'], name='上轨'))
                fig_bb.add_trace(go.Scatter(x=df['trade_date'], y=df['Lower_Band'], name='下轨'))
                fig_bb.add_trace(go.Scatter(x=df['trade_date'], y=df['SMA20'], name='中轨'))
                fig_bb.update_layout(title="布林带指标", xaxis_title="日期", yaxis_title="价格")
                st.plotly_chart(fig_bb, width='stretch')
            
            elif indicator == "KDJ" and all(col in df.columns for col in ['K', 'D', 'J']):
                fig_kdj = go.Figure()
                fig_kdj.add_trace(go.Scatter(x=df['trade_date'], y=df['K'], name='K线'))
                fig_kdj.add_trace(go.Scatter(x=df['trade_date'], y=df['D'], name='D线'))
                fig_kdj.add_trace(go.Scatter(x=df['trade_date'], y=df['J'], name='J线'))
                fig_kdj.add_hline(y=80, line_dash="dash", line_color="red", name="超买线")
                fig_kdj.add_hline(y=20, line_dash="dash", line_color="green", name="超卖线")
                fig_kdj.update_layout(title="KDJ指标", xaxis_title="日期", yaxis_title="值", yaxis_range=[0, 100])
                st.plotly_chart(fig_kdj, width='stretch')
        
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
    
    def display_sectors_page(self):
        """显示热点板块页面"""
        st.title("热点板块分析")
        
        # 使用类中已初始化的ak_client
        
        # 获取热点板块数据
        with st.spinner("正在获取热点板块数据..."):
            try:
                # 尝试使用新的热点板块数据获取方法
                sectors_df = self.data_client.get_hot_sectors()
                
                # 如果数据为空，使用模拟数据
                if sectors_df.empty:
                    st.warning("无法获取实时热点板块数据，使用模拟数据")
                    self._show_mock_sectors_data()
                else:
                    # 添加涨跌幅颜色标记
                    def highlight_change(val):
                        color = 'green' if val > 0 else 'red'
                        return f'color: {color}'
                    
                    # 显示热点板块表格
                    st.subheader("今日热点板块涨幅榜")
                    
                    # 根据数据结构确定列名
                    if 'sector_name' in sectors_df.columns:
                        # 使用英文列名的数据
                        display_columns = ['sector_name', 'change_percent', 'leading_stock']
                        if 'volume' in sectors_df.columns:
                            display_columns.append('volume')
                        
                        # 重命名显示列
                        rename_dict = {
                            'sector_name': '板块名称',
                            'change_percent': '涨跌幅',
                            'leading_stock': '领涨股',
                            'volume': '成交量'
                        }
                        display_df = sectors_df.rename(columns=rename_dict)
                        styled_df = display_df.style.applymap(highlight_change, subset=['涨跌幅'])
                    elif '板块名称' in sectors_df.columns:
                        # 使用中文列名的数据
                        display_columns = ['板块名称', '涨跌幅', '领涨股']
                        if '成交量' in sectors_df.columns:
                            display_columns.append('成交量')
                        
                        display_df = sectors_df[display_columns]
                        styled_df = display_df.style.applymap(highlight_change, subset=['涨跌幅'])
                    else:
                        # 默认显示所有列
                        display_df = sectors_df
                        styled_df = display_df
                    
                    st.dataframe(styled_df, width='stretch')
                    
                    # 显示板块涨幅图表
                    st.subheader("板块涨幅分布")
                    
                    # 根据数据结构确定图表数据
                    if 'sector_name' in sectors_df.columns and 'change_percent' in sectors_df.columns:
                        names = sectors_df['sector_name'][:10]  # 只显示前10个板块
                        changes = sectors_df['change_percent'][:10]
                    elif '板块名称' in sectors_df.columns and '涨跌幅' in sectors_df.columns:
                        names = sectors_df['板块名称'][:10]  # 只显示前10个板块
                        changes = sectors_df['涨跌幅'][:10]
                    else:
                        # 如果列名不匹配，使用模拟数据
                        names = ['人工智能', '新能源', '医药生物', '半导体', '金融服务', '消费零售', '房地产', '军工']
                        changes = [3.2, 2.8, 1.5, 4.1, 0.9, -0.5, -1.2, 2.3]
                    
                    # 使用plotly创建图表
                    fig = go.Figure(data=[go.Bar(x=names, y=changes, marker_color=['red' if x > 0 else 'green' for x in changes])])
                    fig.update_layout(title="板块涨跌幅排行", xaxis_title="板块", yaxis_title="涨跌幅(%)")
                    st.plotly_chart(fig, width='stretch')
            
                    # 添加概念板块标签页
                    st.subheader("概念板块")
                    with st.spinner("正在获取概念板块数据..."):
                        try:
                            concept_df = self.data_client.get_concept_sectors()
                            if not concept_df.empty:
                                st.dataframe(concept_df, width='stretch')
                            else:
                                st.info("暂无概念板块数据")
                        except Exception:
                            st.info("获取概念板块数据失败")
            
                    # 板块详情查询
                    st.subheader("板块详情查询")
                    sector_code = st.text_input("请输入板块代码查询板块内股票：")
                    if sector_code:
                        with st.spinner(f"正在获取板块 {sector_code} 的股票列表..."):
                            try:
                                stocks_df = self.data_client.get_sector_stocks(sector_code)
                                if not stocks_df.empty:
                                    st.dataframe(stocks_df, width='stretch')
                                else:
                                    st.info(f"未找到板块 {sector_code} 的股票信息")
                            except Exception:
                                st.info(f"获取板块 {sector_code} 股票信息失败")
            except Exception as e:
                st.warning(f"获取热点板块数据出错: {str(e)}")
                self._show_mock_sectors_data()
    
    def _show_mock_sectors_data(self):
        """显示模拟的板块数据"""
        mock_data = {
            "板块名称": ["半导体", "新能源", "医药生物", "金融服务", "消费电子"],
            "涨跌幅": [3.5, 2.8, -1.2, 0.5, 4.2],
            "成交额(亿)": [450, 320, 280, 520, 380],
            "领涨股": ["中芯国际", "宁德时代", "恒瑞医药", "招商银行", "立讯精密"]
        }
        df = pd.DataFrame(mock_data)
        
        # 添加颜色标记
        def highlight_positive(s):
            return ['background-color: #d4edda' if v > 0 else 'background-color: #f8d7da' if v < 0 else '' for v in s]
        
        styled_df = df.style.apply(highlight_positive, subset=['涨跌幅'])
        st.dataframe(styled_df, width='stretch')
        
        # 简单图表
        fig = go.Figure(data=[go.Bar(x=df['板块名称'], y=df['涨跌幅'], marker_color=['red' if x > 0 else 'green' for x in df['涨跌幅']])])
        fig.update_layout(title="板块涨跌幅排行", xaxis_title="板块", yaxis_title="涨跌幅(%)")
        st.plotly_chart(fig, width='stretch')
    
    def display_strong_stocks_page(self):
        """显示强势股票页面"""
        st.title("🚀 强势股票")
        st.markdown("筛选市场中的强势股和潜在投资机会")
        
        # 加载股票列表
        stocks = self.load_stock_list()
        
        # 模拟强势股数据
        if stocks:
            # 简单筛选逻辑（实际应基于技术指标）
            st.info("强势股筛选中...")
            
            # 显示模拟数据
            mock_data = {
                "股票代码": ["600519", "000858", "300750", "601888", "002594"],
                "股票名称": ["贵州茅台", "五粮液", "宁德时代", "中国中免", "比亚迪"],
                "今日涨幅": [2.8, 3.5, 5.2, 1.8, 4.6],
                "5日涨幅": [8.2, 7.5, 12.8, 5.2, 15.3],
                "技术信号": ["买入", "买入", "强烈买入", "持有", "强烈买入"]
            }
            df = pd.DataFrame(mock_data)
            
            # 添加颜色标记
            def highlight_signals(s):
                colors = []
                for v in s:
                    if v == '强烈买入':
                        colors.append('background-color: #28a745; color: white')
                    elif v == '买入':
                        colors.append('background-color: #d4edda')
                    elif v == '持有':
                        colors.append('background-color: #fff3cd')
                    elif v == '卖出':
                        colors.append('background-color: #f8d7da')
                    else:
                        colors.append('')
                return colors
            
            styled_df = df.style.apply(highlight_signals, subset=['技术信号'])
            st.dataframe(styled_df, width='stretch')
            
            # 涨幅分布图表
            fig = go.Figure(data=[go.Bar(x=df['股票名称'], y=df['5日涨幅'], marker_color='rgba(54, 162, 235, 0.7)')])
            fig.update_layout(title="5日涨幅排行", xaxis_title="股票", yaxis_title="涨幅(%)")
            st.plotly_chart(fig, width='stretch')
        else:
            st.error("无法加载股票数据")
    
    def display_navigation(self):
        """显示导航菜单"""
        st.sidebar.title("导航菜单")
        
        if st.sidebar.button("🏠 总览页面", width='stretch'):
            st.session_state.page = 'overview'
        
        if st.sidebar.button("📈 K线分析", width='stretch'):
            st.session_state.page = 'kline'
        
        if st.sidebar.button("🔥 热点板块", width='stretch'):
            st.session_state.page = 'sectors'
        
        if st.sidebar.button("🚀 强势股票", width='stretch'):
            st.session_state.page = 'strong_stocks'
    
    def run(self):
        """运行应用"""
        st.set_page_config(
            page_title="MyQuantWorld - 股票分析系统",
            page_icon="📈",
            layout="wide"
        )
        
        # 显示导航菜单
        self.display_navigation()
        
        # 根据当前页面状态显示对应内容
        if st.session_state.page == 'overview':
            self.display_overview_page()
        elif st.session_state.page == 'kline':
            self.display_kline_page()
        elif st.session_state.page == 'sectors':
            self.display_sectors_page()
        elif st.session_state.page == 'strong_stocks':
            self.display_strong_stocks_page()

if __name__ == "__main__":
    app = StockAnalysisApp()
    app.run()