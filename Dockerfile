# AWS Lambda container image for OmniAnalyst (API + worker share one image).
FROM public.ecr.aws/lambda/python:3.12

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ${LAMBDA_TASK_ROOT}/

# Both entry points are importable from the same image:
#   lambda_function.lambda_handler  (HTTP API)
#   worker.lambda_handler           (SQS worker)
CMD ["lambda_function.lambda_handler"]
