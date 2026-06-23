import pandas as pd


def get_candles_df(candles, timezone):
    _candles = pd.DataFrame(candles)

    _candles["Datetime"] = pd.to_datetime(_candles["time"], unit="s").dt.tz_localize("UTC").dt.tz_convert(str(timezone))

    _candles = _candles.set_index("Datetime")

    return _candles


def filter_props(obj, keys):
    t = {}
    for key in keys:
        t[key] = obj[key]
    return t

def reverse_dict(d: dict):
    return {v: k for k, v in d.items()}

class Map(dict):
    """
    Example:
    m = Map({'first_name': 'Eduardo'}, last_name='Pool', age=24, sports=['Soccer'])
    """
    def __init__(self, *args, **kwargs):
        super(Map, self).__init__(*args, **kwargs)
        for arg in args:
            if isinstance(arg, dict):
                for k, v in arg.items():
                    self[k] = v

        if kwargs:
            for k, v in kwargs.items():
                self[k] = v

    def __getattr__(self, attr):
        return self.get(attr)

    def __setattr__(self, key, value):
        self.__setitem__(key, value)

    def __setitem__(self, key, value):
        super(Map, self).__setitem__(key, value)
        self.__dict__.update({key: value})

    def __delattr__(self, item):
        self.__delitem__(item)

    def __delitem__(self, key):
        super(Map, self).__delitem__(key)
        del self.__dict__[key]