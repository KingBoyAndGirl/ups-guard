"""机器学习预测服务 - 使用轻量级统计分析方法"""
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from models import Event, Metric, EventType

logger = logging.getLogger(__name__)


class MLPredictor:
    """轻量级机器学习预测器，基于统计分析"""
    
    def __init__(self):
        self.min_samples_for_prediction = 5  # 最少需要的样本数
    
    async def predict_outage_duration(
        self, 
        events: List[Event]
    ) -> Optional[Dict[str, Any]]:
        """
        预测停电时长
        基于历史停电事件（POWER_LOST → POWER_RESTORED 的时间差）
        使用加权移动平均（最近的事件权重更大）
        """
        # 提取停电恢复事件对
        outage_durations = []
        
        power_lost_time = None
        for event in sorted(events, key=lambda e: e.timestamp):
            if event.event_type == EventType.POWER_LOST:
                power_lost_time = event.timestamp
            elif event.event_type == EventType.POWER_RESTORED and power_lost_time:
                duration_seconds = (event.timestamp - power_lost_time).total_seconds()
                outage_durations.append({
                    'duration': duration_seconds,
                    'timestamp': event.timestamp
                })
                power_lost_time = None
        
        if len(outage_durations) < self.min_samples_for_prediction:
            return {
                'available': False,
                'message': f'数据不足，需要至少 {self.min_samples_for_prediction} 次停电恢复记录',
                'current_samples': len(outage_durations)
            }
        
        # 加权移动平均（最近的事件权重更大）
        total_weight = 0
        weighted_sum = 0
        
        for i, outage in enumerate(reversed(outage_durations)):
            # 指数权重：最近的权重更大
            weight = 2 ** i
            weighted_sum += outage['duration'] * weight
            total_weight += weight
        
        avg_duration = weighted_sum / total_weight
        
        # 计算标准差（用于置信度）
        variance = sum(
            ((outage['duration'] - avg_duration) ** 2) 
            for outage in outage_durations
        ) / len(outage_durations)
        std_dev = variance ** 0.5
        
        # 置信度：标准差越小，置信度越高
        confidence = max(0, min(100, 100 - (std_dev / avg_duration * 100)))
        
        return {
            'available': True,
            'predicted_duration_seconds': int(avg_duration),
            'predicted_duration_minutes': round(avg_duration / 60, 1),
            'confidence_percent': round(confidence, 1),
            'sample_count': len(outage_durations),
            'min_duration_seconds': int(min(o['duration'] for o in outage_durations)),
            'max_duration_seconds': int(max(o['duration'] for o in outage_durations))
        }
    
    async def assess_battery_health(
        self, 
        metrics: List[Metric],
        events: List[Event]
    ) -> Optional[Dict[str, Any]]:
        """
        评估电池健康度
        基于断电后的电池放电速率
        对比不同时期的放电速率变化趋势
        """
        if not metrics or not events:
            return {
                'available': False,
                'message': '数据不足，需要更多历史数据'
            }
        
        # 找到断电事件期间的指标数据
        discharge_periods = []
        
        power_lost_time = None
        for event in sorted(events, key=lambda e: e.timestamp):
            if event.event_type == EventType.POWER_LOST:
                power_lost_time = event.timestamp
            elif event.event_type == EventType.POWER_RESTORED and power_lost_time:
                # 提取这段时间的指标
                period_metrics = [
                    m for m in metrics 
                    if power_lost_time <= m.timestamp <= event.timestamp
                    and m.battery_charge is not None
                ]
                
                if len(period_metrics) >= 2:
                    # 计算放电速率（%/小时）
                    duration_hours = (event.timestamp - power_lost_time).total_seconds() / 3600
                    if duration_hours > 0:
                        charge_drop = period_metrics[0].battery_charge - period_metrics[-1].battery_charge
                        discharge_rate = charge_drop / duration_hours
                        
                        discharge_periods.append({
                            'timestamp': event.timestamp,
                            'discharge_rate': discharge_rate,
                            'duration_hours': duration_hours
                        })
                
                power_lost_time = None
        
        if len(discharge_periods) < 2:
            return {
                'available': False,
                'message': '需要至少2次完整的断电记录来评估电池健康度',
                'current_samples': len(discharge_periods)
            }
        
        # 计算平均放电速率
        avg_discharge_rate = sum(p['discharge_rate'] for p in discharge_periods) / len(discharge_periods)
        
        # 计算趋势（最近的放电速率是否增加）
        recent_rate = sum(p['discharge_rate'] for p in discharge_periods[-3:]) / min(3, len(discharge_periods))
        older_rate = sum(p['discharge_rate'] for p in discharge_periods[:3]) / min(3, len(discharge_periods))
        
        # 健康度评分：基于放电速率稳定性
        # 放电速率越稳定，健康度越高
        rate_variance = sum((p['discharge_rate'] - avg_discharge_rate) ** 2 for p in discharge_periods) / len(discharge_periods)
        rate_std = rate_variance ** 0.5
        
        # 健康度百分比（放电速率变化小 = 健康）
        health_percent = max(0, min(100, 100 - (rate_std / avg_discharge_rate * 50)))
        
        # 如果最近放电速率显著增加，降低健康度
        if recent_rate > older_rate * 1.3:
            health_percent *= 0.8
        
        # 预估剩余寿命（基于健康度）
        if health_percent > 80:
            recommendation = "电池状态良好"
            months_remaining = "> 12"
        elif health_percent > 60:
            recommendation = "电池状态正常，建议6个月后检查"
            months_remaining = "6-12"
        elif health_percent > 40:
            recommendation = "电池性能下降，建议3个月内更换"
            months_remaining = "3-6"
        else:
            recommendation = "电池性能严重下降，建议尽快更换"
            months_remaining = "< 3"
        
        return {
            'available': True,
            'health_percent': round(health_percent, 1),
            'avg_discharge_rate_per_hour': round(avg_discharge_rate, 2),
            'discharge_trend': 'increasing' if recent_rate > older_rate * 1.1 else 'stable',
            'recommendation': recommendation,
            'estimated_months_remaining': months_remaining,
            'sample_count': len(discharge_periods)
        }
    
    async def predict_runtime(
        self,
        current_battery_charge: Optional[float],
        current_load: Optional[float],
        metrics: List[Metric],
        events: List[Event]
    ) -> Optional[Dict[str, Any]]:
        """
        预测电池剩余运行时间
        基于当前负载和电量，结合历史放电数据
        线性回归拟合放电曲线
        """
        if current_battery_charge is None or current_load is None:
            return {
                'available': False,
                'message': '缺少当前电池电量或负载数据'
            }
        
        if current_battery_charge <= 0:
            return {
                'available': True,
                'predicted_runtime_minutes': 0,
                'message': '电池电量已耗尽'
            }
        
        # 找到最近的断电期间的放电数据
        power_lost_time = None
        recent_discharge_metrics = []
        
        for event in sorted(events, key=lambda e: e.timestamp, reverse=True):
            if event.event_type == EventType.POWER_RESTORED:
                power_lost_time = None
            elif event.event_type == EventType.POWER_LOST:
                power_lost_time = event.timestamp
                
                # 获取这次断电期间的指标
                discharge_metrics = [
                    m for m in metrics 
                    if m.timestamp >= power_lost_time
                    and m.battery_charge is not None
                    and m.load_percent is not None
                ]
                
                if len(discharge_metrics) >= 3:
                    recent_discharge_metrics = discharge_metrics
                    break
        
        if len(recent_discharge_metrics) < 3:
            # 使用简单估算：假设线性放电
            # 典型 UPS 在 100% 负载下约 10-30 分钟
            estimated_full_runtime = 20  # 默认估算值（分钟）
            
            # 根据当前负载调整
            if current_load > 0:
                adjusted_runtime = estimated_full_runtime * (100 / current_load)
                # 根据当前电量调整
                predicted_minutes = adjusted_runtime * (current_battery_charge / 100)
            else:
                predicted_minutes = estimated_full_runtime * (current_battery_charge / 100)
            
            return {
                'available': True,
                'predicted_runtime_minutes': int(predicted_minutes),
                'confidence': 'low',
                'message': '基于默认估算，数据不足以精确预测',
                'method': 'default_estimate'
            }
        
        # 使用历史数据进行预测
        # 计算平均放电速率（考虑负载）
        total_rate = 0
        count = 0
        
        for i in range(len(recent_discharge_metrics) - 1):
            current_m = recent_discharge_metrics[i]
            next_m = recent_discharge_metrics[i + 1]
            
            time_diff = (next_m.timestamp - current_m.timestamp).total_seconds() / 3600  # 小时
            if time_diff > 0:
                charge_diff = current_m.battery_charge - next_m.battery_charge
                avg_load = (current_m.load_percent + next_m.load_percent) / 2
                
                if avg_load > 0:
                    # 放电速率（%/小时），归一化到100%负载
                    normalized_rate = (charge_diff / time_diff) * (100 / avg_load)
                    total_rate += normalized_rate
                    count += 1
        
        if count == 0:
            return {
                'available': False,
                'message': '无法计算放电速率'
            }
        
        avg_normalized_rate = total_rate / count
        
        # 根据当前负载调整放电速率
        if current_load > 0:
            actual_rate = avg_normalized_rate * (current_load / 100)
        else:
            actual_rate = avg_normalized_rate * 0.1  # 空载假设为10%负载
        
        # 预测运行时间
        if actual_rate > 0:
            predicted_hours = current_battery_charge / actual_rate
            predicted_minutes = predicted_hours * 60
        else:
            predicted_minutes = 999  # 很长时间
        
        return {
            'available': True,
            'predicted_runtime_minutes': int(min(predicted_minutes, 999)),
            'confidence': 'high',
            'discharge_rate_per_hour': round(actual_rate, 2),
            'sample_count': len(recent_discharge_metrics),
            'method': 'historical_data'
        }
    
    async def detect_anomalies(
        self,
        metrics: List[Metric]
    ) -> Dict[str, Any]:
        """
        异常检测
        基于历史数据的统计分布（均值 ± 3σ）
        检测电压异常、负载突变等
        """
        if len(metrics) < 10:
            return {
                'available': False,
                'message': '数据不足，需要至少10个指标样本',
                'current_samples': len(metrics)
            }
        
        anomalies = []
        
        # 计算各指标的统计特征
        def calc_stats(values: List[float]) -> Tuple[float, float]:
            """计算均值和标准差"""
            if not values:
                return 0, 0
            mean = sum(values) / len(values)
            variance = sum((x - mean) ** 2 for x in values) / len(values)
            std = variance ** 0.5
            return mean, std
        
        # 输入电压异常检测
        input_voltages = [m.input_voltage for m in metrics if m.input_voltage is not None]
        if len(input_voltages) >= 10:
            mean, std = calc_stats(input_voltages)
            recent_voltage = input_voltages[-1]
            
            if abs(recent_voltage - mean) > 3 * std:
                severity = 'high' if abs(recent_voltage - mean) > 4 * std else 'medium'
                anomalies.append({
                    'type': 'input_voltage',
                    'severity': severity,
                    'message': f'输入电压异常: {recent_voltage:.1f}V (正常范围: {mean-3*std:.1f}-{mean+3*std:.1f}V)',
                    'current_value': recent_voltage,
                    'expected_range': [mean - 3 * std, mean + 3 * std]
                })
        
        # 输出电压异常检测
        output_voltages = [m.output_voltage for m in metrics if m.output_voltage is not None]
        if len(output_voltages) >= 10:
            mean, std = calc_stats(output_voltages)
            recent_voltage = output_voltages[-1]
            
            if abs(recent_voltage - mean) > 3 * std:
                severity = 'high' if abs(recent_voltage - mean) > 4 * std else 'medium'
                anomalies.append({
                    'type': 'output_voltage',
                    'severity': severity,
                    'message': f'输出电压异常: {recent_voltage:.1f}V (正常范围: {mean-3*std:.1f}-{mean+3*std:.1f}V)',
                    'current_value': recent_voltage,
                    'expected_range': [mean - 3 * std, mean + 3 * std]
                })
        
        # 负载突变检测
        loads = [m.load_percent for m in metrics if m.load_percent is not None]
        if len(loads) >= 10:
            mean, std = calc_stats(loads)
            recent_load = loads[-1]
            
            # 检测负载突变（与前一个值相比）
            if len(loads) >= 2:
                load_change = abs(recent_load - loads[-2])
                if load_change > 20:  # 负载变化超过20%
                    anomalies.append({
                        'type': 'load_change',
                        'severity': 'medium',
                        'message': f'负载突变: {load_change:.1f}% (从 {loads[-2]:.1f}% 到 {recent_load:.1f}%)',
                        'current_value': recent_load,
                        'change': load_change
                    })
        
        # 温度异常检测
        temperatures = [m.temperature for m in metrics if m.temperature is not None]
        if len(temperatures) >= 10:
            mean, std = calc_stats(temperatures)
            recent_temp = temperatures[-1]
            
            # 温度过高警告
            if recent_temp > 45:  # 超过45°C
                anomalies.append({
                    'type': 'temperature',
                    'severity': 'high' if recent_temp > 50 else 'medium',
                    'message': f'温度过高: {recent_temp:.1f}°C',
                    'current_value': recent_temp,
                    'threshold': 45
                })
            elif abs(recent_temp - mean) > 3 * std:
                anomalies.append({
                    'type': 'temperature',
                    'severity': 'low',
                    'message': f'温度异常: {recent_temp:.1f}°C (正常范围: {mean-3*std:.1f}-{mean+3*std:.1f}°C)',
                    'current_value': recent_temp,
                    'expected_range': [mean - 3 * std, mean + 3 * std]
                })
        
        return {
            'available': True,
            'anomaly_count': len(anomalies),
            'anomalies': anomalies,
            'sample_count': len(metrics),
            'has_critical': any(a['severity'] == 'high' for a in anomalies)
        }


# 全局实例
_ml_predictor: Optional[MLPredictor] = None


def get_ml_predictor() -> MLPredictor:
    """获取 ML 预测器实例"""
    global _ml_predictor
    if _ml_predictor is None:
        _ml_predictor = MLPredictor()
    return _ml_predictor
