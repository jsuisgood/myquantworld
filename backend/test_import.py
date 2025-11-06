# 这个脚本直接放在backend目录下
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("开始测试导入...")
try:
    from data_fetching import akshare_client
    print("成功导入 data_fetching 模块")
except Exception as e:
    print(f"导入失败: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

print("测试完成")