def format_date_for_sql(date_string):
    """
    Convert date from DD.MM.YYYY format to YYYY-MM-DD for SQL queries
    
    Args:
        date_string (str): Date in DD.MM.YYYY format
        
    Returns:
        str: Date in YYYY-MM-DD format
    """
    if not date_string:
        return None
        
    try:
        day, month, year = date_string.split('.')
        return f"{year}-{month}-{day}"
    except Exception as e:
        raise ValueError(f"Неверный формат даты. Ожидается ДД.ММ.ГГГГ, получено: {date_string}") from e