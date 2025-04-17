# coding=utf-8
#
# 大哥2.0策略 - 聚宽平台实现版本
# 基于《趋势交易》一书中的策略
#

import pandas as pd
import numpy as np
from typing import List
# import talib
from jqdata import *
from utils import *
from const import *

# 策略参数
class Parameter():
    break_n = 50    # 突破周期
    atr_n = 20      # ATR计算周期
    long_n = 100    # 长期均线周期
    short_n = 50    # 短期均线周期
    stop_n = 3      # 止损ATR倍数
    risk = 0.002    # 风险因子(0.2%)

class TradeSignal():
    def __init__(self, signal, contract, future, volume, side, price, priority, day=None):
        self.signal = signal
        self.contract = contract
        self.future = future
        self.volume = volume
        self.side = side
        self.price = price
        self.priority = priority
        self.day = day

# 初始化函数，设定基准等等
def initialize(context):


    ## 设置单个账户
    # 获取初始资金
    init_cash = context.portfolio.starting_cash 
    # 设定账户为金融账户，初始资金为 init_cash 变量代表的数值（如不使用设置多账户，默认只有subportfolios[0]一个账户，Portfolio 指向该账户。）
    set_subportfolios([SubPortfolioConfig(cash=init_cash, type='futures')])

    log.info("可用资金:{0} {1}".format(context.subportfolios[0].available_cash, init_cash))
    # 设置参数
    g.params = Parameter()
    
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
    g.future_list = [
        'AG', 'AL', 'AU', 'BU', 'C', 'CF', 'CS', 'CU', 
        'FG', 'HC', 'I', 'J', 'JM', 'L', 'M', 'MA', 
        'NI', 'OI', 'P', 'PB', 'PP', 'RB', 'RM', 'RU', 
        'SC', 'SN', 'SR', 'T', 'TA', 'TF', 'V', 'Y', 'ZC', 'ZN'
    ]

    g.map_future_to_exchange = {
        # 上海期货交易所（SHFE）
        'AG': 'SHFE',
        'AL': 'SHFE',
        'AU': 'SHFE',
        'BU': 'SHFE',
        'CU': 'SHFE',
        'HC': 'SHFE',
        'NI': 'SHFE',
        'PB': 'SHFE',
        'RB': 'SHFE',
        'RU': 'SHFE',
        'SN': 'SHFE',
        'ZN': 'SHFE',
        
        # 大连商品交易所（DCE）
        'C': 'DCE',
        'CS': 'DCE',
        'I': 'DCE',
        'J': 'DCE',
        'JM': 'DCE',
        'L': 'DCE',
        'M': 'DCE',
        'P': 'DCE',
        'PP': 'DCE',
        'V': 'DCE',
        'Y': 'DCE',
        
        # 郑州商品交易所（CZCE）
        'CF': 'CZCE',
        'FG': 'CZCE',
        'MA': 'CZCE',
        'OI': 'CZCE',
        'RM': 'CZCE',
        'SR': 'CZCE',
        'TA': 'CZCE',
        'ZC': 'CZCE',
        
        # 中国金融期货交易所（CFFEX）
        'T': 'CFFEX',
        'TF': 'CFFEX',

        # 上期能源（INE）
        'SC': 'INE'
    }
    
    # 持仓信息字典
    g.signal1_list = [] # 日盘信号列表
    g.signal2_list = [] # 股指信号列表
    g.signal3_list = [] # 夜盘信号列表

    g.map_future_to_main_contract = {} # 期货品种与主力合约的映射
    g.map_future_to_long_position = {} # 期货品种与多头持仓的映射
    g.map_future_to_short_position = {} # 期货品种与空头持仓的映射

    g.persist = {} # 持久化数据
    g.persist['roll_over_first_position'] = {} # 换月追溯首次持仓

    # 每日开盘前运行
    # run_daily(processing_signal1, time='08:55')

    # 开盘处理遗漏信号
    run_daily(check_signal1_processed, time='09:01')
    
    # 处理股指和国债信号
    # run_daily(processing_signal2, time='09:25')
    
    # 处理遗漏信号
    run_daily(check_signal2_processed, time='09:31')

    # 处理夜盘信号
    # run_daily(processing_signal3, time='20:55')
    
    # 处理遗漏信号
    # run_daily(check_signal3_processed, time='21:01')

    # 更新数据
    # run_daily(refresh_all, time='15:20')

    # 更新净值
    # run_daily(update_equity, time='15:30')

    # 计算交易信号
    run_daily(collect_quote, time='17:00')
    
    
    # 打印策略参数
    log.info("大哥2.0策略初始化完成")
    log.info("策略参数：突破周期=%d, ATR周期=%d, 长期均线=%d, 短期均线=%d, 止损倍数=%d, 风险系数=%.4f" % 
             (g.params.break_n, g.params.atr_n, g.params.long_n, 
              g.params.short_n, g.params.stop_n, g.params.risk))


# 8:55 处理信号1
def processing_signal1(context):
    # 查询今天是否为交易日

    '''
    如果是交易日，在DB中查询所有符合以下条件的日盘信号：
        不属于中金所(CFFEX)的品种(各类股指、国债期货期权)
        信号产生时间在上一交易日之后
        属于当前策略
        是日盘交易品种（非夜盘）
        尚未处理过的信号
    上述查询条件按优先级排序
    '''
    pass

    # 如果是假期后第一个交易日（距离上一交易日超过3天），还会处理节前未成交的夜盘信号

# 9:01 处理遗漏信号1
def check_signal1_processed(context):
    # 查询今天是否为交易日

    # 按8:55的查询条件处理遗漏日盘信号
    for sig in g.signal1_list:
        if sig.signal == SignalType.BUY: # 多头开仓
            order(sig.contract, sig.volume, side=SideType.LONG)
        elif sig.signal == SignalType.SELL: # 多头平仓
            order_target(sig.contract, 0, side=SideType.LONG)
        elif sig.signal == SignalType.SELL_SHORT: # 空头开仓
            order(sig.contract, sig.volume, side=SideType.SHORT)
        elif sig.signal == SignalType.BUY_COVER: # 空头平仓
            order_target(sig.contract, 0, side=SideType.SHORT)
        elif sig.signal == SignalType.ROLL_CLOSE: # 换月平旧仓
            order_target(sig.contract, 0, side=sig.side)
        elif sig.signal == SignalType.ROLL_OPEN: # 换月开新仓
            order(sig.contract, sig.volume, side=sig.side)
            
    g.signal1_list = []
    

# 9:25 处理信号2
def processing_signal2(context):
    # 查询今天是否为交易日
    
    '''
    如果是交易日，查询所有符合以下条件的信号：
        属于中金所(CFFEX)的品种（主要是股指期货如IF、IC、IH和国债期货如T、TF）
        信号产生时间在上一交易日之后
        属于当前策略
        是日盘交易品种
        尚未处理过的信号
        按优先级顺序处理这些信号
    '''
    pass

# 9:31 处理遗漏信号2
def check_signal2_processed(context):
    # 查询今天是否为交易日

    # 按9:25的查询条件处理遗漏股指和国债信号
    # 查询今天是否为交易日

    # 按8:55的查询条件处理遗漏日盘信号
    for sig in g.signal2_list:
        if sig.signal == SignalType.BUY: # 多头开仓
            order(sig.contract, sig.volume, side=SideType.LONG)
        elif sig.signal == SignalType.SELL: # 多头平仓
            order_target(sig.contract, 0, side=SideType.LONG)
        elif sig.signal == SignalType.SELL_SHORT: # 空头开仓
            order(sig.contract, sig.volume, side=SideType.SHORT)
        elif sig.signal == SignalType.BUY_COVER: # 空头平仓
            order_target(sig.contract, 0, side=SideType.SHORT)
        elif sig.signal == SignalType.ROLL_CLOSE: # 换月平旧仓
            order_target(sig.contract, 0, side=sig.side)
        elif sig.signal == SignalType.ROLL_OPEN: # 换月开新仓
            order(sig.contract, sig.volume, side=sig.side)
            
    g.signal1_list = []

# 20:55 处理信号3
def processing_signal3(context):
    # 查询今天是否为交易日

    '''
    如果是交易日，查询所有符合以下条件的信号：
        信号产生时间在上一交易日之后
        属于当前策略
        是夜盘交易品种（night_trade=True）
        尚未处理过的信号
        按优先级顺序处理这些信号
    '''
    pass
  
# 21:01 处理遗漏信号3  
def check_signal3_processed(context):
    # 查询今天是否为交易日

    # 按20:55的查询条件处理遗漏夜盘信号
    pass

# 15:20 更新数据
def refresh_all(context):
    # 查询今天是否为交易日，不是则return

    '''
    更新账户信息 (refresh_account)
        查询交易账户的最新数据，包括：
            可用资金
            当前动态权益
            静态权益
            占用保证金
            出入金情况
        将数据更新到数据库，以便后续统计和分析
    '''

    '''
    更新持仓信息 (refresh_position)
        获取所有当前持有的期货合约头寸
        计算持仓的盈亏情况
        更新或创建相应的交易记录
        删除不存在的头寸记录
    '''

    '''
    更新合约信息 (refresh_instrument)
    从交易所获取最新的合约信息
    更新合约的基本数据，如：
        合约代码
        交易所
        合约乘数
        价格波动最小单位（价格跳动）
        保证金率
        手续费率
    '''
    pass

# 15:30 更新净值
def update_equity(context):
    '''
    检查交易日
        首先检查今天是否为交易日
        如果不是交易日，则跳过所有操作
        计算分红和虚拟资金
        查询历史分红总和
    计算当日分红（入金-出金）
        更新虚拟资金：虚拟资金 = 原始虚拟资金 - 入金 + 出金
        如果虚拟资金小于1，则设为0
    计算净值指标
        计算单位数量：单位数量 = 历史分红 + 虚拟资金
        计算单位净值：单位净值 = (动态权益 + 虚拟资金) / 单位数量
        计算累计净值：累计净值 = 动态权益 / (单位数量 - 虚拟资金)
    更新绩效数据
        在数据库中创建或更新当日的绩效记录，包括：
        占用保证金
        当日分红（入金-出金）
        虚拟资金
        当前资金
        单位数量
        单位净值
        累计净值
    记录日志
        输出详细的账户状态信息，包括：
        动态权益（当前总资产）
        静态权益（上日结算权益）
        可用资金
        保证金占用
        虚拟资金
        当日入金和出金
        单位净值和累计净值
    '''
    pass

# 17:00 收集交易所数据
def collect_quote(context):
    '''
    检查交易日
        首先检查今天是否为交易日
        如果不是交易日，则跳过所有操作，记录日志后直接返回
    '''
    if False: # TODO 检查交易日
        return
    '''
    收集交易所数据
        从所有交易所获取最新的日线行情数据，包括：
            上海期货交易所 (SHFE)
            大连商品交易所 (DCE)
            郑州商品交易所 (CZCE)
            中国金融期货交易所 (CFFEX)
            广州期货交易所 (GFEX)
            另外还会获取合约参数信息
    '''

    '''
    计算交易信号
        遍历所有关注的期货品种，生成连续合约数据，计算技术指标
    '''
    g.map_future_to_main_contract = {}
    
    for future in g.future_list:
        try:
            # 获取主力合约
            dominant = get_dominant_future(future)
            if dominant:
                g.map_future_to_main_contract[future] = dominant
                log.info(f"{product}主力合约: {dominant}")
        except Exception as e:
            log.error(f"获取{product}主力合约失败: {str(e)}")


    g.map_future_to_long_position = {}
    long_positions_dict = context.portfolio.long_positions
    for position in list(long_positions_dict.values()):
        future = contract_to_future(position.security)
        g.map_future_to_long_position[future] = position
    
    g.map_future_to_short_position = {}
    short_positions_dict = context.portfolio.short_positions
    for position in list(short_positions_dict.values()): 
        future = contract_to_future(position.security)
        g.map_future_to_short_position[future] = position

    '''
        根据趋势跟踪策略生成多空交易信号
        计算合适的仓位大小和风险控制
    '''

    for future in g.future_list:
        day = context.current_dt.date()
        sigs = calc_signal(context, future, day)
        for sig in sigs:
            exchange = g.map_future_to_exchange[sig.future]
            if exchange == 'SHFE':
                g.signal1_list.append(sig)
            elif exchange == 'CFFEX':
                g.signal2_list.append(sig)
            elif exchange == 'DCE':
                g.signal1_list.append(sig)
            elif exchange == 'CZCE':
                g.signal1_list.append(sig)
            elif exchange == 'GFEX':
                g.signal1_list.append(sig)
            elif exchange == 'INE':
                g.signal1_list.append(sig)
    '''
    失败处理机制
        如果部分数据获取失败，系统会在10分钟后重试失败的任务
        确保即使有临时网络问题也能完成数据收集
    '''

def calc_signal(context, future, day) -> List[TradeSignal]:
    break_n = g.params.break_n
    atr_n = g.params.atr_n
    long_n = g.params.long_n
    short_n = g.params.short_n
    stop_n = g.params.stop_n
    risk = g.params.risk

    ret = []

    # 主力合约
    main_contract = g.map_future_to_main_contract[future]

    # 获取历史数据
    df = get_price(main_contract, count=400, end_date=day, 
            frequency='daily', fields=['open', 'high', 'low', 'close'])
    # df = df.iloc[::-1]  # 日期升序排列

    # 计算技术指标
    df["atr"] = calculate_atr(df.high, df.low, df.close, period=atr_n)  # 真实波动幅度
    df["short_trend"] = df.close  # 短期均线
    df["long_trend"] = df.close   # 长期均线
            
    # 手动计算移动平均线
    for idx in range(1, df.shape[0]): # 手动计算SMA
        df.short_trend[idx] = (df.short_trend[idx-1] * (short_n - 1) + df.close[idx]) / short_n
        df.long_trend[idx] = (df.long_trend[idx-1] * (long_n - 1) + df.close[idx]) / long_n
        
        if pd.isna(df.short_trend[idx-1]):
            df.short_trend[idx] = df.close[idx]
        if pd.isna(df.long_trend[idx-1]):
            df.long_trend[idx] = df.close[idx]


    # 计算突破指标
    df["high_line"] = df.close.rolling(window=break_n).max()  # N日最高收盘价
    df["low_line"] = df.close.rolling(window=break_n).min()   # N日最低收盘价
    
    idx = -1  # 使用最新数据
                
    # 生成交易信号
    # 多头信号：短期均线在长期均线上方且价格突破N日最高价
    buy_sig = df.short_trend[idx] > df.long_trend[idx] and df.close[idx] >= df.high_line[idx - 1]
    # 空头信号：短期均线在长期均线下方且价格跌破N日最低价
    sell_sig = df.short_trend[idx] < df.long_trend[idx] and df.close[idx] <= df.low_line[idx - 1]
                   

    # 检查当前持仓
    long_position = g.map_future_to_long_position.get(future)
    short_position = g.map_future_to_short_position.get(future)

    roll_over = False # 换月
    if long_position:
        roll_over = long_position.security != main_contract and long_position.security < main_contract
    elif short_position:
        roll_over = short_position.security != main_contract and short_position.security < main_contract
    
    # TODO 处理手动开仓

    # 后续代码处理持仓管理、止损、换月和开仓逻辑...
    signal = signal_code = price = volume = volume_ori = use_margin = side = None
    priority = PriorityType.LOW
    # 多头持仓
    if long_position:
        first_pos = long_position
        if g.persist['roll_over_first_position'].get(future):
            first_pos = g.persist['roll_over_first_position'][future]

        # 获取首次持仓开仓时间在价格数据中的位置索引
        pos_idx = df.index.get_loc(first_pos.init_time.astimezone().date().isoformat())   

        # 多头止损逻辑: 当前收盘价低于开仓以来最高价减去N倍ATR
        if df.close[idx] <= df.high[pos_idx:idx].max() - df.atr[pos_idx - 1] * stop_n:
            signal = SignalType.SELL                      # 生成卖出信号
            signal_contract = long_position.security      # 设置信号对应的合约代码
            volume = long_position.closeable_amount       # 设置卖出数量为持仓量
            side = SideType.LONG
            
            # 获取结算价
            pos_sett = Decimal(get_extras('futures_sett_price', [long_position.security],end_date=day,count=2)[long_position.security][0])
            # 计算卖出价格(向下接近跌停价以确保成交)
            price = calc_down_limit(future, pos_sett)
            priority = PriorityType.High                  # 止损信号设为高优先级
        
        # 多头换月逻辑: 当前持有的合约不再是主力合约且需要换月
        elif roll_over:
            signal = SignalType.ROLL_OPEN                 # 生成换月开新仓信号
            signal_contract = main_contract
            volume = long_position.closeable_amount       # 设置开仓数量为当前持仓量
            side = SideType.LONG
            # 获取结算价
            main_sett = Decimal(get_extras('futures_sett_price', [main_contract],end_date=day,count=2)[main_contract][0])
            # 计算开新仓价格(接近涨停价以确保成交)
            price = calc_up_limit(future, main_sett)
            priority = PriorityType.Normal                # 换月信号设为普通优先级

            # 同时创建平旧仓信号 - 换月需要同时平旧仓开新仓
            pos_sett = Decimal(get_extras('futures_sett_price', [long_position.security],end_date=day,count=2)[long_position.security][0])
            ret.append(TradeSignal(
                signal=SignalType.ROLL_CLOSE,
                contract=long_position.security,
                future=future,
                volume=volume,
                side=SideType.LONG,
                price=calc_down_limit(future, pos_sett),
                priority=priority,
            ))
    # 空头持仓
    elif short_position:
        first_pos = short_position
        if g.persist['roll_over_first_position'].get(future):
            first_pos = g.persist['roll_over_first_position'][future]

        # 获取首次持仓开仓时间在价格数据中的位置索引
        pos_idx = df.index.get_loc(first_pos.init_time.astimezone().date().isoformat())   

        # 空头止损逻辑: 当前收盘价高于开仓以来最高价加上N倍ATR
        if df.close[idx] >= df.low[pos_idx:idx].max() + df.atr[pos_idx - 1] * stop_n:
            signal = SignalType.BUY_COVER                      # 生成卖出信号
            signal_contract = short_position.security      # 设置信号对应的合约代码
            volume = short_position.closeable_amount       # 设置卖出数量为持仓量
            side = SideType.SHORT
            # 获取结算价
            pos_sett = Decimal(get_extras('futures_sett_price', [short_position.security],end_date=day,count=2)[short_position.security][0])
            # 计算卖出价格(向上接近涨停价以确保成交)
            price = calc_up_limit(future, pos_sett)
            priority = PriorityType.High                  # 止损信号设为高优先级
        
        # 空头换月逻辑: 当前持有的合约不再是主力合约且需要换月
        elif roll_over:
            signal = SignalType.ROLL_OPEN                 # 生成换月开新仓信号
            signal_contract = main_contract
            volume = short_position.closeable_amount      # 设置开仓数量为当前持仓量
            side = SideType.SHORT
            # 获取结算价
            main_sett = Decimal(get_extras('futures_sett_price', [main_contract],end_date=day,count=2)[main_contract][0])
            # 计算开新仓价格(向下接近跌停价以确保成交)
            price = calc_down_limit(future, main_sett)
            priority = PriorityType.Normal                # 换月信号设为普通优先级

            # 同时创建平旧仓信号 - 换月需要同时平旧仓开新仓
            pos_sett = Decimal(get_extras('futures_sett_price', [short_position.security],end_date=day,count=2)[short_position.security][0])
            ret.append(TradeSignal(
                signal=SignalType.ROLL_CLOSE,
                contract=short_position.security,
                future=future,
                volume=volume,
                side=SideType.SHORT,
                price=calc_up_limit(future, pos_sett),
                priority=priority,
            ))
    # 开新仓
    elif buy_sig or sell_sig:
        # 计算每点价值
        # contract_multiplier = get_extras('unit_net_value', [contract_id])[contract_id]
        point_value = df.atr.iloc[idx]
        total_value = Decimal(context.portfolio.total_value)
        
        # 计算仓位大小
        profit = Decimal(0) # TODO 获取持仓盈亏
        margin_rate = Decimal(0.1) # TODO 获取保证金率
        volume_multiple = Decimal(100) # TODO 获取合约乘数
        risk_each = Decimal(df.atr[idx]) * volume_multiple
        volume_ori = (total_value + profit) * Decimal(risk) / Decimal(risk_each)
        volume = round(volume_ori)
        if volume > 0:
            main_sett = Decimal(get_extras('futures_sett_price', [main_contract],end_date=day,count=2)[main_contract][0])
            use_margin = main_sett * volume_multiple * margin_rate * volume
            price = calc_up_limit(main_contract, main_sett) if buy_sig else calc_down_limit(main_contract, main_sett)
            signal = SignalType.BUY if buy_sig else SignalType.SELL_SHORT
            signal_contract = main_contract
            side = SideType.LONG if buy_sig else SideType.SHORT
        else:
            log.info(f"做{'多' if buy_sig else '空'}{main_contract},单手风险:{risk_each:.0f},超出风控额度，放弃。")
    # 生成信号
    if signal:
        ret.append(TradeSignal(
            signal=signal,
            contract=signal_contract,
            future=future,
            volume=volume,
            side=side,
            price=price,
            priority=priority,
        ))
    
    return ret


