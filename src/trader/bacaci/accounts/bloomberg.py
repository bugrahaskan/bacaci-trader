import datetime as dt
from datetime import datetime
import os
import pandas as pd
import logging

try:
    import blpapi
except ImportError:
    pass

class Bloomberg:
    def __init__(self):
        logging.basicConfig(level=logging.INFO)

        self.output_file = ""

        self.host = "localhost"
        self.port = 8194

    

if __name__ == "__main__":
    data = Bloomberg()