from datetime import datetime

def convert_date(s:str)->str|None:
    if not s:
        return None
    try:
        return datetime.strptime(s, '%Y-%m-%d').date()
    except:
        return None