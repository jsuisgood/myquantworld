# MyQuantWorld - 股票分析系统

基于akshare和POLAR的股票分析应用，使用PostgreSQL存储数据，Streamlit构建前端界面，FastAPI提供后端API服务。

## 项目架构

```
myquantworld/
├── backend/             # 后端API服务
│   └── main.py          # FastAPI主入口
├── frontend/            # 前端应用
│   └── app.py           # Streamlit应用主入口
├── database/            # 数据库相关
│   ├── config.py        # 数据库配置
│   ├── connection.py    # 数据库连接管理
│   └── models.py        # 数据库模型定义
├── data_fetching/       # 数据获取模块
│   └── akshare_client.py # Akshare客户端
├── data_processing/     # 数据处理模块
│   └── data_processor.py # 数据处理工具
├── data_storage/        # 数据存储模块
│   └── db_storage.py    # 数据库存储管理
├── analysis/            # 分析模块
│   ├── technical_analyzer.py # 技术分析工具
│   └── polar_analyzer.py     # POLAR模式识别和预测
├── requirements.txt     # 项目依赖
├── .env                 # 环境变量配置
└── .env.example         # 环境变量示例
```

## 功能特性

- **数据获取**：通过akshare获取股票历史数据、基本面数据和宏观经济数据
- **数据存储**：使用PostgreSQL存储数据，支持批量操作和查询优化
- **技术分析**：计算各种技术指标（MA、MACD、RSI、布林带、KDJ等）
- **POLAR分析**：集成POLAR进行模式识别和价格预测
- **可视化界面**：使用Streamlit构建交互式可视化界面
- **API服务**：提供RESTful API供其他应用调用

## 技术栈

- **后端**：Python 3.9+, FastAPI
- **前端**：Streamlit, Plotly
- **数据库**：PostgreSQL
- **数据处理**：pandas, numpy
- **分析工具**：akshare, polar, scikit-learn

## 快速开始

### 1. 环境要求

- Python 3.9+
- PostgreSQL 13+

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

复制示例环境变量文件并根据实际情况修改：

```bash
cp .env.example .env
```

编辑`.env`文件，设置数据库连接信息：

```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=myquantworld
DB_USER=postgres
DB_PASSWORD=postgres
```

### 4. 启动应用

#### 启动Streamlit前端

```bash
cd frontend
streamlit run app.py
```

访问 `http://localhost:8501` 查看前端界面。

#### 启动FastAPI后端

```bash
cd backend
python main.py
```

访问 `http://localhost:8000/docs` 查看API文档。

## API文档

启动后端服务后，可以访问以下地址查看交互式API文档：

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

主要API端点：

- `GET /api/stocks` - 获取股票列表
- `GET /api/stocks/{stock_code}` - 获取股票基本信息
- `GET /api/stocks/{stock_code}/daily-data` - 获取股票日线数据
- `GET /api/stocks/{stock_code}/technical-analysis` - 获取技术分析结果
- `GET /api/stocks/{stock_code}/polar-analysis` - 获取POLAR分析结果
- `GET /api/stocks/{stock_code}/financial-indicators` - 获取财务指标
- `GET /api/macro-economic/{indicator}` - 获取宏观经济数据
- `GET /api/system/status` - 获取系统状态

## 注意事项

1. 确保PostgreSQL数据库已正确安装并运行
2. 首次运行时，系统会自动创建数据库表结构
3. 获取数据时可能受到API调用频率限制，请合理使用
4. POLAR库可能需要单独安装，请按照官方文档进行配置

## 扩展建议

1. 添加用户认证和授权功能
2. 实现数据缓存机制，减少API调用
3. 添加更多技术指标和分析方法
4. 实现策略回测功能
5. 添加实时行情监控功能

## 许可证

MIT