import { useState, useEffect } from 'react';
import { monitoringApi } from '../services/api';
import { MonitoringData } from '../types';

interface RealTimeMonitoringOptions {
  experimentId: number;
  formulaId: number;
  dataTypes?: string[];
  updateInterval?: number; // 秒
  autoConnect?: boolean;
}

export const useRealTimeMonitoring = ({
  experimentId,
  formulaId,
  dataTypes = ['charge_discharge', 'voltage', 'impedance', 'temperature'],
  updateInterval = 3,
  autoConnect = true
}: RealTimeMonitoringOptions) => {
  const [monitoringData, setMonitoringData] = useState<MonitoringData[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<string | null>(null);

  // 获取监控数据
  const loadMonitoringData = async () => {
    try {
      setIsLoading(true);
      setError(null);

      const response = await monitoringApi.getFormulaMonitoringData({
        experiment_id: experimentId,
        formula_id: formulaId,
        data_types: dataTypes,
        limit: 100
      });

      if (response.success && response.data) {
        setMonitoringData(response.data.monitoring_data);
        setLastUpdate(new Date().toISOString());
      }
    } catch (err) {
      console.error('获取监控数据失败:', err);
      setError('获取监控数据失败');
    } finally {
      setIsLoading(false);
    }
  };

  // 组件挂载时加载初始数据
  useEffect(() => {
    if (autoConnect) {
      loadMonitoringData();
    }
  }, [autoConnect, experimentId, formulaId, dataTypes]);

  // 定期刷新数据
  useEffect(() => {
    if (!autoConnect || isLoading) return;

    const interval = setInterval(() => {
      loadMonitoringData();
    }, updateInterval * 1000);

    return () => clearInterval(interval);
  }, [autoConnect, isLoading, loadMonitoringData, updateInterval]);

  // 手动刷新
  const refreshData = () => {
    loadMonitoringData();
  };

  return {
    // 数据
    monitoringData,

    // 状态
    isConnected,
    isLoading,
    error,
    lastUpdate,

    // 方法
    refreshData,

    // 计算属性
    hasData: monitoringData.length > 0,
    totalDataPoints: monitoringData.length
  };
};

export default useRealTimeMonitoring;