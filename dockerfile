FROM python:3.8-slim
LABEL author="aleksandr bondar"
LABEL description="this image contains python script, which connects to specified IMAP server and gets\
new email according to specified criteria, old emails removed periodically. Then, telegram notification occour."
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
ENTRYPOINT [ "python", "./main.py" ]