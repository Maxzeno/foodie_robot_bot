import re

def extract_user_code(text: str):
    match = re.search(r"#([A-Za-z0-9]+)", text)
    if match:
        return match.group(1)   # returns the code without the '#'
    return None