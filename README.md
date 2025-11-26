- 🛡️ **风险控制**

  - Long Only（只做多，禁止做空）
  - MA200 趋势过滤器（避免熊市）
  - VIX 波动率过滤

- 🔄 **策略对比模式**

  - 一键对比所有策略表现
  - 并排展示关键指标
  - 多策略资金曲线叠加图

- 💾 **本地数据缓存**
  - 自动缓存历史数据（24 小时有效）
  - 手动更新数据功能
  - 支持 1y/2y/5y/10y 回测周期

---

## 🚀 快速开始

### 环境要求

- Python 3.9 或更高版本
- pip 包管理器

### 安装步骤

```bash
# 1. 克隆仓库
git clone https://github.com/cnhjp/quant-trading-system.git
cd quant-trading-system

# 2. 安装依赖
pip install -r requirements.txt

# 3. 运行应用
streamlit run app.py
```

应用将在浏览器中自动打开 `http://localhost:8501`

---

## 📖 使用指南

### 基本操作

1. **选择标的**：支持 SPY 和 QQQ
2. **设置初始资金**：默认 10,000 美元
3. **选择策略**：从下拉菜单选择策略（默认：每日定投）
4. **设置回测周期**：1 年、2 年、5 年或 10 年（默认：1 年）
5. **点击"开始回测"**：查看回测结果

### 策略对比模式

1. 勾选侧边栏的"对比所有策略"
2. 点击"开始回测"
3. 系统将自动运行所有策略并生成对比表格和图表

### 更新数据

点击"更新数据"按钮强制从 Yahoo Finance 重新下载最新数据。

---

## 🎯 策略说明

### 1. 流动性掠夺 (SFP)

**核心理念**：捕捉假突破后的反转机会

**买入条件**：

- 最低价 < 昨日最低价 (PDL)
- 收盘价 > 昨日最低价
- 收盘价 > MA200（趋势过滤）

**卖出条件**：

- 出现看跌 SFP 形态
- 收盘价 < MA200

**适用场景**：震荡市、区间突破

---

### 2. 趋势共振

**核心理念**：顺势而为，低波动环境入场

**买入条件**：

- 收盘价 > 月度锚定 VWAP
- VIX < VIX 20 日均线

**卖出条件**：

- 收盘价 < VWAP

**适用场景**：趋势市场、低波动期

---

### 3. 均值回归 (RSI)

**核心理念**：超卖反弹，配合趋势过滤

**买入条件**：

- RSI < 45（优化后阈值）
- 收盘价 > MA200

**卖出条件**：

- RSI > 70
- 收盘价 < MA200

**适用场景**：震荡市、超卖反弹

---

### 4. 每日定投 (DCA)

**核心理念**：将初始资金平分到每个交易日

**执行逻辑**：

- 每日在开盘价买入固定金额
- 剩余现金保持不动
- 对比一次性投入基准

**适用场景**：长期投资、降低择时风险

---

## 📁 项目结构

```
quant-trading-system/
│
├── app.py                  # Streamlit 主应用
├── data_loader.py          # 数据获取和缓存模块
├── strategies.py           # 交易策略实现
├── backtester.py           # 回测引擎
├── test_system.py          # 测试脚本
│
├── requirements.txt        # Python 依赖
├── .gitignore             # Git 忽略规则
├── README.md              # 项目文档
│
└── data/                  # 本地数据缓存（自动生成）
    ├── SPY_1y_1d.csv
    └── ...
```

---

## 🔧 技术栈

| 技术          | 用途         | 版本  |
| ------------- | ------------ | ----- |
| **Python**    | 核心语言     | 3.9+  |
| **Streamlit** | Web 界面框架 | 1.31+ |
| **yfinance**  | 获取股票数据 | -     |
| **pandas**    | 数据处理     | -     |
| **numpy**     | 数值计算     | -     |
| **plotly**    | 交互式图表   | -     |

---

## 📊 性能指标说明

| 指标         | 说明                             |
| ------------ | -------------------------------- |
| **总收益率** | (最终净值 - 初始资金) / 初始资金 |
| **基准收益** | SPY Buy & Hold 策略的收益率      |
| **胜率**     | 盈利交易天数 / 总交易天数        |
| **最大回撤** | 从峰值到谷底的最大跌幅百分比     |

---

## 🌐 部署

### Streamlit Community Cloud（推荐）

1. 将代码推送到 GitHub
2. 访问 [share.streamlit.io](https://share.streamlit.io)
3. 连接 GitHub 仓库
4. 选择 `app.py` 作为主文件
5. 点击 Deploy

**优势**：免费、官方支持、自动部署

### Railway / Render

支持 Python 应用的其他免费部署平台，配置简单。

---

## ⚠️ 免责声明

本项目仅用于教育和研究目的。

- ⚠️ 回测结果不代表未来表现
- ⚠️ 投资有风险，入市需谨慎
- ⚠️ 请勿将本系统用于实盘交易决策
- ⚠️ 作者不对任何投资损失负责

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

### 贡献指南

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 📝 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

---

## 📧 联系方式

如有问题或建议，欢迎通过以下方式联系：

- 📧 Email: your-email@example.com
- 💬 GitHub Issues: [提交问题](https://github.com/cnhjp/quant-trading-system/issues)

---

<div align="center">

⭐ 如果这个项目对您有帮助，请给个 Star！

Made with ❤️ by [Your Name]

</div>
