# -*- coding: utf-8 -*-
"""
HR看板 - 示例数据生成脚本（增强版）
运行此脚本生成3个月的模拟数据（2026年1-3月）
新增字段：职级、工龄、学历、奖金、离职状态、离职原因、奖金总额
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import pandas as pd
import numpy as np
import os
from datetime import datetime

np.random.seed(42)

DEPARTMENTS = ["研发部", "市场部", "销售部", "人事部", "财务部", "运营部"]
POSITIONS = {
    "研发部": ["工程师", "高级工程师", "架构师", "测试工程师"],
    "市场部": ["市场专员", "品牌经理", "市场总监"],
    "销售部": ["销售代表", "销售经理", "大客户经理"],
    "人事部": ["HR专员", "HR经理", "招聘专员"],
    "财务部": ["会计", "财务经理", "财务分析师"],
    "运营部": ["运营专员", "运营经理", "数据分析师"],
}
# ── 新增字段映射 ────────────────────────────────────────────────
LEVEL_MAP = {
    "工程师": "P2", "高级工程师": "P3", "架构师": "P5", "测试工程师": "P2",
    "市场专员": "P1", "品牌经理": "P3", "市场总监": "P5",
    "销售代表": "P1", "销售经理": "P3", "大客户经理": "P4",
    "HR专员": "P1", "HR经理": "P3", "招聘专员": "P2",
    "会计": "P2", "财务经理": "P4", "财务分析师": "P3",
    "运营专员": "P1", "运营经理": "P3", "数据分析师": "P3",
}
EDU_OPTIONS = ["大专", "本科", "硕士", "博士"]
EDU_WEIGHTS = [0.10, 0.55, 0.30, 0.05]
LEAVE_REASONS = ["薪酬不满", "发展受限", "家庭原因", "工作压力", "人际关系", "其他"]
PERF_GRADES = ["S", "A", "B", "C", "D"]
PERF_WEIGHTS = [0.05, 0.25, 0.45, 0.20, 0.05]
POTENTIAL = ["高", "中", "低"]
RISK = ["高", "中", "低"]
SUCCESSOR = ["可晋升", "需培养", "维持现状", "待评估"]

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "data_sample")
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ── 员工主数据（固定，跨月复用）──────────────────────────────
def gen_employees(n=120):
    employees = []
    eid = 1001
    for dept in DEPARTMENTS:
        size = {
            "研发部": 30, "市场部": 15, "销售部": 25,
            "人事部": 12, "财务部": 13, "运营部": 25
        }[dept]
        for _ in range(size):
            pos = np.random.choice(POSITIONS[dept])
            base = {
                "工程师": 15000, "高级工程师": 22000, "架构师": 35000,
                "测试工程师": 13000, "市场专员": 10000, "品牌经理": 18000,
                "市场总监": 30000, "销售代表": 9000, "销售经理": 18000,
                "大客户经理": 22000, "HR专员": 9000, "HR经理": 16000,
                "招聘专员": 9500, "会计": 10000, "财务经理": 18000,
                "财务分析师": 14000, "运营专员": 9500, "运营经理": 15000,
                "数据分析师": 16000,
            }.get(pos, 12000)
            base = base + np.random.randint(-1000, 1500)
            level = LEVEL_MAP.get(pos, "P2")
            edu = np.random.choice(EDU_OPTIONS, p=EDU_WEIGHTS)
            tenure = round(np.random.uniform(0.5, 15.0), 1)
            # 职级越高的工龄倾向更长
            if level in ["P5", "P4"]:
                tenure = round(np.random.uniform(3.0, 15.0), 1)
            elif level == "P3":
                tenure = round(np.random.uniform(2.0, 10.0), 1)
            else:
                tenure = round(np.random.uniform(0.5, 8.0), 1)
            # 初始离职状态：约5-8%的人在不同月离职
            is_left = np.random.choice([True, False], p=[0.06, 0.94])
            leave_reason = np.random.choice(LEAVE_REASONS) if is_left else ""
            employees.append({
                "员工ID": f"E{eid}",
                "姓名": f"员工{eid}",
                "部门": dept,
                "岗位": pos,
                "职级": level,
                "工龄": tenure,
                "学历": edu,
                "基本工资": int(base),
                "离职状态": "已离职" if is_left else "在职",
                "离职原因": leave_reason,
            })
            eid += 1
    return pd.DataFrame(employees)

EMP = gen_employees()


# ── 薪酬考勤表（增强版）────────────────────────────────────────
def gen_payroll(yyyymm: str, noise: float = 1.0, leave_rate: float = 0.03):
    rows = EMP.copy()
    n = len(rows)

    # 模拟逐月离职：越后面的月份，离职累积越多
    month_idx = int(yyyymm[4:]) - 1  # 1月=0, 2月=1, 3月=2
    # 之前已离职的人不在当月工资表中；当月新离职的人还在
    rows["本月离职标记"] = False
    for i in range(len(rows)):
        if rows.iloc[i]["离职状态"] == "已离职":
            # 随机分配离职月份（前几个月离职的概率更高）
            leave_month = np.random.randint(0, 3)  # 在第0、1、2月中离职
            if leave_month < month_idx:
                # 之前已离职，不出现在当月工资表中
                rows.loc[i, "本月离职标记"] = True
            elif leave_month == month_idx:
                # 当月离职，仍在工资表中但标记
                pass
    rows = rows[~rows["本月离职标记"]].drop(columns=["本月离职标记"])

    n_actual = len(rows)
    rows["绩效工资"] = (rows["基本工资"] * np.random.uniform(0.05, 0.30, n_actual) * noise).astype(int)
    rows["奖金"] = (rows["基本工资"] * np.random.uniform(0.0, 0.15, n_actual) * noise).astype(int)
    rows["加班费"] = np.random.choice([0, 0, 0, 500, 800, 1200, 1500], n_actual)
    rows["扣款"] = np.random.choice([0, 0, 100, 200, 300], n_actual)
    rows["实发工资"] = rows["基本工资"] + rows["绩效工资"] + rows["奖金"] + rows["加班费"] - rows["扣款"]
    rows["应出勤天数"] = 21
    rows["实际出勤天数"] = np.random.choice(range(18, 22), n_actual, p=[0.05, 0.10, 0.15, 0.70])
    rows["迟到次数"] = np.random.choice([0, 0, 0, 1, 2, 3], n_actual, p=[0.55, 0.20, 0.10, 0.08, 0.05, 0.02])
    rows["缺勤天数"] = rows["应出勤天数"] - rows["实际出勤天数"]

    cols = ["员工ID", "姓名", "部门", "职级", "工龄", "学历",
            "基本工资", "绩效工资", "奖金", "加班费", "扣款", "实发工资",
            "应出勤天数", "实际出勤天数", "迟到次数", "缺勤天数",
            "离职状态", "离职原因"]
    path = os.path.join(OUTPUT_DIR, f"payroll_{yyyymm}.xlsx")
    rows[cols].to_excel(path, index=False)
    print(f"  ✅ 生成: {path}  ({len(rows)} 行)")


# ── 人力成本表（增强版）────────────────────────────────────────
def gen_hr_cost(yyyymm: str, noise: float = 1.0):
    rows = []
    for dept in DEPARTMENTS:
        dept_emp = EMP[EMP["部门"] == dept]
        for pos in dept_emp["岗位"].unique():
            pos_emp = dept_emp[dept_emp["岗位"] == pos]
            wage = int(pos_emp["基本工资"].sum() * noise * np.random.uniform(0.95, 1.10))
            bonus = int(wage * np.random.uniform(0.05, 0.15))
            social = int(wage * 0.20)
            welfare = int(wage * 0.03 * np.random.uniform(0.8, 1.2))
            recruit = int(np.random.choice([0, 0, 3000, 5000, 8000, 15000]))
            train = int(np.random.choice([0, 1000, 2000, 3000, 5000]))
            total = wage + bonus + social + welfare + recruit + train
            rows.append({
                "部门": dept, "岗位": pos,
                "工资总额": wage, "奖金总额": bonus,
                "社保公积金": social, "福利费": welfare,
                "招聘费": recruit, "培训费": train,
                "总成本": total
            })
    df = pd.DataFrame(rows)
    path = os.path.join(OUTPUT_DIR, f"hr_cost_{yyyymm}.xlsx")
    df.to_excel(path, index=False)
    print(f"  ✅ 生成: {path}  ({len(df)} 行)")


# ── 人才盘点表 ────────────────────────────────────────────────
def gen_talent(yyyymm: str):
    rows = EMP.copy()
    n = len(rows)
    rows["绩效等级"] = np.random.choice(PERF_GRADES, n, p=PERF_WEIGHTS)
    rows["潜力评级"] = np.random.choice(POTENTIAL, n, p=[0.20, 0.55, 0.25])
    rows["离职风险"] = np.random.choice(RISK, n, p=[0.15, 0.35, 0.50])
    rows["关键岗位"] = np.random.choice(["是", "否"], n, p=[0.25, 0.75])
    rows["继任者准备度"] = np.random.choice(SUCCESSOR, n, p=[0.20, 0.35, 0.30, 0.15])
    cols = ["员工ID", "姓名", "部门", "职级", "工龄", "学历",
            "绩效等级", "潜力评级", "离职风险", "关键岗位", "继任者准备度"]
    path = os.path.join(OUTPUT_DIR, f"talent_review_{yyyymm}.xlsx")
    rows[cols].to_excel(path, index=False)
    print(f"  ✅ 生成: {path}  ({len(rows)} 行)")


# ── 主函数 ────────────────────────────────────────────────────
if __name__ == "__main__":
    months = [
        ("202601", 1.00),
        ("202602", 1.02),
        ("202603", 1.04),
    ]
    print("=" * 50)
    print("HR看板 · 示例数据生成器（增强版）")
    print(f"输出目录: {OUTPUT_DIR}")
    print("=" * 50)
    for ym, noise in months:
        print(f"\n📅 生成 {ym[:4]}年{ym[4:]}月数据...")
        gen_payroll(ym, noise)
        gen_hr_cost(ym, noise)
        gen_talent(ym)
    print("\n✅ 全部完成！共生成 9 个Excel文件（3类×3月）")
    print("新增字段：职级、工龄、学历、奖金、离职状态、离职原因、奖金总额")