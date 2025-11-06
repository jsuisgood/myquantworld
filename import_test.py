import sys
import os

# 打印当前路径信息
print(f"当前工作目录: {os.getcwd()}")
print(f"脚本目录: {os.path.dirname(os.path.abspath(__file__))}")

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
print(f"修改后的Python路径: {sys.path[0]}")

# 尝试导入模块
try:
    from data_fetching import akshare_client
    print("成功导入 data_fetching.akshare_client 模块")
except ImportError as e:
    print(f"导入失败: {e}")
    import traceback
    traceback.print_exc()