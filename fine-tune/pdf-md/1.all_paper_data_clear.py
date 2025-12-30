import pandas as pd
import re
import textwrap
from openai import OpenAI
import logging
import nltk
# nltk.download('punkt')
# nltk.download('punkt_tab')
import sys
import os
import re
import fitz  # PyMuPDF
import pandas as pd
import json



import re

from nltk.tokenize import sent_tokenize

from utils import  retry_with_json,extract_pages,extract_text_layout,extract_text_from_scanned_pdf

API_KEY = "sk-e387e1a310824ad7ac7b84f6f82cd284"  # 或你的环境变量名
client = OpenAI(api_key=API_KEY, base_url="https://api.deepseek.com/v1")
MODEL_NAME="deepseek-reasoner"#"deepseek-chat"

# 配置日志输出到文件和控制台
log_formatter = logging.Formatter(
    "[%(asctime)s] %(levelname)s in %(module)s.%(funcName)s (line %(lineno)d): %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# 控制台日志
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(log_formatter)


PAPER_PDF_DIR = rf"C:\Users\54226\project\LLM_DATA\downloads"
DOOK_PDF_DIR=rf"C:\Users\54226\project\electrolyte_project\create_LLM_evluation_set\paper_download\book"
CONTENT_CSV_FILE=rf"C:\Users\54226\project\electrolyte_project\create_LLM_evluation_set\create_LLM_DATA\LLM_SFT_DATA\qa_sampling_plan_no_topic.csv"
MD_TEXT_DIR= rf"C:\Users\54226\project\electrolyte_project\create_LLM_evluation_set\create_LLM_DATA\LLM_SFT_DATA\paper_md_text"
PAIR_JSON_DIR=rf"C:\Users\54226\project\electrolyte_project\create_LLM_evluation_set\create_LLM_DATA\LLM_SFT_DATA\pair_json"
"""
总策略：
paper 和书  都先进行基础的DAPT级别的清洗，优先使用pdf库抽取文本，无法抽取文本的书用mathpix

之后进行SFT级别清洗
"""


def split_into_sentences(text: str):
    return sent_tokenize(text)


def LLM_judge_battery_research(text):
    prompt = r"""
    You are a scientific literature classification assistant.

Input: The first two pages of a research paper.

Task: Determine whether this paper is related to **battery research**, including battery systems, electrolytes, interfaces, additives, materials design, performance optimization, safety, and related topics.  
- Focus only on battery-related chemistry, materials, or engineering research.  
- Do NOT consider papers unrelated to batteries, such as general chemistry, physics, or medical studies.  

Output must be a **valid JSON object** with the following structure:

{
  "is_battery_related": true|false,   # true if related to battery research, false otherwise
  "reason": "short explanation (1-2 sentences)"
}

Do not output any other text outside this JSON object.

"""
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": text}
        ],

    )

    raw_output = response.choices[0].message.content
    return raw_output

def LLM_create_definition( text):
    prompt=r"""
You are a scientific research assistant. The following is the cleaned main text of an academic paper in the field of batteries (excluding the abstract and references):


Task: Based on this article, generate 3-5 question-answer pairs, where each question tests basic definitions or concepts.

Requirements:
- Questions should be concise, clear, and independently understandable.
- Answers should be short, complete sentences (1-3 sentences), and should not directly copy the text.
- Avoid using words like "this paper" or "the article"; the Q&A should be generalizable.

Output format (as JSON):
[
  {
    "question": "Your question here",
    "answer": "Your answer here"
  },
  {
    "question": "Another question",
    "answer": "Corresponding answer"
  }
]

    """
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": text}
        ],

    )
    raw_output = response.choices[0].message.content
    return raw_output

def extract_and_replace_special(text: str):
    """
    抽取 + 替换 特殊内容（公式 / 表格 / 图）
    返回：
    - cleaned_text: 带占位符的文本
    - context: dict 存储替换内容
    """
    context = {
        "formulas_inline": [],
        "formulas_block": [],
        "tables": [],
        "figures": []
    }

    # 1. inline LaTeX ($...$)
    for match in re.finditer(r"\$.*?\$", text):
        context["formulas_inline"].append(match.group())
    text = re.sub(r"\$.*?\$", "<FORMULA>", text)

    # 2. block LaTeX (\[...\])
    for match in re.finditer(r"\\\[.*?\\\]", text):
        context["formulas_block"].append(match.group())
    text = re.sub(r"\\\[.*?\\\]", "<FORMULA>", text)

    # 3. Table
    for match in re.finditer(r"Table \d+.*", text, flags=re.I):
        context["tables"].append(match.group())
    text = re.sub(r"Table \d+.*", "<TABLE>", text, flags=re.I)

    # 4. Figure
    for match in re.finditer(r"Figure \d+.*", text, flags=re.I):
        context["figures"].append(match.group())
    text = re.sub(r"Figure \d+.*", "<FIGURE>", text, flags=re.I)

    return text, context


def clean_text_for_dapt(raw_text: str, page_num,min_line_len: int = 15) -> str:
    """
    清洗 PDF 文本（DAPT级别）
    1. 去页眉页脚（频率 + 正则双保险）
    2. 合并断行 / 连字符
    3. 占位公式、图表、图片
    4. 特殊字符标准化
    5. 去尾部 References / 致谢
    6. 过滤过短内容
    """

    # 1. 按行拆分
    lines = [line.strip() for line in raw_text.split("\n") if line.strip()]

    # 2. 去掉 header/footer
    freq = {}
    for line in lines:
        freq[line] = freq.get(line, 0) + 1
    threshold=page_num*0.5
    common_lines = dict({(line, count) for line, count in freq.items() if count >= threshold})

    cleaned_lines = []
    for line in lines:
        if line in common_lines.keys():
            continue
        if re.match(r"^Page\s*\d+", line, re.I):
            continue
        if re.search(r"doi", line, re.I):
            continue
        if re.match(r"^\s*references?\s*$", line, re.I):
            continue
        if len(line) < min_line_len:
            continue
        cleaned_lines.append(line)

    # 3. 合并行（处理连字符断行）
    text = "\n".join(cleaned_lines)
    text = re.sub(r"-\n", "", text)   # 连字符断行
    text = re.sub(r"\n", " ", text)   # 普通换行变空格

    # 4. 占位符替换（公式/表格/图像）
    #
    # # 修正后的正则表达式
    # text = re.sub(r"\$.*?\$", "<FORMULA>", text)  # LaTeX inline
    # print(f"LaTeX inline处理后长度: {len(text)}")
    #
    # text = re.sub(r"\\\[.*?\\\]", "<FORMULA>", text)  # LaTeX block
    # print(f" LaTeX block处理后长度: {len(text)}")
    #
    # # 修正表格引用匹配 - 添加非贪婪匹配和边界限制
    # text = re.sub(r"Table \d+.*?(?=\n|$)", "<TABLE>", text, flags=re.I)
    # print(f"table 处理后长度: {len(text)}")
    #
    # # 修正图表引用匹配
    # text = re.sub(r"Figure \d+.*?(?=\n|$)", "<FIGURE>", text, flags=re.I)
    # print(f"figure 处理后长度: {len(text)}")

    # 5. 特殊字符标准化
    replacements = {
        "\u2013": "-",  # 短横线
        "\u2014": "-",  # 长横线
        "\u00a0": " ",  # 不间断空格
    }
    for old, new in replacements.items():
        text = text.replace(old, new)

    # 6. 去除尾部 References / 致谢
    ref_keywords = ["references", "bibliography", "acknowledgements", "acknowledgments", "funding"]
    pattern = re.compile(rf"\b({'|'.join(ref_keywords)})\b.*", re.IGNORECASE)
    text = pattern.split(text)[0]
    # print("len(text)",len(text))
    # for i,tmp in enumerate(text_list):
    #     print(rf"{i},{len( tmp)}")
    # 7. 去掉过短内容
    if len(text) < min_line_len:
        return ""

    #text_lines= textwrap.wrap(text, width=120, break_long_words=False, break_on_hyphens=False)
    text_lines=split_into_sentences( text)
    text="\n".join(text_lines)
    return text.strip()



def extract_text_from_pdf(pdf_path: str) -> str:
    doc = fitz.open(pdf_path)
    texts = []
    for page in doc:
        texts.append(page.get_text("text"))
    page_num=len(doc)
    return "\n".join(texts),page_num




import re

def extract_main_text_abstract_from_md(lines):
    """
    处理 Mathpix 转 PDF 的 Markdown 文件
    返回：
        main_text: 除 Abstract 外的正文
        abstract_text: Abstract 内容（可能为空）
    """

    abstract_lines = []
    main_lines = []

    in_abstract = False
    in_main = False

    # 正则匹配标题
    abstract_pattern = re.compile(r"^#+\s*abstract", re.I)
    tail_pattern = re.compile(r"^#+\s*(references|bibliography|acknowledgements|acknowledgments|funding)", re.I)
    header_pattern = re.compile(r"^#+\s+")

    for line in lines:
        # 抽象开始
        if abstract_pattern.match(line):
            in_abstract = True
            in_main = False
            continue

        # 尾部关键词 → 停止
        if tail_pattern.match(line):
            in_abstract = False
            in_main = False
            break

        # 普通标题切换逻辑
        if header_pattern.match(line):
            # abstract 结束，进入正文
            if in_abstract:
                in_abstract = False
                in_main = True
                main_lines.append(line)
                continue

        if in_abstract:
            abstract_lines.append(line)
        elif in_main:
            main_lines.append(line)

    abstract_text = "\n".join([l for l in abstract_lines if l.strip()])

    # # 如果没有抽象，重新扫描一次，只做 tail 截断
    # if abstract_text == "":
    #     main_lines = []
    #     for line in lines:
    #         if tail_pattern.match(line):
    #             break
    #         main_lines.append(line)


    return main_lines, abstract_text



def extract_figures_and_clean_text(lines):
    """
    输入：markdown文件的行列表
    输出：
        main_text: 去掉图片/图注后的正文
        figures: list[dict]，包含 {id, caption, url}
    """
    figures = []
    clean_lines = []

    image_pattern = re.compile(r"^!\[.*\]\((.*)\)")
    figure_pattern = re.compile(
        r"^\s*(?:Figure|Fig)\.?\s*(\d+[a-zA-Z]?)[:.]?\s*(.*)", re.I
    )
    """
    (?:Figure|Fig) ：匹配 Figure 或 Fig

    \.? ：可选点号
    
    (\d+[a-zA-Z]?) ：图号，可以是 1 或 1a
    
    [:.]? ：可选的冒号或点号
    
    (.*) ：剩余为 caption
    """
    skip_next = False
    for i, line in enumerate(lines):
        if skip_next:
            skip_next = False
            continue

        m = image_pattern.match(line.strip())
        if m:
            img_url = m.group(1).strip()

            # 找下一非空行
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1

            if j < len(lines):
                cap_line = lines[j].strip()
                m2 = figure_pattern.match(cap_line)
                if m2:  # 是图注
                    fig_id = f"Figure {m2.group(1)}"
                    caption = cap_line
                    figures.append({
                        "id": fig_id,
                        "caption": caption,
                        "url": img_url
                    })
                    skip_next = True  # 跳过 caption 行
                    continue

            # 如果不是 Figure caption，就保留图片行
            else:
                clean_lines.append(line)

        else:
            clean_lines.append(line)

    return clean_lines, figures


import re


def extract_tables_and_clean_text(lines):
    """
    输入: markdown文件行列表
    输出:
      main_text: 去掉表格后的正文
      tables: list[dict], 每个包含 {id, caption, content}
    """
    tables = []
    clean_lines = []

    table_caption_pattern = re.compile(r"^\s*Table\s+(\d+)\.?", re.I)

    i = 0
    while i < len(lines):
        line = lines[i].rstrip("\n")

        m = table_caption_pattern.match(line)
        if m:
            # 捕获 Table id & caption
            table_id = f"Table {m.group(1)}"
            caption = line.strip()
            content_lines = []

            # 收集后续表格行（| 开头 或者 注释行）
            j = i + 1
            while j < len(lines) and (
                    lines[j].strip().startswith("|") or lines[j].strip().startswith(":") or not lines[j].strip()):
                content_lines.append(lines[j].rstrip("\n"))
                j += 1

            tables.append({
                "id": table_id,
                "caption": caption,
                "content": "\n".join(content_lines).strip()
            })

            i = j  # 跳过表格段
            continue
        else:
            clean_lines.append(line)
            i += 1

    # main_text = "\n".join(clean_lines).strip()
    return clean_lines, tables


def clean_references(text: str) -> str:
    """
    删除文中引用：
    1. [1], [2,3], [4-6] 这种方括号形式
    2. ${ }^{8}$, ${ }^{9-11}$ 这种 LaTeX 上标形式
    """
    # 删除 [数字] 类引用
    text = re.sub(r"\[\s*\d+(?:[\s,\-–]\s*\d+)*\s*\]", "", text)

    # 删除 ${ }^{数字}$ 类引用
    text = re.sub(r"\$\{\s*\}\^\{[0-9,\-–]+\}\$", "", text)

    return text


def main():
    df=pd.read_csv(CONTENT_CSV_FILE)
    # 打乱行序，reset_index 丢弃原来的索引
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)
    for idx, row in df.iterrows():
        pdf_filename = row["pdf_filename"]
        json_filename = row["json_filename"]
        doi_filename_pref =json_filename[:-5]
        ori_md_filepath = os.path.join(MD_TEXT_DIR, doi_filename_pref+ ".md")
        cleared_md_filepath = os.path.join(MD_TEXT_DIR, doi_filename_pref+ "_cleared.md")
        pdf_path = os.path.join(PAPER_PDF_DIR, pdf_filename)
        qa_type=row["qa_type"]

        pair_json_filepath = os.path.join(PAIR_JSON_DIR, rf"{doi_filename_pref}_{qa_type}_{idx}.json")
        # if qa_type!="summary":
        #     continue
        if qa_type!="definition":
            continue
        if not os.path.exists(pdf_path):
            # print(f"[WARN] PDF not found: {pdf_file}")
            continue

        doc = fitz.open(pdf_path)
        texts = []
        for page in doc:
            texts.append(page.get_text("text"))
            if len(texts)==2:
                break
        first_2_page_text="\n".join(texts)

        if not os.path.exists(ori_md_filepath):

            judge_result_json = retry_with_json(LLM_judge_battery_research,
                                               first_2_page_text,max_retries=4)
            if judge_result_json["is_battery_related"]==False:
                with open(ori_md_filepath, "w", encoding="utf-8") as f:
                    judge_result_json["pdf_filename"]=pdf_filename
                    json.dump(judge_result_json, f, ensure_ascii=False, indent=4)
                continue
            else:
                md_text=extract_text_from_scanned_pdf(pdf_path=pdf_path,out_path=ori_md_filepath)


        if not os.path.exists(ori_md_filepath):
            continue
        # 如果是 json 文件就跳过
        try:
            json.load(open(ori_md_filepath))
            continue
        except:
            pass

        #if "10.1109_62.949535.md" in ori_md_filepath:
        #if "10.1149_1945-7111_ab7221" in ori_md_filepath:

        if not os.path.exists(cleared_md_filepath):
            with open(ori_md_filepath, "r", encoding="utf-8") as f:
                lines = [line.rstrip() for line in f]
            clean_lines, abstract_text = extract_main_text_abstract_from_md(lines)
            clean_lines, figures =extract_figures_and_clean_text(clean_lines)
            clean_lines, tables = extract_tables_and_clean_text(clean_lines)

            clean_lines.append("")
            clean_lines.append("## Figures")
            clean_lines.append("")
            for fig_data in figures:
                fig_id = fig_data["id"]
                fig_caption = fig_data["caption"]
                fig_url = fig_data["url"]
                clean_lines.append(f"{fig_caption}")
                clean_lines.append("")

            clean_lines.append("")
            clean_lines.append("## Tables")
            clean_lines.append("")
            for table_data in tables:
                table_id = table_data["id"]
                table_caption = table_data["caption"]
                table_content = table_data["content"]
                clean_lines.append(f"{table_caption}")
                clean_lines.append("")
                clean_lines.append(table_content)
                clean_lines.append("")

            clean_lines=[f"## Abstract {abstract_text.replace("\n","")}"]+clean_lines

            text="\n".join(clean_lines)
            text=clean_references(text)
            with open(cleared_md_filepath, "w", encoding="utf-8") as f:
                f.write(text)


        if not os.path.exists(cleared_md_filepath):
            continue
        text=open(cleared_md_filepath,"r",encoding="utf-8").read()
        if len(text.strip())<1000:
            continue



        if qa_type=="summary":

            with open(cleared_md_filepath, "r", encoding="utf-8") as f:
                # 从f中提取abstract 和main_text  首行为 abstract 其余行为 main_text
                abstract_line=next(f)
                main_text="".join([line for line in f])
                if "## Abstract" not in abstract_line:

                    print(f"[WARN] Abstract not found: {cleared_md_filepath}")

                abstract_text=abstract_line.replace("## Abstract","")

                pair_json_dict={
                    "instruction": "Summarize the paper",
                    "input": main_text,
                    "output":abstract_text,
                    "pdf_filename": pdf_filename,
                    "cleared_md_filepath": cleared_md_filepath,

                }
                with open(pair_json_filepath, "w", encoding="utf-8") as f:
                    json.dump(pair_json_dict, f, ensure_ascii=False, indent=4)
                print(f"[INFO] Summarize {pdf_filename} done.")

        elif qa_type=="definition":
            with open(cleared_md_filepath, "r", encoding="utf-8") as f:
                text=f.read()
                pair_json_r=retry_with_json(LLM_create_definition,text,max_retries=4)







main()