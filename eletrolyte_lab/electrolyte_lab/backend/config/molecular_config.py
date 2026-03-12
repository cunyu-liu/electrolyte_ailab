import os

# 分子生成配置
SURGE_PATH = os.path.join(os.path.dirname(__file__), '../../../molecular_generation_code/surge')
ISOMERS_PATH = os.path.join(os.path.dirname(__file__), '../../../molecular_generation_code/isomers')

# PDF处理配置
SPARK_PATH = os.path.join(os.path.dirname(__file__), '../../../SPARK-master-20250803')
PDF_STORAGE_PATH = os.path.join(os.path.dirname(__file__), '../../SicPDF')

# 处理配置
DEFAULT_BATCH_SIZE = 5
MAX_GENERATION_COUNT = 200
CONFIDENCE_THRESHOLD = 0.5