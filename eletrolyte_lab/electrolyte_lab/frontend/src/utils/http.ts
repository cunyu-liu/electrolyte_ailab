// 封装 Axios 请求 - src/utils/http.js
import axios from 'axios';
import { message } from 'antd';
// 创建axios实例
const baseURL = process.env.REACT_APP_API_BASE_URL || '/api';
const instance = axios.create({ 
    baseURL, 
    headers: {
        'Content-Type': 'application/json',
          Accept: "application/json;charset=utf-8",
    },
    responseType: "json",
    transformResponse: [
        function (data) {
          // 确保数据以UTF-8编码处理
          if (typeof data === "string") {
            return JSON.parse(data);
          }
          return data;
        },
    ],

  });

// 请求拦截器
instance.interceptors.request.use(config => {
  // 自动添加 JWT token 到请求头
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, error => {
  return Promise.reject(error);
});

// 响应拦截器
instance.interceptors.response.use(response => {
  return response;
}, error => {
  // 统一错误处理
  if (error.response) {
    switch (error.response.status) {
      case 401:
        message.error('登录已过期，请重新登录');
        localStorage.removeItem('accessToken');
        localStorage.removeItem('refreshToken');
        // 可以在这里添加重定向到登录页的逻辑
        break;
      case 403:
        message.error('没有权限访问');
        break;
      case 500:
        message.error('服务器错误');
        break;
      default:
        message.error('请求失败');
    }
  } else {
    message.error('网络连接异常');
  }
  return Promise.reject(error);
});

export default instance;