import React from 'react';

const TestPage: React.FC = () => {
  console.log('TestPage: 组件正在渲染');

  return (
    <div style={{ padding: '20px', textAlign: 'center' }}>
      <h1>测试页面</h1>
      <p>如果您能看到这个页面，说明React应用正在正常工作。</p>
      <div style={{
        background: '#f0f0f0',
        padding: '20px',
        borderRadius: '8px',
        marginTop: '20px'
      }}>
        <h2>应用状态检查：</h2>
        <ul style={{ textAlign: 'left' }}>
          <li>✅ React应用启动成功</li>
          <li>✅ 路由系统工作正常</li>
          <li>✅ 组件渲染正常</li>
        </ul>
      </div>
    </div>
  );
};

export default TestPage;