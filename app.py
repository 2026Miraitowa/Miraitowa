# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os, re, io, base64, zipfile
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

def load_all_data():
    pd_l, cd_l, td_l = [], [], []
    if not os.path.isdir("data_sample"):
        return None, None, None
    for fn in sorted(os.listdir("data_sample")):
        path = os.path.join("data_sample", fn)
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

# 加载数据
payroll_raw, cost_raw, talent_raw = load_all_data()
ALL_MONTHS = sorted(set(
    payroll_raw["_month"].unique().tolist() if payroll_raw is not None else [] +
    cost_raw["_month"].unique().tolist() if cost_raw is not None else [] +
    talent_raw["_month"].unique().tolist() if talent_raw is not None else []
))

# 侧边栏
st.sidebar.title("HR 分析看板")
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
