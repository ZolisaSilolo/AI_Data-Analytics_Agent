# AWS Lambda Python Container Image for OmniAnalyst Backend
FROM public.ecr.aws/lambda/python:3.12

# Copy requirements
COPY requirements.txt .

# Install dependencies into container
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source code
COPY src/ ${LAMBDA_TASK_ROOT}

# Set the Lambda handler
CMD ["lambda_function.lambda_handler"]
