#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PostgreSQL数据库初始化脚本
创建papers表并插入示例数据
"""

import psycopg2
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_database():
    """初始化PostgreSQL数据库"""
    try:
        # 连接到PostgreSQL
        conn = psycopg2.connect(
            dbname="postgres",
            user="postgres",
            password="123456",
            host="localhost",
            port=5432
        )
        cur = conn.cursor()

        logger.info("成功连接到PostgreSQL数据库")

        # 创建papers表（如果不存在）
        create_table_query = """
        CREATE TABLE IF NOT EXISTS papers (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            abstract TEXT,
            doi TEXT,
            year INTEGER,
            authors TEXT,
            journal TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """

        cur.execute(create_table_query)
        logger.info("创建/检查papers表完成")

        # 检查是否已有数据
        cur.execute("SELECT COUNT(*) FROM papers")
        count = cur.fetchone()[0]

        if count > 0:
            logger.info(f"papers表已有 {count} 条记录，跳过示例数据插入")
        else:
            # 插入示例数据
            sample_papers = [
                (
                    "High-energy lithium-ion battery electrolytes with novel carbonate solvents",
                    "Development of high-energy density lithium-ion batteries using ethylene carbonate-based electrolytes with novel carbonate solvent systems. The study investigates the electrochemical performance and thermal stability of these electrolyte formulations for electric vehicle applications.",
                    "10.1016/j.jpowsour.2023.233456",
                    2023,
                    "Zhang, L.; Wang, Y.; Chen, J.; Liu, H.; Brown, M.",
                    "Journal of Power Sources"
                ),
                (
                    "Advanced electrolyte additives for high-power lithium-ion batteries",
                    "Comprehensive study of electrolyte additives for high-power lithium-ion battery applications. Focus on SEI formation, charge transfer resistance, and long-term cycling stability in fast-charging scenarios.",
                    "10.1016/j.elecom.2023.107890",
                    2023,
                    "Li, S.; Yang, K.; Brown, M.; Davis, R.; Wilson, A.",
                    "Electrochemistry Communications"
                ),
                (
                    "Novel fluorinated electrolytes for next-generation lithium batteries",
                    "Investigation of fluorinated electrolyte systems for enhanced voltage stability and improved safety characteristics in lithium battery applications. Including thermal runaway prevention and flame retardancy mechanisms.",
                    "10.1002/aenm.202301234",
                    2023,
                    "Wang, X.; Thompson, J.; Martinez, A.; Kim, H.; Lee, S.",
                    "Advanced Energy Materials"
                ),
                (
                    "Low-temperature electrolyte formulations for electric vehicle applications",
                    "Development of electrolyte formulations suitable for low-temperature operation of electric vehicles. Including ionic conductivity and viscosity measurements at sub-zero temperatures down to -40°C.",
                    "10.1016/j.electrochem.2023.117890",
                    2023,
                    "Chen, Y.; Liu, Z.; Kumar, P.; Anderson, R.; Taylor, M.",
                    "Journal of The Electrochemical Society"
                ),
                (
                    "Sustainable electrolyte design for energy storage systems",
                    "Sustainable and environmentally friendly electrolyte design for large-scale energy storage systems. Life cycle analysis and environmental impact assessment of various electrolyte formulations with focus on recyclability.",
                    "10.1039/d3ee00123a",
                    2023,
                    "Johnson, K.; Smith, R.; Garcia, L.; White, P.; Hall, T.",
                    "Energy & Environmental Science"
                ),
                (
                    "Electrolyte optimization for high-voltage cathode materials",
                    "Design and optimization of electrolyte systems for high-voltage cathode materials including NCM811 and NCA. Investigation of oxidative stability and interface compatibility at 4.5V+ operation.",
                    "10.1016/j.jpowsour.2023.245678",
                    2023,
                    "Anderson, P.; Wilson, T.; Chen, X.; Kumar, S.; Lee, J.",
                    "Journal of Power Sources"
                ),
                (
                    "Solid-state electrolyte development for next-generation batteries",
                    "Comprehensive review of solid-state electrolyte development including sulfide, oxide, and polymer electrolytes. Focus on ionic conductivity, mechanical properties, and interface engineering.",
                    "10.1038/s41560-023-01234-5",
                    2023,
                    "Thompson, R.; Garcia, M.; Wang, H.; Liu, K.; Brown, P.",
                    "Nature Energy"
                ),
                (
                    "Electrolyte formulations for sodium-ion battery systems",
                    "Development of electrolyte formulations specifically designed for sodium-ion battery systems. Comparison with lithium-ion battery electrolytes and optimization for sodium chemistry.",
                    "10.1016/j.ensm.2023.101234",
                    2023,
                    "Martinez, L.; Smith, J.; Anderson, K.; Wilson, R.; Chen, P.",
                    "Energy Storage Materials"
                ),
                (
                    "Fire-retardant electrolytes for enhanced battery safety",
                    "Development of fire-retardant electrolyte additives and formulations to enhance battery safety. Evaluation of flame retardancy mechanisms and impact on electrochemical performance.",
                    "10.1002/aenm.202303456",
                    2023,
                    "Wilson, S.; Brown, T.; Garcia, K.; Anderson, L.; Lee, M.",
                    "Advanced Energy Materials"
                ),
                (
                    "High-concentration electrolytes for lithium metal batteries",
                    "Investigation of high-concentration electrolyte systems for lithium metal battery applications. Focus on dendrite suppression, coulombic efficiency, and long-term cycling stability.",
                    "10.1016/j.jpowsour.2023.256789",
                    2023,
                    "Lee, H.; Kim, P.; Wang, L.; Johnson, K.; Smith, R.",
                    "Journal of Power Sources"
                )
            ]

            insert_query = """
            INSERT INTO papers (title, abstract, doi, year, authors, journal)
            VALUES (%s, %s, %s, %s, %s, %s)
            """

            cur.executemany(insert_query, sample_papers)
            logger.info(f"成功插入 {len(sample_papers)} 条示例数据")

        # 提交事务
        conn.commit()

        # 验证数据
        cur.execute("SELECT COUNT(*) FROM papers")
        final_count = cur.fetchone()[0]
        logger.info(f"数据库初始化完成，papers表现在有 {final_count} 条记录")

        # 关闭连接
        cur.close()
        conn.close()

        return True

    except Exception as e:
        logger.error(f"数据库初始化失败: {str(e)}")
        return False

if __name__ == "__main__":
    print("开始初始化PostgreSQL数据库...")
    success = init_database()
    if success:
        print("✅ 数据库初始化成功！")
        print("现在可以启动后端服务器并使用BM25搜索功能了。")
    else:
        print("❌ 数据库初始化失败，请检查PostgreSQL连接配置。")