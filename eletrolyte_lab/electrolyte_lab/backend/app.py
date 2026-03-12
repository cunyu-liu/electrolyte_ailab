from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
from extensions import db
import os
import logging
import sys

# 加载环境变量
load_dotenv()

 #全局变量，开始实验的实例
injector_obj_list = []

def create_app(config_name='development'):
    app = Flask(__name__)

    # 配置
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JSON_AS_ASCII'] = False
    app.config['JSONIFY_MIMETYPE'] = 'application/json; charset=utf-8'

    LANDIAN_DB_CONFIG = {
        'host': os.getenv('LANDIAN_DB_HOST'),
        'port': int(os.getenv('LANDIAN_DB_PORT', 50003)), # 必须转为 int！默认值给个50003防崩
        'user': os.getenv('LANDIAN_DB_USER'),
        'password': os.getenv('LANDIAN_DB_PASS'),
        'database': os.getenv('LANDIAN_DB_NAME')
    }
    
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)s: %(message)s',
        force=True,
        # 改用 handlers 列表，包含两个处理器
        handlers=[
            # 处理器 1：负责写文件 (建议加上 encoding='utf-8' 防止中文乱码)
            logging.FileHandler('app.log', mode='a', encoding='utf-8'),
            
            # 处理器 2：负责输出到终端
            logging.StreamHandler(sys.stdout)
        ]
    )

    logging.getLogger('werkzeug').setLevel(logging.INFO)

    # 确保JSON响应使用UTF-8编码
    app.json.ensure_ascii = False

    # 初始化扩展
    db.init_app(app)
    CORS(app)

    # 注册蓝图
    from api.ai_designer_routes import ai_designer_bp, scheduler
    from api.ai_experimenter_routes import ai_experimenter_bp
    from api.closed_loop_routes import closed_loop_bp
    from api.auth_routes import auth_bp
    from api.experiments_routes import experiments_bp
    from api.experiment_data_routes import experiment_data_bp
    from api.video_routes_fixed import video_bp

    app.register_blueprint(ai_designer_bp, url_prefix='/api/ai-designer')
    app.register_blueprint(ai_experimenter_bp, url_prefix='/api/ai-experimenter')
    app.register_blueprint(closed_loop_bp, url_prefix='/api/closed-loop')
    app.register_blueprint(auth_bp)
    app.register_blueprint(experiments_bp, url_prefix='/api')
    app.register_blueprint(experiment_data_bp)
    app.register_blueprint(video_bp, url_prefix='/api/video')

    # 创建数据库表
    with app.app_context():
        db.create_all()

    scheduler.init_app(app)
    scheduler.start()

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5009)