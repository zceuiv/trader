import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from utils import calculate_tr, calculate_atr

def test_tr_with_nans():
    """测试TR函数处理含有NaN值的数据"""
    print("\n===== 测试TR函数处理NaN数据 =====")
    
    # 案例1: 第一天数据就有NaN
    high1 = np.array([np.nan, 102.0, 104.0, 103.0, 105.0])
    low1 = np.array([np.nan, 98.0, 99.0, 97.0, 101.0])
    close1 = np.array([np.nan, 100.0, 102.0, 101.0, 103.0])
    
    tr1 = calculate_tr(high1, low1, close1)
    print("案例1: 第一天数据有NaN")
    print("高价:", high1)
    print("低价:", low1)
    print("收盘价:", close1)
    print("TR值:", tr1)
    print("是否还有NaN:", np.isnan(tr1).any(), "NaN的位置:", np.where(np.isnan(tr1))[0])
    
    # 案例2: 中间有NaN值
    high2 = np.array([102.0, 104.0, np.nan, 105.0, 106.0])
    low2 = np.array([98.0, 99.0, np.nan, 101.0, 102.0])
    close2 = np.array([100.0, 102.0, np.nan, 103.0, 104.0])
    
    tr2 = calculate_tr(high2, low2, close2)
    print("\n案例2: 中间有NaN值")
    print("高价:", high2)
    print("低价:", low2)
    print("收盘价:", close2)
    print("TR值:", tr2)
    print("是否还有NaN:", np.isnan(tr2).any(), "NaN的位置:", np.where(np.isnan(tr2))[0])
    
    # 案例3: 只有收盘价有NaN值
    high3 = np.array([102.0, 104.0, 103.0, 105.0, 106.0])
    low3 = np.array([98.0, 99.0, 97.0, 101.0, 102.0])
    close3 = np.array([100.0, np.nan, 102.0, np.nan, 104.0])
    
    tr3 = calculate_tr(high3, low3, close3)
    print("\n案例3: 只有收盘价有NaN值")
    print("高价:", high3)
    print("低价:", low3)
    print("收盘价:", close3)
    print("TR值:", tr3)
    print("是否还有NaN:", np.isnan(tr3).any(), "NaN的位置:", np.where(np.isnan(tr3))[0])
    
    # 检查是否正确处理: 第二个TR值应该等于high_low（因为前一个收盘价是NaN）
    assert not np.isnan(tr3[1]), "第二个TR值不应该是NaN"
    assert tr3[1] == high3[1] - low3[1], "第二个TR值应该只用当天的high-low"
    
    # 断言NaN不会传导：如果当前位置的高低价有效，TR应该有值
    for i in range(len(high3)):
        if not (np.isnan(high3[i]) or np.isnan(low3[i])):
            if i == 0 or np.isnan(close3[i-1]):
                assert not np.isnan(tr3[i]), f"位置{i}应该用high-low计算，不应为NaN"
            else:
                assert not np.isnan(tr3[i]), f"位置{i}应该计算所有三种差值，不应为NaN"

def test_atr_with_nans():
    """测试ATR函数处理含有NaN值的数据"""
    print("\n===== 测试ATR函数处理NaN数据 =====")
    
    # 案例1: 前几天都有NaN
    high1 = np.array([np.nan, np.nan, np.nan, 103.0, 105.0, 104.0, 106.0, 107.0, 108.0, 106.0])
    low1 = np.array([np.nan, np.nan, np.nan, 97.0, 101.0, 100.0, 102.0, 103.0, 104.0, 102.0])
    close1 = np.array([np.nan, np.nan, np.nan, 101.0, 103.0, 102.0, 104.0, 105.0, 106.0, 104.0])
    
    period = 3  # 使用较小的周期使例子更清晰
    atr1 = calculate_atr(high1, low1, close1, period=period)
    print(f"案例1: 前{period}天有NaN，ATR周期={period}")
    print("ATR值:", atr1)
    print("是否还有NaN:", np.isnan(atr1).any(), "NaN的位置:", np.where(np.isnan(atr1))[0])
    
    # 案例2: 中间有NaN值
    high2 = np.array([102.0, 104.0, 103.0, np.nan, 105.0, 104.0, np.nan, 107.0, 108.0, 106.0])
    low2 = np.array([98.0, 99.0, 97.0, np.nan, 101.0, 100.0, np.nan, 103.0, 104.0, 102.0])
    close2 = np.array([100.0, 102.0, 101.0, np.nan, 103.0, 102.0, np.nan, 105.0, 106.0, 104.0])
    
    atr2 = calculate_atr(high2, low2, close2, period=period)
    print(f"\n案例2: 中间有NaN值，ATR周期={period}")
    print("ATR值:", atr2)
    print("是否还有NaN:", np.isnan(atr2).any(), "NaN的位置:", np.where(np.isnan(atr2))[0])
    
    # 案例3: 分散的NaN值
    high3 = np.array([102.0, np.nan, 103.0, 105.0, np.nan, 104.0, 106.0, 107.0, 108.0, np.nan])
    low3 = np.array([98.0, np.nan, 97.0, 101.0, np.nan, 100.0, 102.0, 103.0, 104.0, np.nan])
    close3 = np.array([100.0, np.nan, 101.0, 103.0, np.nan, 102.0, 104.0, 105.0, 106.0, np.nan])
    
    atr3 = calculate_atr(high3, low3, close3, period=period)
    print(f"\n案例3: 分散的NaN值，ATR周期={period}")
    print("ATR值:", atr3)
    print("是否还有NaN:", np.isnan(atr3).any(), "NaN的位置:", np.where(np.isnan(atr3))[0])
    
    # 测试恢复计算：在有效数据后应能正常计算ATR
    print("\n检查是否能在有效数据恢复后正常计算ATR")
    tr3 = calculate_tr(high3, low3, close3)
    for i in range(period, len(high3)):
        if not np.isnan(tr3[i]) and not np.isnan(atr3[i-1]):
            print(f"位置{i}：前ATR={atr3[i-1]:.2f}, 当前TR={tr3[i]:.2f}, 计算ATR={atr3[i]:.2f}")
            expected = ((period-1) * atr3[i-1] + tr3[i]) / period
            assert abs(atr3[i] - expected) < 1e-10, f"位置{i}的ATR计算错误"

def test_with_real_pattern():
    """测试一个接近实际数据模式的案例"""
    print("\n===== 测试接近实际数据模式的案例 =====")
    
    # 创建一个模拟真实数据的模式：前30天是NaN，然后是有效数据
    n = 100
    high = np.zeros(n)
    low = np.zeros(n)
    close = np.zeros(n)
    
    # 前30天设为NaN
    high[:30] = np.nan
    low[:30] = np.nan
    close[:30] = np.nan
    
    # 后面生成随机数据
    np.random.seed(42)  # 设定随机数种子，使结果可重现
    for i in range(30, n):
        base = 100 + i * 0.1  # 基础价格有轻微上升趋势
        volatility = 2.0  # 波动率
        
        high[i] = base + np.random.random() * volatility
        low[i] = base - np.random.random() * volatility
        close[i] = base + (np.random.random() - 0.5) * volatility
    
    # 计算TR和ATR
    period = 14
    tr = calculate_tr(high, low, close)
    atr = calculate_atr(high, low, close, period=period)
    
    # 生成位置索引以便绘图
    idx = np.arange(n)
    
    # 绘制结果
    plt.figure(figsize=(12, 10))
    
    # 价格图
    plt.subplot(3, 1, 1)
    plt.plot(idx, high, 'g-', label='High', alpha=0.7)
    plt.plot(idx, low, 'r-', label='Low', alpha=0.7)
    plt.plot(idx, close, 'b-', label='Close')
    plt.title('Price Data with NaN values in first 30 days')
    plt.legend()
    plt.grid(True)
    
    # TR图
    plt.subplot(3, 1, 2)
    plt.plot(idx, tr, 'r-', label='TR')
    plt.title('True Range (TR)')
    plt.legend()
    plt.grid(True)
    
    # ATR图
    plt.subplot(3, 1, 3)
    plt.plot(idx, atr, 'b-', label=f'ATR ({period})')
    plt.title(f'Average True Range (ATR) with period {period}')
    plt.legend()
    plt.grid(True)
    
    plt.tight_layout()
    plt.savefig('atr_test_results.png')
    plt.close()
    
    print(f"生成了{n}天的数据，前30天为NaN")
    print(f"TR中NaN的数量: {np.sum(np.isnan(tr))}")
    print(f"ATR中NaN的数量: {np.sum(np.isnan(atr))}")
    print(f"ATR应该在第{30+period-1}天开始有值")
    print(f"实际上ATR在第{np.where(~np.isnan(atr))[0][0]}天开始有值")
    
    # 检查ATR能否正确从NaN数据恢复
    first_valid_idx = np.where(~np.isnan(atr))[0][0]
    print(f"第一个有效的ATR值出现在位置{first_valid_idx}，值为{atr[first_valid_idx]:.4f}")
    
    # 验证后续ATR值是按预期计算的
    valid_tr = tr[~np.isnan(tr)]
    if len(valid_tr) >= period:
        expected_first_atr = np.mean(valid_tr[:period])
        print(f"基于前{period}个有效TR的期望初始ATR: {expected_first_atr:.4f}")
        print(f"实际计算的初始ATR: {atr[first_valid_idx]:.4f}")
        assert abs(atr[first_valid_idx] - expected_first_atr) < 1e-10, "初始ATR计算错误"

if __name__ == "__main__":
    test_tr_with_nans()
    test_atr_with_nans()
    test_with_real_pattern()
    
    print("\n所有测试通过！calculate_tr和calculate_atr函数正确处理了NaN数据。") 