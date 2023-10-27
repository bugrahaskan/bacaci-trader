import datetime as dt
from datetime import datetime
import os
import pandas as pd
import logging

from bloomberg import Bloomberg

try:
    import blpapi
except ImportError:
    pass

class BarData(Bloomberg):
    def __init__(self):
        logging.basicConfig(level=logging.INFO)

        super().__init__()

        self.security_name = "IBM US Equity"
        self.startDateTime = "2022-06-24T00:00:00"
        self.endDateTime = "2022-12-24T00:00:00"
        self.interval = 1

        #output_filename = os.getcwd()+f"/{self.security_name}-{self.interval}.csv"
        #output_file = open(output_filename, "w")

        sessionOptions = blpapi.SessionOptions()
        sessionOptions.setServerHost(self.host)
        sessionOptions.setServerPort(self.port)
        self.session = blpapi.Session(sessionOptions)

        logging.info(f"Connecting from {self.host} to {self.port}")

        try:
            assert(self.session.start())
            logging.info("Session started...")
        except:
            logging.error("Failed to start session.")
            return

        try:
            assert(self.session.openService("//blp/refdata"))
            logging.info("Service //blp/refdata is ready")
        except:
            logging.error("Failed to open //blp/refdata")
            return
        

    def retrieve_data(self, security, interval, startDateTime, endDateTime):
        refDataService = self.session.getService("//blp/refdata")
        request = refDataService.createRequest("IntradayBarRequest")

        request.set("security", security)
        request.set("eventType", "TRADE")
        request.set("interval", interval)

        request.set("startDateTime", startDateTime)
        request.set("endDateTime", endDateTime)
        
        self.session.sendRequest(request)

        output_filename = os.getcwd()+f"/BİST30/{security}-{interval}min.csv"
        self.output_file = open(output_filename, "w")
        header = format("Date,Open,High,Low,Close,Volume\n")
        self.output_file.write(header)
        self.eventLoop(self.session)
        self.output_file.close()

    def eventLoop(self, session):
        done = False
        while not done:
            event = session.nextEvent(500)
            if event.eventType() == blpapi.Event.PARTIAL_RESPONSE:
                self.processResponseEvent(event)
            elif event.eventType() == blpapi.Event.RESPONSE:
                self.processResponseEvent(event)
                done = True
            else:
                for msg in event:
                    if event.eventType() == blpapi.Event.SESSION_STATUS:
                        if msg.messageType() == blpapi.Name("SessionTerminated"):
                            done = True

    def processResponseEvent(self, event):
        for msg in event:
            if msg.hasElement(blpapi.Name("responseError")):
                continue
            self.processMessage(msg)

    def processMessage(self, msg):
        data = msg.getElement("barData").getElement("barTickData")
        
        for item in data.values():
            time = item.getElementAsDatetime(blpapi.Name("time"))
            open = item.getElementAsFloat(blpapi.Name("open"))
            high = item.getElementAsFloat(blpapi.Name("high"))
            low = item.getElementAsFloat(blpapi.Name("low"))
            close = item.getElementAsFloat(blpapi.Name("close"))
            volume = item.getElementAsInteger(blpapi.Name("volume"))

            line = format("%s,%f,%f,%f,%f,%d\n" % (time, open, high, low, close, volume))
            self.output_file.write(line)
    
if __name__ == "__main__":
    d = BarData()

    end = datetime.now()
    start = end - dt.timedelta(days=365)

    bist = ['AKBNK',
            'AKSEN',
            'ARCLK',
            'ASELS',
            'BIMAS',
            'EKGYO',
            'EREGL',
            'FROTO',
            'GARAN',
            'GUBRF',
            'HEKTS',
            'ISCTR',
            'KCHOL',
            'KOZAA',
            'KOZAL',
            'KRDMD',
            'PETKM',
            'PGSUS',
            'SAHOL',
            'SASA',
            'SISE',
            'TAVHL',
            'TCELL',
            'THYAO',
            'TKFEN',
            'TOASO',
            'TTKOM',
            'TUPRS',
            'VESTL',
            'YKBNK'
            ]
    
    bist_tickers = []
    for b in bist:
        bist_tickers.append(b+f" TI Equity")

    for ticker in tqdm(bist_tickers, total=len(bist_tickers)):
        d.retrieve_data(security=ticker, interval=1, startDateTime = start, endDateTime = end)
        d.retrieve_data(security=ticker, interval=5, startDateTime = start, endDateTime = end)
        d.retrieve_data(security=ticker, interval=15, startDateTime = start, endDateTime = end)
        d.retrieve_data(security=ticker, interval=30, startDateTime = start, endDateTime = end)
        d.retrieve_data(security=ticker, interval=60, startDateTime = start, endDateTime = end)