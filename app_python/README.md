## **Overview**
The **DevOps Info Service** is a lightweight web application that provides detailed information about the system, runtime environment, and service metadata.  
It exposes two API endpoints used throughout the DevOps course for monitoring, containerization, CI/CD, and Kubernetes health checks.

---

## **Prerequisites**
- Python **3.11+**
- pip package manager
- Virtual environment recommended

Dependencies are listed in `requirements.txt`.

---

## **Installation**

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## **Running the Application**

### Default run
```bash
python app.py
```

### Custom configuration
```bash
PORT=8080 python app.py
```

Or with multiple variables:

```bash
HOST=127.0.0.1 PORT=3000 DEBUG=true python app.py
```

---

## **API Endpoints**

### **GET /**
Returns:
- Service metadata  
- System information  
- Runtime uptime  
- Current timestamp  
- Request details  
- List of available endpoints  

### **GET /health**
Returns:
- Health status  
- Current timestamp  
- Uptime in seconds  

Used for monitoring and Kubernetes liveness/readiness probes.

---

## **Configuration**

The application supports environment variables for runtime configuration:

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `0.0.0.0` | Address the server binds to |
| `PORT` | `5000` | Port the service listens on |
| `DEBUG` | `False` | Enables debug mode when set to `true` |