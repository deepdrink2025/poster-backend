import re

def extract_dimensions(prompt: str) -> tuple[int, int]:
    """从 prompt 中提取尺寸信息，如果没有则返回默认值。"""
    # 匹配 "横版"
    if "横版" in prompt:
        print("检测到'横版'关键词，使用尺寸 1200x800")
        return 1200, 800
    
    # 匹配如 1920x1080, 800*600 的尺寸
    match = re.search(r'(\d+)\s*[x*×]\s*(\d+)', prompt)
    if match:
        width, height = int(match.group(1)), int(match.group(2))
        print(f"从 prompt 中提取到尺寸: {width}x{height}")
        return width, height

    # 匹配如 16:9, 4:3 的宽高比
    match = re.search(r'(\d+)\s*:\s*(\d+)', prompt)
    if match:
        width = 1200
        height = int(width * int(match.group(2)) / int(match.group(1)))
        print(f"从 prompt 中提取到宽高比，计算出尺寸: {width}x{height}")
        return width, height

    print("未在 prompt 中发现尺寸信息，使用默认尺寸 800x1200")
    return 800, 1200 # 默认尺寸