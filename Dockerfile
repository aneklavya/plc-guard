FROM python:3.13-slim

WORKDIR /app
COPY requirements-app.txt .
RUN pip install --no-cache-dir -r requirements-app.txt

COPY plcguard/ plcguard/
COPY dataset/ dataset/
COPY results/ results/
COPY app.py .

RUN useradd --create-home plcguard && chown -R plcguard /app
USER plcguard

EXPOSE 8501
# NVIDIA_API_KEY is optional; without it only cached example scans use the LLM.
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501", \
     "--server.headless=true", "--browser.gatherUsageStats=false"]
