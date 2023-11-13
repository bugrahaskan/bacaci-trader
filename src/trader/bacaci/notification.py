import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Any

class Notification:

    def __init__(self, receiver_email, message):

        smtp_outlook = "smtp-mail.outlook.com"
        smtp_gmail = "smtp.gmail.com"

        # Connect to the SMTP server
        try:
            self.server = smtplib.SMTP(
                smtp_outlook,
                587 # Port for secure connection (TLS)
                )
            
            self.server.connect(smtp_outlook, 25)
            
            self.server.starttls()
        except ConnectionRefusedError:
            print("Connection unsuccesful")
            exit(1)

        # Email configuration
        self.sender_email = "bugrahaskan@outlook.com"
        password = "FevziBugra@1987"
        
        # Log in to your email account
        try:
            self.server.login(self.sender_email, password)
        except smtplib.SMTPAuthenticationError:
            print("Authentication refused")
            exit(1)

        # Create the email message
        self.msg = MIMEMultipart()
        self.msg["From"] = self.sender_email
        self.msg["Subject"] = "NOTIFICATION FROM BACACI TRADING BOT"

        # Reciever's email
        self.msg["To"] = receiver_email
        self.msg.attach(MIMEText(message, "plain"))

        # Send the email
        text = self.msg.as_string()
        self.server.sendmail(self.sender_email, receiver_email, text)

        # Close the connection
        #self.server.quit()

        