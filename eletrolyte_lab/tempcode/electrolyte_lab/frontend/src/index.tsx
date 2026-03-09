import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import 'antd/dist/reset.css';
import './index.css';

// 导入主App组件
import App from './App';
import ErrorBoundary from './components/ErrorBoundary';
import { initClickDebugger } from './utils/debug';

// 初始化调试工具（仅在开发环境）
if (process.env.NODE_ENV === 'development') {
  initClickDebugger();
}

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);

root.render(
  <ErrorBoundary>
    <React.StrictMode>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </React.StrictMode>
  </ErrorBoundary>
);