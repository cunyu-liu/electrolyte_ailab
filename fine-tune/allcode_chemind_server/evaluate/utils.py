
import logging
import time
import json
import fitz  # PyMuPDF
from pathlib import Path


from pypdf import PdfReader, PdfWriter
import pytesseract
from pdf2image import convert_from_path
import re


pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'



from openai import OpenAI
API_KEY = "sk-e387e1a310824ad7ac7b84f6f82cd284"  # 或你的环境变量名
client = OpenAI(api_key=API_KEY, base_url="https://api.deepseek.com/v1")
MODEL_NAME="deepseek-reasoner"#"deepseek-chat"
WWXQ_API_KEY="sk-yeqwxkqsinzddrwz"
WWXQ_MY_API_KEY="sk-2xoohlqxvrqwv6fq"
WWXQ_BASE_URL="https://cloud.infini-ai.com/maas/v1"
wwxq_client = OpenAI(api_key=WWXQ_MY_API_KEY, base_url=WWXQ_BASE_URL)


def check_pdf_type(pdf_path, min_chars=30):
    """
    判断 PDF 类型：文字版 / 扫描件 / 混合
    参数:
        pdf_path (str | Path): PDF 文件路径
        min_chars (int): 判定为文字页所需的最少字符数
    返回:
        str: "text", "scanned", "mixed"
    """
    pdf_path = Path(pdf_path)
    doc = fitz.open(pdf_path)
    text_pages = 0
    image_pages = 0
    total_pages = len(doc)

    for page in doc:
        text = page.get_text().strip()
        if len(text) >= min_chars:
            text_pages += 1
        elif page.get_images():
            image_pages += 1
    doc.close()

    if text_pages == total_pages:
        return "text"
    elif image_pages == total_pages:
        return "scanned"
    else:
        return "mixed"



def retry_with_json(func, *args, max_retries=2, retry_delay=0, length_check=None, **kwargs):
    """
    多次重试执行函数并解析 JSON。

    Args:
        func: 要执行的函数（返回字符串）。
        *args, **kwargs: 传给 func 的参数。
        max_retries: 最大重试次数。
        retry_delay: 重试之间的延迟（秒）。
        length_check: 如果传入一个 int，会检查解析结果长度是否匹配。

    Returns:
        解析后的 JSON 对象。

    Raises:
        ValueError: 超过重试次数仍解析失败。
    """
    for attempt in range(1, max_retries + 1):
        t = time.time()
        # with open(f"tmp", 'w', encoding="utf-8") as fp:
        #     fp.write(raw_output)
        try:
            raw_output = func(*args, **kwargs)
            logging.info(f"{func.__name__} took {time.time() - t:.2f} seconds (attempt {attempt}/{max_retries})")

            results = json.loads(clean_json_text(raw_output))

            if length_check is not None and len(results) != length_check:
                raise ValueError(f"Length mismatch: expected {length_check}, got {len(results)}")

            return results  # 成功解析，直接返回

        except Exception as e:
            logging.error(f"Error parsing JSON from {func.__name__} (attempt {attempt}/{max_retries}): {e}")
            try:
                logging.error(f"Raw output: {raw_output}")
            except:
                pass
            import random
            r=str(random.random())[:5]
            try:
                with open(f"tmp_{r}", 'w', encoding="utf-8") as fp:
                    fp.write(raw_output)
            except:
                pass
            if attempt >= max_retries:
                raise ValueError(f"{func.__name__} failed after max retries") from e

            if retry_delay > 0:
                time.sleep(retry_delay)

    # 理论上不会走到这里
    raise ValueError(f"{func.__name__} failed unexpectedly")



def clean_json_text(text: str) -> str:
    """
    进行了深度的修复应该可以应对各种转义
    提取 JSON 部分并清理 Markdown、全角引号及非法引号问题
    新增反斜杠转义处理
    """
    # 去掉 Markdown 代码块标记
    text = text.strip()
    text = re.sub(r"^```json\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^```", "", text)
    text = re.sub(r"```$", "", text)

    # 提取 JSON 主体
    json_match = re.search(r'(\{.*\}|\[.*\])', text, flags=re.DOTALL)
    if not json_match:
        raise ValueError("❌ 文本中未找到 JSON 部分")
    json_text = json_match.group(0)

    # 删除 ASCII 控制字符 (0x00 - 0x1F), 保留 \n \r \t
    json_text = re.sub(r'\\x[0-9a-fA-F]{2}', '', json_text)

    # 修复全角引号
    json_text = json_text.replace("“", r'\"').replace("”", r'\"').replace("‘", "'").replace("’", "'")

    # 新增：处理反斜杠转义问题
    def escape_backslashes_in_strings(match):
        """处理字符串值中的反斜杠"""
        string_content = match.group(1)
        # 转义反斜杠，但保留已转义的序列（如 \n, \t 等）
        # 匹配未转义的反斜杠（前面没有反斜杠的反斜杠）
        string_content = re.sub(r'(?<!\\)\\(?![\\"bfnrtu])', r'\\\\', string_content)
        return '"' + string_content + '"'

    # 处理所有JSON字符串中的反斜杠
    json_text = re.sub(r'"([^"\\]*(?:\\.[^"\\]*)*)"', escape_backslashes_in_strings, json_text)

    # 修复非法的内部引号（不影响已转义的 \")
    def escape_inner_quotes(match):
        inner = match.group(1)
        # 只替换未转义的 "
        fixed_inner = re.sub(r'(?<!\\)"', r'\"', inner)
        return '"' + fixed_inner + '"'

    json_text = re.sub(r'"([^"\\]*(?:\\.[^"\\]*)*)"', escape_inner_quotes, json_text)

    return json_text


def extract_text_layout(pdf_path):
    doc = fitz.open(pdf_path)
    all_text = []
    for page in doc:
        text = page.get_text("text", sort=True)  # 自动排序
        all_text.append(text)
    return "\n\n".join(all_text)



def extract_pages(input_path, output_path, page_numbers):
    """
    从输入的PDF中提取指定页面并保存为新的PDF文件。

    Args:
        input_path (str): 输入的PDF文件路径。
        output_path (str): 输出的新PDF文件路径。
        page_numbers (list): 要提取的页码列表，从0开始索引。
                            例如 [0, 2, 4, 5, 6] 表示第1, 3, 5, 6, 7页。
    """
    # 初始化PDF读取器和写入器
    pdf_reader = PdfReader(input_path)
    pdf_writer = PdfWriter()

    # 获取总页数，用于验证输入的页码是否有效
    total_pages = len(pdf_reader.pages)
    print(f"文档总页数: {total_pages}")

    # 遍历指定的页码列表，将对应的页面添加到写入器
    for page_num in page_numbers:
        # 检查页码是否有效
        if page_num < 0 or page_num >= total_pages:
            print(f"警告: 页码 {page_num} 无效，已跳过。")
            continue
        # 获取页面对象并添加到写入器
        page = pdf_reader.pages[page_num]
        pdf_writer.add_page(page)
        print(f"已添加第 {page_num + 1} 页。")

    # 将添加的所有页面写入到新的PDF文件中
    with open(output_path, 'wb') as output_file:
        pdf_writer.write(output_file)

    print(f"成功！新PDF已保存至: {output_path}")


import cv2
import numpy as np

def detect_formula_regions(image):
    """检测可能包含公式的区域"""
    # 转换为OpenCV格式
    open_cv_image = np.array(image)
    open_cv_image = open_cv_image[:, :, ::-1].copy()  # RGB to BGR

    # 简单的基于连通组件的方法
    gray = cv2.cvtColor(open_cv_image, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # 查找轮廓
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    formula_regions = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        # 过滤太小或太大的区域
        if 50 < w < 500 and 20 < h < 200:
            formula_regions.append((x, y, w, h))

    return formula_regions


from PIL import Image, ImageEnhance, ImageFilter


def preprocess_image(image):
    """增强图像质量以提高OCR精度"""
    # 增强对比度
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(2.0)

    # 增强锐度
    enhancer = ImageEnhance.Sharpness(image)
    image = enhancer.enhance(2.0)

    # 二值化处理（可选）
    # image = image.convert('L').point(lambda x: 0 if x < 128 else 255, '1')

    return image


#def extract_text_from_scanned_pdf(pdf_path,eng_only=False):
    # """
    # 提取扫描PDF中的文本，针对电化学内容优化
    # """
    # try:
    #     # 将PDF转换为高分辨率图像
    #     images = convert_from_path(
    #         pdf_path,
    #         dpi=400,
    #         poppler_path=r'C:\poppler-25.07.0\Library\bin',
    #         grayscale=True,
    #         thread_count=4
    #     )
    #
    #     full_text_raw=""
    #     for i, image in enumerate(images):
    #         print(f"正在处理第 {i + 1} 页...")
    #
    #         # 使用中英文混合识别
    #         custom_config = r'--oem 3 --psm 6'
    #
    #         if eng_only:
    #             raw_text = pytesseract.image_to_string(image, config=custom_config, lang='eng')
    #         else:
    #             raw_text = pytesseract.image_to_string(image, config=custom_config, lang='chi_sim+eng')
    #
    #
    #         full_text_raw += f"{raw_text}\n"
    #
    #
    #         if (i + 1) % 5 == 0:
    #             print(f"已处理 {i + 1} 页")
    #
    #     return full_text_raw
    #
    # except Exception as e:
    #     print(f"处理错误: {e}")
    #     return None



import os
from mpxpy.mathpix_client import MathpixClient
from mpxpy.errors import ConversionIncompleteError


def extract_text_from_scanned_pdf(pdf_path, eng_only=False, timeout=120, out_path=None):
    """
    提取扫描 PDF 文本（通过 Mathpix OCR API 转换为 Markdown）

    Args:
        pdf_path (str): 本地 PDF 文件路径
        eng_only (bool): 是否只保留英文（简单过滤）
        timeout (int): 等待 Mathpix 处理的最大秒数
        out_path (str): 保存的 Markdown 文件路径

    Returns:
        str | None: Markdown 文本（如果成功），否则 None
    """
    from mpxpy.mathpix_client import MathpixClient
    mathpix_APP_ID = "tsinghua_d0198f_662cf4"
    mathpix_API_KEY = "f4790fbc09c69adc99059f9a96109e00994a5626ab539c9bd4588d0fadac64fe"

    client = MathpixClient(app_id=mathpix_APP_ID, app_key=mathpix_API_KEY)

    try:
        if not os.path.exists(pdf_path):
            print(f"❌ 文件不存在: {pdf_path}")
            return None

        # 上传 PDF
        pdf = client.pdf_new(
            file_path=pdf_path,
            convert_to_md=True,
        )

        # 等待处理
        if not pdf.wait_until_complete(timeout=timeout):
            print("❌ PDF 转换失败或超时")
            return None

        # 导出 Markdown
        if out_path is not None:
            md_output_path = pdf.to_md_file(path=out_path)
            print(f"✅ Markdown 已保存: {md_output_path}")

        md_text = pdf.to_md_text() or ""
        if eng_only:
            md_text = "\n".join([line for line in md_text.splitlines() if any(c.isalpha() for c in line)])

        return md_text

    except ConversionIncompleteError:
        print("❌ 转换未完成，无法导出 Markdown")

    except Exception as e:
        print(f"❌ 未知错误: {e}")

    return None


if __name__ == "__main__":
    pdf_file = r"C:\Users\54226\project\electrolyte_project\create_LLM_evluation_set\paper_download\extraction_question_from_book\《电化学原理》(第三版)李荻_第0章习题.pdf"
    text = extract_text_from_scanned_pdf(pdf_file, eng_only=False)

    if text:
        print("\n--- Markdown 预览 ---")
        print(text[:800])  # 打印前 800 字
