def csv(values, strip=True):
    return [v for v in ((v.strip() if strip else v) for v in values.split(',')) if v]