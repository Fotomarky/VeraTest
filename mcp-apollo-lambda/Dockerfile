FROM public.ecr.aws/lambda/python:3.12

WORKDIR ${LAMBDA_TASK_ROOT}

COPY app.py ${LAMBDA_TASK_ROOT}

RUN pip install --no-cache-dir \
    mcpengine[lambda] \
    requests \
    httpx

CMD ["app.handler"]
