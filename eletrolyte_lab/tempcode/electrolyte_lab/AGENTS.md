# 悟行：智能电池设计与实验系统 - AI代理开发指南

## 项目概述

**悟行**（Wu Xing）是一个面向电池材料研发的智能实验平台，采用AI驱动的闭环优化流程，实现从需求输入到配方生成、实验执行、结果评估的自动化。

### 核心业务模块

1. **AI设计员 (AI Designer)**: 用户需求解析、文献数据挖掘、分子性质预测、配方生成
2. **AI实验员 (AI Experimenter)**: 实验执行控制、实时数据监控、实验结果采集
3. **闭环优化 (Closed Loop)**: 贝叶斯优化算法、实验结果评估、智能决策生成、配方重设计

### 实验-配方数据模型

- **配方 (Formula)**: 每个配方固定包含 **10个组分** (溶剂、盐、添加剂)
- **实验 (Experiment)**: 一次实验最多可测试 **64个配方**
- **电池测试**: 每个配方注入到 **3个电池** 中进行并行测试

---

## 技术栈

### 前端技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| React | 18.2.0 | UI框架 |
| TypeScript | 4.9.4 | 类型系统 |
| Ant Design | 5.1.7 | UI组件库 |
| ECharts | 5.4.1 | 数据可视化 |
| Three.js | 0.162.0 | 3D分子展示 |
| React Router | 6.6.1 | 路由管理 |
| Axios | 1.2.2 | HTTP客户端 |

### 后端技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| Python | 3.9+ | 运行环境 |
| Flask | 2.3.3 | Web框架 |
| SQLAlchemy | 2.0.21 | ORM |
| PyJWT | 2.8.0 | 身份认证 |
| PostgreSQL/MySQL | - | 数据库 |
| Redis | 4.6.0 | 缓存/队列 |
| Celery | 5.3.1 | 异步任务 |

### 算法技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| PyTorch | 2.0.0+ | 深度学习 |
| BoTorch | - | 贝叶斯优化 |
| GPyTorch | - | 高斯过程 |
| RDKit | 2023.3.2+ | 分子处理 |
| Transformers | 4.30.0+ | NLP模型 |

---

## 项目结构

```
electrolyte_lab/
├── backend/                    # Flask后端
│   ├── api/                   # API路由蓝图
│   │   ├── ai_designer_routes.py      # AI设计员接口
│   │   ├── ai_experimenter_routes.py  # AI实验员接口
│   │   ├── closed_loop_routes.py      # 闭环优化接口
│   │   ├── auth_routes.py             # 用户认证接口
│   │   ├── experiments_routes.py      # 实验管理接口
│   │   └── video_routes_fixed.py      # 视频监控接口
│   ├── models/                # SQLAlchemy数据模型
│   │   ├── user.py            # 用户模型(含JWT认证)
│   │   ├── experiment.py      # 实验模型
│   │   ├── formula.py         # 配方模型(10组分约束)
│   │   ├── requirement.py     # 用户需求模型
│   │   └── project.py         # 项目模型
│   ├── utils/                 # 工具函数
│   │   └── auth.py            # JWT认证装饰器
│   ├── extensions.py          # Flask扩展初始化
│   ├── app.py                 # 应用入口
│   └── requirements.txt       # Python依赖
│
├── frontend/                   # React前端
│   ├── src/
│   │   ├── pages/             # 页面组件
│   │   │   ├── AIDesignerPage.tsx     # AI设计员页面
│   │   │   ├── AIExperimenterPage.tsx # AI实验员页面
│   │   │   ├── ClosedLoopPage.tsx     # 闭环优化页面
│   │   │   ├── LoginPage.tsx          # 登录页
│   │   │   ├── RegisterPage.tsx       # 注册页
│   │   │   └── ProfilePage.tsx        # 个人中心
│   │   ├── components/        # 可复用组件
│   │   │   ├── MoleculeThreeViewer.tsx # 3D分子展示
│   │   │   ├── ChargeDischargeChart.tsx # 充放电曲线
│   │   │   └── TextMiningResults.tsx   # 文本挖掘结果
│   │   ├── services/          # API服务
│   │   │   ├── api.ts         # 业务API封装
│   │   │   └── deepseek-api.ts # DeepSeek AI接口
│   │   ├── types/             # TypeScript类型定义
│   │   │   └── index.ts       # 全量类型定义
│   │   ├── utils/             # 工具函数
│   │   │   └── http.ts        # Axios实例配置
│   │   ├── hooks/             # 自定义Hooks
│   │   └── App.tsx            # 应用路由配置
│   ├── package.json           # npm依赖
│   └── tsconfig.json          # TypeScript配置
│
├── algorithm/                  # 算法模块
│   ├── bayes_opt.py           # 贝叶斯优化核心
│   ├── bayes_opt_app.py       # Flask应用封装
│   ├── bayes_opt_simple.py    # 简化版优化器
│   └── Bo.py                  # 优化器基类
│
├── fpxh_control_sdk/           # 硬件控制SDK
│   └── plc_control_new.py     # PLC控制器接口
│
├── data/                       # 数据目录
│   ├── literature/            # 文献数据
│   └── molecules/             # 分子数据
│
├── SicPDF/                     # 样本PDF文件
├── docs/                       # 文档目录
├── logs/                       # 日志目录
├── start.sh                    # 一键启动脚本
└── stop.sh                     # 停止脚本
```

---

## 开发环境配置

### 前置要求

- **Python**: 3.9+ (推荐3.11)
- **Node.js**: 18+ LTS
- **Anaconda**: 推荐用于Python环境管理
- **Git**: 版本控制

### 环境初始化

```bash
# 1. 克隆项目后，创建Python环境
conda create -n ailab python=3.11
conda activate ailab

# 2. 安装后端依赖
cd backend
pip install -r requirements.txt

# 3. 安装前端依赖
cd ../frontend
npm install
npm install react-scripts@4.0.3  # 注意：必须使用4.x版本
```

### 环境变量配置

在 `backend/` 目录创建 `.env` 文件：

```env
# 应用配置
SECRET_KEY=your-secret-key-here
FLASK_ENV=development

# 数据库配置 (PostgreSQL)
DATABASE_URL=postgresql://user:password@localhost:5432/battery_lab

# 或 SQLite (开发环境)
DATABASE_URL=sqlite:///battery_lab.db

# 蓝点数据库 (外部设备数据)
LANDIAN_DB_HOST=101.6.160.48
LANDIAN_DB_PORT=50003
LANDIAN_DB_USER=landian
LANDIAN_DB_PASS=123456
LANDIAN_DB_NAME=electrolyte

# DeepSeek AI API (可选)
DEEPSEEK_API_KEY=your-api-key
```

---

## 构建与运行

### 方式一：一键启动（推荐）

```bash
# 项目根目录
./start.sh

# 停止服务
./stop.sh
```

### 方式二：手动启动

```bash
# 终端1：启动后端
conda activate ailab
cd backend
PYTHONPATH=. python app.py  # 默认端口5009

# 终端2：启动前端
cd frontend
NODE_OPTIONS="--openssl-legacy-provider" npm start  # 端口3000
```

### 访问地址

- **前端界面**: http://localhost:3000
- **后端API**: http://localhost:5009
- **API文档**: 通过代码中的路由注释查看

---

## 代码规范

### Python代码规范

1. **模型定义**: 使用SQLAlchemy ORM，所有模型需包含 `to_dict()` 方法
   ```python
   class Experiment(db.Model):
       __tablename__ = 'experiments'
       id = db.Column(db.Integer, primary_key=True)
       
       def to_dict(self):
           return {'id': self.id, ...}
   ```

2. **API路由**: 使用Flask Blueprint，统一响应格式
   ```python
   @ai_designer_bp.route('/parse-request', methods=['POST'])
   def parse_request():
       try:
           # 业务逻辑
           return jsonify({'success': True, 'data': result})
       except Exception as e:
           return jsonify({'success': False, 'error': str(e)}), 500
   ```

3. **认证装饰器**: 使用 `@token_required` 保护需要登录的接口
   ```python
   from utils.auth import token_required, admin_required
   
   @token_required
   def protected_route():
       current_user = request.current_user
       ...
   ```

### TypeScript代码规范

1. **类型定义**: 所有数据类型定义在 `src/types/index.ts`
   ```typescript
   export interface Experiment {
     id: number;
     name: string;
     status: 'pending' | 'running' | 'completed' | 'failed';
     // ...
   }
   ```

2. **API调用**: 使用封装好的 `api.ts` 中的方法
   ```typescript
   import { aiDesignerApi } from '../services/api';
   
   const response = await aiDesignerApi.parseRequest(data);
   ```

3. **组件结构**: 函数组件 + Hooks
   ```typescript
   const MyComponent: React.FC<Props> = ({ prop1, prop2 }) => {
     const [state, setState] = useState(initialState);
     
     useEffect(() => {
       // 副作用处理
     }, [deps]);
     
     return <div>...</div>;
   };
   ```

---

## 数据库模型

### 核心模型关系

```
User (1) ───< (N) Experiment (N) >─── (1) Formula (1) ───< (N) Component
                    │
                    └──< (N) ExperimentResult
```

### 关键约束

1. **配方组分约束**: 每个配方必须有且仅有10个组分
   ```python
   COMPONENTS_PER_FORMULA = 10
   ```

2. **实验配方约束**: 一次实验最多64个配方
   ```python
   MAX_FORMULAS_PER_EXPERIMENT = 64
   ```

3. **用户角色**: admin, user, researcher
   ```python
   class UserRole(enum.Enum):
       ADMIN = "admin"
       USER = "user"
       RESEARCHER = "researcher"
   ```

---

## API接口规范

### 接口前缀

- AI设计员: `/api/ai-designer/*`
- AI实验员: `/api/ai-experimenter/*`
- 闭环优化: `/api/closed-loop/*`
- 用户认证: `/api/auth/*`
- 实验数据: `/api/experiments/*`
- 视频监控: `/api/video/*`

### 统一响应格式

```json
{
  "success": true|false,
  "data": { ... },
  "message": "提示信息",
  "error": "错误信息"
}
```

---

## 测试策略

### 手动测试脚本

项目包含以下测试/诊断脚本：

```bash
# 系统整体测试
python test_system.py

# 真实数据集成测试
python test_real_data_integration.py

# 后端API调试
python backend/debug_api.py

# 步骤转换调试
python debug_step_transition.py
```

### 日志查看

```bash
# 实时查看后端日志
tail -f logs/backend.log

# 实时查看前端日志
tail -f logs/frontend.log

# 查看应用日志
tail -f backend/app.log
```

---

## 部署说明

### 生产环境部署

1. **数据库**: 使用PostgreSQL，配置连接池
2. **Web服务器**: 使用Gunicorn
   ```bash
   gunicorn -w 4 -b 0.0.0.0:5009 "app:create_app()"
   ```
3. **前端构建**:
   ```bash
   cd frontend
   npm run build
   # 将build目录部署到Nginx/Apache
   ```
4. **环境变量**: 生产环境必须修改 `SECRET_KEY`，使用强密码

### 端口配置

- 后端默认端口: 5009 (可在 `app.py` 中修改)
- 前端开发服务器: 3000
- 如需修改后端端口，同步更新前端代理配置

---

## 常见问题

### 1. 前端启动失败 (OpenSSL错误)

```bash
# 解决方案：添加Node选项
export NODE_OPTIONS="--openssl-legacy-provider"
npm start
```

### 2. 后端端口被占用

```bash
# 查找占用端口的进程
lsof -i :5009
# 终止进程后重新启动
```

### 3. 数据库连接失败

- 检查 `.env` 文件中的数据库URL
- 确保PostgreSQL/MySQL服务已启动
- 对于开发环境，可使用SQLite简化配置

### 4. CORS跨域错误

- 后端已配置CORS支持
- 检查前端请求的API地址是否正确

---

## 安全注意事项

1. **密钥管理**: 生产环境必须使用强密钥，不要提交 `.env` 到Git
2. **JWT令牌**: access_token有效期1小时，refresh_token有效期7天
3. **密码策略**: 最少8位，必须包含大小写字母和数字
4. **SQL注入**: 使用SQLAlchemy ORM，避免原始SQL拼接
5. **文件上传**: 验证文件类型和大小，使用安全文件名

---

## 相关文档

- `README.md` - 项目基础说明
- `backend/DEPLOYMENT_GUIDE.md` - 后端部署指南
- `algorithm/README_BAYES_OPT.md` - 贝叶斯优化说明
- `FEATURES.md` - 功能特性说明
- `BM25_Integration_Summary.md` - 文献检索集成说明

---

## 开发团队联系方式

如有问题，请参考项目中的Markdown文档或联系项目负责人。
