# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os, re, io, base64, zipfile, json
from datetime import datetime
import auth

st.set_page_config(page_title="HR分析看板", page_icon="📊", layout="wide", initial_sidebar_state="expanded")
if not auth.check_password():
    st.stop()

COLOR_BG   = "#F8FAFC"
COLOR_CARD = "#FFFFFF"

def extract_month(fn):
    m = re.search(r'(\d{6})', fn)
    return m.group(1) if m else None

def load_data_from_private_repo():
    """从私有GitHub仓库读取真实HR数据（通过Personal Access Token认证）"""
    try:
        token = st.secrets.get("github_data_token", "")
        repo = st.secrets.get("github_data_repo", "")
    except Exception:
        return None, None, None
    if not token or not repo:
        return None, None, None

    import requests as req

    # 尝试读取 data/ 目录和根目录下的数据文件
    pd_l, cd_l, td_l = [], [], []
    paths_to_check = ["data", ""]

    for data_path in paths_to_check:
        api_url = f"https://api.github.com/repos/{repo}/contents/{data_path}"
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        try:
            resp = req.get(api_url, headers=headers, timeout=15)
            if resp.status_code != 200:
                continue
            items = resp.json()
            if not isinstance(items, list):
                continue
            for item in items:
                fn = item.get("name", "")
                if not fn.endswith((".xlsx", ".xls")):
                    continue
                m = extract_month(fn)
                download_url = item.get("download_url", "")
                if not download_url:
                    continue
                try:
                    file_resp = req.get(download_url, headers=headers, timeout=30)
                    if file_resp.status_code != 200:
                        continue
                    df = pd.read_excel(io.BytesIO(file_resp.content))
                    df["_month"] = m
                    if fn.startswith("payroll_"):
                        pd_l.append(df)
                    elif fn.startswith("hr_cost_"):
                        cd_l.append(df)
                    elif fn.startswith("talent_"):
                        td_l.append(df)
                except Exception:
                    continue
        except Exception:
            continue

    pr = pd.concat(pd_l, ignore_index=True) if pd_l else None
    co = pd.concat(cd_l, ignore_index=True) if cd_l else None
    ta = pd.concat(td_l, ignore_index=True) if td_l else None
    return pr, co, ta

def load_all_data():
    pd_l, cd_l, td_l = [], [], []
    # 搜索 data/ 和 data_sample/ 两个目录
    data_dirs = ["data", "data_sample"]
    for data_dir in data_dirs:
        if not os.path.isdir(data_dir):
            continue
        for fn in sorted(os.listdir(data_dir)):
            path = os.path.join(data_dir, fn)
            m = extract_month(fn)
            try:
                if fn.startswith("payroll_") and fn.endswith((".xlsx",".xls")):
                    df = pd.read_excel(path); df["_month"] = m; pd_l.append(df)
                elif fn.startswith("hr_cost_") and fn.endswith((".xlsx",".xls")):
                    df = pd.read_excel(path); df["_month"] = m; cd_l.append(df)
                elif fn.startswith("talent_") and fn.endswith((".xlsx",".xls")):
                    df = pd.read_excel(path); df["_month"] = m; td_l.append(df)
            except Exception as e:
                st.warning(f"读取{fn}失败：{e}")
    pr = pd.concat(pd_l, ignore_index=True) if pd_l else None
    co = pd.concat(cd_l, ignore_index=True) if cd_l else None
    ta = pd.concat(td_l, ignore_index=True) if td_l else None
    return pr, co, ta

def generate_demo_data():
    """自动生成演示数据（无文件时使用）"""
    np.random.seed(42)
    DEPTS = ["研发部", "市场部", "销售部", "人事部", "财务部", "运营部"]
    POS_MAP = {
        "研发部": ["工程师", "高级工程师", "架构师", "测试工程师"],
        "市场部": ["市场专员", "品牌经理", "市场总监"],
        "销售部": ["销售代表", "销售经理", "大客户经理"],
        "人事部": ["HR专员", "HR经理", "招聘专员"],
        "财务部": ["会计", "财务经理", "财务分析师"],
        "运营部": ["运营专员", "运营经理", "数据分析师"],
    }
    LEVEL_MAP = {
        "工程师":"P2","高级工程师":"P3","架构师":"P5","测试工程师":"P2",
        "市场专员":"P1","品牌经理":"P3","市场总监":"P5",
        "销售代表":"P1","销售经理":"P3","大客户经理":"P4",
        "HR专员":"P1","HR经理":"P3","招聘专员":"P2",
        "会计":"P2","财务经理":"P4","财务分析师":"P3",
        "运营专员":"P1","运营经理":"P3","数据分析师":"P3",
    }
    BASE_PAY = {
        "工程师":15000,"高级工程师":22000,"架构师":35000,"测试工程师":13000,
        "市场专员":10000,"品牌经理":18000,"市场总监":30000,
        "销售代表":9000,"销售经理":18000,"大客户经理":22000,
        "HR专员":9000,"HR经理":16000,"招聘专员":9500,
        "会计":10000,"财务经理":18000,"财务分析师":14000,
        "运营专员":9500,"运营经理":15000,"数据分析师":16000,
    }
    EDU = ["大专","本科","硕士","博士"]
    EDU_W = [0.10,0.55,0.30,0.05]
    REASONS = ["薪酬不满","发展受限","家庭原因","工作压力","人际关系","其他"]
    PLEVELS = ["S","A","B","C","D"]
    PW = [0.05,0.25,0.45,0.20,0.05]
    POT = ["高","中","低"]
    RISK = ["高","中","低"]
    SUCC = ["可晋升","需培养","维持现状","待评估"]
    DEPT_SIZE = {"研发部":30,"市场部":15,"销售部":25,"人事部":12,"财务部":13,"运营部":25}

    # 生成员工主数据
    employees = []
    eid = 1001
    for dept in DEPTS:
        for _ in range(DEPT_SIZE[dept]):
            pos = np.random.choice(POS_MAP[dept])
            base = BASE_PAY.get(pos, 12000) + np.random.randint(-1000, 1500)
            level = LEVEL_MAP.get(pos, "P2")
            edu = np.random.choice(EDU, p=EDU_W)
            if level in ["P5","P4"]: tenure = round(np.random.uniform(3.0,15.0),1)
            elif level == "P3": tenure = round(np.random.uniform(2.0,10.0),1)
            else: tenure = round(np.random.uniform(0.5,8.0),1)
            is_left = np.random.choice([True,False], p=[0.06,0.94])
            employees.append({
                "员工ID": f"E{eid}", "姓名": f"员工{eid}", "部门": dept,
                "岗位": pos, "职级": level, "工龄": tenure, "学历": edu,
                "基本工资": int(base), "离职状态": "已离职" if is_left else "在职",
                "离职原因": np.random.choice(REASONS) if is_left else "",
                "_leave_month": np.random.randint(0,3) if is_left else -1,
            })
            eid += 1
    emp_df = pd.DataFrame(employees)

    payroll_list, cost_list, talent_list = [], [], []
    for mi, (yyyymm, noise) in enumerate([("202601",1.00),("202602",1.02),("202603",1.04)]):
        # 薪酬考勤
        mask = ~((emp_df["离职状态"]=="已离职") & (emp_df["_leave_month"] < mi))
        pr = emp_df[mask].copy().drop(columns=["_leave_month"])
        n = len(pr)
        pr["绩效工资"] = (pr["基本工资"]*np.random.uniform(0.05,0.30,n)*noise).astype(int)
        pr["奖金"] = (pr["基本工资"]*np.random.uniform(0.0,0.15,n)*noise).astype(int)
        pr["加班费"] = np.random.choice([0,0,0,500,800,1200,1500],n)
        pr["扣款"] = np.random.choice([0,0,100,200,300],n)
        pr["实发工资"] = pr["基本工资"]+pr["绩效工资"]+pr["奖金"]+pr["加班费"]-pr["扣款"]
        pr["应出勤天数"] = 21
        pr["实际出勤天数"] = np.random.choice(range(18,22),n,p=[0.05,0.10,0.15,0.70])
        pr["迟到次数"] = np.random.choice([0,0,0,1,2,3],n,p=[0.55,0.20,0.10,0.08,0.05,0.02])
        pr["缺勤天数"] = pr["应出勤天数"]-pr["实际出勤天数"]
        pr["_month"] = yyyymm
        payroll_list.append(pr)

        # 人力成本
        cost_rows = []
        for dept in DEPTS:
            dept_emp = emp_df[emp_df["部门"]==dept]
            for pos in dept_emp["岗位"].unique():
                pos_emp = dept_emp[dept_emp["岗位"]==pos]
                wage = int(pos_emp["基本工资"].sum()*noise*np.random.uniform(0.95,1.10))
                bonus = int(wage*np.random.uniform(0.05,0.15))
                social = int(wage*0.20)
                welfare = int(wage*0.03*np.random.uniform(0.8,1.2))
                recruit = int(np.random.choice([0,0,3000,5000,8000,15000]))
                train = int(np.random.choice([0,1000,2000,3000,5000]))
                cost_rows.append({
                    "部门":dept,"岗位":pos,"工资总额":wage,"奖金总额":bonus,
                    "社保公积金":social,"福利费":welfare,"招聘费":recruit,"培训费":train,
                    "总成本":wage+bonus+social+welfare+recruit+train,"_month":yyyymm
                })
        cost_list.append(pd.DataFrame(cost_rows))

        # 人才盘点
        ta = emp_df.copy().drop(columns=["_leave_month"])
        n2 = len(ta)
        ta["绩效等级"] = np.random.choice(PLEVELS,n2,p=PW)
        ta["潜力评级"] = np.random.choice(POT,n2,p=[0.20,0.55,0.25])
        ta["离职风险"] = np.random.choice(RISK,n2,p=[0.15,0.35,0.50])
        ta["关键岗位"] = np.random.choice(["是","否"],n2,p=[0.25,0.75])
        ta["继任者准备度"] = np.random.choice(SUCC,n2,p=[0.20,0.35,0.30,0.15])
        ta["_month"] = yyyymm
        talent_list.append(ta)

    payroll = pd.concat(payroll_list, ignore_index=True) if payroll_list else None
    cost = pd.concat(cost_list, ignore_index=True) if cost_list else None
    talent = pd.concat(talent_list, ignore_index=True) if talent_list else None
    return payroll, cost, talent

def load_uploaded_data(uploaded_files):
    """从用户上传的文件中加载数据"""
    pd_l, cd_l, td_l = [], [], []
    for f in uploaded_files:
        m = extract_month(f.name)
        try:
            if f.name.startswith("payroll_") and f.name.endswith((".xlsx",".xls")):
                df = pd.read_excel(f); df["_month"] = m; pd_l.append(df)
            elif f.name.startswith("hr_cost_") and f.name.endswith((".xlsx",".xls")):
                df = pd.read_excel(f); df["_month"] = m; cd_l.append(df)
            elif f.name.startswith("talent_") and f.name.endswith((".xlsx",".xls")):
                df = pd.read_excel(f); df["_month"] = m; td_l.append(df)
        except Exception as e:
            st.warning(f"读取{f.name}失败：{e}")
    pr = pd.concat(pd_l, ignore_index=True) if pd_l else None
    co = pd.concat(cd_l, ignore_index=True) if cd_l else None
    ta = pd.concat(td_l, ignore_index=True) if td_l else None
    return pr, co, ta

def filter_df(df, months, dept):
    if df is None: return None
    d = df[df["_month"].isin(months)] if months else df
    if dept != "全部" and "部门" in d.columns:
        d = d[d["部门"]==dept]
    return d

def calc_kpi(pr, co, ta):
    tc = co["总成本"].sum() if co is not None and "总成本" in co.columns else 0
    av = pr["实发工资"].mean() if pr is not None and "实发工资" in pr.columns else 0
    hd = len(pr["员工ID"].unique()) if pr is not None else 0
    ar, hr = 0, 0
    if pr is not None and "应出勤天数" in pr.columns:
        ar = round(pr["实际出勤天数"].sum()/pr["应出勤天数"].sum()*100,1) if pr["应出勤天数"].sum()>0 else 0
    if ta is not None and "离职风险" in ta.columns:
        hr = int((ta["离职风险"]=="高").sum())
    return tc, av, hd, ar, hr

# 侧边栏 - 数据上传
st.sidebar.title("HR 分析看板")
st.sidebar.markdown("### 📤 上传数据文件")
st.sidebar.caption("支持 payroll_/hr_cost_/talent_ 开头的Excel文件")
uploaded = st.sidebar.file_uploader(
    "选择Excel文件（可多选）",
    type=["xlsx","xls"],
    accept_multiple_files=True,
    key="data_upload"
)
if uploaded:
    payroll_raw, cost_raw, talent_raw = load_uploaded_data(uploaded)
    st.sidebar.success(f"✅ 已加载 {len(uploaded)} 个文件")
else:
    # 数据加载优先级：私有仓库真实数据 > 本地示例数据 > 自动演示数据
    payroll_raw, cost_raw, talent_raw = load_data_from_private_repo()
    if payroll_raw is not None or cost_raw is not None or talent_raw is not None:
        st.sidebar.info("🔒 使用私有仓库真实数据")
    else:
        payroll_raw, cost_raw, talent_raw = load_all_data()
        if payroll_raw is not None or cost_raw is not None or talent_raw is not None:
            st.sidebar.info("📂 使用本地示例数据")
        else:
            payroll_raw, cost_raw, talent_raw = generate_demo_data()
            st.sidebar.info("📊 使用自动生成的演示数据")

ALL_MONTHS = sorted(set(
    (payroll_raw["_month"].unique().tolist() if payroll_raw is not None else []) +
    (cost_raw["_month"].unique().tolist() if cost_raw is not None else []) +
    (talent_raw["_month"].unique().tolist() if talent_raw is not None else [])
))

nav = st.sidebar.radio("选择模块", [
    "🏠 综合仪表板", "💰 薪酬考勤分析", "📈 人力资源分析",
    "💼 人工成本分析", "🎯 人员盘点分析", "🏆 绩效分析",
    "📅 考勤异常分析", "📝 一键生成周报"
])
st.sidebar.markdown("---")
st.sidebar.caption(f"数据月份：{', '.join(ALL_MONTHS) if ALL_MONTHS else '无'}")

sel_months = st.sidebar.multiselect("筛选月份", ALL_MONTHS, default=ALL_MONTHS[-1:] if ALL_MONTHS else [])
sel_dept = "全部"
if payroll_raw is not None and "部门" in payroll_raw.columns:
    depts = ["全部"] + sorted(payroll_raw["部门"].unique().tolist())
    sel_dept = st.sidebar.selectbox("筛选部门", depts)

payroll = filter_df(payroll_raw, sel_months, sel_dept)
cost    = filter_df(cost_raw,    sel_months, sel_dept)
talent  = filter_df(talent_raw,  sel_months, sel_dept)

# ═══════════════════════════════════════════════════════════
# 模块1：综合仪表板
# ═══════════════════════════════════════════════════════════
if nav == "🏠 综合仪表板":
    st.title("🏠 综合仪表板")
    if payroll is None and cost is None and talent is None:
        st.warning("⚠️ 未检测到数据文件，请将Excel放入 data_sample/ 目录")
        st.info("💡 运行 python generate_sample_data.py 可生成3个月示例数据")
        st.stop()
    tc, av, hd, ar, hr = calc_kpi(payroll, cost, talent)
    c1,c2,c3,c4,c5 = st.columns(5)
    with c1: st.metric("总人数", f"{hd}人")
    with c2: st.metric("总成本", f"¥{tc:,.0f}")
    with c3: st.metric("平均薪酬", f"¥{av:,.0f}")
    with c4: st.metric("出勤率", f"{ar}%")
    with c5: st.metric("高风险人数", f"{hr}人")
    st.markdown("---")
    colL, colR = st.columns([1,1])
    with colL:
        if cost is not None and "部门" in cost.columns:
            cols = [c for c in ["工资总额","社保公积金","福利费","招聘费","培训费"] if c in cost.columns]
            if cols:
                dfc = cost.groupby("部门")[cols].sum().reset_index()
                fig = px.bar(dfc, x="部门", y=cols, title="各部门成本构成", barmode="stack")
                st.plotly_chart(fig, use_container_width=True)
    with colR:
        if cost is not None and "部门" in cost.columns and "总成本" in cost.columns:
            dfp = cost.groupby("部门")["总成本"].sum().reset_index()
            fig = px.pie(dfp, names="部门", values="总成本", hole=0.4, title="成本按部门占比")
            st.plotly_chart(fig, use_container_width=True)
    if talent is not None and "离职风险" in talent.columns:
        st.subheader("⚠️ 离职风险一览")
        risk = talent[talent["离职风险"].isin(["高","中"])].copy()
        if not risk.empty:
            st.dataframe(risk, use_container_width=True)
        else:
            st.success("✅ 当前无中高风险人员")

# ═══════════════════════════════════════════════════════════
# 模块2：薪酬考勤分析
# ═══════════════════════════════════════════════════════════
if nav == "💰 薪酬考勤分析":
    st.title("💰 薪酬考勤分析")
    if payroll is None:
        st.warning("⚠️ 未检测到薪酬考勤数据"); st.stop()
    metric_map = {"平均工资":"实发工资","加班费总额":"加班费","缺勤天数合计":"缺勤天数","迟到次数合计":"迟到次数","奖金总额":"奖金"}
    avail = [k for k,v in metric_map.items() if v in payroll.columns]
    if not avail:
        st.info("💡 数据中无可用指标字段"); st.stop()
    sel = st.selectbox("选择指标", avail)
    col_name = metric_map[sel]
    if payroll[col_name].dtype.kind in "bi":
        df = payroll.groupby("部门")[col_name].sum().reset_index()
    else:
        df = payroll.groupby("部门")[col_name].mean().reset_index()
    fig = px.bar(df, x="部门", y=col_name, title=f"各部门{sel}", color="部门")
    st.plotly_chart(fig, use_container_width=True)
    st.subheader("📋 员工薪酬明细")
    show = [c for c in ["员工ID","姓名","部门","岗位","基本工资","绩效工资","加班费","奖金","实发工资"] if c in payroll.columns]
    st.dataframe(payroll[show], use_container_width=True)

# ═══════════════════════════════════════════════════════════
# 模块3：人力资源分析
# ═══════════════════════════════════════════════════════════
if nav == "📈 人力资源分析":
    st.title("📈 人力资源分析")
    if payroll is None:
        st.warning("⚠️ 未检测到薪酬数据"); st.stop()
    tabs = st.tabs(["离职率","离职原因","留存率","职级","工龄","学历"])
    with tabs[0]:
        st.subheader("离职率分析")
        if "离职状态" in payroll.columns:
            dr = payroll.groupby("部门").apply(
                lambda x: round((x["离职状态"]=="已离职").sum()/len(x)*100,1) if len(x)>0 else 0
            ).reset_index()
            dr.columns = ["部门","离职率%"]
            fig = px.bar(dr, x="部门", y="离职率%", title="各部门离职率", color="离职率%", color_continuous_scale="Reds")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("💡 数据表中需增加'离职状态'字段")
    with tabs[1]:
        st.subheader("离职原因分析")
        if "离职原因" in payroll.columns and "离职状态" in payroll.columns:
            lv = payroll[payroll["离职状态"]=="已离职"]
            if not lv.empty:
                rc = lv["离职原因"].value_counts().reset_index()
                rc.columns = ["离职原因","人数"]
                fig = px.pie(rc, names="离职原因", values="人数", title="离职原因分布")
                st.plotly_chart(fig, use_container_width=True)
                st.dataframe(lv, use_container_width=True)
            else:
                st.success("✅ 当前无离职人员")
        else:
            st.info("💡 数据表中需增加'离职原因'字段")
    with tabs[2]:
        st.subheader("留存率分析")
        if "工龄" in payroll.columns:
            bins = [0,1,3,5,10,100]
            labels = ["1年以内","1-3年","3-5年","5-10年","10年以上"]
            payroll["工龄段"] = pd.cut(payroll["工龄"], bins=bins, labels=labels, right=False)
            rt = payroll.groupby("工龄段")["员工ID"].nunique().reset_index()
            rt.columns = ["工龄段","在职人数"]
            fig = px.bar(rt, x="工龄段", y="在职人数", title="各工龄段在职人数")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("💡 数据表中需增加'工龄'字段")
    with tabs[3]:
        st.subheader("职级分析")
        if "职级" in payroll.columns:
            lc = payroll["职级"].value_counts().reset_index()
            lc.columns = ["职级","人数"]
            fig = px.bar(lc, x="职级", y="人数", title="各职级人数分布")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("💡 数据表中需增加'职级'字段")
    with tabs[4]:
        st.subheader("工龄分析")
        if "工龄" in payroll.columns:
            fig = px.histogram(payroll, x="工龄", nbins=20, title="工龄分布直方图")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("💡 数据表中需增加'工龄'字段")
    with tabs[5]:
        st.subheader("学历分析")
        if "学历" in payroll.columns:
            ec = payroll["学历"].value_counts().reset_index()
            ec.columns = ["学历","人数"]
            fig = px.pie(ec, names="学历", values="人数", title="员工学历分布")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("💡 数据表中需增加'学历'字段")

# ═══════════════════════════════════════════════════════════
# 模块4：人工成本分析
# ═══════════════════════════════════════════════════════════
if nav == "💼 人工成本分析":
    st.title("💼 人工成本分析")
    if cost is None and payroll is None:
        st.warning("⚠️ 未检测到成本或薪酬数据"); st.stop()
    tabs = st.tabs(["成本构成","奖金分析","团队业绩","TOP10"])
    with tabs[0]:
        st.subheader("成本构成（堆积柱状图）")
        if cost is not None and "部门" in cost.columns:
            cols = [c for c in ["工资总额","社保公积金","福利费","招聘费","培训费"] if c in cost.columns]
            if cols:
                dfc = cost.groupby("部门")[cols].sum().reset_index()
                fig = px.bar(dfc, x="部门", y=cols, barmode="stack", title="各部门成本构成")
                st.plotly_chart(fig, use_container_width=True)
    with tabs[1]:
        st.subheader("奖金分析")
        if payroll is not None and "奖金" in payroll.columns:
            df = payroll.groupby("部门")["奖金"].sum().reset_index()
            fig = px.bar(df, x="部门", y="奖金", title="各部门奖金总额")
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(payroll.nlargest(20,"奖金")[["员工ID","姓名","部门","奖金"]], use_container_width=True)
        else:
            st.info("💡 数据表中需增加'奖金'字段")
    with tabs[2]:
        st.subheader("团队业绩（人均成本）")
        if payroll is not None and "部门" in payroll.columns:
            perf = payroll.groupby("部门").agg(
                人数=("员工ID","nunique"), 总薪酬=("实发工资","sum")
            ).reset_index()
            fig = px.bar(perf, x="部门", y="总薪酬", title="各部门总薪酬")
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(perf, use_container_width=True)
    with tabs[3]:
        st.subheader("TOP10 高薪酬个人")
        if payroll is not None and "实发工资" in payroll.columns:
            cols = [c for c in ["员工ID","姓名","部门","岗位","实发工资"] if c in payroll.columns]
            st.dataframe(payroll.nlargest(10,"实发工资")[cols], use_container_width=True)

# ═══════════════════════════════════════════════════════════
# 模块5：人员盘点分析
# ═══════════════════════════════════════════════════════════
if nav == "🎯 人员盘点分析":
    st.title("🎯 人员盘点分析")
    if talent is None:
        st.warning("⚠️ 未检测到人才盘点数据"); st.stop()
    tabs = st.tabs(["九宫格","团队能力","团队职级","继任计划"])
    with tabs[0]:
        st.subheader("人才九宫格（绩效 × 潜力）")
        if "绩效等级" in talent.columns and "潜力评级" in talent.columns:
            ps = {"S":5,"A":4,"B":3,"C":2,"D":1}
            pt = {"高":3,"中":2,"低":1}
            df9 = talent.copy()
            df9["绩效分"] = df9["绩效等级"].map(ps)
            df9["潜力分"] = df9["潜力评级"].map(pt)
            grid = df9.groupby(["绩效分","潜力分"])["员工ID"].count().reset_index()
            grid.columns = ["绩效分","潜力分","人数"]
            fig = px.scatter(grid, x="绩效分", y="潜力分", size="人数",
                             title="九宫格（气泡大小=人数）", size_max=60)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("💡 需'绩效等级'和'潜力评级'字段")
    with tabs[1]:
        st.subheader("团队能力（绩效分布）")
        if "绩效等级" in talent.columns and "部门" in talent.columns:
            perf = pd.crosstab(talent["部门"], talent["绩效等级"])
            fig = px.bar(perf.reset_index().melt(id_vars="部门", var_name="绩效", value_name="人数"),
                           x="部门", y="人数", color="绩效", barmode="stack", title="各部门绩效分布")
            st.plotly_chart(fig, use_container_width=True)
    with tabs[2]:
        st.subheader("团队职级分布")
        if payroll is not None and "职级" in payroll.columns and "部门" in payroll.columns:
            cross = pd.crosstab(payroll["部门"], payroll["职级"])
            fig = px.bar(cross.reset_index().melt(id_vars="部门", var_name="职级", value_name="人数"),
                           x="部门", y="人数", color="职级", barmode="stack", title="各部门职级分布")
            st.plotly_chart(fig, use_container_width=True)
    with tabs[3]:
        st.subheader("继任计划（可晋升人员）")
        if "继任者准备度" in talent.columns:
            succ = talent[talent["继任者准备度"].isin(["可晋升","Ready now"])].copy()
            if not succ.empty:
                st.dataframe(succ, use_container_width=True)
            else:
                st.info("当前无'可晋升'状态人员")
        else:
            st.info("💡 需'继任者准备度'字段")

# ═══════════════════════════════════════════════════════════
# 模块6：绩效分析
# ═══════════════════════════════════════════════════════════
if nav == "🏆 绩效分析":
    st.title("🏆 绩效分析")
    if talent is None:
        st.warning("⚠️ 未检测到人才盘点数据"); st.stop()
    tabs = st.tabs(["团队绩效","个人绩效"])
    with tabs[0]:
        st.subheader("团队绩效（部门分布）")
        if "绩效等级" in talent.columns and "部门" in talent.columns:
            perf = pd.crosstab(talent["部门"], talent["绩效等级"])
            fig = px.bar(perf.reset_index().melt(id_vars="部门", var_name="绩效", value_name="人数"),
                           x="部门", y="人数", color="绩效", barmode="stack")
            st.plotly_chart(fig, use_container_width=True)
    with tabs[1]:
        st.subheader("个人绩效查询")
        cols = [c for c in ["员工ID","姓名","部门","绩效等级","潜力评级","离职风险","关键岗位"] if c in talent.columns]
        st.dataframe(talent[cols], use_container_width=True)

# ═══════════════════════════════════════════════════════════
# 模块7：考勤异常分析
# ═══════════════════════════════════════════════════════════
if nav == "📅 考勤异常分析":
    st.title("📅 考勤异常分析")
    if payroll is None:
        st.warning("⚠️ 未检测到薪酬考勤数据"); st.stop()
    tabs = st.tabs(["异常人员清单","部门对比"])
    with tabs[0]:
        st.subheader("考勤异常人员清单")
        cond = pd.Series([False]*len(payroll))
        if "迟到次数" in payroll.columns:
            cond = cond | (payroll["迟到次数"]>=2)
        if "缺勤天数" in payroll.columns:
            cond = cond | (payroll["缺勤天数"]>=1)
        ab = payroll[cond]
        if not ab.empty:
            st.dataframe(ab, use_container_width=True)
        else:
            st.success("✅ 当前无考勤异常人员")
    with tabs[1]:
        st.subheader("各部门出勤率对比")
        if "应出勤天数" in payroll.columns:
            ar = payroll.groupby("部门").apply(
                lambda x: round(x["实际出勤天数"].sum()/x["应出勤天数"].sum()*100,1) if x["应出勤天数"].sum()>0 else 0
            ).reset_index()
            ar.columns = ["部门","出勤率%"]
            fig = px.bar(ar, x="部门", y="出勤率%", title="各部门出勤率(%)", color="出勤率%", color_continuous_scale="Greens")
            st.plotly_chart(fig, use_container_width=True)

# ═══════════════════════════════════════════════════════════
# 模块8：一键生成周报
# ═══════════════════════════════════════════════════════════
if nav == "📝 一键生成周报":
    st.title("📝 一键生成周报")
    if st.button("🚀 生成周报", type="primary", use_container_width=True):
        tc, av, hd, ar, hr = calc_kpi(payroll, cost, talent)
        r = []
        r.append("# HR数据分析周报")
        r.append(f"生成时间：{datetime.now().strftime('%Y年%m月%d日')}")
        r.append(f"数据月份：{', '.join(sel_months) if sel_months else '全部'}")
        r.append(f"总人数：{hd}人  总成本：¥{tc:,.0f}  平均薪酬：¥{av:,.0f}")
        r.append(f"出勤率：{ar}%  高风险人数：{hr}人")
        report = "\n".join(r)
        st.markdown(report)
        st.download_button("📥 下载报告", report, "HR周报.md", "text/markdown")
