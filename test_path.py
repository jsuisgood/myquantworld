import os
import sys

# 打印当前Python路径
print("当前Python路径:")
for path in sys.path:
    print(f"- {path}")

# 打印项目根目录
project_root = os.path.dirname(os.path.abspath(__file__))
print(f"\n项目根目录: {project_root}")

# 尝试导入data_fetching包
try:
    import data_fetching
    print("\n成功导入data_fetching包")
    print(f"data_fetching模块路径: {data_fetching.__file__}")
except ImportError as e:
    print(f"\n导入data_fetching包失败: {e}")

# 检查data_fetching目录是否存在
data_fetching_dir = os.path.join(project_root, "data_fetching")
print(f"\ndata_fetching目录存在: {os.path.exists(data_fetching_dir)}")
if os.path.exists(data_fetching_dir):
    print("data_fetching目录内容:")
    for item in os.listdir(data_fetching_dir):
        print(f"- {item}")