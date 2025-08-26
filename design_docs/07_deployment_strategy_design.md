# AI-Shifu SaaS Deployment Strategy Design

## Overview

This document outlines the comprehensive deployment strategy for the AI-Shifu SaaS platform, covering Kubernetes-based infrastructure, CI/CD pipelines, multi-environment management, and scalability considerations for independent deployment with unified management.

## 1. Architecture Overview

### 1.1 Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Management Plane                          │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐│
│  │  Central GitOps │  │   Monitoring    │  │  Tenant Portal  ││
│  │     (ArgoCD)    │  │ (Prometheus +   │  │   (Management)  ││
│  │                 │  │   Grafana)      │  │                 ││
│  └─────────────────┘  └─────────────────┘  └─────────────────┘│
└─────────────────────────────────────────────────────────────┘
                             │
                    ┌────────┴────────┐
                    │                 │
┌───────────────────▼────┐  ┌─────────▼───────────────┐
│    Tenant Cluster A    │  │    Tenant Cluster B     │
│  ┌───────────────────┐ │  │  ┌───────────────────┐  │
│  │   AI-Shifu App    │ │  │  │   AI-Shifu App    │  │
│  │   (Dedicated)     │ │  │  │   (Dedicated)     │  │
│  └───────────────────┘ │  │  └───────────────────┘  │
│  ┌───────────────────┐ │  │  ┌───────────────────┐  │
│  │   MySQL StatefulSet│ │  │  │   MySQL StatefulSet│  │
│  │   (Dedicated DB)  │ │  │  │   (Dedicated DB)  │  │
│  └───────────────────┘ │  │  └───────────────────┘  │
│  ┌───────────────────┐ │  │  ┌───────────────────┐  │
│  │   Redis Cluster   │ │  │  │   Redis Cluster   │  │
│  └───────────────────┘ │  │  └───────────────────┘  │
└────────────────────────┘  └─────────────────────────┘
```

### 1.2 Deployment Models

**1. Shared Infrastructure Model (Cost-Effective)**
- Multiple tenants on shared K8S clusters
- Row-level security for data isolation
- Namespace-based tenant separation

**2. Dedicated Infrastructure Model (High Security/Compliance)**
- Dedicated K8S cluster per enterprise tenant
- Complete infrastructure isolation
- Independent scaling and customization

**3. Hybrid Model (Balanced Approach)**
- Shared clusters for standard tenants
- Dedicated clusters for enterprise/compliance tenants
- Flexible scaling based on tenant requirements

## 2. Kubernetes Infrastructure

### 2.1 Cluster Architecture

```yaml
# Production Cluster Configuration
apiVersion: v1
kind: ConfigMap
metadata:
  name: cluster-config
  namespace: ai-shifu-system
data:
  cluster-spec.yaml: |
    cluster:
      name: ai-shifu-prod
      region: us-west-2
      version: "1.28"

      nodeGroups:
        - name: system-nodes
          instanceType: t3.large
          desiredCapacity: 3
          minSize: 3
          maxSize: 5
          labels:
            role: system
          taints:
            - key: system-reserved
              value: "true"
              effect: NoSchedule

        - name: app-nodes
          instanceType: c5.2xlarge
          desiredCapacity: 5
          minSize: 3
          maxSize: 20
          labels:
            role: application

        - name: data-nodes
          instanceType: r5.2xlarge
          desiredCapacity: 3
          minSize: 3
          maxSize: 10
          labels:
            role: database
          taints:
            - key: database-only
              value: "true"
              effect: NoSchedule

      addons:
        - aws-load-balancer-controller
        - ebs-csi-driver
        - cluster-autoscaler
        - cert-manager
        - external-secrets-operator

---
# Namespace Template for Tenants
apiVersion: v1
kind: Namespace
metadata:
  name: tenant-${TENANT_BID}
  labels:
    tenant: ${TENANT_BID}
    tier: ${TENANT_TIER}  # standard, premium, enterprise
    isolation: ${ISOLATION_LEVEL}  # shared, dedicated
  annotations:
    ai-shifu.io/tenant-bid: ${TENANT_BID}
    ai-shifu.io/created-at: ${CREATION_TIME}
spec:
  finalizers:
    - kubernetes

---
# Resource Quotas per Tenant
apiVersion: v1
kind: ResourceQuota
metadata:
  name: tenant-quota
  namespace: tenant-${TENANT_BID}
spec:
  hard:
    # Compute Resources
    requests.cpu: ${CPU_REQUESTS}
    requests.memory: ${MEMORY_REQUESTS}
    limits.cpu: ${CPU_LIMITS}
    limits.memory: ${MEMORY_LIMITS}

    # Storage
    persistentvolumeclaims: ${PVC_COUNT}
    requests.storage: ${STORAGE_REQUESTS}

    # Networking
    services: ${SERVICE_COUNT}
    services.loadbalancers: ${LB_COUNT}

    # Objects
    pods: ${POD_COUNT}
    replicationcontrollers: ${RC_COUNT}
    secrets: ${SECRET_COUNT}
    configmaps: ${CONFIGMAP_COUNT}

---
# Network Policy for Tenant Isolation
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: tenant-isolation
  namespace: tenant-${TENANT_BID}
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: nginx-ingress
  - from:
    - namespaceSelector:
        matchLabels:
          name: ai-shifu-system
  - from:
    - namespaceSelector:
        matchLabels:
          tenant: ${TENANT_BID}
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: kube-system
  - to: []  # Allow egress to external services
    ports:
    - protocol: TCP
      port: 443
    - protocol: TCP
      port: 80
    - protocol: UDP
      port: 53
```

### 2.2 Application Deployment Configuration

```yaml
# AI-Shifu API Deployment Template
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ai-shifu-api
  namespace: tenant-${TENANT_BID}
  labels:
    app: ai-shifu-api
    tenant: ${TENANT_BID}
    version: ${APP_VERSION}
spec:
  replicas: ${API_REPLICAS}
  selector:
    matchLabels:
      app: ai-shifu-api
      tenant: ${TENANT_BID}
  template:
    metadata:
      labels:
        app: ai-shifu-api
        tenant: ${TENANT_BID}
        version: ${APP_VERSION}
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "5000"
        prometheus.io/path: "/metrics"
    spec:
      serviceAccountName: ai-shifu-api
      nodeSelector:
        role: application
      containers:
      - name: api
        image: ${ECR_REGISTRY}/ai-shifu-api:${APP_VERSION}
        imagePullPolicy: Always
        ports:
        - containerPort: 5000
          name: http
        env:
        - name: TENANT_BID
          value: ${TENANT_BID}
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: database-credentials
              key: url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: redis-credentials
              key: url
        - name: JWT_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: jwt-secrets
              key: secret-key
        resources:
          requests:
            cpu: ${API_CPU_REQUEST}
            memory: ${API_MEMORY_REQUEST}
          limits:
            cpu: ${API_CPU_LIMIT}
            memory: ${API_MEMORY_LIMIT}
        livenessProbe:
          httpGet:
            path: /health
            port: 5000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 5000
          initialDelaySeconds: 5
          periodSeconds: 5
        volumeMounts:
        - name: config
          mountPath: /app/config
          readOnly: true
        - name: logs
          mountPath: /app/logs
      volumes:
      - name: config
        configMap:
          name: ai-shifu-config
      - name: logs
        emptyDir: {}

---
# Web Frontend Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ai-shifu-web
  namespace: tenant-${TENANT_BID}
spec:
  replicas: ${WEB_REPLICAS}
  selector:
    matchLabels:
      app: ai-shifu-web
      tenant: ${TENANT_BID}
  template:
    metadata:
      labels:
        app: ai-shifu-web
        tenant: ${TENANT_BID}
    spec:
      nodeSelector:
        role: application
      containers:
      - name: web
        image: ${ECR_REGISTRY}/ai-shifu-web:${APP_VERSION}
        ports:
        - containerPort: 3000
        env:
        - name: REACT_APP_API_URL
          value: https://${TENANT_DOMAIN}/api
        - name: REACT_APP_TENANT_BID
          value: ${TENANT_BID}
        resources:
          requests:
            cpu: ${WEB_CPU_REQUEST}
            memory: ${WEB_MEMORY_REQUEST}
          limits:
            cpu: ${WEB_CPU_LIMIT}
            memory: ${WEB_MEMORY_LIMIT}

---
# Cook Web (CMS) Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ai-shifu-cook-web
  namespace: tenant-${TENANT_BID}
spec:
  replicas: ${COOK_REPLICAS}
  selector:
    matchLabels:
      app: ai-shifu-cook-web
      tenant: ${TENANT_BID}
  template:
    metadata:
      labels:
        app: ai-shifu-cook-web
        tenant: ${TENANT_BID}
    spec:
      containers:
      - name: cook-web
        image: ${ECR_REGISTRY}/ai-shifu-cook-web:${APP_VERSION}
        ports:
        - containerPort: 3000
        env:
        - name: NEXT_PUBLIC_API_URL
          value: https://${TENANT_DOMAIN}/api
        - name: TENANT_BID
          value: ${TENANT_BID}
```

### 2.3 Database Deployment (StatefulSet)

```yaml
# MySQL StatefulSet for Database-Per-Tenant
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: mysql-${TENANT_BID}
  namespace: tenant-${TENANT_BID}
spec:
  serviceName: mysql-${TENANT_BID}
  replicas: 3  # Primary + 2 replicas
  selector:
    matchLabels:
      app: mysql
      tenant: ${TENANT_BID}
  template:
    metadata:
      labels:
        app: mysql
        tenant: ${TENANT_BID}
    spec:
      nodeSelector:
        role: database
      tolerations:
      - key: database-only
        operator: Equal
        value: "true"
        effect: NoSchedule
      containers:
      - name: mysql
        image: mysql:8.0
        env:
        - name: MYSQL_ROOT_PASSWORD
          valueFrom:
            secretKeyRef:
              name: mysql-credentials
              key: root-password
        - name: MYSQL_DATABASE
          value: ai_shifu_${TENANT_BID}
        - name: MYSQL_USER
          value: ai_shifu
        - name: MYSQL_PASSWORD
          valueFrom:
            secretKeyRef:
              name: mysql-credentials
              key: user-password
        ports:
        - containerPort: 3306
        volumeMounts:
        - name: mysql-storage
          mountPath: /var/lib/mysql
        - name: mysql-config
          mountPath: /etc/mysql/conf.d
        resources:
          requests:
            cpu: ${DB_CPU_REQUEST}
            memory: ${DB_MEMORY_REQUEST}
          limits:
            cpu: ${DB_CPU_LIMIT}
            memory: ${DB_MEMORY_LIMIT}
        livenessProbe:
          exec:
            command:
            - mysqladmin
            - ping
            - -h
            - localhost
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          exec:
            command:
            - mysql
            - -h
            - localhost
            - -e
            - SELECT 1
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: mysql-config
        configMap:
          name: mysql-config
  volumeClaimTemplates:
  - metadata:
      name: mysql-storage
    spec:
      accessModes: ["ReadWriteOnce"]
      storageClassName: ${STORAGE_CLASS}
      resources:
        requests:
          storage: ${DB_STORAGE_SIZE}

---
# Redis Cluster for Caching
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: redis-${TENANT_BID}
  namespace: tenant-${TENANT_BID}
spec:
  serviceName: redis-${TENANT_BID}
  replicas: 3
  selector:
    matchLabels:
      app: redis
      tenant: ${TENANT_BID}
  template:
    metadata:
      labels:
        app: redis
        tenant: ${TENANT_BID}
    spec:
      containers:
      - name: redis
        image: redis:7.0-alpine
        command:
        - redis-server
        - /etc/redis/redis.conf
        ports:
        - containerPort: 6379
        volumeMounts:
        - name: redis-config
          mountPath: /etc/redis
        - name: redis-storage
          mountPath: /data
        resources:
          requests:
            cpu: ${REDIS_CPU_REQUEST}
            memory: ${REDIS_MEMORY_REQUEST}
          limits:
            cpu: ${REDIS_CPU_LIMIT}
            memory: ${REDIS_MEMORY_LIMIT}
      volumes:
      - name: redis-config
        configMap:
          name: redis-config
  volumeClaimTemplates:
  - metadata:
      name: redis-storage
    spec:
      accessModes: ["ReadWriteOnce"]
      storageClassName: ${STORAGE_CLASS}
      resources:
        requests:
          storage: ${REDIS_STORAGE_SIZE}
```

## 3. CI/CD Pipeline

### 3.1 GitOps Workflow

```yaml
# GitHub Actions CI/CD Pipeline
name: AI-Shifu CI/CD Pipeline

on:
  push:
    branches: [main, develop]
    tags: ['v*']
  pull_request:
    branches: [main]

env:
  ECR_REGISTRY: ${{ secrets.ECR_REGISTRY }}
  AWS_REGION: us-west-2

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4

    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Setup Node.js
      uses: actions/setup-node@v4
      with:
        node-version: '18'

    - name: Install API dependencies
      run: |
        cd src/api
        pip install -r requirements.txt
        pip install -r requirements-dev.txt

    - name: Run API tests
      run: |
        cd src/api
        pytest --cov=flaskr --cov-report=xml

    - name: Install Web dependencies
      run: |
        cd src/web
        npm ci

    - name: Run Web tests
      run: |
        cd src/web
        npm test -- --coverage --watchAll=false

    - name: Install Cook Web dependencies
      run: |
        cd src/cook-web
        npm ci

    - name: Run Cook Web tests
      run: |
        cd src/cook-web
        npm run test:ci

    - name: Security scan
      uses: securecodewarrior/github-action-add-sarif@v1
      with:
        sarif-file: security-scan-results.sarif

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main' || startsWith(github.ref, 'refs/tags/v')

    outputs:
      api-image: ${{ steps.build-api.outputs.image }}
      web-image: ${{ steps.build-web.outputs.image }}
      cook-web-image: ${{ steps.build-cook-web.outputs.image }}
      version: ${{ steps.version.outputs.version }}

    steps:
    - uses: actions/checkout@v4

    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v4
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: ${{ env.AWS_REGION }}

    - name: Login to Amazon ECR
      id: login-ecr
      uses: aws-actions/amazon-ecr-login@v2

    - name: Generate version
      id: version
      run: |
        if [[ $GITHUB_REF == refs/tags/v* ]]; then
          VERSION=${GITHUB_REF#refs/tags/}
        else
          VERSION=latest
        fi
        echo "version=$VERSION" >> $GITHUB_OUTPUT

    - name: Build API image
      id: build-api
      run: |
        IMAGE_URI=$ECR_REGISTRY/ai-shifu-api:${{ steps.version.outputs.version }}
        docker build -t $IMAGE_URI src/api
        docker push $IMAGE_URI
        echo "image=$IMAGE_URI" >> $GITHUB_OUTPUT

    - name: Build Web image
      id: build-web
      run: |
        IMAGE_URI=$ECR_REGISTRY/ai-shifu-web:${{ steps.version.outputs.version }}
        docker build -t $IMAGE_URI src/web
        docker push $IMAGE_URI
        echo "image=$IMAGE_URI" >> $GITHUB_OUTPUT

    - name: Build Cook Web image
      id: build-cook-web
      run: |
        IMAGE_URI=$ECR_REGISTRY/ai-shifu-cook-web:${{ steps.version.outputs.version }}
        docker build -t $IMAGE_URI src/cook-web
        docker push $IMAGE_URI
        echo "image=$IMAGE_URI" >> $GITHUB_OUTPUT

  deploy-staging:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    environment: staging

    steps:
    - uses: actions/checkout@v4

    - name: Setup ArgoCD CLI
      run: |
        curl -sSL -o argocd-linux-amd64 https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64
        sudo install -m 555 argocd-linux-amd64 /usr/local/bin/argocd

    - name: Update staging manifests
      run: |
        # Update image tags in staging manifests
        sed -i "s|image: .*ai-shifu-api:.*|image: ${{ needs.build.outputs.api-image }}|g" k8s/staging/api-deployment.yaml
        sed -i "s|image: .*ai-shifu-web:.*|image: ${{ needs.build.outputs.web-image }}|g" k8s/staging/web-deployment.yaml
        sed -i "s|image: .*ai-shifu-cook-web:.*|image: ${{ needs.build.outputs.cook-web-image }}|g" k8s/staging/cook-web-deployment.yaml

        # Commit changes
        git config --local user.email "action@github.com"
        git config --local user.name "GitHub Action"
        git add k8s/staging/
        git commit -m "Update staging images to ${{ needs.build.outputs.version }}" || exit 0
        git push origin main

  deploy-production:
    needs: build
    runs-on: ubuntu-latest
    if: startsWith(github.ref, 'refs/tags/v')
    environment: production

    steps:
    - uses: actions/checkout@v4
      with:
        token: ${{ secrets.GITHUB_TOKEN }}

    - name: Update production manifests
      run: |
        # Update image tags in production manifests
        sed -i "s|image: .*ai-shifu-api:.*|image: ${{ needs.build.outputs.api-image }}|g" k8s/production/api-deployment.yaml
        sed -i "s|image: .*ai-shifu-web:.*|image: ${{ needs.build.outputs.web-image }}|g" k8s/production/web-deployment.yaml
        sed -i "s|image: .*ai-shifu-cook-web:.*|image: ${{ needs.build.outputs.cook-web-image }}|g" k8s/production/cook-web-deployment.yaml

        # Commit changes to trigger ArgoCD sync
        git config --local user.email "action@github.com"
        git config --local user.name "GitHub Action"
        git add k8s/production/
        git commit -m "Deploy ${{ needs.build.outputs.version }} to production"
        git push origin main
```

### 3.2 ArgoCD Configuration

```yaml
# ArgoCD Application for Tenant Management
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: ai-shifu-tenant-manager
  namespace: argocd
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  project: default
  source:
    repoURL: https://github.com/your-org/ai-shifu-deployment
    targetRevision: main
    path: k8s/tenant-manager
    helm:
      valueFiles:
        - values.yaml
  destination:
    server: https://kubernetes.default.svc
    namespace: ai-shifu-system
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true

---
# ArgoCD ApplicationSet for Multi-Tenant Deployment
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: ai-shifu-tenants
  namespace: argocd
spec:
  generators:
  - clusters:
      selector:
        matchLabels:
          ai-shifu.io/tenant-deployment: "true"
  - matrix:
      generators:
      - git:
          repoURL: https://github.com/your-org/ai-shifu-deployment
          revision: main
          directories:
          - path: k8s/tenants/*
      - clusters:
          selector:
            matchLabels:
              ai-shifu.io/tenant-deployment: "true"
  template:
    metadata:
      name: '{{path.basename}}-{{name}}'
    spec:
      project: default
      source:
        repoURL: https://github.com/your-org/ai-shifu-deployment
        targetRevision: main
        path: '{{path}}'
        helm:
          valueFiles:
            - values.yaml
            - values-{{name}}.yaml
      destination:
        server: '{{server}}'
        namespace: 'tenant-{{path.basename}}'
      syncPolicy:
        automated:
          prune: true
          selfHeal: true
        syncOptions:
          - CreateNamespace=true
```

## 4. Environment Management

### 4.1 Environment Configuration

```yaml
# Environment-specific Configuration
environments:
  development:
    replicas:
      api: 1
      web: 1
      cook-web: 1
    resources:
      api:
        cpu: "100m"
        memory: "256Mi"
      web:
        cpu: "50m"
        memory: "128Mi"
      cook-web:
        cpu: "50m"
        memory: "128Mi"
    database:
      storage: "10Gi"
      replicas: 1
    domain: "dev.ai-shifu.com"

  staging:
    replicas:
      api: 2
      web: 2
      cook-web: 1
    resources:
      api:
        cpu: "500m"
        memory: "1Gi"
      web:
        cpu: "200m"
        memory: "512Mi"
      cook-web:
        cpu: "200m"
        memory: "512Mi"
    database:
      storage: "50Gi"
      replicas: 2
    domain: "staging.ai-shifu.com"

  production:
    replicas:
      api: 5
      web: 3
      cook-web: 2
    resources:
      api:
        cpu: "1000m"
        memory: "2Gi"
      web:
        cpu: "500m"
        memory: "1Gi"
      cook-web:
        cpu: "500m"
        memory: "1Gi"
    database:
      storage: "200Gi"
      replicas: 3
    domain: "app.ai-shifu.com"
```

### 4.2 Configuration Management

```python
# Environment Configuration Service
from dataclasses import dataclass
from typing import Dict, Any
import yaml
import os

@dataclass
class EnvironmentConfig:
    name: str
    replicas: Dict[str, int]
    resources: Dict[str, Dict[str, str]]
    database: Dict[str, Any]
    domain: str
    features: Dict[str, bool]

class ConfigurationManager:
    def __init__(self, config_path: str = "/app/config"):
        self.config_path = config_path
        self.environments = self._load_environments()

    def _load_environments(self) -> Dict[str, EnvironmentConfig]:
        """Load environment configurations"""
        environments = {}

        config_file = os.path.join(self.config_path, "environments.yaml")
        with open(config_file, 'r') as f:
            data = yaml.safe_load(f)

        for env_name, env_data in data['environments'].items():
            environments[env_name] = EnvironmentConfig(
                name=env_name,
                replicas=env_data['replicas'],
                resources=env_data['resources'],
                database=env_data['database'],
                domain=env_data['domain'],
                features=env_data.get('features', {})
            )

        return environments

    def get_environment_config(self, environment: str) -> EnvironmentConfig:
        """Get configuration for specific environment"""
        if environment not in self.environments:
            raise ValueError(f"Unknown environment: {environment}")

        return self.environments[environment]

    def generate_tenant_manifests(self, tenant_bid: str,
                                environment: str) -> Dict[str, str]:
        """Generate Kubernetes manifests for tenant deployment"""
        config = self.get_environment_config(environment)

        # Template substitution
        templates = self._load_templates()
        manifests = {}

        for template_name, template_content in templates.items():
            manifest = self._substitute_template(
                template_content, tenant_bid, config
            )
            manifests[template_name] = manifest

        return manifests
```

## 5. Scaling and Load Balancing

### 5.1 Horizontal Pod Autoscaling

```yaml
# HPA for API Server
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: ai-shifu-api-hpa
  namespace: tenant-${TENANT_BID}
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ai-shifu-api
  minReplicas: ${MIN_REPLICAS}
  maxReplicas: ${MAX_REPLICAS}
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  - type: Pods
    pods:
      metric:
        name: request_rate
      target:
        type: AverageValue
        averageValue: "100"
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 100
        periodSeconds: 15
      - type: Pods
        value: 2
        periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 10
        periodSeconds: 60

---
# Vertical Pod Autoscaling
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: ai-shifu-api-vpa
  namespace: tenant-${TENANT_BID}
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ai-shifu-api
  updatePolicy:
    updateMode: "Auto"
  resourcePolicy:
    containerPolicies:
    - containerName: api
      maxAllowed:
        cpu: 2000m
        memory: 4Gi
      minAllowed:
        cpu: 100m
        memory: 256Mi
      controlledResources: ["cpu", "memory"]
```

### 5.2 Cluster Autoscaling

```yaml
# Cluster Autoscaler Configuration
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cluster-autoscaler
  namespace: kube-system
spec:
  replicas: 1
  selector:
    matchLabels:
      app: cluster-autoscaler
  template:
    metadata:
      labels:
        app: cluster-autoscaler
    spec:
      serviceAccountName: cluster-autoscaler
      containers:
      - image: k8s.gcr.io/autoscaling/cluster-autoscaler:v1.27.0
        name: cluster-autoscaler
        resources:
          limits:
            cpu: 100m
            memory: 300Mi
          requests:
            cpu: 100m
            memory: 300Mi
        command:
        - ./cluster-autoscaler
        - --v=4
        - --stderrthreshold=info
        - --cloud-provider=aws
        - --skip-nodes-with-local-storage=false
        - --expander=least-waste
        - --node-group-auto-discovery=asg:tag=k8s.io/cluster-autoscaler/enabled,k8s.io/cluster-autoscaler/ai-shifu-prod
        - --balance-similar-node-groups
        - --scale-down-enabled=true
        - --scale-down-delay-after-add=10m
        - --scale-down-unneeded-time=10m
        - --scale-down-utilization-threshold=0.5
        env:
        - name: AWS_REGION
          value: us-west-2
```

## 6. Multi-Region Deployment

### 6.1 Global Load Balancing

```yaml
# Global Load Balancer Configuration
apiVersion: networking.gke.io/v1
kind: ManagedCertificate
metadata:
  name: ai-shifu-global-cert
spec:
  domains:
    - app.ai-shifu.com
    - *.ai-shifu.com

---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ai-shifu-global-ingress
  annotations:
    kubernetes.io/ingress.global-static-ip-name: "ai-shifu-global-ip"
    networking.gke.io/managed-certificates: "ai-shifu-global-cert"
    kubernetes.io/ingress.class: "gce"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/backend-protocol: "HTTP"
spec:
  rules:
  - host: app.ai-shifu.com
    http:
      paths:
      - path: /*
        pathType: ImplementationSpecific
        backend:
          service:
            name: ai-shifu-frontend
            port:
              number: 80
  - host: api.ai-shifu.com
    http:
      paths:
      - path: /*
        pathType: ImplementationSpecific
        backend:
          service:
            name: ai-shifu-api
            port:
              number: 5000
```

### 6.2 Cross-Region Database Replication

```yaml
# MySQL Cross-Region Replication
apiVersion: v1
kind: ConfigMap
metadata:
  name: mysql-replication-config
  namespace: ai-shifu-system
data:
  my.cnf: |
    [mysqld]
    # Replication configuration
    server-id = ${SERVER_ID}
    log-bin = mysql-bin
    binlog-format = ROW
    gtid-mode = ON
    enforce-gtid-consistency = ON

    # Security
    ssl-ca = /etc/mysql/ssl/ca.pem
    ssl-cert = /etc/mysql/ssl/server-cert.pem
    ssl-key = /etc/mysql/ssl/server-key.pem

    # Performance
    innodb_buffer_pool_size = 1G
    innodb_log_file_size = 256M
    max_connections = 500

    # Backup configuration
    backup-lock-timeout = 3600
    backup-lock-retry-count = 3

---
# Cross-Region Backup Job
apiVersion: batch/v1
kind: CronJob
metadata:
  name: mysql-cross-region-backup
  namespace: ai-shifu-system
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: mysql:8.0
            command:
            - /bin/bash
            - -c
            - |
              mysqldump \
                --host=$MYSQL_HOST \
                --user=$MYSQL_USER \
                --password=$MYSQL_PASSWORD \
                --single-transaction \
                --routines \
                --triggers \
                --all-databases \
                --master-data=2 \
                --flush-logs \
                --lock-tables=false | \
              aws s3 cp - s3://$BACKUP_BUCKET/mysql/$(date +%Y%m%d_%H%M%S).sql.gz --sse=AES256
            env:
            - name: MYSQL_HOST
              value: "mysql-primary"
            - name: MYSQL_USER
              valueFrom:
                secretKeyRef:
                  name: mysql-credentials
                  key: username
            - name: MYSQL_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: mysql-credentials
                  key: password
            - name: BACKUP_BUCKET
              value: "ai-shifu-backups"
          restartPolicy: OnFailure
```

## 7. Disaster Recovery

### 7.1 Backup Strategy

```python
# Disaster Recovery Service
from datetime import datetime, timedelta
import boto3
import subprocess
from typing import List, Dict

class DisasterRecoveryService:
    def __init__(self):
        self.s3_client = boto3.client('s3')
        self.backup_bucket = "ai-shifu-dr-backups"
        self.retention_policies = {
            "daily": 30,    # Keep daily backups for 30 days
            "weekly": 12,   # Keep weekly backups for 12 weeks
            "monthly": 12,  # Keep monthly backups for 12 months
            "yearly": 7     # Keep yearly backups for 7 years
        }

    def create_full_backup(self, tenant_bid: str) -> Dict[str, str]:
        """Create full backup of tenant data"""
        backup_id = f"{tenant_bid}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        # Database backup
        db_backup = self._backup_database(tenant_bid, backup_id)

        # File storage backup
        files_backup = self._backup_files(tenant_bid, backup_id)

        # Configuration backup
        config_backup = self._backup_configuration(tenant_bid, backup_id)

        # Create manifest
        manifest = {
            "backup_id": backup_id,
            "tenant_bid": tenant_bid,
            "timestamp": datetime.utcnow().isoformat(),
            "components": {
                "database": db_backup,
                "files": files_backup,
                "configuration": config_backup
            },
            "backup_type": "full",
            "retention_policy": "daily"
        }

        # Upload manifest
        manifest_key = f"backups/{tenant_bid}/{backup_id}/manifest.json"
        self.s3_client.put_object(
            Bucket=self.backup_bucket,
            Key=manifest_key,
            Body=json.dumps(manifest, indent=2),
            ContentType="application/json"
        )

        return manifest

    def _backup_database(self, tenant_bid: str, backup_id: str) -> str:
        """Backup tenant database"""
        dump_file = f"/tmp/{backup_id}_database.sql"

        # Create database dump
        cmd = [
            "mysqldump",
            f"--host=mysql-{tenant_bid}",
            "--user=backup_user",
            f"--password={self._get_db_password(tenant_bid)}",
            "--single-transaction",
            "--routines",
            "--triggers",
            f"ai_shifu_{tenant_bid}",
            f"--result-file={dump_file}"
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"Database backup failed: {result.stderr}")

        # Compress and upload
        compressed_file = f"{dump_file}.gz"
        subprocess.run(["gzip", dump_file])

        s3_key = f"backups/{tenant_bid}/{backup_id}/database.sql.gz"
        self.s3_client.upload_file(compressed_file, self.backup_bucket, s3_key)

        # Cleanup local file
        os.remove(compressed_file)

        return s3_key

    def restore_tenant(self, tenant_bid: str, backup_id: str,
                      target_environment: str) -> Dict[str, str]:
        """Restore tenant from backup"""

        # Download and parse manifest
        manifest = self._get_backup_manifest(tenant_bid, backup_id)

        # Create target namespace if it doesn't exist
        self._create_tenant_namespace(tenant_bid, target_environment)

        # Restore database
        db_result = self._restore_database(
            tenant_bid, manifest["components"]["database"], target_environment
        )

        # Restore files
        files_result = self._restore_files(
            tenant_bid, manifest["components"]["files"], target_environment
        )

        # Restore configuration
        config_result = self._restore_configuration(
            tenant_bid, manifest["components"]["configuration"], target_environment
        )

        # Start applications
        app_result = self._start_tenant_applications(tenant_bid, target_environment)

        return {
            "restore_id": f"restore_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            "tenant_bid": tenant_bid,
            "backup_id": backup_id,
            "target_environment": target_environment,
            "results": {
                "database": db_result,
                "files": files_result,
                "configuration": config_result,
                "applications": app_result
            },
            "status": "completed",
            "restored_at": datetime.utcnow().isoformat()
        }
```

### 7.2 Recovery Testing

```yaml
# Disaster Recovery Testing Job
apiVersion: batch/v1
kind: Job
metadata:
  name: dr-test-${TEST_ID}
  namespace: ai-shifu-dr
spec:
  template:
    spec:
      containers:
      - name: dr-test
        image: ai-shifu-dr-toolkit:latest
        command:
        - /bin/bash
        - -c
        - |
          # Test database recovery
          echo "Testing database recovery..."
          mysql -h mysql-dr-test -u root -p$MYSQL_ROOT_PASSWORD -e "SHOW DATABASES;"

          # Test application connectivity
          echo "Testing application connectivity..."
          curl -f http://ai-shifu-api-dr-test:5000/health || exit 1

          # Test data integrity
          echo "Testing data integrity..."
          python /scripts/verify_data_integrity.py --tenant=${TENANT_BID}

          # Generate test report
          echo "Generating test report..."
          python /scripts/generate_dr_report.py --test-id=${TEST_ID}
        env:
        - name: MYSQL_ROOT_PASSWORD
          valueFrom:
            secretKeyRef:
              name: mysql-dr-credentials
              key: root-password
        - name: TENANT_BID
          value: ${TENANT_BID}
        - name: TEST_ID
          value: ${TEST_ID}
      restartPolicy: Never
  backoffLimit: 3
```

## 8. Implementation Roadmap

### Phase 1: Infrastructure Foundation (Weeks 1-4)
- Set up Kubernetes clusters (dev, staging, production)
- Implement basic networking and security policies
- Configure container registry and build pipelines
- Set up monitoring and logging infrastructure

### Phase 2: Application Deployment (Weeks 5-8)
- Deploy core AI-Shifu applications
- Implement database StatefulSets
- Configure load balancing and ingress
- Set up basic autoscaling

### Phase 3: Multi-Tenancy (Weeks 9-12)
- Implement tenant isolation mechanisms
- Deploy tenant-specific resources
- Configure tenant-specific domains and certificates
- Implement tenant lifecycle management

### Phase 4: Advanced Features (Weeks 13-16)
- Multi-region deployment
- Advanced monitoring and alerting
- Disaster recovery implementation
- Performance optimization

### Phase 5: Production Hardening (Weeks 17-20)
- Security hardening and penetration testing
- Load testing and performance tuning
- Documentation and runbook creation
- Go-live preparation

This comprehensive deployment strategy ensures that the AI-Shifu SaaS platform can scale efficiently while maintaining security, reliability, and operational excellence across multiple tenants and environments.
