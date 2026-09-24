import pandas as pd
from sqlalchemy import create_engine

# 数据库连接配置 (请确保密码正确)
DB_USER = 'root'
DB_PASSWORD = 'root123'
DB_HOST = 'localhost'
DB_PORT = '3306'
DB_NAME = 'ecommerce_project'

engine = create_engine(f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}')

print("================ 模块三：RFM 客户价值模型分析 ================\n")

# 1. 从数据库读取订单明细
query = "SELECT customer_id, invoice_no, invoice_date, total_amount FROM t_retail_orders;"
df = pd.read_sql(query, con=engine)

# 确保日期格式正确
df['invoice_date'] = pd.to_datetime(df['invoice_date'])

# 2. 计算 RFM 原始指标
# 设定一个基准参考日（取数据集中最大日期再加一天，确保 R 的计算基准正确）
max_date = df['invoice_date'].max()
print(f"数据集中订单的最大日期为: {max_date.strftime('%Y-%m-%d')}")
snapshot_date = max_date + pd.Timedelta(days=1)

# 按客户聚合计算 R, F, M
rfm_df = df.groupby('customer_id').agg(
    recency=('invoice_date', lambda x: (snapshot_date - x.max()).days),
    frequency=('invoice_no', 'count'),
    monetary=('total_amount', 'sum')
).reset_index()

print(f"参与 RFM 分析的总客户数: {len(rfm_df)}")

# 3. 对 R, F, M 进行 1-5 分打分 (使用 qcut 分位函数)
# 注意：R 是越小越好（最近买过），所以打分时需要倒序降序；F 和 M 是越大越好
rfm_df['R_score'] = pd.qcut(rfm_df['recency'], 5, labels=[5, 4, 3, 2, 1], duplicates='drop')
rfm_df['F_score'] = pd.qcut(rfm_df['frequency'].rank(method='first'), 5, labels=[1, 2, 3, 4, 5])
rfm_df['M_score'] = pd.qcut(rfm_df['monetary'], 5, labels=[1, 2, 3, 4, 5])

# 将打分转换为数值型
rfm_df['R_score'] = rfm_df['R_score'].astype(int)
rfm_df['F_score'] = rfm_df['F_score'].astype(int)
rfm_df['M_score'] = rfm_df['M_score'].astype(int)

# 计算 R、F、M 的均值，用于后续客户精细化分层
r_med = rfm_df['R_score'].mean()
f_med = rfm_df['F_score'].mean()
m_med = rfm_df['M_score'].mean()

print(f"R/F/M 评分均值基准 -> R_mean: {r_med:.2f}, F_mean: {f_med:.2f}, M_mean: {m_med:.2f}")

# 4. 客户精细化打标规则
def rfm_segmentation(row):
    # 简化版经典八大模型判断逻辑
    if row['R_score'] >= r_med and row['F_score'] >= f_med and row['M_score'] >= m_med:
        return '重要价值客户'
    elif row['R_score'] < r_med and row['F_score'] >= f_med and row['M_score'] >= m_med:
        return '重要保持/挽留客户'
    elif row['R_score'] >= r_med and row['F_score'] < f_med and row['M_score'] >= m_med:
        return '重要深耕客户'
    elif row['R_score'] < r_med and row['F_score'] < f_med and row['M_score'] >= m_med:
        return '重要唤回客户'
    elif row['R_score'] >= r_med and row['F_score'] >= f_med and row['M_score'] < m_med:
        return '一般价值客户'
    elif row['R_score'] < r_med and row['F_score'] >= f_med and row['M_score'] < m_med:
        return '一般保持客户'
    elif row['R_score'] >= r_med and row['F_score'] < f_med and row['M_score'] < m_med:
        return '一般发展客户'
    else:
        return '流失/低价值客户'

rfm_df['customer_segment'] = rfm_df.apply(rfm_segmentation, axis=1)

# 5. 统计各分层客户占比与贡献
segment_summary = rfm_df.groupby('customer_segment').agg(
    customer_count=('customer_id', 'count'),
    total_monetary=('monetary', 'sum'),
    avg_monetary=('monetary', 'mean')
).reset_index()

segment_summary['user_percentage(%)'] = (segment_summary['customer_count'] / len(rfm_df) * 100).round(2)
segment_summary['total_monetary'] = segment_summary['total_monetary'].round(2)
segment_summary['avg_monetary'] = segment_summary['avg_monetary'].round(2)

print("\n4. 客户 RFM 分层统计结果：")
print(segment_summary.sort_values(by='total_monetary', ascending=False).to_string(index=False))
print("\n============================================================")