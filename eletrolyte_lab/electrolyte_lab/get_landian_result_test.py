from fpxh_control.get_landian_result import LandianDataQuery
def main():
    import matplotlib.pyplot as plt
    plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
    plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号

    """主函数示例"""
    # 数据库配置
    db_config = {
        'host': '101.6.160.48',
        'port': 50003,
        'user': 'landian',
        'password': '123456',
        'database': 'electrolyte'
    }

    # 创建查询实例
    query = LandianDataQuery(db_config)

    try:
        main_id_list=query.get_all_main_ids(limit=1000,)
        print(" main_id_list:  ",main_id_list)

        # 示例1：查询循环曲线（输入MainId=4569）
        print("=" * 60)
        print("示例1：查询循环曲线 (MainId=4569)")
        print("=" * 60)

        cycle_curve_result = query.get_cycle_curve("4569")

        # 打印结果
        if "error" in cycle_curve_result:
            print(f"错误: {cycle_curve_result['error']}")
        else:
            """
            最简单的放电容量曲线绘制
            """
            if "error" in cycle_curve_result:
                print(f"错误: {cycle_curve_result['error']}")
                return

            # 提取数据
            cycles = []
            discharge_capacities = []

            for cycle in cycle_curve_result.get("循环曲线", []):
                cycles.append(cycle["循环号"])
                discharge_capacities.append(cycle["放电容量(Ah)"])

            # 绘制曲线
            plt.figure(figsize=(10, 6))
            plt.plot(cycles, discharge_capacities, 'b-o', linewidth=2, markersize=6)

            plt.xlabel("循环次数")
            plt.ylabel("放电容量 (Ah)")
            plt.title("放电容量衰减曲线")
            plt.grid(True, alpha=0.3)

            # 显示数值标签（可选）
            for i, (cycle, capacity) in enumerate(zip(cycles, discharge_capacities)):
                if capacity is not None:
                    plt.annotate(f"{capacity:.2f}",
                                 xy=(cycle, capacity),
                                 xytext=(0, 5),
                                 textcoords="offset points",
                                 ha='center',
                                 fontsize=8)

            plt.show()
        # 示例2：查询循环细节（输入MainId=4569, 循环圈数=3）
        print("\n" + "=" * 60)
        print("示例2：查询循环细节 (MainId=4569, CycleNo=3)")
        print("=" * 60)

        cycle_detail_result = query.get_cycle_details("4569", 30)

        if "error" in cycle_detail_result:
            print(f"错误: {cycle_detail_result['error']}")
        else:
            records=cycle_detail_result["详细记录数据"]["采样记录"]
            # 提取电压和容量数据
            voltages = [r['Voltage'] for r in records if r.get('Voltage') is not None]
            capacities = [r['Capacity'] for r in records if r.get('Capacity') is not None]

            # 方法1：双Y轴图（最简单直观）
            fig, ax1 = plt.subplots(figsize=(12, 7))

            # 第一条线：电压曲线（左侧Y轴）
            color1 = 'tab:red'
            ax1.set_xlabel('记录序号')
            ax1.set_ylabel('电压 (V)', color=color1)
            line1 = ax1.plot(range(len(voltages)), voltages, color=color1, linewidth=2, label='电压')
            ax1.tick_params(axis='y', labelcolor=color1)

            # 第二条线：容量曲线（右侧Y轴）
            ax2 = ax1.twinx()
            color2 = 'tab:blue'
            ax2.set_ylabel('容量 (Ah)', color=color2)
            line2 = ax2.plot(range(len(capacities)), capacities, color=color2, linewidth=2, label='容量',
                             linestyle='--')
            ax2.tick_params(axis='y', labelcolor=color2)

            plt.title('电压与容量变化曲线')
            fig.tight_layout()
            plt.show()
    finally:
        # 关闭数据库连接
        query.close()

main()