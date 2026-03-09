// 简化的跳转修复方案
// 如果当前的复杂逻辑有问题，可以使用这个简化版本

// 替换复杂的解析逻辑为：
const handleParseRequestSimple = async (values) => {
  setLoading(true);

  try {
    // 1. 优先使用基于规则解析
    const response = await parseRequestByRules(values.input);

    if (response.success && response.data) {
      // 2. 直接设置状态，不使用setTimeout
      setParsedParameters(response.data);
      setCurrentStep(1); // 立即跳转

      message.success('需求解析完成！');
      setUserInput(values.input);
    } else {
      message.error('解析失败，请重试');
    }
  } catch (error) {
    console.error('解析错误:', error);
    message.error('解析过程出错，请重试');
  }

  setLoading(false);
};

// 关键点：
// 1. 移除setTimeout延迟
// 2. 简化错误处理
// 3. 确保状态更新顺序正确