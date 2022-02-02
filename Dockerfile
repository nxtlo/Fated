FROM python:3.10

WORKDIR /fated

COPY . /fated
COPY ./requirements.txt /fated/requirements.txt
COPY ./run.py /fated/run.py

RUN python -m pip install -r requirements.txt
CMD ["python", "run.py"]