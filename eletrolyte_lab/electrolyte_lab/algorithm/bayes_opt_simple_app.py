from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import os
import sys
import json
from bayes_opt_simple import SimpleBayesianOptimizationManager

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__)
CORS(app)

# 初始化贝叶斯优化管理器
bo_manager = SimpleBayesianOptimizationManager()

# 简化的HTML模板
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>贝叶斯优化电解液配方系统</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f5f5f5;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }

        header {
            background: linear-gradient(135deg, #4CAF50, #45a049);
            color: white;
            text-align: center;
            padding: 2rem;
            margin-bottom: 2rem;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        .card {
            background: white;
            border-radius: 10px;
            padding: 2rem;
            margin-bottom: 2rem;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }

        .section-title {
            font-size: 1.5rem;
            font-weight: 600;
            margin-bottom: 1.5rem;
            color: #2c3e50;
            border-bottom: 2px solid #4CAF50;
            padding-bottom: 0.5rem;
        }

        .form-group {
            margin-bottom: 1.5rem;
        }

        label {
            display: block;
            margin-bottom: 0.5rem;
            font-weight: 500;
            color: #2c3e50;
        }

        input, select, textarea {
            width: 100%;
            padding: 0.75rem;
            border: 2px solid #e1e8ed;
            border-radius: 5px;
            font-size: 1rem;
            transition: border-color 0.3s;
        }

        input:focus, select:focus, textarea:focus {
            outline: none;
            border-color: #4CAF50;
        }

        .btn {
            background: #4CAF50;
            color: white;
            padding: 0.75rem 2rem;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 1rem;
            font-weight: 500;
            transition: background 0.3s;
            margin-right: 1rem;
        }

        .btn:hover {
            background: #45a049;
        }

        .btn-secondary {
            background: #f44336;
        }

        .btn-secondary:hover {
            background: #da190b;
        }

        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
        }

        .suggestion-card {
            background: #f8f9fa;
            border-left: 4px solid #4CAF50;
            padding: 1rem;
            margin-bottom: 1rem;
            border-radius: 5px;
        }

        .tabs {
            display: flex;
            border-bottom: 2px solid #e1e8ed;
            margin-bottom: 2rem;
        }

        .tab {
            padding: 1rem 2rem;
            cursor: pointer;
            border-bottom: 2px solid transparent;
            transition: all 0.3s;
        }

        .tab.active {
            border-bottom-color: #4CAF50;
            color: #4CAF50;
            font-weight: 600;
        }

        .tab-content {
            display: none;
        }

        .tab-content.active {
            display: block;
        }

        .loading {
            display: none;
            text-align: center;
            padding: 2rem;
        }

        .success-message {
            background: #d4edda;
            color: #155724;
            padding: 1rem;
            border-radius: 5px;
            margin-bottom: 1rem;
            border-left: 4px solid #28a745;
        }

        .error-message {
            background: #f8d7da;
            color: #721c24;
            padding: 1rem;
            border-radius: 5px;
            margin-bottom: 1rem;
            border-left: 4px solid #dc3545;
        }

        .experiment-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 1rem;
        }

        .experiment-table th,
        .experiment-table td {
            padding: 0.75rem;
            text-align: left;
            border-bottom: 1px solid #e1e8ed;
        }

        .experiment-table th {
            background: #f8f9fa;
            font-weight: 600;
            color: #2c3e50;
        }

        .component-display {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin-top: 0.5rem;
        }

        .component-item {
            background: #e9ecef;
            padding: 0.25rem 0.5rem;
            border-radius: 3px;
            font-size: 0.9rem;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>贝叶斯优化电解液配方系统</h1>
            <p>智能推荐最优电解液配方，加速实验迭代</p>
        </header>

        <!-- 标签页 -->
        <div class="tabs">
            <div class="tab active" onclick="switchTab('add-experiment')">添加实验</div>
            <div class="tab" onclick="switchTab('optimize')">优化建议</div>
            <div class="tab" onclick="switchTab('history')">历史数据</div>
        </div>

        <!-- 添加实验页面 -->
        <div id="add-experiment" class="tab-content active">
            <div class="card">
                <h2 class="section-title">记录新实验</h2>

                <form id="experiment-form">
                    <div class="form-group">
                        <label>溶剂配方（总和应为1）</label>
                        <div class="grid" id="component-inputs">
                            <!-- 动态生成 -->
                        </div>
                    </div>

                    <div class="form-group">
                        <label>实验指标</label>
                        <div id="metric-inputs">
                            <!-- 动态生成 -->
                        </div>
                    </div>

                    <div class="form-group">
                        <label>备注</label>
                        <textarea id="notes" rows="3" placeholder="实验备注信息..."></textarea>
                    </div>

                    <button type="submit" class="btn">保存实验数据</button>
                    <button type="button" class="btn btn-secondary" onclick="normalizeComponents()">归一化配方</button>
                </form>
            </div>
        </div>

        <!-- 优化建议页面 -->
        <div id="optimize" class="tab-content">
            <div class="card">
                <h2 class="section-title">优化配置</h2>

                <form id="optimize-form">
                    <div class="form-group">
                        <label>指标权重</label>
                        <div class="grid" id="weight-inputs">
                            <!-- 动态生成 -->
                        </div>
                    </div>

                    <div class="form-group">
                        <label>推荐配方数量</label>
                        <select id="n-candidates">
                            <option value="3">3个</option>
                            <option value="5" selected>5个</option>
                            <option value="10">10个</option>
                        </select>
                    </div>

                    <button type="submit" class="btn">生成优化建议</button>
                </form>
            </div>

            <!-- 加载动画 -->
            <div class="loading" id="loading">
                <p>正在计算最优配方...</p>
            </div>

            <!-- 建议结果 -->
            <div class="card" id="suggestions-container" style="display: none;">
                <h2 class="section-title">优化建议</h2>
                <div id="suggestions">
                    <!-- 动态生成建议 -->
                </div>
            </div>
        </div>

        <!-- 历史数据页面 -->
        <div id="history" class="tab-content">
            <div class="card">
                <h2 class="section-title">实验历史</h2>
                <div id="experiments-table">
                    <!-- 动态生成表格 -->
                </div>
            </div>
        </div>

        <!-- 消息提示 -->
        <div id="message-container"></div>
    </div>

    <script>
        let componentNames = [];
        let metricInfo = {};

        // 页面加载时初始化
        document.addEventListener('DOMContentLoaded', function() {
            loadData();
            setupEventListeners();
        });

        // 加载数据
        async function loadData() {
            try {
                const response = await fetch('/api/metric-info');
                metricInfo = await response.json();

                // 更新组件名称
                componentNames = Array.from({length: 10}, (_, i) => `溶剂${i + 1}`);

                // 生成表单
                generateComponentInputs();
                generateMetricInputs();
                generateWeightInputs();

                // 加载实验历史
                loadExperiments();

            } catch (error) {
                showMessage('加载数据失败: ' + error.message, 'error');
            }
        }

        // 生成溶剂输入框
        function generateComponentInputs() {
            const container = document.getElementById('component-inputs');
            container.innerHTML = '';

            componentNames.forEach((name, index) => {
                const div = document.createElement('div');
                div.innerHTML = `
                    <label>${name}</label>
                    <input type="number" id="solvent_${index + 1}" step="0.01" min="0" max="1"
                           placeholder="0.0" onchange="updateComponentSum()">
                `;
                container.appendChild(div);
            });
        }

        // 生成指标输入框
        function generateMetricInputs() {
            const container = document.getElementById('metric-inputs');
            container.innerHTML = '';

            metricInfo.metrics.forEach((metric, index) => {
                const div = document.createElement('div');
                div.innerHTML = `
                    <label>${metric} (${metricInfo.directions[index] === 'maximize' ? '越大越好' : '越小越好'})</label>
                    <input type="number" id="metric_${metric}" step="0.01"
                           placeholder="${metricInfo.descriptions[index]}">
                `;
                container.appendChild(div);
            });
        }

        // 生成权重输入框
        function generateWeightInputs() {
            const container = document.getElementById('weight-inputs');
            container.innerHTML = '';

            metricInfo.metrics.forEach((metric, index) => {
                const defaultWeight = (1.0 / metricInfo.metrics.length).toFixed(2);
                const div = document.createElement('div');
                div.innerHTML = `
                    <label>${metric} 权重</label>
                    <input type="number" id="weight_${metric}" step="0.01" min="0" max="1"
                           value="${defaultWeight}" onchange="updateWeightSum()">
                `;
                container.appendChild(div);
            });
        }

        // 设置事件监听器
        function setupEventListeners() {
            // 实验表单提交
            document.getElementById('experiment-form').addEventListener('submit', async function(e) {
                e.preventDefault();
                await saveExperiment();
            });

            // 优化表单提交
            document.getElementById('optimize-form').addEventListener('submit', async function(e) {
                e.preventDefault();
                await generateSuggestions();
            });
        }

        // 保存实验数据
        async function saveExperiment() {
            try {
                const components = {};
                let total = 0;

                for (let i = 1; i <= 10; i++) {
                    const value = parseFloat(document.getElementById(`solvent_${i}`).value) || 0;
                    components[`solvent_${i}`] = value;
                    total += value;
                }

                // 归一化
                if (Math.abs(total - 1.0) > 0.01) {
                    for (let key in components) {
                        components[key] = components[key] / total;
                    }
                }

                const metrics = {};
                metricInfo.metrics.forEach(metric => {
                    metrics[metric] = parseFloat(document.getElementById(`metric_${metric}`).value) || 0;
                });

                const notes = document.getElementById('notes').value;

                const response = await fetch('/api/experiments', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        components,
                        metrics,
                        notes
                    })
                });

                if (response.ok) {
                    showMessage('实验数据保存成功！', 'success');
                    document.getElementById('experiment-form').reset();
                    loadExperiments(); // 刷新历史数据
                } else {
                    throw new Error('保存失败');
                }
            } catch (error) {
                showMessage('保存实验数据失败: ' + error.message, 'error');
            }
        }

        // 生成优化建议
        async function generateSuggestions() {
            try {
                document.getElementById('loading').style.display = 'block';
                document.getElementById('suggestions-container').style.display = 'none';

                const weights = {};
                let weightSum = 0;

                metricInfo.metrics.forEach(metric => {
                    weights[`w_${metric.substring(0, 3)}`] =
                        parseFloat(document.getElementById(`weight_${metric}`).value) || 0;
                    weightSum += weights[`w_${metric.substring(0, 3)}`];
                });

                // 归一化权重
                if (Math.abs(weightSum - 1.0) > 0.01) {
                    for (let key in weights) {
                        weights[key] = weights[key] / weightSum;
                    }
                }

                const nCandidates = parseInt(document.getElementById('n-candidates').value);

                const response = await fetch('/api/suggest', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        weights,
                        n_candidates: nCandidates
                    })
                });

                const data = await response.json();

                if (data.success) {
                    displaySuggestions(data.suggestions);
                } else {
                    throw new Error('生成建议失败');
                }
            } catch (error) {
                showMessage('生成优化建议失败: ' + error.message, 'error');
            } finally {
                document.getElementById('loading').style.display = 'none';
            }
        }

        // 显示建议结果
        function displaySuggestions(suggestions) {
            const container = document.getElementById('suggestions');
            container.innerHTML = '';

            suggestions.forEach((suggestion, index) => {
                const div = document.createElement('div');
                div.className = 'suggestion-card';

                // 显示主要组分
                const mainComponents = Object.entries(suggestion.components)
                    .sort((a, b) => b[1] - a[1])
                    .slice(0, 5)
                    .map(([key, value]) => {
                        const solventIndex = parseInt(key.split('_')[1]) - 1;
                        return `${componentNames[solventIndex]}: ${(value * 100).toFixed(1)}%`;
                    })
                    .join(', ');

                div.innerHTML = `
                    <div style="font-weight: 600; margin-bottom: 0.5rem;">
                        配方 ${index + 1} (置信度: ${(suggestion.total_confidence * 100).toFixed(1)}%)
                    </div>
                    <div class="component-display">
                        ${Object.entries(suggestion.components).map(([key, value]) => {
                            const solventIndex = parseInt(key.split('_')[1]) - 1;
                            return `<div class="component-item">${componentNames[solventIndex]}: ${(value * 100).toFixed(1)}%</div>`;
                        }).join('')}
                    </div>
                    <div style="margin-top: 1rem;">
                        <button class="btn" onclick="adoptRecipe('${suggestion.id}')">采用此配方</button>
                        <button class="btn btn-secondary" onclick="copyToClipboard('${suggestion.id}')">复制配方</button>
                    </div>
                `;
                container.appendChild(div);
            });

            document.getElementById('suggestions-container').style.display = 'block';
        }

        // 加载实验历史
        async function loadExperiments() {
            try {
                const response = await fetch('/api/experiments');
                const experiments = await response.json();

                const container = document.getElementById('experiments-table');

                if (experiments.length === 0) {
                    container.innerHTML = '<p>暂无实验数据</p>';
                    return;
                }

                let html = `
                    <table class="experiment-table">
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>时间</th>
                                <th>主要组分</th>
                                <th>指标结果</th>
                                <th>备注</th>
                            </tr>
                        </thead>
                        <tbody>
                `;

                experiments.forEach(exp => {
                    const mainComponents = Object.entries(exp.components)
                        .sort((a, b) => b[1] - a[1])
                        .slice(0, 3)
                        .map(([key, value]) => {
                            const solventIndex = parseInt(key.split('_')[1]) - 1;
                            return `${componentNames[solventIndex]}: ${(value * 100).toFixed(1)}%`;
                        })
                        .join(', ');

                    const metricsSummary = Object.entries(exp.metrics)
                        .map(([key, value]) => `${key}: ${value.toFixed(2)}`)
                        .join(', ');

                    html += `
                        <tr>
                            <td>${exp.id}</td>
                            <td>${new Date(exp.created_at).toLocaleDateString()}</td>
                            <td>${mainComponents}${Object.keys(exp.components).length > 3 ? '...' : ''}</td>
                            <td>${metricsSummary}</td>
                            <td>${exp.notes || '-'}</td>
                        </tr>
                    `;
                });

                html += '</tbody></table>';
                container.innerHTML = html;

            } catch (error) {
                document.getElementById('experiments-table').innerHTML =
                    '<p class="error-message">加载历史数据失败</p>';
            }
        }

        // 采用配方
        function adoptRecipe(suggestionId) {
            switchTab('add-experiment');
            showMessage('已将配方填充到输入表单', 'success');
        }

        // 复制配方
        function copyToClipboard(suggestionId) {
            showMessage('配方已复制到剪贴板', 'success');
        }

        // 归一化配方
        function normalizeComponents() {
            let sum = 0;
            const values = [];

            for (let i = 1; i <= 10; i++) {
                const value = parseFloat(document.getElementById(`solvent_${i}`).value) || 0;
                values.push(value);
                sum += value;
            }

            if (sum > 0) {
                values.forEach((value, index) => {
                    document.getElementById(`solvent_${index + 1}`).value = (value / sum).toFixed(4);
                });
                showMessage('配方已归一化', 'success');
            } else {
                showMessage('请先输入配方数据', 'error');
            }
        }

        // 切换标签页
        function switchTab(tabId) {
            document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));

            event.target.classList.add('active');
            document.getElementById(tabId).classList.add('active');

            if (tabId === 'history') {
                loadExperiments();
            }
        }

        // 显示消息
        function showMessage(message, type = 'info') {
            const container = document.getElementById('message-container');
            const div = document.createElement('div');
            div.className = `${type}-message`;
            div.textContent = message;

            container.appendChild(div);

            setTimeout(() => {
                div.remove();
            }, 3000);
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """主页"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/metric-info', methods=['GET'])
def get_metric_info():
    """获取指标信息"""
    return jsonify(bo_manager.get_metric_info())

@app.route('/api/experiments', methods=['GET'])
def get_experiments():
    """获取所有实验数据"""
    return jsonify(bo_manager.get_experiments())

@app.route('/api/experiments', methods=['POST'])
def add_experiment():
    """添加新的实验数据"""
    try:
        data = request.get_json()

        components = data.get('components', {})
        metrics = data.get('metrics', {})
        notes = data.get('notes', '')

        success = bo_manager.add_experiment(components, metrics, notes)

        if success:
            return jsonify({'success': True, 'message': '实验数据保存成功'})
        else:
            return jsonify({'success': False, 'message': '保存失败'}), 400

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/suggest', methods=['POST'])
def suggest_recipes():
    """生成优化建议"""
    try:
        data = request.get_json()

        weights = data.get('weights', {})
        n_candidates = data.get('n_candidates', 5)

        result = bo_manager.suggest_new_recipes(weights, n_candidates)

        return jsonify(result)

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/status', methods=['GET'])
def get_status():
    """获取系统状态"""
    return jsonify({
        'experiments_count': len(bo_manager.experiments),
        'metrics_count': len(bo_manager.metric_info['metrics']),
        'components_count': len(bo_manager.component_names),
        'last_updated': bo_manager.experiments[-1]['created_at'] if bo_manager.experiments else None
    })

if __name__ == '__main__':
    # 确保数据目录存在
    os.makedirs('data', exist_ok=True)

    print("贝叶斯优化电解液配方系统启动中...")
    print("访问地址: http://localhost:5000")
    print("按 Ctrl+C 停止服务")

    app.run(host='0.0.0.0', port=5000, debug=False)