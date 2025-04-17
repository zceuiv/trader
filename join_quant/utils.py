from decimal import Decimal
import numpy as np
import pandas as pd
# 自定义ATR实现
def calculate_tr(high, low, close):
    """
    计算真实波幅(True Range)
    
    参数:
    high: 高价数组
    low: 低价数组
    close: 收盘价数组
    
    返回:
    tr: 真实波幅数组
    """
    # 确保输入是numpy数组
    high = np.array(high)
    low = np.array(low)
    close = np.array(close)
    
    # 创建tr数组
    tr = np.zeros(len(high))
    
    # 第一个TR值只能用high-low (如果数据有效)
    if not (np.isnan(high[0]) or np.isnan(low[0])):
        tr[0] = high[0] - low[0]
    else:
        tr[0] = np.nan
    
    # 计算剩余的TR值
    for i in range(1, len(high)):
        # 如果当前价格数据有效
        if not (np.isnan(high[i]) or np.isnan(low[i]) or np.isnan(close[i-1])):
            # 计算三种差值
            high_low = high[i] - low[i]
            high_close_prev = abs(high[i] - close[i-1])
            low_close_prev = abs(low[i] - close[i-1])
            tr[i] = max(high_low, high_close_prev, low_close_prev)
        elif not (np.isnan(high[i]) or np.isnan(low[i])):
            # 如果只有前一天收盘价缺失，但今天的高低价有效
            tr[i] = high[i] - low[i]
        else:
            # 如果数据无效，设为nan
            tr[i] = np.nan
    
    return tr

def calculate_atr(high, low, close, period=14):
    """
    计算平均真实波幅(Average True Range)，使用Wilder的原始平滑方法
    
    参数:
    high: 高价数组
    low: 低价数组
    close: 收盘价数组
    period: 计算周期，默认14
    
    返回:
    atr: 平均真实波幅数组
    """
    tr = calculate_tr(high, low, close)
    
    # 初始化ATR数组
    atr = np.zeros(len(tr))
    
    # 前period-1个值设为NaN
    atr[:period-1] = np.nan
    
    # 找到第一个有效的位置来初始化ATR
    valid_tr = tr[~np.isnan(tr)][:period]
    if len(valid_tr) > 0:
        first_valid_tr_sum = np.sum(valid_tr)
        first_valid_tr_count = len(valid_tr)
        
        # 如果收集到足够的有效TR值，计算第一个ATR
        if first_valid_tr_count >= period:
            atr[period-1] = first_valid_tr_sum / period
        elif first_valid_tr_count > 0:
            # 如果TR值不足但有一些有效值，使用可用的计算初始ATR
            atr[period-1] = first_valid_tr_sum / first_valid_tr_count
    
    # 使用Wilder的原始平滑方法计算剩余的ATR值
    for i in range(period, len(tr)):
        # 如果当前TR值和前一个ATR值都有效
        if not np.isnan(tr[i]) and not np.isnan(atr[i-1]):
            atr[i] = ((period-1) * atr[i-1] + tr[i]) / period
        # 如果当前TR值无效但前一个ATR值有效，保持前一个ATR值
        elif not np.isnan(atr[i-1]):
            atr[i] = atr[i-1]
        # 如果前一个ATR值无效，尝试重新计算
        else:
            valid_tr = tr[max(0, i-period+1):i+1]
            valid_tr = valid_tr[~np.isnan(valid_tr)]
            if len(valid_tr) > 0:
                atr[i] = np.mean(valid_tr)
            else:
                atr[i] = np.nan
    
    return atr


def price_round(x: Decimal, base: Decimal):
    """
    根据最小精度取整，例如对于IF最小精度是0.2，那么 1.3 -> 1.2, 1.5 -> 1.4
    :param x: Decimal 待取整的数
    :param base: Decimal 最小精度
    :return: float 取整结果
    """
    if not type(x) is Decimal:
        x = Decimal(x)
    if not type(base) is Decimal:
        base = Decimal(base)
    precision = 0
    s = str(round(base, 3) % 1)
    s = s.rstrip('0').rstrip('.') if '.' in s else s
    p1, *p2 = s.split('.')
    if p2:
        precision = len(p2[0])
    return round(base * round(x / base), precision)


def contract_to_future(contract):
    product = contract.split('.')[0]
    product = ''.join([i for i in product if not i.isdigit()])
    return product

# 根据结算价、停板幅和最小价格精度计算涨停价格
def calc_up_limit(main_contract, settlement: Decimal):
    limit_ratio = Decimal(0.05) # TODO 没有api获取
    price_tick = Decimal(10) # TODO 没有api获取
    price = price_round(settlement * (Decimal(1) + Decimal(limit_ratio)), price_tick)
    return price - price_tick


# 根据结算价、停板幅和最小价格精度计算止损价格
def calc_down_limit(main_contract, settlement: Decimal):
    limit_ratio = Decimal(0.05) # TODO 没有api获取
    price_tick = Decimal(10) # TODO 没有api获取
    price = price_round(settlement * (Decimal(1) - Decimal(limit_ratio)), price_tick)
    return price + price_tick