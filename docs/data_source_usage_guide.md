# 数据源接口使用指南

## 概述

本文档详细介绍了 MyQuantWorld 项目中新增的数据源抽象层和切换功能，旨在帮助开发者理解如何使用统一的接口访问不同的数据源（AKShare 和 TuShare），以及如何平滑地在这些数据源之间进行切换。

## 1. 数据源抽象层设计

### 1.1 核心组件

数据源抽象层主要由以下几个核心组件构成：

- **BaseDataClient**: 抽象基类，定义了所有数据源客户端必须实现的接口方法
- **AKShareClient**: AKShare数据源的适配器实现
- **TuShareClient**: TuShare数据源的适配器实现
- **DataSourceFactory**: 数据源工厂类，负责创建和管理数据源客户端，实现数据源切换功能
- **DataSourceConfig**: 数据源配置管理类，负责加载、保存和管理数据源配置

### 1.2 统一接口方法

所有数据源适配器都实现了以下6个核心接口方法：

| 方法名 | 描述 | 参数 | 返回值 |
|-------|------|------|-------|
| `get_stock_basic_info()` | 获取股票基本信息 | 无 | pandas.DataFrame |
| `get_stock_daily_data(stock_code, start_date, end_date)` | 获取股票日线数据 | stock_code: 股票代码<br>start_date: 开始日期(YYYYMMDD)<br>end_date: 结束日期(YYYYMMDD) | pandas.DataFrame |
| `get_financial_indicators()` | 获取财务指标 | 无 | pandas.DataFrame |
| `get_hot_sectors()` | 获取热点板块 | 无 | pandas.DataFrame |
| `get_money_flow()` | 获取资金流向 | 无 | pandas.DataFrame |
| `get_macro_economic_data()` | 获取宏观经济数据 | 无 | pandas.DataFrame |

## 2. 使用统一接口

### 2.1 基本使用方法

通过 DataSourceFactory 来获取当前激活的数据源客户端，并调用统一接口：

```python
from data_fetching.data_source_factory import data_source_factory

# 获取当前激活的数据源客户端
client = data_source_factory.get_current_client()

# 调用统一接口方法
stock_basic_info = client.get_stock_basic_info()
daily_data = client.get_stock_daily_data('600000', '20240101', '20240131')
```

### 2.2 直接指定数据源

如果你想直接使用特定的数据源而不改变默认设置：

```python
# 直接使用AKShare数据源
akshare_client = data_source_factory.get_client('AKShare')
ak_stock_basic = akshare_client.get_stock_basic_info()

# 直接使用TuShare数据源（需要Token）
tushare_client = data_source_factory.get_client('TuShare', token='your_token_here')
ts_stock_basic = tushare_client.get_stock_basic_info()
```

## 3. 数据源切换功能

### 3.1 基本切换操作

使用 DataSourceFactory 来切换默认数据源：

```python
# 切换到AKShare数据源
data_source_factory.switch_data_source('AKShare')

# 切换到TuShare数据源（需要提供Token）
data_source_factory.switch_data_source('TuShare', token='your_token_here')
```

### 3.2 切换时的Token管理

TuShare数据源需要有效的API密钥：

```python
# 方法1：在切换时提供Token
data_source_factory.switch_data_source('TuShare', token='your_token_here')

# 方法2：先更新配置中的Token，再切换
tushare_config = data_source_factory.config.get_source_config('TuShare')
tushare_config['token'] = 'your_token_here'
data_source_factory.config.update_source_config('TuShare', tushare_config)
data_source_factory.switch_data_source('TuShare')
```

### 3.3 检查数据源可用性

在切换前，可以先检查数据源的可用性：

```python
# 检查AKShare数据源是否可用
if data_source_factory.is_akshare_available():
    print("AKShare数据源可用")

# 检查TuShare数据源是否可用
if data_source_factory.is_tushare_available():
    print("TuShare数据源可用")

# 获取所有可用数据源的状态
available_sources = data_source_factory.get_available_sources()
print(f"所有数据源状态: {available_sources}")
```

### 3.4 清除客户端缓存

如果需要重置客户端，可以清除缓存：

```python
# 清除特定数据源的缓存
data_source_factory.clear_client_cache('AKShare')

# 清除所有数据源的缓存
data_source_factory.clear_client_cache()
```

## 4. 错误处理和健康检查

### 4.1 客户端健康检查

每个数据源客户端都实现了健康检查功能：

```python
client = data_source_factory.get_current_client()
if client.is_healthy():
    print(f"{client.name} 数据源健康")
else:
    print(f"{client.name} 数据源异常")
    # 查看最后一个错误
    print(f"错误详情: {client.get_last_error()}")
```

### 4.2 切换时的错误处理

数据源切换过程中，如果发生错误，会尝试回滚到之前的客户端：

```python
try:
    # 尝试切换到TuShare
    new_client = data_source_factory.switch_data_source('TuShare', token='invalid_token')
    print("切换成功")
except Exception as e:
    print(f"切换失败: {str(e)}")
    # 检查当前客户端是否已回滚
    current = data_source_factory.get_current_client()
    print(f"当前客户端: {current.name}")
```

## 5. 用户界面操作

在应用的用户界面中，提供了数据源切换的交互功能：

1. **数据源选择**：在侧边栏可以选择 AKShare 或 TuShare 数据源
2. **配置设置**：对于 TuShare，可以在配置区域输入和保存 API 密钥
3. **测试连接**：可以测试数据源的连接状态和数据获取功能
4. **状态显示**：显示当前数据源的健康状态和连接信息
5. **错误查看**：查看数据源操作过程中的错误信息
6. **切换历史**：查看数据源的切换历史记录

## 6. 开发最佳实践

### 6.1 优先使用统一接口

在开发新功能时，应该优先使用统一接口，而不是直接依赖特定的数据源实现：

**推荐做法：**
```python
# 通过工厂获取客户端
client = data_source_factory.get_current_client()
# 使用统一接口
data = client.get_stock_basic_info()
```

**避免做法：**
```python
# 直接实例化特定数据源客户端
ak_client = AKShareClient()
data = ak_client.get_stock_basic_info()
```

### 6.2 处理可能的数据格式差异

虽然我们尽量确保不同数据源返回的数据格式一致，但在实际使用中仍需注意可能的差异：

```python
def process_stock_data(data):
    # 检查关键列是否存在
    required_columns = ['code', 'name']
    # 处理列名可能的差异
    column_mapping = {
        'ts_code': 'code',  # TuShare可能使用'ts_code'
        'stock_name': 'name',  # 可能的别名
    }
    
    # 重命名列
    for old_name, new_name in column_mapping.items():
        if old_name in data.columns:
            data = data.rename(columns={old_name: new_name})
    
    # 确保所有必需列都存在
    for col in required_columns:
        if col not in data.columns:
            # 处理缺失列
            print(f"警告: 缺少列 {col}")
    
    return data
```

### 6.3 实现平滑降级

当首选数据源不可用时，实现平滑降级到备选数据源：

```python
def get_data_with_fallback():
    # 首先检查当前数据源是否可用
    current_client = data_source_factory.get_current_client()
    if current_client.is_healthy():
        try:
            return current_client.get_stock_basic_info()
        except Exception as e:
            print(f"当前数据源获取失败: {str(e)}")
    
    # 当前数据源不可用，尝试切换到其他数据源
    available_sources = data_source_factory.get_available_sources()
    for source, available in available_sources.items():
        if available and source != current_client.name:
            try:
                print(f"尝试使用备用数据源: {source}")
                fallback_client = data_source_factory.switch_data_source(source)
                return fallback_client.get_stock_basic_info()
            except Exception as e:
                print(f"备用数据源 {source} 也失败: {str(e)}")
    
    # 所有数据源都不可用，返回空数据
    return pd.DataFrame()
```

## 7. 常见问题解答

### 7.1 TuShare Token 在哪里获取？

TuShare Token 可以通过在 TuShare 官网（https://tushare.pro/）注册账号并申请获得。免费用户有调用频率限制，付费用户可以获得更高的 API 调用额度。

### 7.2 数据源切换会影响现有数据吗？

数据源切换只会影响新获取的数据，不会改变已经保存或处理过的数据。建议在切换数据源后，根据需要重新获取和更新相关数据。

### 7.3 如何处理不同数据源返回的数据格式差异？

在使用统一接口获取数据后，可以实现数据转换函数，将不同数据源返回的数据转换为应用内部一致的数据格式。

### 7.4 如何监控数据源的可用性？

可以定期调用 `is_akshare_available()` 和 `is_tushare_available()` 方法来监控数据源的可用性，并在发现问题时及时通知用户或自动切换到备用数据源。

### 7.5 遇到 API 调用频率限制怎么办？

- 实现请求缓存机制，避免重复获取相同数据
- 对于 TuShare，可以考虑升级到付费套餐以获得更高的调用频率
- 在客户端实现更智能的重试机制，避免频繁失败的请求

## 8. 未来扩展

本设计支持轻松添加新的数据源适配器：

1. 创建一个新的适配器类，继承 `BaseDataClient`
2. 实现所有必需的 `_impl` 方法
3. 在 `DataSourceFactory` 中添加对新数据源的支持
4. 更新用户界面，添加新数据源的配置选项

---

通过以上文档，开发者可以了解如何使用统一的数据源接口，以及如何在不同数据源之间平滑切换。如有任何问题或需要进一步的支持，请联系项目维护者。