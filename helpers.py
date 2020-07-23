def csv(values, strip=True):
    return [v for v in ((v.strip() if strip else v) for v in values.split(',')) if v]

class Fillable:
    def fill(self, _except=[], **kwargs):
        for key in kwargs:
            if key not in _except and hasattr(self, key):
                setattr(self, key, kwargs[key])