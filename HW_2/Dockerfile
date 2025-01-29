FROM python:3.10

WORKDIR /HW_2

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "bot.py"]