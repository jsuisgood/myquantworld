import os
import sys
# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 测试模块导入
try:
    from data_fetching.akshare_client import AkshareClient
    print("成功导入 data_fetching.akshare_client")
except ImportError as e:
    print(f"导入 data_fetching.akshare_client 失败: {e}")

try:
    from data_storage.db_storage import DBStorage
    print("成功导入 data_storage.db_storage")
except ImportError as e:
    print(f"导入 data_storage.db_storage 失败: {e}")

try:
    from analysis.technical_analyzer import TechnicalAnalyzer
    print("成功导入 analysis.technical_analyzer")
except ImportError as e:
    print(f"导入 analysis.technical_analyzer 失败: {e}")

print("测试完成")