"""电池分析服务 - 内阻估算、自检提醒、续航预测"""
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class BatteryAnalytics:
    """电池分析结果"""
    # 内阻估算
    estimated_resistance_mohm: Optional[float] = None  # 估算内阻 (mΩ)
    resistance_trend: Optional[str] = None  # stable/increasing/decreasing
    
    # 自检提醒
    needs_self_test: bool = False
    days_since_last_test: Optional[int] = None
    recommended_test: Optional[str] = None  # quick/deep/none
    
    # 续航预测
    predicted_runtime_minutes: Optional[int] = None
    prediction_confidence: Optional[str] = None  # high/medium/low
    prediction_factors: Optional[list] = None


def analyze_battery(
    battery_voltage: Optional[float],
    battery_charge: Optional[float],
    battery_runtime: Optional[int],
    load_percent: Optional[float],
    input_voltage: Optional[float],
    input_voltage_nominal: Optional[float],
    ups_test_result: Optional[str],
    ups_mfr_date: Optional[str],
    battery_mfr_date: Optional[str],
    status_flags: list,
    history_voltages: Optional[List[float]] = None,
) -> BatteryAnalytics:
    """
    综合电池分析
    """
    result = BatteryAnalytics()
    
    # 1. 内阻估算（基于电压-负载关系）
    result = _estimate_resistance(result, battery_voltage, input_voltage, 
                                   input_voltage_nominal, load_percent, status_flags)
    
    # 2. 自检提醒
    result = _check_self_test(result, ups_test_result, ups_mfr_date)
    
    # 3. 续航预测
    result = _predict_runtime(result, battery_voltage, battery_charge, 
                              battery_runtime, load_percent)
    
    return result


def _estimate_resistance(
    result: BatteryAnalytics,
    battery_voltage: Optional[float],
    input_voltage: Optional[float],
    input_voltage_nominal: Optional[float],
    load_percent: Optional[float],
    status_flags: list,
) -> BatteryAnalytics:
    """
    估算电池内阻
    
    原理：电池内阻↑ = 电池老化↑
    铅酸电池新电池内阻约 5-15 mΩ/Ah，老化后可达 30-50 mΩ/Ah
    
    估算方法：基于浮充电压与额定值的偏差
    - 浮充电压正常（2.25-2.30V/Cell）→ 内阻正常
    - 浮充电压偏高（需要更高电压维持满充）→ 内阻增大
    """
    if battery_voltage is None or input_voltage_nominal is None:
        return result
    
    # APC Back-UPS RS 1000G: 24V 系统 (12V × 2)
    # 正常浮充电压：27.0-27.6V
    # 计算偏差
    nominal_float_voltage = input_voltage_nominal * 1.17  # 约 26.9V for 230V system
    deviation = battery_voltage - nominal_float_voltage
    
    # 粗略估算内阻（仅供趋势参考，不作为精确值）
    if deviation < -0.5:
        # 浮充电压偏低，可能内阻增大或充电不足
        result.estimated_resistance_mohm = 25.0
        result.resistance_trend = "increasing"
    elif deviation > 0.5:
        # 浮充电压偏高，电池可能需要更高电压维持
        result.estimated_resistance_mohm = 20.0
        result.resistance_trend = "stable"
    else:
        result.estimated_resistance_mohm = 15.0
        result.resistance_trend = "stable"
    
    return result


def _check_self_test(
    result: BatteryAnalytics,
    ups_test_result: Optional[str],
    ups_mfr_date: Optional[str],
) -> BatteryAnalytics:
    """
    检查是否需要自检
    
    APC 建议：
    - 每 2 周进行一次快速自检
    - 每 3-6 个月进行一次深度自检
    """
    # 解析上次自检结果
    test_completed = False
    if ups_test_result:
        result_lower = ups_test_result.lower()
        if "pass" in result_lower or "ok" in result_lower:
            test_completed = True
        elif "no test" in result_lower or "none" in result_lower:
            test_completed = False
    
    # 检查生产日期（如果电池超过 2 年，建议深度自检）
    battery_age_months = None
    if ups_mfr_date:
        try:
            # 解析日期格式：2024/12/06
            mfr_date = datetime.strptime(ups_mfr_date, "%Y/%m/%d")
            battery_age_months = (datetime.now() - mfr_date).days // 30
        except ValueError:
            pass
    
    # 判断是否需要自检
    if not test_completed:
        result.needs_self_test = True
        if battery_age_months and battery_age_months > 24:
            result.recommended_test = "deep"
        else:
            result.recommended_test = "quick"
    elif battery_age_months and battery_age_months > 24:
        result.needs_self_test = True
        result.recommended_test = "deep"
    
    return result


def _predict_runtime(
    result: BatteryAnalytics,
    battery_voltage: Optional[float],
    battery_charge: Optional[float],
    battery_runtime: Optional[int],
    load_percent: Optional[float],
) -> BatteryAnalytics:
    """
    预测断电续航时间
    
    结合 UPS 报告的 runtime 和当前负载进行修正
    """
    if battery_runtime is None:
        return result
    
    # 基础续航（UPS 报告）
    base_runtime_minutes = battery_runtime / 60
    
    # 负载修正系数
    if load_percent is not None:
        # UPS runtime 通常基于满载计算
        # 负载越低，实际续航越长（非线性关系）
        if load_percent < 10:
            correction_factor = 1.2  # 极低负载，续航更长
            result.prediction_confidence = "medium"
        elif load_percent < 30:
            correction_factor = 1.0
            result.prediction_confidence = "high"
        elif load_percent < 60:
            correction_factor = 0.95
            result.prediction_confidence = "high"
        else:
            correction_factor = 0.85  # 高负载，续航缩短
            result.prediction_confidence = "medium"
    else:
        correction_factor = 1.0
        result.prediction_confidence = "low"
    
    # 电池健康修正（如果有电压信息）
    if battery_voltage and battery_voltage < 25.0:
        correction_factor *= 0.9  # 电压偏低，健康度可能下降
    
    result.predicted_runtime_minutes = int(base_runtime_minutes * correction_factor)
    
    # 影响因素
    factors = []
    if load_percent:
        factors.append(f"当前负载 {load_percent}%")
    if battery_voltage:
        factors.append(f"电池电压 {battery_voltage}V")
    result.prediction_factors = factors
    
    return result
