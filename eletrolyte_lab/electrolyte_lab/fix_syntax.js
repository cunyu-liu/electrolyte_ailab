const fs = require('fs');

// 读取文件
const filePath = 'D:\\electrolyte\\code\\frontend\\src\\pages\\AIExperimenterPage.tsx';
let content = fs.readFileSync(filePath, 'utf8');

// 修复第425行的模板字符串错误
content = content.replace(
  "message.error('RTSP视频流初始化失败: ${error.message}');",
  "message.error(`RTSP视频流初始化失败: ${error.message}`);"
);

// 写回文件
fs.writeFileSync(filePath, content, 'utf8');
console.log('Fixed template literal syntax error');