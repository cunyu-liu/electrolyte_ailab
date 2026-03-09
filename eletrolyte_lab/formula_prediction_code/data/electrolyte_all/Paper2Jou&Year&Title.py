import pandas as pd
import re

# 读取Excel文件
# 假设文件名为'input.xlsx'，请替换为你的实际文件名
df = pd.read_excel('D:\\2025\CE数据挖掘\\2014-2024\\analysis\data\electrolyte_all\electrolyte_all.xlsx')

# 新建三列
df['Journal'] = ''
df['Year'] = ''
df['Title'] = ''

# 遍历每一行处理Paper列
for idx, row in df.iterrows():
    paper_text = row['Paper']
    
    # 从Paper列中提取信息
    if isinstance(paper_text, str) and 'PDF\\' in paper_text:
        # 移除开头的'PDF\'
        paper_text = paper_text.replace('PDF\\', '', 1)
        
        # 使用正则表达式查找第一个'-'的位置
        match_journal = re.match(r'^(.*?)-', paper_text)
        if match_journal:
            journal = match_journal.group(1)
            df.at[idx, 'Journal'] = journal
            
            # 剩余部分
            remaining = paper_text[len(journal)+1:]
            
            # 查找年份 (假设年份是第二个分段，并且是4位数字)
            match_year = re.match(r'^(\d{4})-', remaining)
            if match_year:
                year = match_year.group(1)
                df.at[idx, 'Year'] = year
                
                # 剩余部分是标题，去掉结尾的.pdf
                title = remaining[len(year)+1:]
                if title.endswith('.pdf'):
                    title = title[:-4]
                df.at[idx, 'Title'] = title
            else:
                # 如果没有找到年份，则将剩余部分作为标题
                title = remaining
                if title.endswith('.pdf'):
                    title = title[:-4]
                df.at[idx, 'Title'] = title
        else:
            # 如果没有找到期刊，则整个文本(除了.pdf)作为标题
            title = paper_text
            if title.endswith('.pdf'):
                title = title[:-4]
            df.at[idx, 'Title'] = title

# 保存到新的Excel文件
df.to_excel('D:\\2025\CE数据挖掘\\2014-2024\\analysis\data\electrolyte_all\output.xlsx', index=False)
print("处理完成，新文件已保存为'output.xlsx'")