"""
Yield Management Module

수율 및 재공품을 관리하는 모듈입니다.
main.py에서는 yield_prediction() 한 줄만 호출하면 모든 처리가 자동으로 수행됩니다.
"""

import pandas as pd
import os
from config import config
from .yield_calc import yield_prediction 

