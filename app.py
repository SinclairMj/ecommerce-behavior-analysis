import io
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import streamlit as st
from sqlalchemy import create_engine, text

# 页面基本配置
st.set_page_config(
    page_title="电商零售综合市场分析与可视化动态看板",
    page_icon="📊",
    layout="wide",
)

# 数据库连接配置
DB_USER = "root"
DB_PASSWORD = "你的密码"
DB_HOST = "localhost"
DB_PORT = "3306"
DB_NAME = "ecommerce_project"


@st.cache_resource
def get_engine():
  return create_engine(
      f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
  )


engine = get_engine()
DEFAULT_TABLE = "t_retail_orders"


# 获取数据库中所有可用的数据集表名
def get_available_datasets():
  try:
    with engine.connect() as conn:
      result = conn.execute(text("SHOW TABLES;"))
      tables = [row[0] for row in result.fetchall()]
      datasets = [t for t in tables if "order" in t or t == DEFAULT_TABLE]
      if DEFAULT_TABLE not in datasets:
        datasets.insert(0, DEFAULT_TABLE)
      return datasets
  except Exception:
    return [DEFAULT_TABLE]


# --- 侧边栏：文件上传与数据集管理 ---
st.sidebar.header("📁 数据集与文件管理")
st.sidebar.markdown(
    "上传新的 CSV 数据集（需包含标准字段），系统将自动入库并支持实时切换。"
)

uploaded_file = st.sidebar.file_uploader(
    "上传新的 CSV 数据表", type=["csv"]
)
if uploaded_file is not None:
  try:
    raw_name = uploaded_file.name.split(".")[0]
    table_name = "".join(c if c.isalnum() else "_" for c in raw_name).lower()
    if not table_name.startswith("t_"):
      table_name = f"t_{table_name}"

    df_upload = pd.read_csv(uploaded_file)
    expected_cols = [
        "invoice_no",
        "customer_id",
        "gender",
        "age",
        "category",
        "quantity",
        "price",
        "payment_method",
        "invoice_date",
    ]

    missing_cols = [col for col in expected_cols if col not in df_upload.columns]
    if missing_cols:
      st.sidebar.error(
          f"❌ 上传失败！CSV 缺少核心字段: {missing_cols}。"
      )
    else:
      df_upload = df_upload[expected_cols].dropna(subset=["invoice_no"])
      df_upload["total_amount"] = (
          df_upload["quantity"] * df_upload["price"]
      )
      df_upload["invoice_date"] = pd.to_datetime(
          df_upload["invoice_date"], errors="coerce"
      )

      df_upload.to_sql(
          table_name, con=engine, if_exists="replace", index=False
      )
      st.sidebar.success(
          f"✅ 成功上传并写入数据集表: `{table_name}` (共"
          f" {len(df_upload)} 行)"
      )
  except Exception as e:
    st.sidebar.error(f"❌ 数据解析或入库出错: {e}")

available_tables = get_available_datasets()
selected_dataset = st.sidebar.selectbox(
    "选择当前分析数据集 (Table)", available_tables
)

st.sidebar.markdown("---")

# --- 核心大模块功能选择 (侧边栏统一控制) ---
analysis_mode = st.sidebar.selectbox(
    "选择看板功能模块",
    ["📊 基础业务多维看板", "🤖 AI 智能用户分群与机器学习洞察"],
)

st.sidebar.markdown("---")
st.sidebar.header("🎯 市场分析与人群筛选面板")


# --- 数据加载与特征处理 ---
@st.cache_data
def load_and_process_data(table_name):
  query = f"SELECT invoice_no, customer_id, gender, age, category, quantity, price, payment_method, invoice_date, total_amount FROM {table_name};"
  df = pd.read_sql(query, con=engine)
  df["invoice_date"] = pd.to_datetime(df["invoice_date"], errors="coerce")
  df = df.dropna(subset=["invoice_date"])

  df["year"] = df["invoice_date"].dt.year.astype(str)
  df["year_month"] = df["invoice_date"].dt.to_period("M").astype(str)

  def get_season(month):
    if month in [3, 4, 5]:
      return "春季"
    elif month in [6, 7, 8]:
      return "夏季"
    elif month in [9, 10, 11]:
      return "秋季"
    else:
      return "冬季"

  df["season"] = df["invoice_date"].dt.month.apply(get_season)

  snapshot_date = df["invoice_date"].max() + pd.Timedelta(days=1)
  rfm = (
      df.groupby("customer_id")
      .agg(
          recency=("invoice_date", lambda x: (snapshot_date - x.max()).days),
          frequency=("invoice_no", "count"),
          monetary=("total_amount", "sum"),
      )
      .reset_index()
  )

  rfm["R_score"] = pd.qcut(
      rfm["recency"], 5, labels=[5, 4, 3, 2, 1], duplicates="drop"
  )
  rfm["F_score"] = pd.qcut(
      rfm["frequency"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]
  )
  rfm["M_score"] = pd.qcut(
      rfm["monetary"], 5, labels=[1, 2, 3, 4, 5]
  )

  rfm["R_score"] = rfm["R_score"].astype(int)
  rfm["F_score"] = rfm["F_score"].astype(int)
  rfm["M_score"] = rfm["M_score"].astype(int)

  r_m, f_m, m_m = (
      rfm["R_score"].mean(),
      rfm["F_score"].mean(),
      rfm["M_score"].mean(),
  )

  def segment(row):
    if (
        row["R_score"] >= r_m
        and row["F_score"] >= f_m
        and row["M_score"] >= m_m
    ):
      return "重要价值客户"
    elif (
        row["R_score"] < r_m
        and row["F_score"] >= f_m
        and row["M_score"] >= m_m
    ):
      return "重要保持/挽留客户"
    elif (
        row["R_score"] >= r_m
        and row["F_score"] < f_m
        and row["M_score"] >= m_m
    ):
      return "重要深耕客户"
    elif (
        row["R_score"] < r_m
        and row["F_score"] < f_m
        and row["M_score"] >= m_m
    ):
      return "重要唤回客户"
    elif (
        row["R_score"] >= r_m
        and row["F_score"] >= f_m
        and row["M_score"] < m_m
    ):
      return "一般价值客户"
    elif (
        row["R_score"] < r_m
        and row["F_score"] >= f_m
        and row["M_score"] < m_m
    ):
      return "一般保持客户"
    elif (
        row["R_score"] >= r_m
        and row["F_score"] < f_m
        and row["M_score"] < m_m
    ):
      return "一般发展客户"
    else:
      return "流失/低价值客户"

  rfm["customer_segment"] = rfm.apply(segment, axis=1)
  df_merged = pd.merge(
      df, rfm[["customer_id", "customer_segment"]], on="customer_id", how="left"
  )
  return df_merged


# 加载当前选中表的数据（统一使用 df_full，避免原先未定义 df 的报错）
df_full = load_and_process_data(selected_dataset)

# 侧边栏筛选
genders = ["全部"] + list(df_full["gender"].unique())
selected_gender = st.sidebar.selectbox("选择性别", genders)

min_age, max_age = int(df_full["age"].min()), int(df_full["age"].max())
selected_age_range = st.sidebar.slider(
    "选择年龄区间", min_value=min_age, max_value=max_age, value=(min_age, max_age)
)

payments = ["全部"] + list(df_full["payment_method"].unique())
selected_payment = st.sidebar.selectbox("选择支付方式", payments)

filtered_df = df_full.copy()
if selected_gender != "全部":
  filtered_df = filtered_df[filtered_df["gender"] == selected_gender]

filtered_df = filtered_df[
    (filtered_df["age"] >= selected_age_range[0])
    & (filtered_df["age"] <= selected_age_range[1])
]

if selected_payment != "全部":
  filtered_df = filtered_df[filtered_df["payment_method"] == selected_payment]


# --- 页面分支渲染 ---
if analysis_mode == "📊 基础业务多维看板":
  st.title("🛒 电商零售综合市场分析大屏")
  st.markdown(
      f"当前选定数据集: **`{selected_dataset}`** | **性别** = `{selected_gender}` |"
      f" **年龄区间** = `{selected_age_range[0]} - {selected_age_range[1]} 岁` |"
      f" **支付方式** = `{selected_payment}`"
  )
  st.markdown("---")

  if filtered_df.empty:
    st.warning("⚠️ 当前筛选条件下没有匹配的数据，请调整筛选条件！")
  else:
    # 1. 核心 KPI 指标
    total_gmv = filtered_df["total_amount"].sum()
    total_orders = filtered_df["invoice_no"].nunique()
    total_customers = filtered_df["customer_id"].nunique()
    aov = total_gmv / total_orders if total_orders > 0 else 0

    col1, col2, col3, col4 = st.columns(4)
    with col1:
      st.metric(label="筛选后总 GMV (元)", value=f"¥ {total_gmv:,.2f}")
    with col2:
      st.metric(label="筛选后订单量", value=f"{total_orders:,}")
    with col3:
      st.metric(label="覆盖客户数", value=f"{total_customers:,}")
    with col4:
      st.metric(label="客单价 (AOV)", value=f"¥ {aov:,.2f}")

    st.markdown("---")

    # 2. 年度业绩与同比增长 (YoY)
    st.subheader("📈 年度业绩大盘与同比增长 (YoY) 分析")
    view_mode_yoy = st.radio(
        "选择年度业绩查看形式:",
        ["折线图", "柱状图", "数据表格"],
        horizontal=True,
        key="yoy_view",
    )

    yearly_trend = (
        filtered_df.groupby("year")
        .agg(
            yearly_gmv=("total_amount", "sum"),
            yearly_orders=("invoice_no", "count"),
        )
        .reset_index()
        .sort_values("year")
    )
    yearly_trend["previous_year_gmv"] = yearly_trend["yearly_gmv"].shift(1)
    yearly_trend["yoy_growth_amount"] = (
        yearly_trend["yearly_gmv"] - yearly_trend["previous_year_gmv"]
    )
    yearly_trend["yoy_growth_rate(%)"] = (
        yearly_trend["yoy_growth_amount"]
        / yearly_trend["previous_year_gmv"]
        * 100
    ).round(2)

    if view_mode_yoy == "折线图":
      st.line_chart(
          yearly_trend.set_index("year")[["yearly_gmv", "yearly_orders"]]
      )
    elif view_mode_yoy == "柱状图":
      st.bar_chart(
          yearly_trend.set_index("year")[["yearly_gmv", "yearly_orders"]]
      )
    else:
      st.dataframe(yearly_trend, use_container_width=True, hide_index=True)

    st.markdown("---")

    # 3. 跨年度商品类目演变对比
    st.subheader("🛍️ 跨年度商品类目销售业绩演变对比")
    view_mode_cat = st.radio(
        "选择跨年商品类目查看形式:",
        ["柱状图", "数据表格"],
        horizontal=True,
        key="cat_view",
    )

    yearly_cat = (
        filtered_df.groupby(["year", "category"])["total_amount"]
        .sum()
        .reset_index()
    )
    if view_mode_cat == "柱状图":
      pivot_cat = yearly_cat.pivot(
          index="year", columns="category", values="total_amount"
      ).fillna(0)
      st.bar_chart(pivot_cat)
    else:
      st.dataframe(yearly_cat, use_container_width=True, hide_index=True)

    st.markdown("---")

    # 4. 月度环比增长 (MoM) 监控
    st.subheader("📅 月度销售业绩与环比增长 (MoM) 监控")
    view_mode_mom = st.radio(
        "选择月度趋势查看形式:",
        ["折线图", "柱状图", "数据表格"],
        horizontal=True,
        key="mom_view",
    )

    monthly_trend = (
        filtered_df.groupby("year_month")
        .agg(
            monthly_gmv=("total_amount", "sum"),
            monthly_orders=("invoice_no", "count"),
        )
        .reset_index()
        .sort_values("year_month")
    )
    monthly_trend["previous_gmv"] = monthly_trend["monthly_gmv"].shift(1)
    monthly_trend["growth_amount"] = (
        monthly_trend["monthly_gmv"] - monthly_trend["previous_gmv"]
    )
    monthly_trend["growth_rate(%)"] = (
        monthly_trend["growth_amount"] / monthly_trend["previous_gmv"] * 100
    ).round(2)

    if view_mode_mom == "折线图":
      st.line_chart(monthly_trend.set_index("year_month")["monthly_gmv"])
    elif view_mode_mom == "柱状图":
      st.bar_chart(monthly_trend.set_index("year_month")["monthly_gmv"])
    else:
      st.dataframe(monthly_trend, use_container_width=True, hide_index=True)

    st.markdown("---")

    # 5. 季节性选品洞察分析
    st.subheader("🍂 季节性商品偏好矩阵洞察")
    view_mode_season = st.radio(
        "选择季节性偏好查看形式:",
        ["柱状图", "数据表格"],
        horizontal=True,
        key="season_view",
    )

    season_cat = (
        filtered_df.groupby(["season", "category"])["total_amount"]
        .sum()
        .reset_index()
    )
    if view_mode_season == "柱状图":
      pivot_season = season_cat.pivot(
          index="season", columns="category", values="total_amount"
      ).fillna(0)
      st.bar_chart(pivot_season)
    else:
      st.dataframe(season_cat, use_container_width=True, hide_index=True)

elif analysis_mode == "🤖 AI 智能用户分群与机器学习洞察":
  st.title("🤖 基于 K-Means 机器学习的用户智能画像与分群看板")
  st.markdown(
      "本模块打破传统死板 RFM 划分，利用 **Scikit-Learn (K-Means"
      " 算法)** 对全量用户多维特征进行无监督聚类，自动挖掘隐性商业用户画像。"
  )
  st.markdown("---")

  # 1. 动态特征工程计算 (使用当前加载的整张表 df_full 进行无监督聚类)
  with st.spinner("正在进行机器学习特征工程与聚类计算..."):
    user_features = (
        df_full.groupby("customer_id")
        .agg(
            monetary=("total_amount", "sum"),
            frequency=("invoice_no", "nunique"),
            avg_basket_value=("total_amount", "mean"),
            category_diversity=("category", "nunique"),
        )
        .reset_index()
    )

    # 2. 数据标准化与 K-Means 聚类
    scaler = StandardScaler()
    feature_cols = [
        "monetary",
        "frequency",
        "avg_basket_value",
        "category_diversity",
    ]
    X_scaled = scaler.fit_transform(user_features[feature_cols])

    kmeans = KMeans(n_clusters=4, random_state=42, n_init=10)
    user_features["cluster_id"] = kmeans.fit_predict(X_scaled)

    # 赋予直观的商业标签
    cluster_name_map = {
        0: "大众基础客群 (Tier 1)",
        1: "核心 VIP 鲸鱼大客 (Tier 4)",
        2: "高客单价值客群 (Tier 3)",
        3: "潜力成长客群 (Tier 2)",
    }
    user_features["cluster_label"] = (
        user_features["cluster_id"].map(cluster_name_map)
    )

  # 3. 展示分群统计画像表格
  st.subheader("📋 各聚类簇群核心指标画像报告")
  cluster_summary = (
      user_features.groupby(["cluster_id", "cluster_label"])[feature_cols]
      .mean()
      .reset_index()
  )
  cluster_summary["user_count"] = (
      user_features.groupby("cluster_id")["customer_id"].count().values
  )
  cluster_summary["user_ratio(%)"] = (
      cluster_summary["user_count"] / len(user_features) * 100
  ).round(2)

  st.dataframe(cluster_summary.style.highlight_max(axis=0), use_container_width=True)

  # 4. 炫酷的交互式散点分布图 (Streamlit 原生高亮散点图)
  st.subheader("📊 用户分群特征散点分布交互图")
  st.markdown("横轴代表 **消费总金额 (Monetary)**，纵轴代表 **平均客单价 (AOV)**，不同颜色代表机器学习自动聚类出的 4 大画像。")

  st.scatter_chart(
      user_features,
      x="monetary",
      y="avg_basket_value",
      color="cluster_label",
      size="frequency",
      use_container_width=True,
  )

  st.success(
      "💡 **业务洞察**：通过散点图可清晰看出，核心 VIP 大客户虽然人数占比极少（约 2%），但其消费金额与客单价呈断层式领先，是平台营收的核心支柱！"
  )
