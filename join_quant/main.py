# coding=utf-8
#
# 大哥2.0策略 - 聚宽平台实现版本
# 基于《趋势交易》一书中的策略
#

import pandas as pd
import numpy as np
# import talib
from jqdata import *

# 策略参数
class Parameter:
    break_n = 50    # 突破周期
    atr_n = 20      # ATR计算周期
    long_n = 100    # 长期均线周期
    short_n = 50    # 短期均线周期
    stop_n = 3      # 止损ATR倍数
    risk = 0.002    # 风险因子(0.2%)

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
    
    # 计算三种差值
    high_low = high - low
    high_close_prev = np.abs(high[1:] - close[:-1])
    low_close_prev = np.abs(low[1:] - close[:-1])
    
    # 第一个TR值只能用high-low
    tr = np.zeros(len(high))
    tr[0] = high_low[0]
    
    # 计算剩余的TR值
    for i in range(1, len(high)):
        tr[i] = max(high_low[i], high_close_prev[i-1], low_close_prev[i-1])
    
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
    
    # 第period个值是前period个TR的平均
    if len(tr) >= period:
        atr[period-1] = np.mean(tr[:period])
    
    # 使用Wilder的原始平滑方法计算剩余的ATR值
    for i in range(period, len(tr)):
        atr[i] = ((period-1) * atr[i-1] + tr[i]) / period
    
    return atr

# 初始化函数，设定基准等等
def initialize(context):
    # 设置参数
    context.params = Parameter()
    
    # 设置基准收益：沪深300指数
    set_benchmark('000300.XSHG')
    
    # 开启动态复权模式(真实价格)
    set_option('use_real_price', True)
    
    # 设置佣金和滑点
    set_order_cost(OrderCost(
        open_tax=0, 
        close_tax=0, 
        open_commission=0.0002, 
        close_commission=0.0002, 
        close_today_commission=0, 
        min_commission=5
    ), type='futures')
    set_slippage(PriceRelatedSlippage(0.0002))
    
    # 期货品种列表 - 可以根据需要调整
    context.future_list = [
        'AG', 'AL', 'AU', 'BU', 'C', 'CF', 'CS', 'CU', 
        'FG', 'HC', 'I', 'J', 'JM', 'L', 'M', 'MA', 
        'NI', 'OI', 'P', 'PB', 'PP', 'RB', 'RM', 'RU', 
        'SC', 'SN', 'SR', 'T', 'TA', 'TF', 'V', 'Y', 'ZC', 'ZN'
    ]
    
    # 持仓信息字典
    context.positions = {}
    
    # 设置交易日日终运行
    run_daily(market_close, time='14:55')
    
    # 每日开盘前运行
    run_daily(before_market_open, time='09:00')
    
    # 打印策略参数
    log.info("大哥2.0策略初始化完成")
    log.info("策略参数：突破周期=%d, ATR周期=%d, 长期均线=%d, 短期均线=%d, 止损倍数=%d, 风险系数=%.4f" % 
             (context.params.break_n, context.params.atr_n, context.params.long_n, 
              context.params.short_n, context.params.stop_n, context.params.risk))

# 在每天交易开始前，获取主力合约
def before_market_open(context):
    # 获取当前所有期货主力合约
    context.main_contracts = {}
    for product in context.future_list:
        try:
            # 获取主力合约
            dominant = get_dominant_future(product)
            if dominant:
                context.main_contracts[product] = dominant
                log.info(f"{product}主力合约: {dominant}")
        except Exception as e:
            log.error(f"获取{product}主力合约失败: {str(e)}")

# 在收盘前进行交易
def market_close(context):
    # 计算账户总资产
    total_value = context.portfolio.total_value
    
    # 遍历所有期货品种
    for product, contract_id in context.main_contracts.items():
        try:
            # 获取合约对象
            contract = get_security_info(contract_id)
            
            # 获取历史数据
            df = get_price(contract_id, count=400, end_date=context.current_dt, 
                          frequency='daily', fields=['open', 'high', 'low', 'close'])
            
            if len(df) < context.params.long_n + 10:
                continue
                
            # # 计算技术指标
            # df['atr'] = talib.ATR(df.high.values, df.low.values, df.close.values, 
            #                      timeperiod=context.params.atr_n)
            # 计算技术指标 - 使用自定义ATR实现
            df['atr'] = calculate_atr(df.high.values, df.low.values, df.close.values, 
                                     period=context.params.atr_n)
            
            # 计算移动平均线
            df['short_trend'] = df.close.copy()
            df['long_trend'] = df.close.copy()
            # log.info(f"cccccc {df.close}")
            # 手动计算SMA，处理NaN值
            # log.info(f"aaaaaa {df.shape[0]}")
            for idx in range(1, df.shape[0]):
                # 检查前一个值和当前收盘价是否为NaN
                prev_short = df.short_trend.iloc[idx-1]
                prev_long = df.long_trend.iloc[idx-1]
                curr_close = df.close.iloc[idx]
                # log.info(f"bbbbbb, {idx}, {prev_short}, {curr_close}, {context.params.short_n}")
                
                # 处理短期均线
                if pd.notna(prev_short) and pd.notna(curr_close):
                    # 正常计算
                    df.short_trend.iloc[idx] = (prev_short * (context.params.short_n - 1) + curr_close) / context.params.short_n
                elif pd.notna(curr_close):
                    # 如果前一个值为NaN但当前收盘价有效，直接使用当前收盘价
                    df.short_trend.iloc[idx] = curr_close
                else:
                    # 如果当前收盘价为NaN，保持NaN
                    df.short_trend.iloc[idx] = np.nan
                
                # 处理长期均线
                if pd.notna(prev_long) and pd.notna(curr_close):
                    # 正常计算
                    df.long_trend.iloc[idx] = (prev_long * (context.params.long_n - 1) + curr_close) / context.params.long_n
                elif pd.notna(curr_close):
                    # 如果前一个值为NaN但当前收盘价有效，直接使用当前收盘价
                    df.long_trend.iloc[idx] = curr_close
                else:
                    # 如果当前收盘价为NaN，保持NaN
                    df.long_trend.iloc[idx] = np.nan
            
            # 计算突破指标
            df['high_line'] = df.close.rolling(window=context.params.break_n).max()  # N日最高收盘价
            df['low_line'] = df.close.rolling(window=context.params.break_n).min()   # N日最低收盘价
            
            # 获取当前持仓
            # current_position = get_position(context, contract_id)
            current_position = get_position2(context, contract_id)
            
            # 获取最新行情数据
            idx = -1
            current_price = df.close.iloc[idx]
            current_atr = df.atr.iloc[idx]
            log.info(f"Close: {contract_id}, {df.short_trend.iloc[idx]}, {df.long_trend.iloc[idx]}, {current_price}, {df.high_line.iloc[idx-1]}, {df.low_line.iloc[idx-1]}")
            # 生成交易信号
            # 多头信号：短期均线在长期均线上方且价格突破N日最高价
            # buy_sig = df.short_trend.iloc[idx] > df.long_trend.iloc[idx] and \
            #           round_price(current_price, contract.price_tick) >= \
            #           round_price(df.high_line.iloc[idx-1], contract.price_tick)
            buy_sig = df.short_trend.iloc[idx] > df.long_trend.iloc[idx] and \
                      current_price >= df.high_line.iloc[idx-1] 
            
            # 空头信号：短期均线在长期均线下方且价格跌破N日最低价
            # sell_sig = df.short_trend.iloc[idx] < df.long_trend.iloc[idx] and \
            #            round_price(current_price, contract.price_tick) <= \
            #            round_price(df.low_line.iloc[idx-1], contract.price_tick)
            sell_sig = df.short_trend.iloc[idx] < df.long_trend.iloc[idx] and \
                       current_price <= df.low_line.iloc[idx-1]
            
            # 持仓管理
            if current_position > 0:  # 持有多头
                # 获取开仓时间和开仓价格
                entry_time = context.positions.get(contract_id, {}).get('entry_time')
                entry_price = context.positions.get(contract_id, {}).get('entry_price')
                
                if entry_time is not None:
                    # 计算开仓以来的最高价
                    entry_idx = df.index.get_loc(entry_time)
                    highest_since_entry = df.high.iloc[entry_idx:idx+1].max()
                    
                    # 多头止损：当价格跌破开仓以来最高价下方3个ATR时止损
                    if current_price <= highest_since_entry - current_atr * context.params.stop_n:
                        log.info(f"多头止损: {contract_id}, 开仓价: {entry_price}, 当前价: {current_price}, "
                                f"开仓以来最高: {highest_since_entry}, 止损线: {highest_since_entry - current_atr * context.params.stop_n}")
                        close_position(context, contract_id)
                
                # 检查是否需要换月
                if need_rollover(context, contract_id):
                    log.info(f"多头换月: {contract_id}")
                    rollover_position(context, contract_id)
                    
            elif current_position < 0:  # 持有空头
                # 获取开仓时间和开仓价格
                entry_time = context.positions.get(contract_id, {}).get('entry_time')
                entry_price = context.positions.get(contract_id, {}).get('entry_price')
                
                if entry_time is not None:
                    # 计算开仓以来的最低价
                    entry_idx = df.index.get_loc(entry_time)
                    lowest_since_entry = df.low.iloc[entry_idx:idx+1].min()
                    
                    # 空头止损：当价格突破开仓以来最低价上方3个ATR时止损
                    if current_price >= lowest_since_entry + current_atr * context.params.stop_n:
                        log.info(f"空头止损: {contract_id}, 开仓价: {entry_price}, 当前价: {current_price}, "
                                f"开仓以来最低: {lowest_since_entry}, 止损线: {lowest_since_entry + current_atr * context.params.stop_n}")
                        close_position(context, contract_id)
                
                # 检查是否需要换月
                if need_rollover(context, contract_id):
                    log.info(f"空头换月: {contract_id}")
                    rollover_position(context, contract_id)
                    
            else:  # 无持仓，考虑开仓
                if buy_sig or sell_sig:
                    # 计算每点价值
                    contract_multiplier = contract.contract_multiplier
                    point_value = contract_multiplier * current_atr
                    
                    # 计算仓位大小
                    risk_amount = total_value * context.params.risk
                    position_size = int(risk_amount / point_value)
                    
                    if position_size > 0:
                        if buy_sig:
                            log.info(f"多头开仓信号: {contract_id}, 价格: {current_price}, 数量: {position_size}")
                            open_position(context, contract_id, position_size, 'long')
                        elif sell_sig:
                            log.info(f"空头开仓信号: {contract_id}, 价格: {current_price}, 数量: {position_size}")
                            open_position(context, contract_id, position_size, 'short')
                    else:
                        log.info(f"做{'多' if buy_sig else '空'}{contract_id}, 单手风险:{point_value}, 超出风控额度，放弃。")
                        
        except Exception as e:
            log.error(f"处理{product}({contract_id})时出错: {str(e)}")

# 开仓函数
def open_position(context, contract_id, amount, direction):
    try:
        if direction == 'long':
            order = order_value(contract_id, amount * get_price(contract_id).close[0])
            if order and order.status == OrderStatus.held:
                context.positions[contract_id] = {
                    'direction': 'long',
                    'amount': amount,
                    'entry_price': order.price,
                    'entry_time': context.current_dt
                }
                log.info(f"多头开仓成功: {contract_id}, 价格: {order.price}, 数量: {amount}")
        else:
            order = order_value(contract_id, -amount * get_price(contract_id).close[0])
            if order and order.status == OrderStatus.held:
                context.positions[contract_id] = {
                    'direction': 'short',
                    'amount': amount,
                    'entry_price': order.price,
                    'entry_time': context.current_dt
                }
                log.info(f"空头开仓成功: {contract_id}, 价格: {order.price}, 数量: {amount}")
    except Exception as e:
        log.error(f"开仓{contract_id}失败: {str(e)}")

# 平仓函数
def close_position(context, contract_id):
    try:
        position = context.portfolio.positions[contract_id]
        if position.closeable_amount > 0:
            order = order_target(contract_id, 0)
            if order and order.status == OrderStatus.held:
                log.info(f"平仓成功: {contract_id}, 价格: {order.price}, 数量: {position.closeable_amount}")
                if contract_id in context.positions:
                    del context.positions[contract_id]
    except Exception as e:
        log.error(f"平仓{contract_id}失败: {str(e)}")

# 换月函数
def rollover_position(context, contract_id):
    try:
        # 获取当前持仓信息
        position = context.portfolio.positions[contract_id]
        old_amount = position.closeable_amount
        direction = context.positions[contract_id]['direction']
        
        # 获取产品代码
        product = contract_id.split('.')[0]
        product = ''.join([i for i in product if not i.isdigit()])
        
        # 获取新的主力合约
        new_contract = get_dominant_future(product)
        
        if new_contract and new_contract != contract_id:
            # 平旧仓
            close_position(context, contract_id)
            
            # 开新仓
            if direction == 'long':
                open_position(context, new_contract, old_amount, 'long')
            else:
                open_position(context, new_contract, old_amount, 'short')
                
            log.info(f"换月完成: {contract_id} -> {new_contract}, 方向: {direction}, 数量: {old_amount}")
    except Exception as e:
        log.error(f"换月{contract_id}失败: {str(e)}")

# 检查是否需要换月
def need_rollover(context, contract_id):
    try:
        product = contract_id.split('.')[0]
        product = ''.join([i for i in product if not i.isdigit()])
        
        new_dominant = get_dominant_future(product)
        return new_dominant != contract_id
    except:
        return False

# 获取持仓数量
def get_position(context, contract_id):
    position = context.portfolio.positions.get(contract_id)
    if position:
        return position.closeable_amount if position.side == SIDE.LONG else -position.closeable_amount
    return 0

def get_position2(context, contract_id):
    long_position = context.portfolio.long_positions.get(contract_id)
    if long_position:
        return long_position.closeable_amount
    short_position = context.portfolio.short_positions.get(contract_id)
    if short_position:
        return -short_position.closeable_amount
    return 0

# 价格取整函数
def round_price(price, tick_size):
    return round(price / tick_size) * tick_size 