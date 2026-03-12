import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import TestPage from './pages/TestPage';

const AppSimple: React.FC = () => {
  console.log('AppSimple: 应用正在启动');

  return (
    <BrowserRouter>
      <div style={{ minHeight: '100vh', background: '#f5f5f5' }}>
        <Routes>
          <Route path="/" element={<TestPage />} />
          <Route path="/login" element={<TestPage />} />
          <Route path="*" element={<TestPage />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
};

export default AppSimple;