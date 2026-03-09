// 调试工具：用于诊断点击事件问题
export const initClickDebugger = () => {
  // 添加全局点击事件监听器
  document.addEventListener('click', (event) => {
    const target = event.target as HTMLElement;
  }, true);

  // 添加键盘事件监听器
  document.addEventListener('keydown', (event) => {
  });

  // 检查React组件是否正确渲染
  console.log('Click debugger initialized');
  console.log('Document ready state:', document.readyState);
  console.log('React root element:', document.getElementById('root'));

  // 检查是否有CSS样式阻止点击
  const rootElement = document.getElementById('root');
  if (rootElement) {
    const computedStyle = window.getComputedStyle(rootElement);
    console.log('Root element styles:', {
      pointerEvents: computedStyle.pointerEvents,
      display: computedStyle.display,
      visibility: computedStyle.visibility,
      zIndex: computedStyle.zIndex
    });
  }
};