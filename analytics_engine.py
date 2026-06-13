# -*- coding: utf-8 -*-
"""
HR智能分析引擎 - 纯Python实现，不依赖外部API
提供：异常检测、趋势分析、对比分析、相关性分析、分布分析、预测预警、聚类分析、NLG报告
"""
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from typing import Dict, List, Tuple, Optional, Any


# ============================================================
# 内部工具函数
# ============================================================

def _safe_divide(a: float, b: float, default: float = 0.0) -> float:
    """安全除法"""
    return a / b if b != 0 else default


def _format_pct(value: float, decimals: int = 1) -> str:
    """百分比格式化"""
    return f"{value*100:.{decimals}f}%"


def _format_currency(value: float) -> str:
    """货币格式化"""
    if abs(value) >= 10000:
        return f"¥{value/10000:.1f}万"
    return f"¥{value:,.0f}"


def _summarize_series(series: pd.Series) -> Dict[str, float]:
    """序列统计摘要"""
    s = series.dropna()
    if len(s) == 0:
        return {"mean": 0, "median": 0, "std": 0, "min": 0, "max": 0, "q25": 0, "q75": 0, "count": 0}
    return {
        "mean": float(s.mean()), "median": float(s.median()),
        "std": float(s.std()), "min": float(s.min()), "max": float(s.max()),
        "q25": float(s.quantile(0.25)), "q75": float(s.quantile(0.75)),
        "count": len(s)
    }


def _check_df(df: Optional[pd.DataFrame], name: str = "数据") -> Optional[str]:
    """检查DataFrame是否有效，无效返回错误信息"""
    if df is None or df.empty:
        return f"⚠️ {name}不足，无法进行分析"
    return None


def _check_col(df: pd.DataFrame, col: str) -> bool:
    """检查列是否存在"""
    return col in df.columns


# ============================================================
# 1. 异常检测模块
# ============================================================

def detect_outliers_iqr(
    df: pd.DataFrame,
    column: str,
    multiplier: float = 1.5,
    group_col: Optional[str] = None
) -> Dict[str, Any]:
    """基于IQR的异常值检测"""
    result = {"total": len(df), "outlier_count": 0, "outlier_pct": 0.0,
              "lower_bound": 0.0, "upper_bound": 0.0, "q1": 0.0, "q3": 0.0, "iqr": 0.0,
              "outliers": pd.DataFrame(), "narrative": ""}

    if not _check_col(df, column):
        result["narrative"] = f"⚠️ 数据中无'{column}'字段，无法进行异常检测"
        return result

    series = df[column].dropna()
    if len(series) < 4:
        result["narrative"] = f"⚠️ {column}的有效数据不足（{len(series)}条），无法进行异常检测"
        return result

    Q1 = float(series.quantile(0.25))
    Q3 = float(series.quantile(0.75))
    IQR = Q3 - Q1
    lower = Q1 - multiplier * IQR
    upper = Q3 + multiplier * IQR

    outliers = df[(df[column] < lower) | (df[column] > upper)].copy()
    outlier_count = len(outliers)
    outlier_pct = _safe_divide(outlier_count, len(df))

    result.update({"outlier_count": outlier_count, "outlier_pct": outlier_pct,
                   "lower_bound": lower, "upper_bound": upper, "q1": Q1, "q3": Q3, "iqr": IQR,
                   "outliers": outliers})

    # 生成中文描述
    if outlier_count == 0:
        result["narrative"] = f"✅ {column}分布正常，未检测到异常值（IQR={IQR:,.0f}，正常范围 {_format_currency(lower)} ~ {_format_currency(upper)}）"
    elif outlier_pct < 0.05:
        result["narrative"] = f"🔵 {column}检测到 {outlier_count} 个异常值（占 {_format_pct(outlier_pct)}），在可控范围内。正常范围 {_format_currency(lower)} ~ {_format_currency(upper)}"
    elif outlier_pct < 0.15:
        result["narrative"] = f"🟡 {column}检测到 {outlier_count} 个异常值（占 {_format_pct(outlier_pct)}），比例偏高，建议关注。正常范围 {_format_currency(lower)} ~ {_format_currency(upper)}"
    else:
        result["narrative"] = f"🔴 {column}检测到 {outlier_count} 个异常值（占 {_format_pct(outlier_pct)}），异常比例较高，需重点排查！正常范围 {_format_currency(lower)} ~ {_format_currency(upper)}"

    return result


def detect_outliers_zscore(
    df: pd.DataFrame,
    column: str,
    threshold: float = 3.0
) -> Dict[str, Any]:
    """基于Z-score的异常值检测"""
    result = {"total": len(df), "outlier_count": 0, "outlier_pct": 0.0,
              "mean": 0.0, "std": 0.0, "outliers": pd.DataFrame(), "narrative": ""}

    if not _check_col(df, column):
        result["narrative"] = f"⚠️ 数据中无'{column}'字段"
        return result

    series = df[column].dropna()
    if len(series) < 4:
        result["narrative"] = f"⚠️ {column}有效数据不足"
        return result

    mean_val = float(series.mean())
    std_val = float(series.std())
    if std_val == 0:
        result["narrative"] = f"✅ {column}所有值相同，无异常"
        result["mean"] = mean_val
        return result

    z_scores = np.abs((df[column] - mean_val) / std_val)
    outliers = df[z_scores > threshold].copy()
    outlier_count = len(outliers)
    outlier_pct = _safe_divide(outlier_count, len(df))

    result.update({"outlier_count": outlier_count, "outlier_pct": outlier_pct,
                   "mean": mean_val, "std": std_val, "outliers": outliers})

    if outlier_count == 0:
        result["narrative"] = f"✅ {column}分布正常，无Z-score异常值（均值={mean_val:,.0f}，标准差={std_val:,.0f}）"
    elif outlier_pct < 0.05:
        result["narrative"] = f"🔵 {column}检测到 {outlier_count} 个极端值（Z>3，占 {_format_pct(outlier_pct)}），在正常范围"
    else:
        result["narrative"] = f"🔴 {column}检测到 {outlier_count} 个极端值（Z>3，占 {_format_pct(outlier_pct)}），存在明显离群现象"

    return result


# ============================================================
# 2. 趋势分析模块
# ============================================================

def analyze_mom_change(
    df: pd.DataFrame,
    value_col: str,
    group_col: Optional[str] = None,
    month_col: str = '_month'
) -> Dict[str, Any]:
    """环比变化分析"""
    result = {"current_value": 0.0, "previous_value": 0.0, "absolute_change": 0.0,
              "pct_change": 0.0, "direction": "持平", "trend_series": pd.DataFrame(), "narrative": ""}

    if not _check_col(df, value_col) or not _check_col(df, month_col):
        result["narrative"] = f"⚠️ 缺少必要字段，无法进行环比分析"
        return result

    months = sorted(df[month_col].unique())
    if len(months) < 2:
        result["narrative"] = f"📅 仅有一个月数据，需要至少两个月才能进行环比分析"
        return result

    if group_col and _check_col(df, group_col):
        agg = df.groupby([month_col, group_col])[value_col].sum().reset_index()
    else:
        agg = df.groupby(month_col)[value_col].sum().reset_index()

    current = agg[agg[month_col] == months[-1]][value_col].sum()
    previous = agg[agg[month_col] == months[-2]][value_col].sum()

    result["current_value"] = float(current)
    result["previous_value"] = float(previous)
    result["absolute_change"] = float(current - previous)
    result["pct_change"] = float(_safe_divide(current - previous, previous))
    result["trend_series"] = agg

    if abs(result["pct_change"]) < 0.01:
        result["direction"] = "持平"
        result["narrative"] = f"📊 {value_col}环比基本持平，变化幅度 {_format_pct(result['pct_change'])}"
    elif result["pct_change"] > 0:
        result["direction"] = "上升"
        if result["pct_change"] > 0.15:
            result["narrative"] = f"🔴 {value_col}环比**大幅上升** {_format_pct(result['pct_change'])}（{_format_currency(result['previous_value'])} → {_format_currency(result['current_value'])}），需关注"
        else:
            result["narrative"] = f"🟡 {value_col}环比上升 {_format_pct(result['pct_change'])}（{_format_currency(result['previous_value'])} → {_format_currency(result['current_value'])}）"
    else:
        result["pct_change"] = -result["pct_change"] if result["pct_change"] < 0 else result["pct_change"]
        result["direction"] = "下降"
        result["narrative"] = f"🟢 {value_col}环比下降 {_format_pct(abs(current-previous)/previous if previous else 0)}（{_format_currency(result['previous_value'])} → {_format_currency(result['current_value'])}）"

    return result


def analyze_moving_average(
    df: pd.DataFrame,
    value_col: str,
    window: int = 3,
    group_col: Optional[str] = None,
    month_col: str = '_month'
) -> Dict[str, Any]:
    """移动平均分析"""
    result = {"ma_series": pd.DataFrame(), "latest_ma": 0.0, "trend_direction": "波动",
              "volatility": 0.0, "narrative": ""}

    if not _check_col(df, value_col) or not _check_col(df, month_col):
        result["narrative"] = f"⚠️ 缺少必要字段"
        return result

    if group_col and _check_col(df, group_col):
        ts = df.groupby(month_col)[value_col].sum()
    else:
        ts = df.groupby(month_col)[value_col].sum()

    if len(ts) < 3:
        result["narrative"] = f"📅 数据不足3个月，移动平均分析需要至少3个月数据"
        return result

    ma = ts.rolling(window=min(window, len(ts)), min_periods=1).mean()
    ma_df = pd.DataFrame({"value": ts.values, "MA": ma.values}, index=ts.index)

    result["ma_series"] = ma_df
    result["latest_ma"] = float(ma.iloc[-1])

    if len(ma) >= 3:
        recent = ma.iloc[-3:].values
        if recent[-1] > recent[0] * 1.05:
            result["trend_direction"] = "持续上升"
        elif recent[-1] < recent[0] * 0.95:
            result["trend_direction"] = "持续下降"
        else:
            result["trend_direction"] = "波动"

    cv = _safe_divide(float(ts.std()), float(ts.mean()))
    result["volatility"] = cv

    if cv < 0.05:
        vol_desc = "波动极小，趋势稳定"
    elif cv < 0.15:
        vol_desc = "存在一定波动"
    else:
        vol_desc = "波动较大，趋势不稳定"

    result["narrative"] = f"📈 {value_col}近{len(ts)}个月呈**{result['trend_direction']}**趋势，{vol_desc}（变异系数={cv:.2f}）。3期移动均值：{_format_currency(result['latest_ma'])}"

    return result


# ============================================================
# 3. 对比分析模块
# ============================================================

def compare_departments(
    df: pd.DataFrame,
    value_col: str,
    dept_col: str = '部门'
) -> Dict[str, Any]:
    """部门间差异检验 (Kruskal-Wallis H检验)"""
    result = {"h_statistic": 0.0, "p_value": 1.0, "is_significant": False,
              "dept_stats": pd.DataFrame(), "top_dept": "", "bottom_dept": "",
              "gap_pct": 0.0, "narrative": ""}

    if not _check_col(df, value_col) or not _check_col(df, dept_col):
        result["narrative"] = f"⚠️ 缺少必要字段"
        return result

    dept_groups = [g[value_col].dropna().values for _, g in df.groupby(dept_col) if len(g) >= 2]
    if len(dept_groups) < 2:
        result["narrative"] = f"⚠️ 有效部门数不足（需≥2），无法进行对比分析"
        return result

    try:
        h_stat, p_value = stats.kruskal(*dept_groups)
        result["h_statistic"] = float(h_stat)
        result["p_value"] = float(p_value)
        result["is_significant"] = p_value < 0.05
    except Exception:
        result["narrative"] = "⚠️ 统计检验失败，数据可能不满足检验条件"
        return result

    dept_stats = df.groupby(dept_col)[value_col].agg(['mean', 'median', 'std', 'count']).reset_index()
    dept_stats.columns = [dept_col, '均值', '中位数', '标准差', '人数']
    result["dept_stats"] = dept_stats

    top_dept = dept_stats.loc[dept_stats['均值'].idxmax()]
    bottom_dept = dept_stats.loc[dept_stats['均值'].idxmin()]
    result["top_dept"] = str(top_dept[dept_col])
    result["bottom_dept"] = str(bottom_dept[dept_col])
    gap = _safe_divide(float(top_dept['均值']) - float(bottom_dept['均值']), float(bottom_dept['均值']))
    result["gap_pct"] = gap

    if result["is_significant"]:
        if gap > 0.5:
            result["narrative"] = (
                f"🔴 **{value_col}在部门间存在显著差异**（Kruskal-Wallis H={h_stat:.2f}, p={p_value:.4f}）。"
                f"{result['top_dept']}均值最高（{_format_currency(top_dept['均值'])}），"
                f"{result['bottom_dept']}最低（{_format_currency(bottom_dept['均值'])}），"
                f"差距达{_format_pct(gap)}，建议审视薪酬公平性。"
            )
        else:
            result["narrative"] = (
                f"🟡 **{value_col}在部门间存在统计差异**（p={p_value:.4f}），"
                f"但差距幅度适中（{_format_pct(gap)}），"
                f"{result['top_dept']}最高、{result['bottom_dept']}最低。"
            )
    else:
        result["narrative"] = (
            f"✅ **{value_col}在部门间无显著统计差异**（p={p_value:.3f}>0.05），"
            f"各部门分布相对均匀。{result['top_dept']}均值略高（{_format_currency(top_dept['均值'])}），"
            f"差距{_format_pct(gap)}。"
        )

    return result


def compare_two_groups(
    group_a: pd.Series,
    group_b: pd.Series,
    label_a: str,
    label_b: str
) -> Dict[str, Any]:
    """两组对比 (Mann-Whitney U检验)"""
    result = {"u_statistic": 0.0, "p_value": 1.0, "is_significant": False,
              "mean_a": 0.0, "mean_b": 0.0, "effect_size": 0.0, "narrative": ""}

    a = group_a.dropna()
    b = group_b.dropna()
    if len(a) < 3 or len(b) < 3:
        result["narrative"] = f"⚠️ 两组数据量不足，无法进行对比检验"
        return result

    try:
        u_stat, p_value = stats.mannwhitneyu(a, b, alternative='two-sided')
        result["u_statistic"] = float(u_stat)
        result["p_value"] = float(p_value)
        result["is_significant"] = p_value < 0.05
    except Exception:
        result["narrative"] = "⚠️ Mann-Whitney检验失败"
        return result

    result["mean_a"] = float(a.mean())
    result["mean_b"] = float(b.mean())
    n_total = len(a) + len(b)
    z = abs(stats.norm.ppf(p_value / 2)) if p_value < 1 else 0
    result["effect_size"] = float(_safe_divide(z, np.sqrt(n_total)))

    diff_pct = _safe_divide(abs(result["mean_a"] - result["mean_b"]), min(result["mean_a"], result["mean_b"]))
    direction = f"{label_a}高于{label_b}" if result["mean_a"] > result["mean_b"] else f"{label_b}高于{label_a}"

    if result["is_significant"]:
        result["narrative"] = f"🔴 **{label_a}与{label_b}存在显著差异**（p={p_value:.4f}），{direction}，差距{_format_pct(diff_pct)}"
    else:
        result["narrative"] = f"✅ **{label_a}与{label_b}无显著差异**（p={p_value:.3f}>0.05），差距{_format_pct(diff_pct)}"

    return result


# ============================================================
# 4. 相关性分析模块
# ============================================================

def analyze_correlation(
    df: pd.DataFrame,
    col_pairs: List[Tuple[str, str]]
) -> Dict[str, Any]:
    """数值-数值Spearman相关性分析"""
    result = {"correlations": [], "narrative": ""}

    narratives = []
    for col1, col2 in col_pairs:
        item = {"var1": col1, "var2": col2, "coefficient": 0.0, "p_value": 1.0,
                "is_significant": False, "strength": "无显著相关", "direction": ""}

        if not _check_col(df, col1) or not _check_col(df, col2):
            item["narrative"] = f"⚠️ 缺少{col1}或{col2}字段"
            result["correlations"].append(item)
            continue

        valid = df[[col1, col2]].dropna()
        if len(valid) < 5:
            item["narrative"] = f"⚠️ 有效数据不足"
            result["correlations"].append(item)
            continue

        try:
            rho, p = stats.spearmanr(valid[col1], valid[col2])
            item["coefficient"] = float(rho)
            item["p_value"] = float(p)
            item["is_significant"] = p < 0.05
            item["direction"] = "正相关" if rho > 0 else "负相关"

            abs_r = abs(rho)
            if abs_r >= 0.7:
                item["strength"] = "强" + item["direction"]
            elif abs_r >= 0.4:
                item["strength"] = "中等" + item["direction"]
            elif p < 0.05:
                item["strength"] = "弱" + item["direction"]
            else:
                item["strength"] = "无显著相关"
        except Exception:
            item["strength"] = "计算失败"

        result["correlations"].append(item)

        if item["is_significant"]:
            narratives.append(f"**{col1}**与**{col2}**呈{item['strength']}（ρ={rho:.3f}, p={p:.4f}）")
        else:
            narratives.append(f"**{col1}**与**{col2}**无显著相关性（p={p:.3f}）")

    result["narrative"] = " | ".join(narratives) if narratives else "无法进行相关性分析"
    return result


def analyze_categorical_relation(
    df: pd.DataFrame,
    col1: str,
    col2: str
) -> Dict[str, Any]:
    """分类-分类关联分析 (卡方检验 + Cramer's V)"""
    result = {"chi2": 0.0, "p_value": 1.0, "cramers_v": 0.0,
              "is_significant": False, "strength": "无关联",
              "contingency_table": pd.DataFrame(), "narrative": ""}

    if not _check_col(df, col1) or not _check_col(df, col2):
        result["narrative"] = f"⚠️ 缺少{col1}或{col2}字段"
        return result

    try:
        ctab = pd.crosstab(df[col1], df[col2])
        result["contingency_table"] = ctab

        if ctab.shape[0] < 2 or ctab.shape[1] < 2:
            result["narrative"] = f"⚠️ 分类维度不足，无法进行关联分析"
            return result

        chi2, p, dof, expected = stats.chi2_contingency(ctab)
        result["chi2"] = float(chi2)
        result["p_value"] = float(p)
        result["is_significant"] = p < 0.05

        n = ctab.sum().sum()
        min_dim = min(ctab.shape) - 1
        cramers_v = np.sqrt(chi2 / (n * min_dim)) if min_dim > 0 else 0
        result["cramers_v"] = float(cramers_v)

        if cramers_v >= 0.3:
            result["strength"] = "强关联"
        elif cramers_v >= 0.15:
            result["strength"] = "中等关联"
        elif p < 0.05:
            result["strength"] = "弱关联"
        else:
            result["strength"] = "无显著关联"
    except Exception:
        result["narrative"] = "⚠️ 卡方检验计算失败"
        return result

    if result["is_significant"]:
        result["narrative"] = (
            f"🔴 **{col1}与{col2}存在{result['strength']}**"
            f"（χ²={chi2:.2f}, p={p:.4f}, Cramér's V={cramers_v:.3f}）。"
            f"说明{col1}分布与{col2}显著相关，非随机分布。"
        )
    else:
        result["narrative"] = (
            f"✅ **{col1}与{col2}无显著关联**（χ²={chi2:.2f}, p={p:.3f}>0.05）。"
            f"两个维度的分布相对独立。"
        )

    return result


# ============================================================
# 5. 分布分析模块
# ============================================================

def calc_gini(series: pd.Series, label: str = '') -> Dict[str, Any]:
    """基尼系数计算"""
    result = {"gini": 0.0, "interpretation": "", "narrative": ""}

    s = series.dropna().values
    if len(s) < 2:
        result["narrative"] = "⚠️ 数据不足，无法计算基尼系数"
        return result

    s_sorted = np.sort(s)
    n = len(s_sorted)
    index = np.arange(1, n + 1)
    gini = (2 * np.sum(index * s_sorted)) / (n * np.sum(s_sorted)) - (n + 1) / n
    result["gini"] = float(gini)

    if gini < 0.2:
        result["interpretation"] = "高度均衡"
        emoji = "✅"
    elif gini < 0.3:
        result["interpretation"] = "相对均衡"
        emoji = "🔵"
    elif gini < 0.4:
        result["interpretation"] = "存在一定差距"
        emoji = "🟡"
    elif gini < 0.5:
        result["interpretation"] = "差距较大"
        emoji = "🟠"
    else:
        result["interpretation"] = "严重不均衡"
        emoji = "🔴"

    prefix = f"**{label}**" if label else "数值"
    result["narrative"] = f"{emoji} {prefix}基尼系数为 **{gini:.3f}**，分布**{result['interpretation']}**。"

    return result


def calc_pareto(
    df: pd.DataFrame,
    value_col: str,
    category_col: str,
    top_n: int = 5
) -> Dict[str, Any]:
    """帕累托分析 (二八法则)"""
    result = {"pareto_data": pd.DataFrame(), "top80_pct_of_categories": 0.0,
              "top_n_contribution": 0.0, "narrative": ""}

    if not _check_col(df, value_col) or not _check_col(df, category_col):
        result["narrative"] = f"⚠️ 缺少必要字段"
        return result

    agg = df.groupby(category_col)[value_col].sum().sort_values(ascending=False)
    total = agg.sum()
    if total == 0:
        result["narrative"] = "⚠️ 总和为0，无法进行帕累托分析"
        return result

    cum_pct = agg.cumsum() / total
    pareto_df = pd.DataFrame({
        category_col: agg.index,
        value_col: agg.values,
        "累计占比": cum_pct.values
    })
    result["pareto_data"] = pareto_df

    # 80%的贡献来自多少%的类别
    idx80 = (cum_pct <= 0.8).sum()
    pct_categories = _safe_divide(idx80 + 1, len(agg))
    result["top80_pct_of_categories"] = pct_categories

    # 前N个贡献占比
    top_contrib = _safe_divide(agg.head(top_n).sum(), total)
    result["top_n_contribution"] = top_contrib

    if pct_categories <= 0.3:
        pareto_desc = f"前{_format_pct(pct_categories)}的类别贡献了80%的{value_col}，集中度较高，符合二八法则"
    else:
        pareto_desc = f"需前{_format_pct(pct_categories)}的类别才能覆盖80%，分布相对分散"

    result["narrative"] = (
        f"📊 **{value_col}帕累托分析**：{pareto_desc}。"
        f"前{top_n}个{category_col}合计贡献 {_format_pct(top_contrib)}。"
    )

    return result


# ============================================================
# 6. 预测预警模块
# ============================================================

def simple_exponential_smoothing(
    series: pd.Series,
    alpha: float = 0.3,
    forecast_periods: int = 1
) -> Dict[str, Any]:
    """简单指数平滑预测"""
    result = {"fitted": pd.Series(dtype=float), "forecast": 0.0,
              "forecast_lower": 0.0, "forecast_upper": 0.0,
              "trend": "平稳", "narrative": ""}

    s = series.dropna()
    if len(s) < 3:
        result["narrative"] = "⚠️ 数据点不足（需≥3），无法进行趋势预测"
        return result

    # 指数平滑拟合
    fitted = [float(s.iloc[0])]
    for i in range(1, len(s)):
        fitted.append(alpha * float(s.iloc[i]) + (1 - alpha) * fitted[-1])

    # 预测
    forecast = alpha * float(s.iloc[-1]) + (1 - alpha) * fitted[-1]
    result["forecast"] = forecast

    # 置信区间（基于拟合误差）
    errors = np.array([float(s.iloc[i]) - fitted[i] for i in range(len(s))])
    std_err = float(np.std(errors)) if len(errors) > 0 else 0
    result["forecast_lower"] = forecast - std_err
    result["forecast_upper"] = forecast + std_err

    # 趋势判断
    if len(fitted) >= 3:
        recent = fitted[-3:]
        if recent[-1] > recent[0] * 1.05:
            result["trend"] = "上升趋势"
        elif recent[-1] < recent[0] * 0.95:
            result["trend"] = "下降趋势"
        else:
            result["trend"] = "平稳"

    result["narrative"] = (
        f"🔮 **趋势预测**：基于指数平滑（α={alpha}），当前呈**{result['trend']}**，"
        f"下期预测值 {_format_currency(forecast)}，"
        f"预测区间 [{_format_currency(result['forecast_lower'])}, {_format_currency(result['forecast_upper'])}]"
    )

    return result


def risk_early_warning(
    df: pd.DataFrame,
    risk_factors: Optional[Dict[str, Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """风险预警综合评分"""
    result = {"risk_scores": pd.DataFrame(), "high_risk_count": 0, "high_risk_pct": 0.0,
              "risk_distribution": {}, "narrative": ""}

    if df is None or df.empty:
        result["narrative"] = "⚠️ 无数据，无法进行风险预警"
        return result

    if risk_factors is None:
        risk_factors = {}

    # 默认风险因子配置
    if not risk_factors:
        if _check_col(df, '离职风险'):
            risk_factors['离职风险'] = {'高': 3, '中': 2, '低': 1}
        if _check_col(df, '绩效等级'):
            risk_factors['绩效等级'] = {'D': 3, 'C': 2}
        if _check_col(df, '关键岗位'):
            risk_factors['关键岗位'] = {'是': 1}

    if not risk_factors:
        result["narrative"] = "⚠️ 未配置风险因子且数据中无可用的风险字段"
        return result

    df_copy = df.copy()
    df_copy['risk_score'] = 0

    for factor, mapping in risk_factors.items():
        if _check_col(df_copy, factor):
            df_copy['risk_score'] += df_copy[factor].map(mapping).fillna(0)

    max_score = df_copy['risk_score'].max()
    if max_score <= 0:
        result["narrative"] = "✅ 当前所有人员风险评分均为0，无预警信号"
        result["risk_scores"] = df_copy
        return result

    # 风险等级划分
    bins = [0, 2, 4, max_score + 1]
    labels = ['低风险', '中风险', '高风险']
    df_copy['risk_level'] = pd.cut(df_copy['risk_score'], bins=bins, labels=labels, right=False)

    dist = df_copy['risk_level'].value_counts().to_dict()
    result["risk_distribution"] = {str(k): int(v) for k, v in dist.items()}
    result["high_risk_count"] = int(dist.get('高风险', 0))
    result["high_risk_pct"] = float(_safe_divide(result["high_risk_count"], len(df_copy)))
    result["risk_scores"] = df_copy

    if result["high_risk_count"] == 0:
        result["narrative"] = "✅ 当前无高风险人员，风险可控"
    elif result["high_risk_pct"] < 0.05:
        result["narrative"] = (
            f"🔵 识别出 **{result['high_risk_count']}** 名高风险人员（占{_format_pct(result['high_risk_pct'])}），"
            f"中风险 **{dist.get('中风险', 0)}** 人。建议对高风险人员重点关注。"
        )
    elif result["high_risk_pct"] < 0.15:
        result["narrative"] = (
            f"🟡 识别出 **{result['high_risk_count']}** 名高风险人员（占{_format_pct(result['high_risk_pct'])}），"
            f"比例偏高，建议制定专项保留计划。"
        )
    else:
        result["narrative"] = (
            f"🔴 识别出 **{result['high_risk_count']}** 名高风险人员（占{_format_pct(result['high_risk_pct'])}），"
            f"风险比例较高，需立即采取干预措施！"
        )

    return result


# ============================================================
# 7. 聚类分析模块
# ============================================================

def cluster_high_risk(
    df: pd.DataFrame,
    features: List[str],
    n_clusters: int = 4,
    random_state: int = 42
) -> Dict[str, Any]:
    """K-Means聚类识别高风险人群"""
    result = {"clustered_data": pd.DataFrame(), "cluster_profiles": pd.DataFrame(),
              "cluster_sizes": {}, "risk_cluster": -1,
              "risk_cluster_characteristics": "", "narrative": ""}

    if df is None or df.empty:
        result["narrative"] = "⚠️ 无数据，无法进行聚类分析"
        return result

    # 检查特征列
    valid_features = [f for f in features if _check_col(df, f)]
    if len(valid_features) < 2:
        result["narrative"] = f"⚠️ 有效特征数不足（需≥2），当前仅{len(valid_features)}个"
        return result

    cluster_df = df[valid_features].dropna().copy()
    if len(cluster_df) < n_clusters * 3:
        result["narrative"] = f"⚠️ 有效数据量（{len(cluster_df)}条）不足以支撑{n_clusters}类聚类"
        return result

    try:
        # 标准化
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(cluster_df)

        # K-Means聚类
        kmeans = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=10)
        labels = kmeans.fit_predict(X_scaled)

        df_result = df.loc[cluster_df.index].copy()
        df_result['cluster'] = labels
        result["clustered_data"] = df_result

        # 聚类规模
        sizes = {int(i): int((labels == i).sum()) for i in range(n_clusters)}
        result["cluster_sizes"] = sizes

        # 聚类中心（用原始单位）
        centers = pd.DataFrame(scaler.inverse_transform(kmeans.cluster_centers_),
                               columns=valid_features)
        result["cluster_profiles"] = centers

        # 识别高风险聚类（基于各聚类中心特征：高离职风险 + 低绩效 + 低工龄等）
        # 简化策略：计算每个聚类在负向特征上的排名
        risk_scores = np.zeros(n_clusters)
        for fi, feat in enumerate(valid_features):
            # 特征值越大风险越高（如果是负向指标如迟到次数）则加分
            center_vals = centers[feat].values
            if feat in ['迟到次数', '缺勤天数']:
                # 越高风险越大
                if center_vals.max() > center_vals.min():
                    risk_scores += (center_vals - center_vals.min()) / (center_vals.max() - center_vals.min())
            elif feat in ['绩效工资', '实发工资', '工龄']:
                # 越低风险越大（反相关）
                if center_vals.max() > center_vals.min():
                    risk_scores += 1 - (center_vals - center_vals.min()) / (center_vals.max() - center_vals.min())

        result["risk_cluster"] = int(np.argmax(risk_scores))

        # 高风险聚类特征描述
        risk_center = centers.iloc[result["risk_cluster"]]
        desc_parts = []
        for feat in valid_features:
            desc_parts.append(f"{feat}={risk_center[feat]:.1f}")
        result["risk_cluster_characteristics"] = ", ".join(desc_parts)

        risk_size = sizes.get(result["risk_cluster"], 0)
        result["narrative"] = (
            f"🔍 **聚类分析结果**：将人员分为 **{n_clusters}** 类，"
            f"其中聚类{result['risk_cluster']}被识别为**高风险群体**（{risk_size}人），"
            f"特征：{result['risk_cluster_characteristics']}。"
            f"建议重点关注该群体的人员动态。"
        )

    except Exception as e:
        result["narrative"] = f"⚠️ 聚类分析失败：{str(e)[:100]}"

    return result


# ============================================================
# 8. 自然语言报告生成
# ============================================================

def generate_narrative(analyses: List[Dict[str, Any]], style: str = 'executive') -> str:
    """基于分析结果动态生成自然语言报告"""
    lines = []
    if style == 'executive':
        lines.append("### 🧠 AI 智能分析\n")
        for i, a in enumerate(analyses):
            if a and isinstance(a, dict) and a.get("narrative"):
                lines.append(f"{a['narrative']}\n")
    elif style == 'detailed':
        lines.append("### 📊 详细分析报告\n")
        for i, a in enumerate(analyses):
            if a and isinstance(a, dict):
                n = a.get("narrative", "")
                if n:
                    lines.append(f"#### 分析维度 {i+1}\n{n}\n")
    elif style == 'action_items':
        lines.append("### 📋 行动建议\n")
        items = []
        for a in analyses:
            if a and isinstance(a, dict) and a.get("narrative"):
                narrative = a["narrative"]
                if "🔴" in narrative:
                    items.append(f"- 🚨 **紧急**：{narrative.split('🔴')[-1].strip()}")
                elif "🟡" in narrative:
                    items.append(f"- ⚠️ **关注**：{narrative.split('🟡')[-1].strip()}")
        if items:
            lines.extend(items)
        else:
            lines.append("当前未发现需要紧急处理的事项。")
    else:
        lines.append(str(analyses))

    return "\n".join(lines)


def generate_full_report(
    payroll: Optional[pd.DataFrame],
    cost: Optional[pd.DataFrame],
    talent: Optional[pd.DataFrame],
    months: List[str],
    department: str = '全部'
) -> str:
    """生成完整周报/月报"""
    from datetime import datetime

    report = []
    report.append(f"# 📊 HR数据分析报告")
    report.append(f"")
    report.append(f"**生成时间**：{datetime.now().strftime('%Y年%m月%d日 %H:%M')} | **数据周期**：{', '.join(months) if months else '全部'} | **部门范围**：{department}")
    report.append(f"")
    report.append(f"---")
    report.append(f"")

    # ── 一、执行摘要 ──
    report.append(f"## 一、执行摘要")
    report.append(f"")

    findings = []

    # 成本分析
    if cost is not None and not cost.empty and "总成本" in cost.columns:
        tc = cost["总成本"].sum()
        report.append(f"- 💰 **总人力成本**：{_format_currency(tc)}")

        if len(months) >= 2 and "_month" in cost.columns:
            mom = analyze_mom_change(cost, "总成本")
            if mom["narrative"]:
                findings.append(mom["narrative"])

    # 薪酬分析
    if payroll is not None and not payroll.empty:
        hd = payroll["员工ID"].nunique() if "员工ID" in payroll.columns else len(payroll)
        report.append(f"- 👥 **总人数**：{hd} 人")

        if "实发工资" in payroll.columns:
            av = payroll["实发工资"].mean()
            report.append(f"- 💵 **平均薪酬**：{_format_currency(av)}")

            gini_result = calc_gini(payroll["实发工资"], "薪酬")
            if gini_result["narrative"]:
                findings.append(gini_result["narrative"])

        if "应出勤天数" in payroll.columns and "实际出勤天数" in payroll.columns:
            ar = _safe_divide(payroll["实际出勤天数"].sum(), payroll["应出勤天数"].sum())
            report.append(f"- 📅 **出勤率**：{_format_pct(ar)}")

            ar_dept = compare_departments(payroll.assign(
                _ar=lambda x: x["实际出勤天数"] / x["应出勤天数"].replace(0, 1)
            ), "_ar")
            if ar_dept["narrative"] and ar_dept["is_significant"]:
                findings.append(ar_dept["narrative"])

    # 风险分析
    if talent is not None and not talent.empty:
        if "离职风险" in talent.columns:
            hr_count = int((talent["离职风险"] == "高").sum())
            report.append(f"- ⚠️ **高风险人员**：{hr_count} 人")

        risk_result = risk_early_warning(talent)
        if risk_result["narrative"]:
            findings.append(risk_result["narrative"])

    report.append(f"")

    if findings:
        report.append(f"> **核心发现**：")
        for f in findings[:5]:
            report.append(f"> {f}")
        report.append(f"")

    report.append(f"---")
    report.append(f"")

    # ── 二、KPI概览 ──
    report.append(f"## 二、关键指标概览")
    report.append(f"")

    kpi_rows = [("指标", "当前值", "状态")]
    if payroll is not None and not payroll.empty:
        hd = payroll["员工ID"].nunique() if "员工ID" in payroll.columns else len(payroll)
        kpi_rows.append(("总人数", f"{hd}人", "🟢"))
    if cost is not None and not cost.empty and "总成本" in cost.columns:
        tc = cost["总成本"].sum()
        kpi_rows.append(("总成本", _format_currency(tc), "🟢" if tc < 10000000 else "🟡"))
    if payroll is not None and not payroll.empty and "实发工资" in payroll.columns:
        av = payroll["实发工资"].mean()
        kpi_rows.append(("平均薪酬", _format_currency(av), "🟢"))
    if payroll is not None and not payroll.empty and "应出勤天数" in payroll.columns:
        ar = _safe_divide(payroll["实际出勤天数"].sum(), payroll["应出勤天数"].sum())
        status = "🟢" if ar > 0.95 else ("🟡" if ar > 0.90 else "🔴")
        kpi_rows.append(("出勤率", _format_pct(ar), status))
    if talent is not None and not talent.empty and "离职风险" in talent.columns:
        hr_count = int((talent["离职风险"] == "高").sum())
        status = "🟢" if hr_count < 5 else ("🟡" if hr_count < 15 else "🔴")
        kpi_rows.append(("高风险人数", f"{hr_count}人", status))

    # 简单表格
    for row in kpi_rows:
        report.append(f"| {' | '.join(row)} |")
    report.append(f"")

    report.append(f"---")
    report.append(f"")

    # ── 三、各维度分析 ──
    report.append(f"## 三、各维度深度分析")
    report.append(f"")

    # 3.1 薪酬分析
    if payroll is not None and not payroll.empty:
        report.append(f"### 3.1 薪酬考勤")
        report.append(f"")

        if "实发工资" in payroll.columns and "部门" in payroll.columns:
            dept_comp = compare_departments(payroll, "实发工资")
            report.append(f"{dept_comp.get('narrative', '')}")
            report.append(f"")

            gini = calc_gini(payroll["实发工资"], "薪酬")
            report.append(f"{gini.get('narrative', '')}")
            report.append(f"")

            outlier = detect_outliers_iqr(payroll, "实发工资")
            report.append(f"{outlier.get('narrative', '')}")
            report.append(f"")

        if "迟到次数" in payroll.columns:
            late_dept = compare_departments(payroll, "迟到次数")
            if late_dept.get("is_significant"):
                report.append(f"{late_dept.get('narrative', '')}")
                report.append(f"")

    # 3.2 成本分析
    if cost is not None and not cost.empty:
        report.append(f"### 3.2 人力成本")
        report.append(f"")

        if "部门" in cost.columns and "总成本" in cost.columns:
            dept_cost = compare_departments(cost, "总成本")
            report.append(f"{dept_cost.get('narrative', '')}")
            report.append(f"")

        cost_cols = [c for c in ["工资总额", "社保公积金", "福利费", "招聘费", "培训费"] if c in cost.columns]
        if cost_cols and "部门" in cost.columns:
            cost_melt = cost.melt(id_vars=["部门"], value_vars=cost_cols, var_name="成本类型", value_name="金额")
            pareto_result = calc_pareto(cost_melt, "金额", "成本类型")
            report.append(f"{pareto_result.get('narrative', '')}")
            report.append(f"")

    # 3.3 人才分析
    if talent is not None and not talent.empty:
        report.append(f"### 3.3 人才盘点")
        report.append(f"")

        if "绩效等级" in talent.columns and "部门" in talent.columns:
            perf_rel = analyze_categorical_relation(talent, "部门", "绩效等级")
            report.append(f"{perf_rel.get('narrative', '')}")
            report.append(f"")

        risk_warn = risk_early_warning(talent)
        report.append(f"{risk_warn.get('narrative', '')}")
        report.append(f"")

        if "继任者准备度" in talent.columns:
            ready = (talent["继任者准备度"] == "可晋升").sum()
            key_ready = talent[(talent["继任者准备度"] == "可晋升") & (talent.get("关键岗位", "") == "是")]
            report.append(f"- 📋 **继任准备**：{ready} 人可晋升，其中 {len(key_ready)} 人为关键岗位")
            report.append(f"")

    report.append(f"---")
    report.append(f"")

    # ── 四、预测与预警 ──
    report.append(f"## 四、预测与预警")
    report.append(f"")

    if cost is not None and not cost.empty and "总成本" in cost.columns and "_month" in cost.columns:
        cost_ts = cost.groupby("_month")["总成本"].sum()
        if len(cost_ts) >= 3:
            forecast = simple_exponential_smoothing(cost_ts)
            report.append(f"{forecast.get('narrative', '')}")
            report.append(f"")

    if talent is not None and not talent.empty:
        cluster_features = []
        for f in ["工龄", "绩效工资"] if payroll is not None else ["工龄"]:
            if _check_col(talent, f):
                cluster_features.append(f)
        if len(cluster_features) >= 2:
            cluster_result = cluster_high_risk(talent, cluster_features, n_clusters=3)
            report.append(f"{cluster_result.get('narrative', '')}")
            report.append(f"")

    report.append(f"---")
    report.append(f"")

    # ── 五、行动建议 ──
    report.append(f"## 五、行动建议")
    report.append(f"")

    suggestions = []

    # 基于分析结果自动生成建议
    if payroll is not None and not payroll.empty and "实发工资" in payroll.columns:
        gini = calc_gini(payroll["实发工资"])
        if gini["gini"] > 0.35:
            suggestions.append(("紧急", "薪酬分布不均衡（基尼系数>0.35），建议审视薪酬结构公平性，重点关注高薪和低薪两端的合理性"))

    if talent is not None and not talent.empty and "离职风险" in talent.columns:
        hr_count = int((talent["离职风险"] == "高").sum())
        if hr_count > 10:
            suggestions.append(("紧急", f"高风险离职人员达{hr_count}人，建议立即启动一对一沟通，了解离职意向并制定挽留方案"))
        elif hr_count > 5:
            suggestions.append(("关注", f"高风险离职人员{hr_count}人，建议定期跟进，提前储备替代人选"))

    if payroll is not None and not payroll.empty and "缺勤天数" in payroll.columns:
        absent = payroll["缺勤天数"].sum()
        if absent > 30:
            suggestions.append(("关注", f"总缺勤天数{absent}天，建议排查是否存在集中请假或异常缺勤模式"))

    if payroll is not None and not payroll.empty and "加班费" in payroll.columns:
        ot_total = payroll["加班费"].sum()
        if ot_total > 50000:
            suggestions.append(("关注", f"加班费总额{_format_currency(ot_total)}，建议评估加班是否常态化，考虑增加人手或优化排班"))

    if talent is not None and not talent.empty and "继任者准备度" in talent.columns:
        key_pos = talent[talent.get("关键岗位", "") == "是"]
        if not key_pos.empty:
            ready_pct = _safe_divide((key_pos["继任者准备度"] == "可晋升").sum(), len(key_pos))
            if ready_pct < 0.3:
                suggestions.append(("持续", f"关键岗位继任覆盖率仅{_format_pct(ready_pct)}，建议加强关键岗位继任者培养"))

    if not suggestions:
        suggestions.append(("持续", "当前各指标在正常范围内，建议保持现有管理节奏，定期关注KPI变化趋势"))
        suggestions.append(("持续", "建议每月更新数据后关注环比变化，及时发现潜在问题"))

    for priority, text in suggestions:
        emoji = {"紧急": "🚨", "关注": "⚠️", "持续": "📌"}.get(priority, "•")
        report.append(f"{emoji} **{priority}**：{text}")
        report.append(f"")

    report.append(f"---")
    report.append(f"*本报告由HR智能分析引擎自动生成 | {datetime.now().strftime('%Y-%m-%d %H:%M')}*")

    return "\n".join(report)


# ============================================================
# 9. 模块集成函数 (供app.py直接调用)
# ============================================================

def analyze_module_1_dashboard(
    payroll: Optional[pd.DataFrame],
    cost: Optional[pd.DataFrame],
    talent: Optional[pd.DataFrame]
) -> str:
    """模块1-综合仪表板: 生成总体洞察文字"""
    analyses = []

    if cost is not None and not cost.empty and "总成本" in cost.columns:
        if "_month" in cost.columns and cost["_month"].nunique() >= 2:
            mom = analyze_mom_change(cost, "总成本")
            analyses.append(mom)
        ma = analyze_moving_average(cost, "总成本")
        if ma["narrative"] and "不足" not in ma["narrative"]:
            analyses.append(ma)

    if payroll is not None and not payroll.empty:
        if "实发工资" in payroll.columns:
            gini = calc_gini(payroll["实发工资"], "薪酬")
            analyses.append(gini)

            outlier = detect_outliers_iqr(payroll, "实发工资")
            analyses.append(outlier)

        if "应出勤天数" in payroll.columns and "部门" in payroll.columns:
            payroll_copy = payroll.copy()
            payroll_copy["_出勤率"] = payroll_copy["实际出勤天数"] / payroll_copy["应出勤天数"].replace(0, 1)
            ar_dept = compare_departments(payroll_copy, "_出勤率")
            analyses.append(ar_dept)

    if talent is not None and not talent.empty:
        risk = risk_early_warning(talent)
        analyses.append(risk)

    if not analyses:
        return "📊 数据加载中，请确保已上传或生成数据文件"

    return generate_narrative(analyses, style='executive')


def analyze_module_2_payroll(
    payroll: pd.DataFrame,
    selected_metric: str
) -> str:
    """模块2-薪酬考勤分析: 基于选中指标生成分析"""
    metric_map = {
        "平均工资": "实发工资", "加班费总额": "加班费",
        "缺勤天数合计": "缺勤天数", "迟到次数合计": "迟到次数",
        "奖金总额": "奖金"
    }
    col_name = metric_map.get(selected_metric, "实发工资")

    analyses = []

    if _check_col(payroll, col_name) and _check_col(payroll, "部门"):
        dept_comp = compare_departments(payroll, col_name)
        analyses.append(dept_comp)

    if col_name == "实发工资" and _check_col(payroll, "实发工资"):
        outlier = detect_outliers_iqr(payroll, "实发工资")
        analyses.append(outlier)
        gini = calc_gini(payroll["实发工资"], "薪酬")
        analyses.append(gini)
    elif _check_col(payroll, col_name) and payroll[col_name].dtype in ['int64', 'float64']:
        outlier = detect_outliers_iqr(payroll, col_name)
        analyses.append(outlier)

    if not analyses:
        return "📊 当前数据无法生成分析，请检查数据完整性"

    return generate_narrative(analyses, style='executive')


def analyze_module_3_hr(
    payroll: pd.DataFrame,
    active_tab: str
) -> str:
    """模块3-人力资源分析: 基于当前tab生成分析"""
    analyses = []

    if active_tab == "离职率" and "离职状态" in payroll.columns and "部门" in payroll.columns:
        payroll_copy = payroll.copy()
        payroll_copy["_离职率"] = (payroll_copy["离职状态"] == "已离职").astype(float)
        dr_dept = compare_departments(payroll_copy, "_离职率")
        analyses.append(dr_dept)

    elif active_tab == "离职原因" and "离职原因" in payroll.columns and "离职状态" in payroll.columns:
        lv = payroll[payroll["离职状态"] == "已离职"]
        if not lv.empty and len(lv["离职原因"].dropna()) > 0:
            pareto = calc_pareto(lv, lv.groupby("离职原因").size().reset_index(name="人数"), "人数", "离职原因")
            analyses.append(pareto)

    elif active_tab == "留存率" and "工龄" in payroll.columns and "离职状态" in payroll.columns:
        corr = analyze_correlation(payroll, [("工龄", "离职状态".replace("已离职", "1").replace("在职", "0"))])
        analyses.append(corr)

    elif active_tab == "职级" and "职级" in payroll.columns:
        # 职级分布分析
        level_counts = payroll["职级"].value_counts()
        if len(level_counts) > 0:
            level_series = pd.Series({l: c for l, c in level_counts.items()})
            gini = calc_gini(level_series, "职级分布")
            analyses.append(gini)

    elif active_tab == "工龄" and "工龄" in payroll.columns:
        outlier = detect_outliers_zscore(payroll, "工龄")
        analyses.append(outlier)

    elif active_tab == "学历" and "学历" in payroll.columns and "职级" in payroll.columns:
        rel = analyze_categorical_relation(payroll, "学历", "职级")
        analyses.append(rel)

    if not analyses:
        return f"📊 当前'{active_tab}'标签暂无深度分析数据，请检查对应数据字段是否完整"

    return generate_narrative(analyses, style='executive')


def analyze_module_4_cost(
    cost: pd.DataFrame,
    payroll: pd.DataFrame,
    active_tab: str
) -> str:
    """模块4-人工成本分析"""
    analyses = []

    if active_tab == "成本构成" and cost is not None and not cost.empty:
        cost_cols = [c for c in ["工资总额", "社保公积金", "福利费", "招聘费", "培训费"] if c in cost.columns]
        if cost_cols and "部门" in cost.columns:
            cost_melt = cost.melt(id_vars=["部门"], value_vars=cost_cols, var_name="成本类型", value_name="金额")
            pareto = calc_pareto(cost_melt, "金额", "成本类型")
            analyses.append(pareto)

        if "_month" in cost.columns and cost["_month"].nunique() >= 2:
            mom = analyze_mom_change(cost, "总成本")
            analyses.append(mom)

    elif active_tab == "奖金分析" and payroll is not None and not payroll.empty and "奖金" in payroll.columns:
        gini = calc_gini(payroll["奖金"], "奖金")
        analyses.append(gini)
        if "部门" in payroll.columns:
            bonus_dept = compare_departments(payroll, "奖金")
            analyses.append(bonus_dept)

    elif active_tab == "团队业绩" and payroll is not None and not payroll.empty and "实发工资" in payroll.columns:
        payroll_copy = payroll.copy()
        if "部门" in payroll.columns:
            dept_comp = compare_departments(payroll, "实发工资")
            analyses.append(dept_comp)

    elif active_tab == "TOP10" and payroll is not None and not payroll.empty and "实发工资" in payroll.columns:
        outlier = detect_outliers_iqr(payroll, "实发工资")
        analyses.append(outlier)

    if not analyses:
        return f"📊 当前'{active_tab}'标签暂无深度分析数据"

    return generate_narrative(analyses, style='executive')


def analyze_module_5_talent_review(
    talent: pd.DataFrame,
    payroll: pd.DataFrame,
    active_tab: str
) -> str:
    """模块5-人员盘点分析"""
    analyses = []

    if active_tab == "九宫格" and talent is not None and not talent.empty:
        if "绩效等级" in talent.columns and "潜力评级" in talent.columns:
            ps = {"S": 5, "A": 4, "B": 3, "C": 2, "D": 1}
            pt = {"高": 3, "中": 2, "低": 1}
            df9 = talent.copy()
            df9["绩效分"] = df9["绩效等级"].map(ps)
            df9["潜力分"] = df9["潜力评级"].map(pt)
            total = len(df9)
            stars = len(df9[(df9["绩效分"] >= 4) & (df9["潜力分"] >= 3)])
            risks = len(df9[(df9["绩效分"] <= 2) & (df9["潜力分"] <= 1)])
            mid = total - stars - risks
            analyses.append({
                "narrative": (
                    f"📊 **人才九宫格概览**：共{total}人，🌟 **明星人才**（高绩效高潜力）{stars}人（{_format_pct(_safe_divide(stars, total))}），"
                    f"⚡ **待观察**{mid}人，⚠️ **风险区**（低绩效低潜力）{risks}人（{_format_pct(_safe_divide(risks, total))}）。"
                    f"{'需重点关注风险区人员' if risks > 0 else '整体人才结构健康'}"
                )
            })

    elif active_tab == "团队能力" and talent is not None and not talent.empty:
        if "绩效等级" in talent.columns and "部门" in talent.columns:
            rel = analyze_categorical_relation(talent, "部门", "绩效等级")
            analyses.append(rel)

    elif active_tab == "团队职级" and payroll is not None and not payroll.empty:
        if "职级" in payroll.columns:
            level_counts = payroll["职级"].value_counts()
            if len(level_counts) > 0:
                gini = calc_gini(pd.Series(level_counts.values, index=level_counts.index), "职级分布")
                analyses.append(gini)

    elif active_tab == "继任计划" and talent is not None and not talent.empty:
        if "继任者准备度" in talent.columns:
            total = len(talent)
            ready = int((talent["继任者准备度"] == "可晋升").sum())
            key_total = int((talent.get("关键岗位", pd.Series(["否"] * len(talent))) == "是").sum())
            key_ready = int(((talent["继任者准备度"] == "可晋升") & (talent.get("关键岗位", "") == "是")).sum())
            analyses.append({
                "narrative": (
                    f"📋 **继任计划概览**：共{total}人，可晋升 {ready} 人（{_format_pct(_safe_divide(ready, total))}）。"
                    f"关键岗位 {key_total} 个，其中 {key_ready} 个有可晋升继任者，"
                    f"覆盖率为 {_format_pct(_safe_divide(key_ready, key_total))}。"
                    f"{'⚠️ 关键岗位继任覆盖率不足，建议加强培养' if key_total > 0 and _safe_divide(key_ready, key_total) < 0.5 else '✅ 继任储备充足'}"
                )
            })

    if not analyses:
        return f"📊 当前'{active_tab}'标签暂无深度分析数据"

    return generate_narrative(analyses, style='executive')


def analyze_module_6_performance(
    talent: pd.DataFrame,
    active_tab: str
) -> str:
    """模块6-绩效分析"""
    analyses = []

    if active_tab == "团队绩效" and talent is not None and not talent.empty:
        if "绩效等级" in talent.columns and "部门" in talent.columns:
            rel = analyze_categorical_relation(talent, "部门", "绩效等级")
            analyses.append(rel)

    elif active_tab == "个人绩效" and talent is not None and not talent.empty:
        risk = risk_early_warning(talent)
        analyses.append(risk)

    if not analyses:
        return f"📊 当前'{active_tab}'标签暂无深度分析数据"

    return generate_narrative(analyses, style='executive')


def analyze_module_7_attendance(
    payroll: pd.DataFrame,
    active_tab: str
) -> str:
    """模块7-考勤异常分析"""
    analyses = []

    if active_tab == "异常人员清单":
        if "迟到次数" in payroll.columns:
            late_outlier = detect_outliers_iqr(payroll, "迟到次数")
            analyses.append(late_outlier)
        if "缺勤天数" in payroll.columns:
            absent_outlier = detect_outliers_iqr(payroll, "缺勤天数")
            analyses.append(absent_outlier)

    elif active_tab == "部门对比":
        if "应出勤天数" in payroll.columns and "部门" in payroll.columns:
            payroll_copy = payroll.copy()
            payroll_copy["_出勤率"] = payroll_copy["实际出勤天数"] / payroll_copy["应出勤天数"].replace(0, 1)
            ar_dept = compare_departments(payroll_copy, "_出勤率")
            analyses.append(ar_dept)

        if "迟到次数" in payroll.columns and "绩效工资" in payroll.columns:
            corr = analyze_correlation(payroll, [("迟到次数", "绩效工资")])
            analyses.append(corr)

    if not analyses:
        return f"📊 当前'{active_tab}'标签暂无深度分析数据"

    return generate_narrative(analyses, style='executive')


def analyze_module_8_report(
    payroll: Optional[pd.DataFrame],
    cost: Optional[pd.DataFrame],
    talent: Optional[pd.DataFrame],
    months: List[str],
    department: str = '全部'
) -> str:
    """模块8-周报: 完整报告生成"""
    return generate_full_report(payroll, cost, talent, months, department)
