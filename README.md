# ══════════════════════════════════════
# HR薪酬与人才分析看板
# ══════════════════════════════════════

> 一个基于 Streamlit + Plotly 的交互式 HR 数据分析系统  
> 支持薪酬考勤、人力成本、人才盘点多维度分析，图表可交互、可导出

---

## 一、功能特性

| 模块 | 功能 |
|------|------|
| 🏠 综合仪表板 | KPI卡片、成本趋势、风险概览 |
| 💰 薪酬考勤分析 | 部门对比、出勤组合图、考勤热力图、员工明细 |
| 💼 人力成本分析 | 成本堆积图、瀑布图、TOP10岗位、环比增长 |
| 🎯 人才盘点分析 | 九宫格矩阵、绩效分布、离职风险仪表盘、继任计划 |
| 📝 一键生成周报 | Markdown报告 + ZIP数据包一键下载 |

**安全特性：**
- ✅ 密码保护（密码存储在 Streamlit Secrets，不硬编码）
- ✅ `.gitignore` 已配置，真实数据不会上传到 GitHub
- ✅ 支持本地运行，数据完全不出本机

---

## 二、本地运行（最简单，推荐）

### 步骤1：安装依赖
```bash
pip install -r requirements.txt
```

### 步骤2：生成示例数据（可选）
```bash
python generate_sample_data.py
```
> 生成3个月模拟数据到 `data_sample/` 目录，用于测试看板功能

### 步骤3：启动看板
```bash
streamlit run app.py
```
> 浏览器自动打开 `http://localhost:8501`  
> 首次访问密码：`hr2026`（可在 `auth.py` 中修改）

---

## 三、部署到 Streamlit Cloud（永久公网链接）

### 准备工作
1. 注册 [GitHub](https://github.com) 账号
2. 注册 [Streamlit Cloud](https://share.streamlit.io) 账号（免费）

### 步骤1：上传代码到 GitHub

1. 登录 GitHub，点击右上角 `+` → `New repository`
2. 仓库名填写：`hr-dashboard`（建议设为 **Private 私有仓库**）
3. 点击 `Create repository`
4. 按照 GitHub 提示，将本地代码推送到仓库：
   ```bash
   git init
   git add .
   git commit -m "初始提交"
   git branch -M main
   git remote add origin https://github.com/你的用户名/hr-dashboard.git
   git push -u origin main
   ```

> ⚠️ **重要**：`data_sample/` 目录已被 `.gitignore` 排除，真实数据不会上传！

### 步骤2：部署到 Streamlit Cloud

1. 登录 [Streamlit Cloud](https://share.streamlit.io)
2. 点击 `New app`
3. 选择你的 GitHub 仓库（`hr-dashboard`）
4. 主文件路径填写：`app.py`
5. 点击 `Deploy`

> 等待约2-3分钟，部署完成后会生成永久链接，例如：  
> `https://你的用户名-hr-dashboard.streamlit.app`

### 步骤3：设置访问密码（重要！）

1. 在 Streamlit Cloud 的应用管理页面，找到你的应用
2. 点击 `Settings` → `Secrets`
3. 添加以下配置：
   ```toml
   hr_dashboard_password = "你的强密码"
   ```
4. 点击 `Save`，应用会自动重新部署
5. 现在访问你的看板链接，会要求输入密码

> ✅ 只有知道密码的人才能查看数据  
> ✅ 密码存储在云端，不会暴露在代码中

---

## 四、数据文件说明

### 文件命名规则
| 文件类型 | 命名格式 | 示例 |
|-----------|-----------|------|
| 薪酬考勤 | `payroll_YYYYMM.xlsx` | `payroll_202601.xlsx` |
| 人力成本 | `hr_cost_YYYYMM.xlsx` | `hr_cost_202601.xlsx` |
| 人才盘点 | `talent_review_YYYYMM.xlsx` | `talent_review_202601.xlsx` |

### 放置位置
- **本地运行**：放入 `data_sample/` 目录，刷新页面即可
- **云端部署**：在看板侧边栏使用"上传数据文件"功能上传

> ⚠️ **云端部署时**：上传的文件仅临时存储，刷新后需重新上传  
> 如需永久存储，请将文件通过 GitHub 提交到仓库（确保仓库为私有）

---

## 五、字段说明

### 薪酬考勤表（payroll_YYYYMM.xlsx）
| 字段名 | 类型 | 说明 |
|--------|------|------|
| 员工ID | 文本 | 唯一标识 |
| 姓名 | 文本 | |
| 部门 | 文本 | |
| 基本工资 | 数字 | |
| 绩效工资 | 数字 | |
| 加班费 | 数字 | |
| 扣款 | 数字 | |
| 实发工资 | 数字 | |
| 应出勤天数 | 数字 | |
| 实际出勤天数 | 数字 | |
| 迟到次数 | 数字 | |
| 缺勤天数 | 数字 | |

### 人力成本表（hr_cost_YYYYMM.xlsx）
| 字段名 | 类型 | 说明 |
|--------|------|------|
| 部门 | 文本 | |
| 岗位 | 文本 | |
| 工资总额 | 数字 | |
| 社保公积金 | 数字 | |
| 福利费 | 数字 | |
| 招聘费 | 数字 | |
| 培训费 | 数字 | |
| 总成本 | 数字 | |

### 人才盘点表（talent_review_YYYYMM.xlsx）
| 字段名 | 类型 | 说明 |
|--------|------|------|
| 员工ID | 文本 | |
| 姓名 | 文本 | |
| 部门 | 文本 | |
| 绩效等级 | 文本 | S/A/B/C/D |
| 潜力评级 | 文本 | 高/中/低 |
| 离职风险 | 文本 | 高/中/低 |
| 关键岗位 | 是/否 | |
| 继任者准备度 | 文本 | 可晋升/准备中/待评估 |

---

## 六、注意事项

### 数据安全
- ✅ 真实HR数据**不要**上传到公开GitHub仓库
- ✅ 建议使用**私有仓库**或仅本地运行
- ✅ 密码通过 Streamlit Secrets 管理，不在代码中明文存储
- ✅ `.gitignore` 已配置，防止误提交数据文件

### 云端部署限制
- Streamlit Cloud 免费版支持**公有仓库**部署
- 如需部署**私有仓库**，需要 Streamlit Cloud Pro（$10/月）
- 或者：部署框架代码（不含数据），数据通过看板上传功能临时加载

---

## 七、故障排除

| 问题 | 解决方案 |
|------|---------|
| 密码忘记了 | 在 Streamlit Cloud Secrets 中重新设置 |
| 数据文件上传失败 | 检查文件命名是否符合 `YYYYMM` 格式 |
| 图表显示异常 | 检查Excel字段名是否与文档一致 |
| 部署后看不到数据 | 云端部署需重新上传数据文件 |

---

*最后更新：2026-06-12*
