# 详细发票处理参考

这是旧版完整工作流的实现参考。优先遵循上级 `SKILL.md` 的隐私、配对和验证规则。

## 适用场景
- 批量 OCR 识别发票 PDF 文件
- 自动分类：火车票、飞机票、退票费、住宿、租车、加油、餐饮、打车、其他
- 按实际时间排序，生成 Excel 汇总表
- 识别行程闭环，按行程归档 PDF 文件
- 自动计算行程金额并填充公司差旅费明细表模板

## 前置条件

### 环境依赖
```bash
pip install pandas openpyxl pdf2image requests pillow xlsxwriter
```

### PDF 转图片依赖 (仅 LM Studio 方案需要)
- **pdf2image**: 需下载 poppler 二进制文件并配置 PATH
- **LM Studio**: 需启动并加载 GLM-OCR 模型 (推荐 GLM-4V-Flash)

### 文件准备
- **模板文件**: `材料、测试加工、差旅费及其他费用明细表.xlsx` (需确保差旅费明细表在第二个 Sheet)

---

## 支持的 OCR 方案

### 方案1: PaddleOCR API (推荐)
| 项目 | 说明 |
|------|------|
| 优点 | 在线识别，无需本地显卡，直接支持 PDF 文件上传 |
| API | `https://1cnab717k5sfp2x0.aistudio-app.com/layout-parsing` |
| Token | 从环境变量 `PADDLEOCR_TOKEN` 读取 |
| 输出格式 | `result["layoutParsingResults"][i]["markdown"]["text"]` |

### 方案2: LM Studio + GLM-OCR
| 项目 | 说明 |
|------|------|
| 优点 | 本地运行，数据隐私性好 |
| API | `http://localhost:1234/v1/chat/completions` |
| 输出格式 | `choices[0]["message"]["content"]` |
| 缺点 | 需手动转换 PDF 为图片，速度较慢 |

---

## 操作步骤

### 第一步：OCR 识别与数据标准化

#### 1.1 PaddleOCR API 实现 (推荐)
直接上传 PDF，无需转换图片。

```python
import base64
import requests
import os
import json

def ocr_with_paddle_api(file_path, output_dir):
    """使用 PaddleOCR API 识别发票"""
    with open(file_path, "rb") as file:
        file_data = base64.b64encode(file.read()).decode("ascii")

    file_type = 0 if file_path.lower().endswith(".pdf") else 1

    headers = {
        "Authorization": f"token {os.environ['PADDLEOCR_TOKEN']}",
        "Content-Type": "application/json"
    }

    payload = {
        "file": file_data,
        "fileType": file_type,
        "useDocOrientationClassify": False,
        "useDocUnwarping": False,
        "useChartRecognition": False,
    }

    response = requests.post(
        "https://1cnab717k5sfp2x0.aistudio-app.com/layout-parsing",
        json=payload, headers=headers, timeout=120
    )

    assert response.status_code == 200, f"API Error: {response.status_code}"
    result = response.json().get("result", {})

    all_text = []
    for res in result.get("layoutParsingResults", []):
        all_text.append(res.get("markdown", {}).get("text", ""))

    full_text = "\n\n".join(all_text)

    json_path = os.path.join(output_dir, os.path.basename(file_path).rsplit(".", 1)[0] + ".json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"text": full_text}, f, ensure_ascii=False, indent=2)

    return json_path
```

#### 1.2 LM Studio 本地实现
需先 PDF 转图片。

```python
import requests
from pdf2image import convert_from_path
import base64
import os
import json

def ocr_with_lm_studio(pdf_path, output_dir):
    images = convert_from_path(pdf_path, dpi=200)
    pil_image = images[0]

    temp_img = os.path.join(output_dir, "temp.png")
    pil_image.save(temp_img)

    with open(temp_img, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()

    payload = {
        "model": "glm-ocr",
        "messages": [
            {"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
                {"type": "text", "text": "请提取这张发票的所有信息..."}
            ]}
        ]
    }

    response = requests.post("http://localhost:1234/v1/chat/completions", json=payload, timeout=120)
    result = response.json()

    content = result["choices"][0]["message"]["content"]

    json_path = os.path.join(output_dir, os.path.basename(pdf_path).replace(".pdf", ".json"))
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"text": content}, f, ensure_ascii=False, indent=2)

    os.remove(temp_img)
    return json_path
```

---

### 第二步：解析 OCR 结果 (核心逻辑)

此步骤包含对火车票 HTML 表格、退票费的特殊处理。

```python
import re
import json

def parse_ocr_result(json_path):
    """解析 JSON，提取关键信息，兼容不同 OCR 来源"""
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "choices" in data:
        content = data["choices"][0]["message"]["content"]
    else:
        content = data.get("text", "")

    is_train = "<table>" in content or "电子客票" in content or "铁路" in content

    # 1. 退票费判定 (必须在火车票之前)
    if is_train and ("退票" in content or "退票费" in content):
        return parse_train_refund(content)

    # 2. 火车票判定
    if is_train and ("客票" in content or "票价" in content):
        return parse_train_ticket(content)

    # 3. 标准发票解析 (住宿、餐饮、机票等)
    return parse_standard_invoice(content)

def parse_train_ticket(content):
    """解析铁路电子客票 (处理 HTML 格式)"""
    info = {"类型": "火车票", "原始内容": content}

    # 发票号码 - 处理 HTML 标签干扰
    match = re.search(r'发票号码[：:]?</?\w*>\s*<?\w*>?\s*(\d+)', content)
    if not match:
        match = re.search(r'发票号码[：:]?\s*(\d{20})', content)
    info["发票代码"] = match.group(1) if match else ""

    # 日期处理 (两个日期：开票日期 + 乘车日期)
    all_dates = re.findall(r'(\d{4})年(\d{1,2})月(\d{1,2})日', content)
    if all_dates:
        info["开票日期"] = f"{all_dates[0][0]}/{all_dates[0][1].zfill(2)}/{all_dates[0][2].zfill(2)}"
        if len(all_dates) >= 2:
            date_str = f"{all_dates[1][0]}/{all_dates[1][1].zfill(2)}/{all_dates[1][2].zfill(2)}"
            time_match = re.search(r'(\d{1,2}):(\d{1,2})开', content)
            if time_match:
                info["实际时间_temp"] = f"{date_str} {time_match.group(1).zfill(2)}:{time_match.group(2).zfill(2)}"
            else:
                info["实际时间_temp"] = date_str

    # 金额
    match = re.search(r"票价[：:]?\s*[¥￥]?\s*(\d+\.?\d*)", content)
    info["金额"] = float(match.group(1)) if match else 0

    # 车站与车次 (通用正则提取站点)
    stations = re.findall(r'([^\n<>]+站)', content)
    if len(stations) >= 2:
        dep_raw = stations[0].replace("站", "").strip()
        arr_raw = stations[1].replace("站", "").strip()
        # 去除车次前缀 (G460南京南 -> 南京南)
        info["出发地"] = re.sub(r'^[GDCTZK\d]+', '', dep_raw).strip()
        info["目的地"] = re.sub(r'^[GDCTZK\d]+', '', arr_raw).strip()

    match = re.search(r'([GDCTZK]\d+)', content)
    info["车次"] = match.group(1) if match else ""
    info["销售方"] = "中国铁路"
    return info

def parse_train_refund(content):
    """解析铁路退票费"""
    info = {"类型": "退票费", "原始内容": content}

    # 发票号码
    match = re.search(r"发票号码[：:]\s*(\d+)", content)
    info["发票代码"] = match.group(1) if match else ""

    # 日期 (退票费通常只有一个日期)
    match = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", content)
    if match:
        dt = f"{match.group(1)}/{match.group(2).zfill(2)}/{match.group(3).zfill(2)}"
        info["开票日期"] = dt
        info["实际时间_temp"] = dt

    # 金额
    match = re.search(r"退票费[：:]?\s*[¥￥]?\s*(\d+\.?\d*)", content)
    info["金额"] = float(match.group(1)) if match else 0

    # 提取站点 - 退票费格式: 汉中站 ... G686 ... 西安北站
    # 注意: 必须用 re.sub 去除车次前缀 (如 G686汉中站 -> 汉中)
    stations = re.findall(r'([^\n<>]+站)', content)
    if len(stations) >= 2:
        dep_raw = stations[0].replace("站", "").strip()
        arr_raw = stations[1].replace("站", "").strip()
        info["出发地"] = re.sub(r'^[GDCTZK\d]+', '', dep_raw).strip()
        info["目的地"] = re.sub(r'^[GDCTZK\d]+', '', arr_raw).strip()

    return info

def parse_standard_invoice(content):
    """解析标准发票 (住宿、餐饮、机票)"""
    info = {"原始内容": content}

    # 发票号码
    match = re.search(r"发票号码[：:]\s*(\d+)", content)
    info["发票代码"] = match.group(1) if match else ""

    # 开票日期
    match = re.search(r"开票日期[：:]\s*(\d{4})年(\d{1,2})月(\d{1,2})日", content)
    if match:
        info["开票日期"] = f"{match.group(1)}/{match.group(2).zfill(2)}/{match.group(3).zfill(2)}"

    # 金额 (优先级: 退票费 > (小写) > 价税合计 > 合计 > 普通)
    # 注意: 退票费必须放在最前面，否则会被"价税合计"误匹配
    amount = re.search(r"退票费[：:]?\s*[¥￥]?\s*(\d+\.?\d*)", content)
    if not amount: amount = re.search(r"[（(]小写[）)]¥\s*(\d+\.?\d*)", content)
    if not amount: amount = re.search(r"价税合计.*?[¥￥]\s*(\d+\.?\d*)", content)
    if not amount: amount = re.search(r"合\s*计.*?(\d+\.?\d*)", content)
    if not amount: amount = re.search(r"¥\s*(\d+\.?\d*)", content)
    info["金额"] = float(amount.group(1)) if amount else 0

    # 销售方
    match = re.search(r"销售方信息.*?名称[:：]\s*([^\n]+)", content)
    info["销售方"] = match.group(1).strip() if match else ""

    # 备注
    match = re.search(r"备注\s*(.+?)(?=\n\n|\n*$|$)", content, re.DOTALL)
    info["备注"] = match.group(1).strip() if match else ""

    # 飞机票特殊处理
    if "代订机票" in content or "机票代理" in content:
        info["类型"] = "飞机票"
        # 从备注中提取路线信息，处理HTML标签
        remark_text = info["备注"]
        # 移除HTML标签 (携程发票备注含 <td> 标签)
        remark_text = re.sub(r'<[^>]+>', ' ', remark_text)
        # 匹配格式: 2026/3/25 武汉-西安 CA8219
        route = re.search(r'(\d{4})/(\d{1,2})/(\d{1,2})\s+([^\s]+)-([^\s]+)', remark_text)
        if route:
            info["出发地"] = route.group(4)
            info["目的地"] = route.group(5)
            info["航班号"] = re.search(r'([A-Z]{2}\d+)', remark_text).group(1) if re.search(r'([A-Z]{2}\d+)', remark_text) else ""

    return info
```

---

### 第三步：分类与实际时间提取

#### 3.1 分类规则
```python
def classify_invoice(info):
    content = info["原始内容"]
    seller = info.get("销售方", "")
    filename = info.get("文件名", "")
    # 优先级：退票 > 火车 > 飞机 > 住宿 > 租车 > 加油 > 餐饮 > 打车 > 其他
    if info.get("类型") == "退票费": return "退票费"
    if "退票" in content: return "退票费"
    if "铁路" in content or "电子客票" in content or "票价" in content: return "火车票"
    if "代订机票" in content or "机票代理" in content: return "飞机票"
    if "航空运输电子客票行程单" in content: return "飞机票"
    # 加油/租车检测 (优先)
    if "汽油" in content or "柴油" in content or "油品" in content or "加油站" in seller: return "加油"
    if "租车" in content or "租赁" in content or "神州" in seller or "一嗨" in seller: return "租车"
    if "酒店" in seller or "住宿" in content or "赫程" in seller: return "住宿"
    if "餐饮" in content or "餐费" in content: return "餐饮"
    if "打车" in filename or "的士" in filename or "滴滴" in content: return "打车"
    return "其他"
```

#### 3.2 实际时间提取
```python
def extract_actual_time(info):
    # 1. 火车票/退票费优先使用解析时的临时字段
    if info.get("实际时间_temp"): return info["实际时间_temp"]

    inv_type = info.get("类型", "")
    remark = info.get("备注", "")

    # 2. 住宿 (备注中的入住日期)
    if inv_type == "住宿" and remark:
        match = re.search(r"(\d{4})/(\d{1,2})/(\d{1,2})\s*[-–]", remark)
        if match: return f"{match.group(1)}/{match.group(2).zfill(2)}/{match.group(3).zfill(2)}"

    # 3. 飞机票 (备注中的乘机日期)
    if inv_type == "飞机票" and remark:
        match = re.search(r"(\d{4})/(\d{1,2})/(\d{1,2})", remark)
        if match: return f"{match.group(1)}/{match.group(2).zfill(2)}/{match.group(3).zfill(2)}"

    # 4. 默认使用开票日期
    return info.get("开票日期", "")
```

---

### 第四步：多级排序与 Excel 生成

**关键点**：使用 `xlsxwriter` 并显式转换字符串以防止科学计数法。

```python
import pandas as pd

TYPE_PRIORITY = {"火车票": 1, "飞机票": 2, "退票费": 3, "住宿": 4, "租车": 5, "加油": 6, "餐饮": 7, "打车": 8, "其他": 9}

def get_sort_key(inv):
    t = inv.get("实际时间", "")
    if not t: t = inv.get("开票日期", "9999/99/99")

    sort_time = t.replace(" ", "T")
    if "T" not in sort_time: sort_time += "T00:00"

    return (
        sort_time.split("T")[0],
        TYPE_PRIORITY.get(inv.get("类型"), 6),
        sort_time,
        inv.get("出发地", ""),
        inv.get("金额", 0)
    )

def generate_excel(invoices, output_path):
    invoices.sort(key=get_sort_key)

    for i, inv in enumerate(invoices, 1): inv["序号"] = i

    df = pd.DataFrame(invoices)
    cols = ["序号", "类型", "发票代码", "开票日期", "实际时间", "出发地", "目的地", "车次", "金额", "销售方", "文件名"]
    df = df[[c for c in cols if c in df.columns]]

    # 关键：解决发票代码科学计数法问题
    df["发票代码"] = df["发票代码"].astype(str)

    with pd.ExcelWriter(output_path, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="发票汇总")

        workbook = writer.book
        text_format = workbook.add_format({'num_format': '@'})
        worksheet = writer.sheets['发票汇总']
        worksheet.set_column('C:C', 25, text_format)
```

---

### 第五步：PDF 文件按行程分类归档

#### 5.1 行程识别算法 (闭环逻辑)

除下方识别算法外，归档后必须执行行程完整性检查：

1. **交通闭环检查**
   - 必须有从基地出发和返回基地的实际火车票或飞机票。
   - 检查相邻交通段能否按城市和日期衔接；缺少去程、回程或存在路线断点时标记 `未闭环`。
   - 退票费、保险、订票服务费和开票记录不能作为实际交通段补齐闭环。
2. **住宿逐晚检查**
   - 跨日行程的应覆盖住宿夜为 `[出发日期, 返程日期)`，即出发日至返程日前一晚；当天往返无应覆盖住宿夜。
   - 住宿凭证按入住日（含）至离店日（不含）覆盖住宿夜，逐晚比较后列出所有缺失日期。
   - 只有开票日期而没有入住/离店区间时，标记该住宿及对应日期 `待复核`，不能自动判定住宿齐全。
   - 夜间火车或夜间航班只有在时间明确且覆盖该晚时，记录为 `夜间交通（待人工确认）`，不能自动消除提醒。
3. **提醒与输出**
   - 交通或住宿任一检查不通过，文件夹名称追加 `_未闭环`。
   - 汇总表和处理报告增加 `完整性状态`、`交通问题`、`缺少住宿日期`、`待复核事项` 字段。
   - 最终向用户逐个报告未闭环行程及原因；不得只在文件夹名中隐含异常。

**关键修复 (v3.0)**:
- `CITY_MAPPING` 必须包含不带"站"后缀的站名 (如 "汉口"、"武昌")，因为正则提取时会去掉"站"字
- 增加 `last_trip` 追踪，处理行程结束后出现的住宿/餐饮发票
- 处理非基地出发的中途交通票 (如退票费)

```python
# 城市映射表 (将具体车站映射到城市)
# 注意: 必须同时包含带"站"和不带"站"的版本!
# 因为 parse_train_ticket 中 stations = re.findall(r'([^\n<>]+站)', content)
# 然后 dep_raw = stations[0].replace("站", "").strip() 会去掉"站"字
CITY_MAPPING = {
    '武汉': ['武汉', '武汉站', '汉口', '汉口站', '武昌', '武昌站'],
    '三亚': ['三亚'],
    '南京': ['南京南', '南京'],
    '成都': ['成都'],
    '西安': ['西安', '西安北', '西安站'],
    '郑州': ['郑州东', '郑州'],
    '北京': ['北京西', '北京'],
    '上海': ['上海', '上海虹桥'],
    '汉中': ['汉中'],
}

def get_city(station):
    """将车站名称映射为城市"""
    if not station: return None
    for city, stations in CITY_MAPPING.items():
        if station in stations: return city
    return station

def identify_trips(invoices):
    """识别行程闭环"""
    trips = []
    current_trip = None
    last_trip = None  # 追踪最后一个已完成的行程，用于处理孤儿发票

    for inv in invoices:
        inv_type = inv.get("类型")

        if inv_type in ["火车票", "飞机票", "退票费"]:
            dep = inv.get("出发地", "")
            arr = inv.get("目的地", "")
            dep_city = get_city(dep)
            arr_city = get_city(arr)

            is_from_base = dep_city in ["武汉", "三亚"]
            is_to_base = arr_city in ["武汉", "三亚"]

            if is_from_base:
                # 从基地出发 -> 新行程开始
                if current_trip:
                    trips.append(current_trip)
                current_trip = {
                    "start_date": inv.get("实际时间", "").split(" ")[0],
                    "start_location": dep,
                    "end_location": arr,
                    "cities": [dep_city, arr_city],
                    "invoices": [inv],
                    "closed": False
                }
            elif current_trip:
                # 行程中
                current_trip["invoices"].append(inv)
                current_trip["end_location"] = arr
                current_trip["cities"].append(arr_city)

                if is_to_base:
                    # 回到基地 -> 行程结束
                    current_trip["closed"] = True
                    trips.append(current_trip)
                    last_trip = current_trip
                    current_trip = None
            else:
                # 非基地出发的交通票且无当前行程 -> 归入上一个行程
                if last_trip:
                    last_trip["invoices"].append(inv)
                    last_trip["cities"].append(arr_city)
                    if is_to_base:
                        last_trip["closed"] = True

        elif inv_type in ["住宿", "租车", "加油", "餐饮", "打车"]:
            if current_trip:
                current_trip["invoices"].append(inv)
            elif last_trip:
                # 行程结束后的住宿/餐饮/租车/加油/打车 -> 归入最后一个行程
                last_trip["invoices"].append(inv)

    if current_trip:
        trips.append(current_trip)

    return trips
```

#### 5.2 文件夹命名与归档逻辑

命名规则:
- 文件夹: `{起始日期}至{结束日期}_{城市路径}[_未闭环]`
- 文件: `{YYYYMMDD}-{类型}-{出发地}-{目的地}-{金额}.pdf`
- 住宿/餐饮: `{YYYYMMDD}-{类型}-{金额}.pdf`

**关键修复 (v3.0)**:
- `unique_cities` 必须过滤 `None` 值 (退票费可能没有出发地/目的地)
- 归档前清理旧文件夹，避免重复

```python
import shutil
import re
import glob

def archive_pdfs_by_trip(trips, source_dir, output_base_dir):
    """按行程归档 PDF 文件"""

    pdf_files = glob.glob(os.path.join(source_dir, "*.pdf"))

    for trip in trips:
        start_date = trip["start_date"].replace("/", "")
        end_date = trip["invoices"][-1]["实际时间"].split(" ")[0].replace("/", "")

        # 注意: 必须过滤 None 值!
        unique_cities = []
        for c in trip["cities"]:
            if c and c not in unique_cities:
                unique_cities.append(c)
        route_str = "-".join(unique_cities)

        folder_name = f"{start_date}至{end_date}_{route_str}"
        if not trip["closed"]:
            folder_name += "_未闭环"

        trip_folder = os.path.join(output_base_dir, folder_name)
        os.makedirs(trip_folder, exist_ok=True)

        for inv in trip["invoices"]:
            json_name = inv.get("文件名", "")
            pdf_name = json_name.replace(".json", ".pdf").replace("-电子发票", "")
            src_pdf = os.path.join(source_dir, pdf_name)

            if not os.path.exists(src_pdf):
                base_prefix = json_name.split("-")[0]
                matches = [f for f in pdf_files if os.path.basename(f).startswith(base_prefix)]
                if matches: src_pdf = matches[0]
                else:
                    print(f"  [警告] 未找到 PDF: {json_name}")
                    continue

            actual_time = inv.get("实际时间", "")
            date_part = actual_time.split(" ")[0].replace("/", "") if actual_time else "00000000"
            inv_type = inv.get("类型", "其他")
            amount = inv.get("金额", 0)

            if inv_type in ["住宿", "餐饮"]:
                new_filename = f"{date_part}-{inv_type}-{amount:.2f}.pdf"
            else:
                dep = inv.get("出发地", "")
                arr = inv.get("目的地", "")
                dep = re.sub(r'[\\/:*?"<>|]', '', dep)
                arr = re.sub(r'[\\/:*?"<>|]', '', arr)
                new_filename = f"{date_part}-{inv_type}-{dep}-{arr}-{amount:.2f}.pdf"

            dst_pdf = os.path.join(trip_folder, new_filename)
            shutil.copy2(src_pdf, dst_pdf)
            print(f"  归档: {new_filename} -> {folder_name}")
```

---

### 第六步：自动填写差旅费明细表模板

#### 6.1 填写规则
- **差旅金额 (E列)**: 仅包含 **火车票、飞机票、住宿**
  - 格式: `交通: 路线金额+...; 住宿: 金额+...`
- **其他金额 (F列)**: 仅包含 **餐饮、打车、退票费**
  - 格式: `餐饮: 金额+...; 退票: 金额+...`
- **出差人员 (D列)**: 留空
- **起止时间 (C列)**: 支持换行显示 (`\n`)

#### 6.2 数据准备逻辑

```python
def format_travel_amount(items):
    """格式化差旅金额字符串"""
    parts = []
    trans_items = [i for i in items if i['type'] in ['火车票', '飞机票']]
    hotel_items = [i for i in items if i['type'] == '住宿']

    if trans_items:
        trans_str = "+".join([f"{i['route']}{i['amount']}" for i in trans_items])
        parts.append(f"交通: {trans_str}")

    if hotel_items:
        hotel_str = "+".join([str(i['amount']) for i in hotel_items])
        parts.append(f"住宿: {hotel_str}")

    return "; ".join(parts)

def format_other_amount(items):
    """格式化其他金额字符串"""
    parts = []
    # 餐饮、打车、租车、加油、退票费都放入"其他金额"
    other_items = [i for i in items if i['type'] in ['餐饮', '打车', '租车', '加油', '退票费']]
    
    if other_items:
        # 按类型分组
        type_groups = {}
        for item in other_items:
            t = item['type']
            if t not in type_groups: type_groups[t] = []
            type_groups[t].append(str(item['amount']))
        
        for t, amounts in type_groups.items():
            if t == '餐饮': parts.append(f"餐饮: {'+'.join(amounts)}")
            elif t == '打车': parts.append(f"打车: {'+'.join(amounts)}")
            elif t == '租车': parts.append(f"租车: {'+'.join(amounts)}")
            elif t == '加油': parts.append(f"加油: {'+'.join(amounts)}")
            elif t == '退票费': parts.append(f"退票: {'+'.join(amounts)}")
    
    return "; ".join(parts)
```

#### 6.3 openpyxl 操作实现

```python
import openpyxl
from openpyxl.styles import Font, Alignment, Border, Side

def fill_travel_expense_template(trips_data, template_path, output_path):
    """填写差旅费明细表模板"""

    wb = openpyxl.load_workbook(template_path)
    ws = wb[wb.sheetnames[1]]  # 第二个 sheet 是差旅费明细表

    data_font = Font(name='宋体', size=10)
    thin_border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )
    center_align = Alignment(horizontal='center', vertical='center', wrap_text=True)

    for i, trip in enumerate(trips_data):
        row = 6 + i

        ws[f'B{row}'] = trip['no']
        ws[f'C{row}'] = trip['period']
        ws[f'D{row}'] = ''
        ws[f'E{row}'] = trip['travel_amount']
        ws[f'F{row}'] = trip['other_amount']
        ws[f'G{row}'] = ''

        for col in ['B', 'C', 'D', 'E', 'F', 'G']:
            cell = ws[f'{col}{row}']
            cell.font = data_font
            cell.alignment = center_align
            cell.border = thin_border

    wb.save(output_path)
    print(f'差旅费明细表已更新: {output_path}')
    return output_path
```

---

## 常见问题汇总表

### 模板填写问题
| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 时间格式不换行 | Excel 未识别 `\n` | 确保单元格样式中 `wrap_text=True` |
| 字体不是宋体 | 模板样式冲突 | 代码强制设置 `Font(name='宋体')` |
| 右边框消失 | 写入数据覆盖了样式 | 循环中显式应用 `thin_border` 样式 |
| 数据错位 | 起始行设置错误 | 确认模板表格头占用的行数，通常数据从第 6 行开始 |

### 数据处理问题
| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 发票代码变科学计数法 | Excel 默认浮点 | **必须**使用 `xlsxwriter` + `astype(str)` |
| 其他金额漏填退票费 | 分类逻辑遗漏 | 确保分类函数中退票费优先级高于火车票 |
| 城市识别错误 | 车站名不在映射表中 | 扩展 `CITY_MAPPING` 字典，增加常用站点 |
| 住宿发票未归入行程 | 发票时间晚于行程结束时间或行程已闭环 | 使用 `last_trip` 追踪，将孤儿发票归入最后一个行程 |
| 文件夹日期范围不准 | 行程内发票时间跨度大 | 使用行程第一张和最后一张发票的时间作为起止日期 |

### 环境与依赖
| 问题 | 原因 | 解决方案 |
|------|------|----------|
| `pdf2image` 报错 | 未安装 poppler | 下载 poppler-windows 并添加 bin 到 PATH |
| LM Studio 连接超时 | 服务未启动 | 确保 localhost:1234 可访问 |
| 内存溢出 | DPI 过高 | 建议 DPI=200 |

### 数据处理
| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 发票代码变科学计数法 | Excel 默认浮点 | **必须**使用 `xlsxwriter` + `astype(str)` |
| 火车票发票号码提取失败 | 含 HTML 标签 `<td>` | 正则兼容：`r'发票号码[：:]?</?\w*>\s*<?\w*>?\s*(\d+)'` |
| 退票费金额为 0 | 误匹配票价 | 金额提取优先级: 退票费 > (小写) > 价税合计 > 合计 |
| 站名提取不全 | 正则受限 | 使用通用正则 `r'([^\n<>]+站)'` |
| 退票费出发地/目的地为空 | 未去除车次前缀 | 使用 `re.sub(r'^[GDCTZK\d]+', '', station)` 清理 |
| 飞机票路线为空 | 备注含 HTML 标签 | 先用 `re.sub(r'<[^>]+>', ' ', remark)` 清理 HTML |

### 业务逻辑
| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 退票费误判为火车票 | 分类优先级错误 | 分类时先判断 "退票" 再判断 "火车票" |
| 住宿实际时间为空 | 备注格式不同 | 支持多种备注正则匹配 |
| 目的地包含车次号 | OCR识别粘连，如 "G460南京南" | 使用正则 `re.sub(r'^[GDCTZK\d]+', '', ...)` 清理前缀 |
| 文件名包含非法字符 | 地点名可能有特殊符号 | 显式清除 `\/:*?"<>|` 字符 |
| 行程未闭环 | 缺少回程票或识别错误 | 文件夹名添加 `_未闭环` 后缀，供人工复核 |
| 跨日行程缺少住宿 | 某个住宿夜没有入住/离店区间覆盖 | 列出缺少住宿的具体日期，并将行程标记为 `_未闭环` |
| 住宿只有开票日期 | 开票日期不能证明实际入住日期 | 标记待复核，不自动判定住宿齐全 |
| 夜间交通替代住宿 | 夜间车次/航班可能覆盖住宿夜 | 记录为待人工确认，凭证时间不明确时仍提示缺少住宿 |
| PDF 查找失败 | JSON与PDF文件名不完全一致 | 使用前缀模糊匹配作为兜底策略 |
| 行程发票总数不足 | 孤儿发票未分配 | 使用 `last_trip` 追踪，将行程结束后的住宿/餐饮/退票费归入最后一个行程 |
| 归档文件夹重复 | 多次运行未清理旧数据 | 运行前清理 `行程归档/` 目录下的旧文件夹 |
| `TypeError: sequence item expected str, NoneType` | `cities` 列表含 `None` | 过滤: `if c and c not in unique_cities` |

---

## v3.0 更新日志 (2026-03-30 实战修复)

### 问题发现
处理 `C:\Users\tyytr\Desktop\20260330差旅` (27 张发票) 时发现:
1. 行程识别只分配了 22 张发票，5 张未分配
2. 退票费 (汉中→西安北) 出发地/目的地为空
3. 3 张携程住宿发票 (尾号3182/3833/9212) 日期在行程结束后，未归入任何行程
4. 机票退票费 (¥559) 金额被误匹配为价税合计
5. 飞机票路线信息未从 HTML 备注中提取
6. 归档时 `cities` 列表含 `None` 导致 `TypeError`

### 修复方案
1. **CITY_MAPPING**: 增加 "汉口"、"武昌" (不带"站"后缀)
2. **parse_train_refund**: 增加 `re.sub(r'^[GDCTZK\d]+', '', ...)` 去除车次前缀
3. **parse_standard_invoice 金额**: 退票费优先级提到最前
4. **parse_standard_invoice 飞机票**: 先清理 HTML 标签再提取路线
5. **identify_trips**: 增加 `last_trip` 追踪，孤儿发票归入最后一个行程
6. **identify_trips**: 处理非基地出发的中途交通票
7. **archive_pdfs_by_trip**: 过滤 `None` 值: `if c and c not in unique_cities`
8. **main**: 打印行程时过滤 `None`: `set(c for c in trip["cities"] if c)`

### 验证结果
- 27 张发票全部正确分配
- 5 个闭环行程: 2+3+4+3+15 = 27 ✓
- 归档文件夹: 5 个，共 27 个 PDF ✓

---

## v3.1 更新日志 (2026-03-30 材料费处理)

### 场景
处理 `C:\Users\tyytr\Desktop\20260330材料费` (2 张材料费发票)

### 材料费重命名规则
- **格式**: `{开票日期}-{材料名称}-{金额}.pdf`
- **材料名称提取**: 从项目名称中去掉 `*分类*` 前缀 (如 `*化学试剂*WD-40防锈润滑剂` → `WD-40防锈润滑剂`)
- **示例**:
  - `20251230-WD-40防锈润滑剂-29.90.pdf`
  - `20260313-3M胶带-825.00.pdf`

### 模板填写规则 (材料测试加工等费用 Sheet)
- **Sheet**: 第一个 Sheet (材料测试加工等费用)
- **表头行**: Row 4 (B=序号, C=费用类别, D=金额, E=用途/明细说明, F=备注)
- **数据起始行**: Row 5 (查找第一个空序号行)
- **填写列**:
  - B列: 序号 (自动递增)
  - C列: 费用类别 (材料费/测试加工费)
  - D列: 金额
  - E列: 用途/明细说明 (项目名称，如 `*化学试剂*WD-40防锈润滑剂`)
  - F列: 备注 (发票号码)

### 材料费解析逻辑
```python
def parse_invoice(json_path):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    content = data.get("text", "")
    info = {"原始内容": content}

    # 发票号码
    match = re.search(r"发票号码[：:]\s*(\d+)", content)
    info["发票号码"] = match.group(1) if match else ""

    # 开票日期
    match = re.search(r"开票日期[：:]\s*(\d{4})年(\d{1,2})月(\d{1,2})日", content)
    if match:
        info["开票日期"] = f"{match.group(1)}/{match.group(2).zfill(2)}/{match.group(3).zfill(2)}"

    # 金额 (优先级: (小写) > 价税合计 > 合计 > 普通)
    amount = re.search(r"[（(]小写[）)]¥\s*(\d+\.?\d*)", content)
    if not amount: amount = re.search(r"价税合计.*?[¥￥]\s*(\d+\.?\d*)", content)
    if not amount: amount = re.search(r"合\s*计.*?(\d+\.?\d*)", content)
    if not amount: amount = re.search(r"¥\s*(\d+\.?\d*)", content)
    info["金额"] = float(amount.group(1)) if amount else 0

    # 销售方
    match = re.search(r"销售方信息.*?名称[:：]\s*([^\n]+)", content)
    info["销售方"] = match.group(1).strip() if match else ""

    # 货物或应税劳务名称 (材料费关键信息)
    # 从表格中提取 *分类*名称 格式
    match = re.search(r'\*([^*]+)\*([^<\n]+)', content)
    if match:
        info["项目名称"] = f"*{match.group(1)}*{match.group(2).strip()}"
    else:
        info["项目名称"] = ""

    # 分类 - 材料费统一为"材料费"
    info["类型"] = "材料费"

    return info
```

### 材料费重命名逻辑
```python
def rename_material_pdfs(invoices, source_dir):
    for info in invoices:
        json_name = info.get("文件名", "")
        pdf_name = json_name.replace(".json", ".pdf")
        src_pdf = os.path.join(source_dir, pdf_name)

        if not os.path.exists(src_pdf):
            # Fuzzy match
            base_prefix = json_name.split("-")[0] if "-" in json_name else json_name.replace(".json", "")
            pdf_files = glob.glob(os.path.join(source_dir, "*.pdf"))
            matches = [f for f in pdf_files if os.path.basename(f).startswith(base_prefix[:10])]
            if matches:
                src_pdf = matches[0]
            else:
                continue

        # 材料名称: 去掉 *分类* 前缀
        project_name = info.get("项目名称", "")
        material_name = re.sub(r'\*[^*]+\*', '', project_name).strip()
        if not material_name:
            material_name = info.get("类型", "材料")
        material_name = material_name[:30]
        material_name = re.sub(r'[\\/:*?"<>|]', '', material_name)

        date_part = info.get("开票日期", "").replace("/", "")
        amount = info.get("金额", 0)
        new_filename = f"{date_part}-{material_name}-{amount:.2f}.pdf"
        dst_pdf = os.path.join(source_dir, new_filename)

        if src_pdf != dst_pdf:
            if os.path.exists(dst_pdf):
                os.remove(src_pdf)
            else:
                os.rename(src_pdf, dst_pdf)
```

### 模板填写逻辑
```python
def fill_material_template(invoices, template_path, output_path):
    wb = openpyxl.load_workbook(template_path)
    ws = wb[wb.sheetnames[0]]  # 第一个 Sheet

    # 清空之前的内容 (Row 5-17)
    for row in range(5, 18):
        for col in [2, 3, 4, 5, 6]:
            try:
                ws.cell(row=row, column=col).value = None
            except AttributeError:
                pass

    # 从第5行开始重新填写
    start_row = 5

    for i, info in enumerate(invoices):
        row = start_row + i
        ws.cell(row=row, column=2).value = i + 1  # B列: 序号
        ws.cell(row=row, column=3).value = "材料费"  # C列: 费用类别 (统一为"材料费")
        ws.cell(row=row, column=4).value = info.get("金额", 0)  # D列: 金额
        ws.cell(row=row, column=5).value = info.get("项目名称", "")  # E列: 用途/明细
        # F列: 备注 (不写，留空)

    wb.save(output_path)
```

### 遇到的问题
| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 重复处理发票 | 重命名用 copy2 导致原文件+副本共存 | 改用 `os.rename`，已存在时删除原文件 |
| 模板填写到错误行 | 空行判断逻辑不准确 | 先清空 Row 5-17，从第5行重新填写 |
| MergedCell 错误 | F列有合并单元格 (E19:F19) | 用 try/except 跳过合并单元格 |
| 材料名称过长 | 销售方名称包含统一信用代码 | 从项目名称提取，去掉 `*分类*` 前缀 |
| 费用类别不统一 | 分类逻辑复杂 | 材料费统一填写为"材料费" |
| 备注列不需要 | 用户要求 | F列留空不填写 |

### 验证结果
- 2 张材料费发票正确识别 ✓
- 重命名: `20251230-WD-40防锈润滑剂-29.90.pdf`, `20260313-3M胶带-825.00.pdf` ✓
- 模板填写: Row 5-6 正确填入，费用类别统一为"材料费"，备注留空 ✓

---

## v4.0 更新日志 (2026-04-14 租车/加油分类支持)

### 场景
处理 `E:\Onedrive-tyytrty\OneDrive\桌面\whb` (17 张发票)

### 新增功能
1. **新增分类**: 租车、加油
2. **其他金额扩展**: 租车、加油、餐饮、打车、退票费都放入"其他金额"列
3. **PDF重命名**: 按日期-类型-金额格式自动重命名

### 分类规则更新
```python
TYPE_PRIORITY = {"火车票": 1, "飞机票": 2, "退票费": 3, "住宿": 4, "租车": 5, "加油": 6, "餐饮": 7, "打车": 8, "其他": 9}

# 分类函数增加
if "汽油" in content or "柴油" in content or "油品" in content or "加油站" in seller: return "加油"
if "租车" in content or "租赁" in content or "神州" in seller or "一嗨" in seller: return "租车"
```

### 模板填写更新
- **差旅金额 (E列)**: 火车票、飞机票、住宿
- **其他金额 (F列)**: 餐饮、打车、租车、加油、退票费 (按类型分组显示)

### 验证结果
- 17 张发票正确分类: 机票×2, 火车票×3, 住宿×2, 加油×4, 餐饮×3, 打车×3 ✓
- PDF 文件按格式重命名 ✓
- 模板正确填入 3 个行程 ✓
