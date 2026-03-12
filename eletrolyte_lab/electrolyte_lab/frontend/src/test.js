// 简单的测试脚本
console.log('测试脚本运行正常');

// 检查React是否可用
try {
  const React = require('react');
  console.log('React版本:', React.version);
} catch (e) {
  console.error('React加载失败:', e);
}

// 检查Antd是否可用
try {
  const antd = require('antd');
  console.log('Antd加载成功');
} catch (e) {
  console.error('Antd加载失败:', e);
}