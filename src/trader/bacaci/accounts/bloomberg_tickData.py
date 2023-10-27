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

class TickData(Bloomberg):
    def __init__(self):
        logging.basicConfig(level=logging.INFO)

        super().__init__()

        self.security_name = "IBM US Equity"
        self.startDateTime = "2022-06-24T00:00:00"
        self.endDateTime = "2022-12-24T00:00:00"

        self.TICK_DATA = blpapi.Name("tickData")
        self.COND_CODE = blpapi.Name("conditionCodes")
        self.TICK_SIZE = blpapi.Name("size")
        self.TIME = blpapi.Name("time")
        self.TYPE = blpapi.Name("type")
        self.VALUE = blpapi.Name("value")
        self.RESPONSE_ERROR = blpapi.Name("responseError")
        self.CATEGORY = blpapi.Name("category")
        self.MESSAGE = blpapi.Name("message")
        self.SESSION_TERMINATED = blpapi.Name("SessionTerminated")

        #output_filename = os.getcwd()+f"/{self.security_name}-tickData.csv"
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
        

    def retrieve_data(self, security, startDateTime, endDateTime):
        refDataService = self.session.getService("//blp/refdata")
        request = refDataService.createRequest("IntradayTickRequest")
    
        # only one security/eventType per request
        request.set("security", security)
    
        # Add fields to request
        eventTypes = request.getElement("eventTypes")
        for event in ["TRADE"]: # "AT_TRADE" # correct
            eventTypes.appendValue(event)
    
        # All times are in GMT
        request.set("startDateTime", startDateTime)
        request.set("endDateTime", endDateTime)
        request.set("includeConditionCodes", True)
            
        print("Sending Request:", request)
        self.session.sendRequest(request)

        output_filename = os.getcwd()+f"/BİST30/{security}-tickData.csv"
        self.output_file = open(output_filename, "w")
        header = format("Date,Type,Price,Size\n")
        self.output_file.write(header)
        self.eventLoop(self.session)
        self.output_file.close()


    def eventLoop(self, session):
        done = False
        while not done:
            # nextEvent() method below is called with a timeout to let
            # the program catch Ctrl-C between arrivals of new events
            event = session.nextEvent(500)
            if event.eventType() == blpapi.Event.PARTIAL_RESPONSE:
                self.processResponseEvent(event)
            elif event.eventType() == blpapi.Event.RESPONSE:
                self.processResponseEvent(event)
                done = True
            else:
                for msg in event:
                    if event.eventType() == blpapi.Event.SESSION_STATUS:
                        if msg.messageType() == self.SESSION_TERMINATED:
                            done = True
                        

    def processResponseEvent(self, event):
        for msg in event:
            if msg.hasElement(self.RESPONSE_ERROR):
                print(msg.getElement(self.RESPONSE_ERROR))
                continue
            self.processMessage(msg)


    def processMessage(self, msg):
        data = msg.getElement(self.TICK_DATA).getElement(self.TICK_DATA)
        for item in data.values():
            time = item.getElementAsDatetime(self.TIME)
            timeString = item.getElementAsString(self.TIME)
            type = item.getElementAsString(self.TYPE)
            value = item.getElementAsFloat(self.VALUE)
            size = item.getElementAsInteger(self.TICK_SIZE)
            if item.hasElement(self.COND_CODE):
                cc = item.getElementAsString(self.COND_CODE)
            else:
                cc = ""
    
            line = format("%s,%s,%.3f,%d\n" % (time, type, value, size))
            self.output_file.write(line)

if __name__ == "__main__":
    end = datetime.now()
    start = end - dt.timedelta(days=2)
    security = "IBM US Equity"
    
    startDateTime = datetime.fromisoformat("2022-12-22 00:00:00")
    endDateTime = datetime.fromisoformat('2023-01-06 00:00:00')

    data = TickData()
    data.retrieve_data(security = "IBM US Equity",
                    startDateTime = "2022-06-24T00:00:00",
                    endDateTime = "2022-12-24T00:00:00"
                    )
