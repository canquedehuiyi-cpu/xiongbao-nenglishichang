---
title: Follow Container Deployment Best Practices
impact: LOW-MEDIUM
impactDescription: ensures reliable Kubernetes deployments
tags: devops, docker, kubernetes, containers, deployment
---

## Follow Container Deployment Best Practices

**Impact: LOW-MEDIUM (ensures reliable Kubernetes deployments)**

ICM 11+ is container-based and runs in Kubernetes clusters. Following container best practices ensures reliable deployments and efficient operations.

**Incorrect (monolithic container configuration):**

```dockerfile
# Bad: Overloaded container with too many concerns
FROM intershop/icm-as:latest

# Installing tools at runtime - slow startup
RUN apt-get update && apt-get install -y debugging-tools

# Hardcoded configuration
ENV ICM_DB_URL=jdbc:oracle:thin:@prod-db:1521/ICMDB
ENV ICM_DB_PASSWORD=secretpassword  # Bad: Secret in image!

# Large image size
COPY all-cartridges/ /opt/intershop/
```

**Correct (optimized container configuration):**

```dockerfile
# Good: Multi-stage build for smaller images
FROM intershop/icm-as:latest AS base

# Build stage - separate from runtime
FROM base AS builder
COPY custom-cartridges/ /build/cartridges/
RUN /opt/intershop/tools/build-cartridges.sh

# Runtime stage - minimal footprint
FROM base AS runtime
COPY --from=builder /build/output/ /opt/intershop/cartridges/

# Non-root user for security
USER intershop

# Health check for Kubernetes
HEALTHCHECK --interval=30s --timeout=10s \
  CMD curl -f http://localhost:8080/health || exit 1

# Expose only necessary ports
EXPOSE 8080 8443
```

**Kubernetes configuration:**

```yaml
# Good: Proper Kubernetes deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: icm-application-server
spec:
  replicas: 2
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    spec:
      containers:
      - name: icm-as
        image: registry.example.com/icm-as:1.0.0
        resources:
          requests:
            memory: "4Gi"
            cpu: "2"
          limits:
            memory: "8Gi"
            cpu: "4"
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 60
          periodSeconds: 10
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 120
          periodSeconds: 30
        env:
        - name: ICM_DB_PASSWORD
          valueFrom:
            secretKeyRef:
              name: icm-db-credentials
              key: password
        - name: ICM_DB_URL
          valueFrom:
            configMapKeyRef:
              name: icm-config
              key: database-url

---
# Separate secrets from configuration
apiVersion: v1
kind: Secret
metadata:
  name: icm-db-credentials
type: Opaque
data:
  password: <base64-encoded-password>

---
# ConfigMap for non-sensitive configuration
apiVersion: v1
kind: ConfigMap
metadata:
  name: icm-config
data:
  database-url: "jdbc:oracle:thin:@db.example.com:1521/ICMDB"
  log-level: "INFO"
```

**Helm chart structure:**

```
icm-helm-chart/
├── Chart.yaml
├── values.yaml
├── values-prod.yaml
├── values-staging.yaml
├── templates/
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── configmap.yaml
│   ├── secrets.yaml
│   ├── ingress.yaml
│   └── hpa.yaml
└── charts/
    └── dependencies...
```

**Container best practices:**

| Practice | Description |
|----------|-------------|
| Multi-stage builds | Reduce image size |
| Non-root user | Security compliance |
| Health checks | Enable K8s self-healing |
| Resource limits | Prevent resource exhaustion |
| Secrets management | Never in images or configs |
| Rolling updates | Zero-downtime deployments |
| Horizontal Pod Autoscaler | Scale based on load |

Reference: [Concept - Intershop Commerce Platform System Overview](https://support.intershop.com/kb/index.php/Display/301T35)
