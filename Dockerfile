FROM python:3
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /code
COPY requirements_dev.txt /code/
COPY setup.py /code/
COPY README.rst /code/
RUN pip install .
RUN pip install -r requirements_dev.txt
COPY . /code/
RUN example/manage.py migrate
COPY . /code/
