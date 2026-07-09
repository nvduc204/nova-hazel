FROM python:3.13.14

WORKDIR /app

# Cài đặt dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Tạo thư mục chứa metadata
RUN mkdir -p /app/data

# Chạy script
CMD ["python", "main.py"]
