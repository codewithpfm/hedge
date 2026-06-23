import MetaTrader5 as mt5
from typing import Any, TypedDict

class Response(TypedDict):
    magic: int
    data: Any
    is_error: bool
    error: str | None
    params: dict | None



class BaseHandler: 
  
    def __init__(self, magic: int = -1, debug: bool = False): 
        self.magic = magic
        self.debug = debug
      
    def success(self, data) -> Response:
      return {
        'magic': self.magic,
        'data': data,
        'is_error': False,
        'error': None,
        'params': None,
      }
    
    def error(self, data: Any | None = None, params: dict | None = None) -> Response:
      last_error = mt5.last_error()
      
      return {
        'magic': self.magic,
        'data': None,
        'is_error': True,
        'error': last_error,
        'params': params,
      }
    
    def res(self, data = None, params = None):
      if data is None:
        return self.error(data=data, params=params)
      
      return self.success(data)