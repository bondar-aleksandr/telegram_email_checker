
def normalize_header(header: str):
    header = header.replace('<', '')
    header = header.replace('>', '')
    return header