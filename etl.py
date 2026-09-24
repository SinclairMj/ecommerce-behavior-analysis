import pandas as pd
from sqlalchemy import create_engine

# 1. 数据库连接配置 (请把密码换成你实际的MySQL密码)
DB_USER = 'root'
DB_PASSWORD = 'root123'
DB_HOST = 'localhost'
DB_PORT = '3306'
DB_NAME = 'ecommerce_project'

engine = create_engine(f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}')

print("正在读取 CSV 数据...")
# 直接读取，因为 CSV 自带表头
df = pd.read_csv('UserBehavior.csv')

print("开始数据清洗...")
# 1. 丢弃完全多余的空列（从刚才的 head 看到后面有很多无用的空列）
df = df.dropna(how='all', axis=1)

# 2. 去除重复行
df.drop_duplicates(inplace=True)

# 3. 转换日期格式 (原格式是 2022/8/5)
df['invoice_date'] = pd.to_datetime(df['invoice_date'], format='%Y/%m/%d')

# 4. 计算总金额（数量 × 单价，方便后续做销售额分析）
df['total_amount'] = df['quantity'] * df['price']

print("正在将数据批量写入 MySQL 数据库...")
# 写入 MySQL，表名改为 t_retail_orders
df.to_sql('t_retail_orders', con=engine, if_exists='replace', index=False, chunksize=10000)

print("恭喜！零售数据集 ETL 流程跑通，数据已成功入库！")