import pandas as pd
from sqlalchemy import create_engine

# 连接配置
engine = create_engine('mysql+pymysql://root:root123@localhost:3306/ecommerce_project')

# 读取整张表进行数据检查
df = pd.read_sql('t_retail_orders', con=engine)

print("=== 数据基本信息 ===")
print(df.info())

print("\n=== 前 3 行数据预览 ===")
print(df.head(3))

print("\n=== 各商品类目销售额统计 ===")
category_sales = df.groupby('category')['total_amount'].sum().reset_index()
print(category_sales.sort_values(by='total_amount', ascending=False))