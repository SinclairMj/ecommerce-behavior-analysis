# 🛒 电商零售综合市场分析与动态 BI 智能看板

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-App-red)](https://streamlit.io/)
[![MySQL](https://img.shields.io/badge/Database-MySQL-orange)](https://www.mysql.com/)

## 📌 项目用途与业务场景
本项目是一个面向电商零售运营、市场分析师及管理层的**端到端数据分析与动态 BI 看板系统**。
主要解决以下实际业务痛点：
* **多维大盘监控**：实时追踪平台总 GMV、订单量、活跃用户及客单价（AOV）。
* **时间序列分析**：提供直观的**年度同比增长 (YoY)** 与 **月度环比增长 (MoM)** 监控，辅助管理层进行业绩复盘。
* **市场与人群洞察**：支持按性别、年龄段、支付方式进行侧边栏多维联动筛选，精准定位特定细分市场的偏好。
* **季节性选品矩阵**：自动化归纳不同季节下各商品类目的销售占比，指导市场部进行科学备货与营销。
* **RFM 客户价值分层**：利用动态打分模型识别高价值客户与流失风险客户，赋能精准营销。

---

## 🚀 核心功能亮点
1. **动态 CSV 文件上传与入库**：支持在网页端直接上传新的标准格式 CSV 数据集，系统自动校验字段、计算衍生指标并写入 MySQL，实现多数据集自由切换对比。
2. **多形式视图自由切换**：打破传统单一表格的局限，所有时序与品类分析均支持**“折线图 / 柱状图 / 数据表格”**一键自由切换，提升数据可读性。
3. **全链路技术栈**：Python (Pandas) + MySQL (SQLAlchemy) + Streamlit 构建的轻量级、响应式 Web 数据应用。
<img width="3838" height="1895" alt="image" src="https://github.com/user-attachments/assets/f9c09989-2268-4e6a-9f52-80d281ebc8b9" />
<img width="3356" height="1484" alt="image" src="https://github.com/user-attachments/assets/dc78808f-d436-4431-b7c0-f762d7bcb66f" />

---

## 🛠️ 快速上手与运行指南

数据库配置

```
DB_USER = "root"
DB_PASSWORD = "你的MySQL密码"
DB_HOST = "localhost"
DB_PORT = "3306"
DB_NAME = "ecommerce_project"
```

1.启动看板
在项目根目录下执行以下命令启动 Streamlit 服务
```
streamlit run app.py
```
在浏览器中打开提示的本地链接（通常为 http://localhost:8501）即可体验！

2.标准 CSV 上传格式要求
请确保 CSV 文件包含以下标准表头字段：
invoice_no,customer_id,gender,age,category,quantity,price,payment_method,invoice_date

3.测试数据
淘宝用户行为数据集，可做用户聚类分析，消费者行为分析
下载地址：https://tianchi.aliyun.com/dataset/224006

### 1. 环境准备
确保本地或服务器已安装 Python 3.8+ 及 MySQL 数据库。
安装依赖包：
```bash
pip install -r requirements.txt
