# AI-Shifu SaaS Monitoring and Operations Design

## Overview

This document outlines the comprehensive monitoring and operations strategy for the AI-Shifu SaaS platform, covering observability, alerting, incident response, performance monitoring, and operational automation across multi-tenant environments.

## 1. Observability Architecture

### 1.1 Three Pillars of Observability

```
┌─────────────────────────────────────────────────────────────┐
│                  Observability Stack                        │
├─────────────────┬─────────────────┬─────────────────────────┤
│     Metrics     │     Traces      │         Logs            │
│   (Prometheus)  │    (Jaeger)     │    (ELK/Loki)          │
├─────────────────┼─────────────────┼─────────────────────────┤
│ • System Metrics│ • Request Traces│ • Application Logs      │
│ • App Metrics   │ • Performance   │ • Security Logs         │
│ • Business KPIs │ • Dependencies  │ • Audit Logs           │
│ • SLA Tracking  │ • Error Analysis│ • Debug Information     │
└─────────────────┴─────────────────┴─────────────────────────┘
                             │
                    ┌────────▼────────┐
                    │     Grafana     │
                    │  (Visualization │
                    │  & Dashboards)  │
                    └─────────────────┘
```

### 1.2 Monitoring Stack Components

```yaml
# Prometheus Configuration
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
  namespace: monitoring
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s
      evaluation_interval: 15s
      external_labels:
        cluster: 'ai-shifu-prod'
        environment: 'production'

    rule_files:
      - "rules/*.yml"

    scrape_configs:
      # Kubernetes API Server
      - job_name: 'kubernetes-apiservers'
        kubernetes_sd_configs:
        - role: endpoints
        scheme: https
        tls_config:
          ca_file: /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
        bearer_token_file: /var/run/secrets/kubernetes.io/serviceaccount/token
        relabel_configs:
        - source_labels: [__meta_kubernetes_namespace, __meta_kubernetes_service_name, __meta_kubernetes_endpoint_port_name]
          action: keep
          regex: default;kubernetes;https

      # AI-Shifu Applications
      - job_name: 'ai-shifu-api'
        kubernetes_sd_configs:
        - role: pod
        relabel_configs:
        - source_labels: [__meta_kubernetes_pod_label_app]
          action: keep
          regex: ai-shifu-api
        - source_labels: [__meta_kubernetes_pod_label_tenant]
          target_label: tenant_bid
        - source_labels: [__address__, __meta_kubernetes_pod_annotation_prometheus_io_port]
          action: replace
          regex: ([^:]+)(?::\d+)?;(\d+)
          replacement: $1:$2
          target_label: __address__

      # Database Metrics
      - job_name: 'mysql-exporter'
        kubernetes_sd_configs:
        - role: service
        relabel_configs:
        - source_labels: [__meta_kubernetes_service_label_app]
          action: keep
          regex: mysql-exporter
        - source_labels: [__meta_kubernetes_service_label_tenant]
          target_label: tenant_bid

      # Redis Metrics
      - job_name: 'redis-exporter'
        kubernetes_sd_configs:
        - role: service
        relabel_configs:
        - source_labels: [__meta_kubernetes_service_label_app]
          action: keep
          regex: redis-exporter
        - source_labels: [__meta_kubernetes_service_label_tenant]
          target_label: tenant_bid

    alerting:
      alertmanagers:
      - static_configs:
        - targets:
          - alertmanager:9093

---
# Grafana Configuration
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-config
  namespace: monitoring
data:
  grafana.ini: |
    [server]
    root_url = https://monitoring.ai-shifu.com/grafana

    [security]
    admin_user = admin
    admin_password = ${GRAFANA_ADMIN_PASSWORD}
    secret_key = ${GRAFANA_SECRET_KEY}

    [auth.generic_oauth]
    enabled = true
    name = OAuth
    allow_sign_up = true
    client_id = ${OAUTH_CLIENT_ID}
    client_secret = ${OAUTH_CLIENT_SECRET}
    scopes = openid profile email
    auth_url = https://auth.ai-shifu.com/oauth/authorize
    token_url = https://auth.ai-shifu.com/oauth/token
    api_url = https://auth.ai-shifu.com/oauth/userinfo

    [dashboards]
    default_home_dashboard_path = /var/lib/grafana/dashboards/ai-shifu-overview.json

    [alerting]
    enabled = true
    execute_alerts = true
```

## 2. Application Performance Monitoring (APM)

### 2.1 Custom Metrics Implementation

```python
# Application Metrics Service
from prometheus_client import Counter, Histogram, Gauge, start_http_server
from functools import wraps
import time
import logging

class MetricsService:
    def __init__(self):
        # Request metrics
        self.request_count = Counter(
            'ai_shifu_requests_total',
            'Total number of HTTP requests',
            ['method', 'endpoint', 'status', 'tenant']
        )

        self.request_duration = Histogram(
            'ai_shifu_request_duration_seconds',
            'HTTP request duration in seconds',
            ['method', 'endpoint', 'tenant'],
            buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
        )

        # Business metrics
        self.active_sessions = Gauge(
            'ai_shifu_active_sessions',
            'Number of active user sessions',
            ['tenant']
        )

        self.shifu_interactions = Counter(
            'ai_shifu_interactions_total',
            'Total number of Shifu interactions',
            ['tenant', 'shifu_type', 'interaction_type']
        )

        self.llm_requests = Counter(
            'ai_shifu_llm_requests_total',
            'Total LLM API requests',
            ['provider', 'model', 'tenant', 'status']
        )

        self.llm_token_usage = Counter(
            'ai_shifu_llm_tokens_total',
            'Total LLM token usage',
            ['provider', 'model', 'tenant', 'token_type']
        )

        # Database metrics
        self.db_connections = Gauge(
            'ai_shifu_db_connections',
            'Number of database connections',
            ['tenant', 'pool']
        )

        self.db_query_duration = Histogram(
            'ai_shifu_db_query_duration_seconds',
            'Database query duration in seconds',
            ['tenant', 'operation'],
            buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5]
        )

        # Error metrics
        self.error_count = Counter(
            'ai_shifu_errors_total',
            'Total number of errors',
            ['tenant', 'service', 'error_type']
        )

        # Cache metrics
        self.cache_hits = Counter(
            'ai_shifu_cache_hits_total',
            'Total cache hits',
            ['tenant', 'cache_type']
        )

        self.cache_misses = Counter(
            'ai_shifu_cache_misses_total',
            'Total cache misses',
            ['tenant', 'cache_type']
        )

    def track_request(self, method: str, endpoint: str, tenant: str):
        """Decorator to track HTTP requests"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                status = 'success'

                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    status = 'error'
                    self.error_count.labels(
                        tenant=tenant,
                        service='api',
                        error_type=type(e).__name__
                    ).inc()
                    raise
                finally:
                    duration = time.time() - start_time

                    self.request_count.labels(
                        method=method,
                        endpoint=endpoint,
                        status=status,
                        tenant=tenant
                    ).inc()

                    self.request_duration.labels(
                        method=method,
                        endpoint=endpoint,
                        tenant=tenant
                    ).observe(duration)

            return wrapper
        return decorator

    def track_llm_usage(self, provider: str, model: str, tenant: str,
                       prompt_tokens: int, completion_tokens: int):
        """Track LLM API usage"""
        self.llm_requests.labels(
            provider=provider,
            model=model,
            tenant=tenant,
            status='success'
        ).inc()

        self.llm_token_usage.labels(
            provider=provider,
            model=model,
            tenant=tenant,
            token_type='prompt'
        ).inc(prompt_tokens)

        self.llm_token_usage.labels(
            provider=provider,
            model=model,
            tenant=tenant,
            token_type='completion'
        ).inc(completion_tokens)

    def track_database_query(self, tenant: str, operation: str):
        """Decorator to track database queries"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()

                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    duration = time.time() - start_time
                    self.db_query_duration.labels(
                        tenant=tenant,
                        operation=operation
                    ).observe(duration)

            return wrapper
        return decorator

# Usage in Flask application
metrics = MetricsService()

@app.route('/api/shifu/<shifu_bid>/interact', methods=['POST'])
@metrics.track_request('POST', '/api/shifu/interact', get_tenant_bid())
def interact_with_shifu(shifu_bid):
    """Shifu interaction endpoint with metrics"""
    tenant_bid = get_tenant_bid()

    # Track active session
    metrics.active_sessions.labels(tenant=tenant_bid).inc()

    try:
        # Process interaction
        result = process_shifu_interaction(shifu_bid, request.json)

        # Track interaction metrics
        metrics.shifu_interactions.labels(
            tenant=tenant_bid,
            shifu_type=result['shifu_type'],
            interaction_type=result['interaction_type']
        ).inc()

        return jsonify(result)

    finally:
        # Track session end
        metrics.active_sessions.labels(tenant=tenant_bid).dec()
```

### 2.2 Distributed Tracing Configuration

```yaml
# Jaeger Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: jaeger
  namespace: monitoring
spec:
  replicas: 1
  selector:
    matchLabels:
      app: jaeger
  template:
    metadata:
      labels:
        app: jaeger
    spec:
      containers:
      - name: jaeger
        image: jaegertracing/all-in-one:latest
        env:
        - name: COLLECTOR_ZIPKIN_HTTP_PORT
          value: "9411"
        - name: SPAN_STORAGE_TYPE
          value: "elasticsearch"
        - name: ES_SERVER_URLS
          value: "http://elasticsearch:9200"
        - name: ES_USERNAME
          value: "jaeger"
        - name: ES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: elasticsearch-credentials
              key: password
        ports:
        - containerPort: 16686  # UI
        - containerPort: 14268  # HTTP collector
        - containerPort: 9411   # Zipkin collector
        - containerPort: 6831   # UDP agent
        - containerPort: 6832   # UDP agent
        resources:
          requests:
            cpu: 100m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 1Gi

---
# OpenTelemetry Collector
apiVersion: apps/v1
kind: Deployment
metadata:
  name: otel-collector
  namespace: monitoring
spec:
  replicas: 2
  selector:
    matchLabels:
      app: otel-collector
  template:
    metadata:
      labels:
        app: otel-collector
    spec:
      containers:
      - name: otel-collector
        image: otel/opentelemetry-collector:latest
        command:
        - /otelcol
        - --config=/etc/otel-collector-config.yaml
        volumeMounts:
        - name: config
          mountPath: /etc/otel-collector-config.yaml
          subPath: otel-collector-config.yaml
        ports:
        - containerPort: 8888  # Prometheus metrics
        - containerPort: 8889  # Prometheus exporter
        - containerPort: 13133 # Health check
        - containerPort: 4317  # OTLP gRPC receiver
        - containerPort: 4318  # OTLP HTTP receiver
      volumes:
      - name: config
        configMap:
          name: otel-collector-config

---
apiVersion: v1
kind: ConfigMap
metadata:
  name: otel-collector-config
  namespace: monitoring
data:
  otel-collector-config.yaml: |
    receivers:
      otlp:
        protocols:
          grpc:
            endpoint: 0.0.0.0:4317
          http:
            endpoint: 0.0.0.0:4318

      prometheus:
        config:
          scrape_configs:
          - job_name: 'ai-shifu-metrics'
            static_configs:
            - targets: ['ai-shifu-api:5000']

    processors:
      batch:

      attributes:
        actions:
        - key: tenant_bid
          action: insert
          from_attribute: tenant
        - key: environment
          action: insert
          value: production

    exporters:
      jaeger:
        endpoint: jaeger:14250
        tls:
          insecure: true

      prometheus:
        endpoint: "0.0.0.0:8889"

      logging:
        loglevel: debug

    service:
      pipelines:
        traces:
          receivers: [otlp]
          processors: [batch, attributes]
          exporters: [jaeger, logging]

        metrics:
          receivers: [otlp, prometheus]
          processors: [batch, attributes]
          exporters: [prometheus, logging]
```

## 3. Logging Infrastructure

### 3.1 Centralized Logging with ELK Stack

```yaml
# Elasticsearch Cluster
apiVersion: elasticsearch.k8s.elastic.co/v1
kind: Elasticsearch
metadata:
  name: ai-shifu-elasticsearch
  namespace: logging
spec:
  version: 8.8.0
  nodeSets:
  - name: master
    count: 3
    config:
      node.roles: ["master"]
      xpack.security.enabled: true
      xpack.security.authc:
        anonymous:
          roles: monitoring
          username: anonymous
    podTemplate:
      spec:
        containers:
        - name: elasticsearch
          resources:
            requests:
              memory: 2Gi
              cpu: 1000m
            limits:
              memory: 4Gi
              cpu: 2000m
          env:
          - name: ES_JAVA_OPTS
            value: -Xms2g -Xmx2g
    volumeClaimTemplates:
    - metadata:
        name: elasticsearch-data
      spec:
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 50Gi
        storageClassName: fast-ssd

  - name: data
    count: 3
    config:
      node.roles: ["data", "ingest"]
      xpack.security.enabled: true
    podTemplate:
      spec:
        containers:
        - name: elasticsearch
          resources:
            requests:
              memory: 4Gi
              cpu: 2000m
            limits:
              memory: 8Gi
              cpu: 4000m
          env:
          - name: ES_JAVA_OPTS
            value: -Xms4g -Xmx4g
    volumeClaimTemplates:
    - metadata:
        name: elasticsearch-data
      spec:
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 200Gi
        storageClassName: fast-ssd

---
# Kibana Deployment
apiVersion: kibana.k8s.elastic.co/v1
kind: Kibana
metadata:
  name: ai-shifu-kibana
  namespace: logging
spec:
  version: 8.8.0
  count: 2
  elasticsearchRef:
    name: ai-shifu-elasticsearch
  config:
    server.publicBaseUrl: "https://logs.ai-shifu.com"
    xpack.security.encryptionKey: ${KIBANA_ENCRYPTION_KEY}
    xpack.encryptedSavedObjects.encryptionKey: ${KIBANA_SAVED_OBJECTS_KEY}
  podTemplate:
    spec:
      containers:
      - name: kibana
        resources:
          requests:
            memory: 1Gi
            cpu: 500m
          limits:
            memory: 2Gi
            cpu: 1000m

---
# Logstash Configuration
apiVersion: apps/v1
kind: Deployment
metadata:
  name: logstash
  namespace: logging
spec:
  replicas: 3
  selector:
    matchLabels:
      app: logstash
  template:
    metadata:
      labels:
        app: logstash
    spec:
      containers:
      - name: logstash
        image: docker.elastic.co/logstash/logstash:8.8.0
        volumeMounts:
        - name: config
          mountPath: /usr/share/logstash/pipeline
        - name: logstash-yml
          mountPath: /usr/share/logstash/config/logstash.yml
          subPath: logstash.yml
        resources:
          requests:
            cpu: 500m
            memory: 1Gi
          limits:
            cpu: 1000m
            memory: 2Gi
        env:
        - name: LS_JAVA_OPTS
          value: "-Xmx1g -Xms1g"
      volumes:
      - name: config
        configMap:
          name: logstash-config
      - name: logstash-yml
        configMap:
          name: logstash-yml

---
apiVersion: v1
kind: ConfigMap
metadata:
  name: logstash-config
  namespace: logging
data:
  logstash.conf: |
    input {
      beats {
        port => 5044
      }

      http {
        port => 8080
        codec => json
        additional_codecs => {
          "application/json" => "json"
        }
      }
    }

    filter {
      # Parse JSON logs
      if [fields][log_type] == "application" {
        json {
          source => "message"
        }

        # Add tenant information
        if [tenant_bid] {
          mutate {
            add_field => { "[@metadata][index_suffix]" => "-%{tenant_bid}" }
          }
        } else {
          mutate {
            add_field => { "[@metadata][index_suffix]" => "-shared" }
          }
        }

        # Parse timestamp
        date {
          match => [ "timestamp", "ISO8601" ]
          target => "@timestamp"
        }

        # Categorize log levels
        if [level] == "ERROR" or [level] == "FATAL" {
          mutate {
            add_tag => [ "error" ]
          }
        } else if [level] == "WARN" {
          mutate {
            add_tag => [ "warning" ]
          }
        }

        # Extract request information
        if [request_id] {
          mutate {
            add_field => { "trace_id" => "%{request_id}" }
          }
        }
      }

      # Parse security logs
      if [fields][log_type] == "security" {
        grok {
          match => {
            "message" => "%{TIMESTAMP_ISO8601:timestamp} \[%{WORD:severity}\] %{WORD:event_type} user=%{WORD:user_bid} tenant=%{WORD:tenant_bid} ip=%{IP:source_ip} result=%{WORD:result}"
          }
        }

        mutate {
          add_tag => [ "security", "audit" ]
          add_field => { "[@metadata][index_suffix]" => "-security" }
        }
      }

      # Enrich with GeoIP
      if [source_ip] {
        geoip {
          source => "source_ip"
          target => "geoip"
        }
      }
    }

    output {
      elasticsearch {
        hosts => ["ai-shifu-elasticsearch-es-http:9200"]
        user => "${ELASTIC_USER}"
        password => "${ELASTIC_PASSWORD}"
        ssl => true
        ssl_certificate_verification => false
        index => "ai-shifu-logs-%{+YYYY.MM.dd}%{[@metadata][index_suffix]}"
        template_name => "ai-shifu-logs"
        template => "/usr/share/logstash/templates/ai-shifu-template.json"
        template_overwrite => true
      }

      stdout {
        codec => rubydebug
      }
    }
```

### 3.2 Application Logging Configuration

```python
# Structured Logging Configuration
import logging
import json
from datetime import datetime
from flask import request, g
import traceback

class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""

    def format(self, record):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }

        # Add request context if available
        if hasattr(g, 'tenant_bid'):
            log_entry["tenant_bid"] = g.tenant_bid

        if hasattr(g, 'user_bid'):
            log_entry["user_bid"] = g.user_bid

        if request:
            log_entry.update({
                "request_id": getattr(g, 'request_id', None),
                "method": request.method,
                "url": request.url,
                "remote_addr": request.remote_addr,
                "user_agent": request.headers.get('User-Agent')
            })

        # Add exception information
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info)
            }

        # Add custom fields
        if hasattr(record, 'custom_fields'):
            log_entry.update(record.custom_fields)

        return json.dumps(log_entry, ensure_ascii=False)

# Logging configuration
def configure_logging(app):
    """Configure application logging"""

    # Remove default handlers
    app.logger.handlers.clear()

    # Console handler with JSON formatting
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(JSONFormatter())
    console_handler.setLevel(logging.INFO)

    # File handler for persistent storage
    file_handler = logging.FileHandler('/app/logs/ai-shifu.log')
    file_handler.setFormatter(JSONFormatter())
    file_handler.setLevel(logging.INFO)

    # Error file handler
    error_handler = logging.FileHandler('/app/logs/ai-shifu-errors.log')
    error_handler.setFormatter(JSONFormatter())
    error_handler.setLevel(logging.ERROR)

    # Add handlers
    app.logger.addHandler(console_handler)
    app.logger.addHandler(file_handler)
    app.logger.addHandler(error_handler)
    app.logger.setLevel(logging.INFO)

    # Security logger
    security_logger = logging.getLogger('security')
    security_handler = logging.FileHandler('/app/logs/security.log')
    security_handler.setFormatter(JSONFormatter())
    security_logger.addHandler(security_handler)
    security_logger.setLevel(logging.INFO)

# Logging utilities
class LoggingService:
    def __init__(self):
        self.app_logger = logging.getLogger(__name__)
        self.security_logger = logging.getLogger('security')
        self.business_logger = logging.getLogger('business')

    def log_security_event(self, event_type: str, details: dict):
        """Log security events"""
        self.security_logger.info(
            f"Security event: {event_type}",
            extra={
                "custom_fields": {
                    "event_type": event_type,
                    "security_event": True,
                    **details
                }
            }
        )

    def log_business_event(self, event_type: str, details: dict):
        """Log business events"""
        self.business_logger.info(
            f"Business event: {event_type}",
            extra={
                "custom_fields": {
                    "event_type": event_type,
                    "business_event": True,
                    **details
                }
            }
        )

    def log_error(self, error: Exception, context: dict = None):
        """Log errors with context"""
        self.app_logger.error(
            f"Application error: {str(error)}",
            exc_info=True,
            extra={
                "custom_fields": {
                    "error_type": type(error).__name__,
                    "context": context or {}
                }
            }
        )
```

## 4. Alerting and Incident Management

### 4.1 AlertManager Configuration

```yaml
# AlertManager Configuration
apiVersion: v1
kind: ConfigMap
metadata:
  name: alertmanager-config
  namespace: monitoring
data:
  alertmanager.yml: |
    global:
      smtp_smarthost: 'smtp.gmail.com:587'
      smtp_from: 'alerts@ai-shifu.com'
      smtp_auth_username: ${SMTP_USERNAME}
      smtp_auth_password: ${SMTP_PASSWORD}

    route:
      group_by: ['alertname', 'tenant']
      group_wait: 30s
      group_interval: 5m
      repeat_interval: 12h
      receiver: 'default'
      routes:
      # Critical alerts
      - match:
          severity: critical
        receiver: 'critical-alerts'
        group_wait: 10s
        group_interval: 1m
        repeat_interval: 5m

      # Tenant-specific alerts
      - match_re:
          tenant: '.+'
        receiver: 'tenant-alerts'
        group_by: ['tenant', 'alertname']

      # Security alerts
      - match:
          category: security
        receiver: 'security-team'
        group_wait: 0s
        group_interval: 30s
        repeat_interval: 1h

    receivers:
    - name: 'default'
      email_configs:
      - to: 'ops-team@ai-shifu.com'
        subject: '[AI-Shifu] {{ .GroupLabels.alertname }}'
        body: |
          {{ range .Alerts }}
          Alert: {{ .Annotations.summary }}
          Description: {{ .Annotations.description }}
          Labels: {{ range .Labels.SortedPairs }}{{ .Name }}={{ .Value }}, {{ end }}
          {{ end }}

    - name: 'critical-alerts'
      email_configs:
      - to: 'critical-alerts@ai-shifu.com'
        subject: '[AI-Shifu CRITICAL] {{ .GroupLabels.alertname }}'
        body: |
          CRITICAL ALERT TRIGGERED

          {{ range .Alerts }}
          Alert: {{ .Annotations.summary }}
          Description: {{ .Annotations.description }}
          Severity: {{ .Labels.severity }}
          Tenant: {{ .Labels.tenant }}
          Started: {{ .StartsAt }}
          {{ end }}

      slack_configs:
      - api_url: ${SLACK_WEBHOOK_URL}
        channel: '#critical-alerts'
        title: 'Critical Alert: {{ .GroupLabels.alertname }}'
        text: |
          {{ range .Alerts }}
          🚨 **CRITICAL ALERT**
          **Alert:** {{ .Annotations.summary }}
          **Description:** {{ .Annotations.description }}
          **Tenant:** {{ .Labels.tenant }}
          **Started:** {{ .StartsAt }}
          {{ end }}

    - name: 'tenant-alerts'
      webhook_configs:
      - url: 'https://api.ai-shifu.com/webhooks/alerts'
        send_resolved: true
        http_config:
          bearer_token: ${WEBHOOK_TOKEN}

    - name: 'security-team'
      email_configs:
      - to: 'security@ai-shifu.com'
        subject: '[AI-Shifu SECURITY] {{ .GroupLabels.alertname }}'
        body: |
          SECURITY ALERT

          {{ range .Alerts }}
          Alert: {{ .Annotations.summary }}
          Description: {{ .Annotations.description }}
          Tenant: {{ .Labels.tenant }}
          Source IP: {{ .Labels.source_ip }}
          User: {{ .Labels.user_bid }}
          Started: {{ .StartsAt }}
          {{ end }}

---
# Prometheus Alert Rules
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-rules
  namespace: monitoring
data:
  ai-shifu-rules.yml: |
    groups:
    - name: ai-shifu.rules
      interval: 30s
      rules:

      # Application Health
      - alert: ApplicationDown
        expr: up{job="ai-shifu-api"} == 0
        for: 1m
        labels:
          severity: critical
          category: availability
        annotations:
          summary: "AI-Shifu API is down"
          description: "AI-Shifu API for tenant {{ $labels.tenant }} has been down for more than 1 minute."

      # High Error Rate
      - alert: HighErrorRate
        expr: (
          rate(ai_shifu_requests_total{status="error"}[5m]) /
          rate(ai_shifu_requests_total[5m])
        ) > 0.05
        for: 2m
        labels:
          severity: warning
          category: errors
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }} for tenant {{ $labels.tenant }}"

      # High Response Time
      - alert: HighResponseTime
        expr: histogram_quantile(0.95, rate(ai_shifu_request_duration_seconds_bucket[5m])) > 2
        for: 3m
        labels:
          severity: warning
          category: performance
        annotations:
          summary: "High response time detected"
          description: "95th percentile response time is {{ $value }}s for tenant {{ $labels.tenant }}"

      # Database Issues
      - alert: DatabaseConnectionHigh
        expr: ai_shifu_db_connections > 80
        for: 2m
        labels:
          severity: warning
          category: database
        annotations:
          summary: "High database connection count"
          description: "Database connections for tenant {{ $labels.tenant }} is {{ $value }}"

      - alert: DatabaseSlowQuery
        expr: histogram_quantile(0.95, rate(ai_shifu_db_query_duration_seconds_bucket[5m])) > 1
        for: 3m
        labels:
          severity: warning
          category: database
        annotations:
          summary: "Slow database queries detected"
          description: "95th percentile DB query time is {{ $value }}s for tenant {{ $labels.tenant }}"

      # Resource Usage
      - alert: HighCPUUsage
        expr: (
          rate(container_cpu_usage_seconds_total{pod=~"ai-shifu-.*"}[5m]) * 100
        ) > 80
        for: 5m
        labels:
          severity: warning
          category: resources
        annotations:
          summary: "High CPU usage"
          description: "CPU usage is {{ $value }}% for pod {{ $labels.pod }}"

      - alert: HighMemoryUsage
        expr: (
          container_memory_working_set_bytes{pod=~"ai-shifu-.*"} /
          container_spec_memory_limit_bytes{pod=~"ai-shifu-.*"}
        ) * 100 > 85
        for: 5m
        labels:
          severity: warning
          category: resources
        annotations:
          summary: "High memory usage"
          description: "Memory usage is {{ $value }}% for pod {{ $labels.pod }}"

      # Security Alerts
      - alert: UnauthorizedAccess
        expr: increase(ai_shifu_errors_total{error_type="Unauthorized"}[5m]) > 10
        for: 1m
        labels:
          severity: critical
          category: security
        annotations:
          summary: "Multiple unauthorized access attempts"
          description: "{{ $value }} unauthorized access attempts in last 5 minutes for tenant {{ $labels.tenant }}"

      # Business Metrics
      - alert: LowActiveUsers
        expr: ai_shifu_active_sessions < 1
        for: 10m
        labels:
          severity: info
          category: business
        annotations:
          summary: "Low active user count"
          description: "Only {{ $value }} active sessions for tenant {{ $labels.tenant }}"

      - alert: HighLLMTokenUsage
        expr: (
          rate(ai_shifu_llm_tokens_total[1h]) >
          on(tenant) ai_shifu_tenant_token_limit * 0.9
        )
        for: 5m
        labels:
          severity: warning
          category: billing
        annotations:
          summary: "High LLM token usage"
          description: "Tenant {{ $labels.tenant }} approaching token limit"
```

### 4.2 Incident Response Automation

```python
# Incident Response Service
from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime
import requests
import logging

@dataclass
class Incident:
    id: str
    title: str
    description: str
    severity: str  # low, medium, high, critical
    status: str    # open, investigating, resolved
    tenant_bid: Optional[str]
    affected_services: List[str]
    created_at: datetime
    resolved_at: Optional[datetime]
    assignee: Optional[str]
    tags: List[str]

class IncidentManager:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.incidents = {}
        self.escalation_rules = self._load_escalation_rules()

    def create_incident(self, alert_data: dict) -> Incident:
        """Create incident from alert"""
        incident = Incident(
            id=f"INC-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}",
            title=alert_data.get('alertname', 'Unknown Alert'),
            description=alert_data.get('description', ''),
            severity=self._map_severity(alert_data.get('severity', 'unknown')),
            status='open',
            tenant_bid=alert_data.get('tenant'),
            affected_services=self._identify_affected_services(alert_data),
            created_at=datetime.utcnow(),
            resolved_at=None,
            assignee=None,
            tags=alert_data.get('tags', [])
        )

        self.incidents[incident.id] = incident

        # Auto-assign based on rules
        self._auto_assign_incident(incident)

        # Trigger automated response
        self._trigger_automated_response(incident, alert_data)

        # Log incident creation
        self.logger.info(
            f"Incident created: {incident.id}",
            extra={
                "custom_fields": {
                    "incident_id": incident.id,
                    "severity": incident.severity,
                    "tenant_bid": incident.tenant_bid
                }
            }
        )

        return incident

    def _trigger_automated_response(self, incident: Incident, alert_data: dict):
        """Trigger automated incident response"""

        # Critical incidents
        if incident.severity == 'critical':
            self._handle_critical_incident(incident, alert_data)

        # Security incidents
        if 'security' in incident.tags:
            self._handle_security_incident(incident, alert_data)

        # Performance incidents
        if 'performance' in incident.tags:
            self._handle_performance_incident(incident, alert_data)

        # Database incidents
        if 'database' in incident.tags:
            self._handle_database_incident(incident, alert_data)

    def _handle_critical_incident(self, incident: Incident, alert_data: dict):
        """Handle critical incidents with automated response"""

        # Scale up resources
        if 'high_cpu' in alert_data.get('alertname', '').lower():
            self._scale_application(incident.tenant_bid, 'api', scale_factor=2)

        # Restart unhealthy services
        if 'application_down' in alert_data.get('alertname', '').lower():
            self._restart_service(incident.tenant_bid, 'api')

        # Enable maintenance mode if needed
        if incident.severity == 'critical' and len(incident.affected_services) > 2:
            self._enable_maintenance_mode(incident.tenant_bid)

    def _handle_security_incident(self, incident: Incident, alert_data: dict):
        """Handle security incidents"""

        # Block suspicious IPs
        if 'unauthorized_access' in alert_data.get('alertname', '').lower():
            source_ip = alert_data.get('source_ip')
            if source_ip:
                self._block_ip_address(source_ip)

        # Disable compromised accounts
        if 'account_compromise' in incident.tags:
            user_bid = alert_data.get('user_bid')
            if user_bid:
                self._disable_user_account(user_bid)

    def _scale_application(self, tenant_bid: str, service: str, scale_factor: int):
        """Scale application resources"""
        try:
            # Call Kubernetes API to scale deployment
            response = requests.patch(
                f"https://kubernetes.default.svc/apis/apps/v1/namespaces/tenant-{tenant_bid}/deployments/ai-shifu-{service}",
                headers={"Authorization": f"Bearer {self._get_k8s_token()}"},
                json={
                    "spec": {
                        "replicas": self._get_current_replicas(tenant_bid, service) * scale_factor
                    }
                }
            )

            if response.status_code == 200:
                self.logger.info(f"Scaled {service} for tenant {tenant_bid} by factor {scale_factor}")
            else:
                self.logger.error(f"Failed to scale {service}: {response.text}")

        except Exception as e:
            self.logger.error(f"Error scaling application: {str(e)}")

    def _restart_service(self, tenant_bid: str, service: str):
        """Restart service by deleting pods"""
        try:
            response = requests.delete(
                f"https://kubernetes.default.svc/api/v1/namespaces/tenant-{tenant_bid}/pods",
                headers={"Authorization": f"Bearer {self._get_k8s_token()}"},
                params={
                    "labelSelector": f"app=ai-shifu-{service},tenant={tenant_bid}"
                }
            )

            if response.status_code in [200, 202]:
                self.logger.info(f"Restarted {service} for tenant {tenant_bid}")
            else:
                self.logger.error(f"Failed to restart {service}: {response.text}")

        except Exception as e:
            self.logger.error(f"Error restarting service: {str(e)}")

# Webhook endpoint for AlertManager
@app.route('/webhooks/alerts', methods=['POST'])
def handle_alert_webhook():
    """Handle incoming alerts from AlertManager"""

    alerts = request.json.get('alerts', [])
    incident_manager = IncidentManager()

    for alert in alerts:
        # Create incident for firing alerts
        if alert['status'] == 'firing':
            incident = incident_manager.create_incident(alert)

        # Resolve incident for resolved alerts
        elif alert['status'] == 'resolved':
            incident_manager.resolve_incident_by_alert(alert)

    return jsonify({"status": "processed"})
```

## 5. Performance Monitoring

### 5.1 SLA Monitoring Dashboard

```json
{
  "dashboard": {
    "title": "AI-Shifu SLA Dashboard",
    "tags": ["ai-shifu", "sla", "monitoring"],
    "timezone": "UTC",
    "panels": [
      {
        "title": "Overall System Health",
        "type": "stat",
        "targets": [
          {
            "expr": "avg(up{job=\"ai-shifu-api\"})",
            "legendFormat": "Availability"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "thresholds": {
              "steps": [
                {"color": "red", "value": 0},
                {"color": "yellow", "value": 0.95},
                {"color": "green", "value": 0.99}
              ]
            }
          }
        }
      },
      {
        "title": "Response Time SLA (95th Percentile)",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(ai_shifu_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th Percentile - {{tenant}}"
          }
        ],
        "yAxes": [
          {
            "label": "Response Time (seconds)",
            "max": 2,
            "min": 0
          }
        ]
      },
      {
        "title": "Error Rate by Tenant",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(ai_shifu_requests_total{status=\"error\"}[5m]) / rate(ai_shifu_requests_total[5m]) * 100",
            "legendFormat": "Error Rate - {{tenant}}"
          }
        ],
        "yAxes": [
          {
            "label": "Error Rate (%)",
            "max": 5,
            "min": 0
          }
        ]
      },
      {
        "title": "Active Sessions by Tenant",
        "type": "graph",
        "targets": [
          {
            "expr": "ai_shifu_active_sessions",
            "legendFormat": "Active Sessions - {{tenant}}"
          }
        ]
      },
      {
        "title": "LLM Token Usage vs Limits",
        "type": "bargauge",
        "targets": [
          {
            "expr": "rate(ai_shifu_llm_tokens_total[1h]) / on(tenant) ai_shifu_tenant_token_limit * 100",
            "legendFormat": "{{tenant}}"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "max": 100,
            "min": 0,
            "unit": "percent",
            "thresholds": {
              "steps": [
                {"color": "green", "value": 0},
                {"color": "yellow", "value": 70},
                {"color": "red", "value": 90}
              ]
            }
          }
        }
      },
      {
        "title": "Database Performance",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(ai_shifu_db_query_duration_seconds_bucket[5m]))",
            "legendFormat": "95th Percentile Query Time - {{tenant}}"
          },
          {
            "expr": "ai_shifu_db_connections",
            "legendFormat": "Active Connections - {{tenant}}",
            "yAxis": 2
          }
        ]
      }
    ]
  }
}
```

### 5.2 Tenant-Specific Monitoring

```python
# Tenant Performance Monitoring Service
from typing import Dict, List
import redis
import json
from datetime import datetime, timedelta

class TenantMonitoringService:
    def __init__(self):
        self.redis_client = redis.Redis.from_url(get_config("REDIS_URL"))
        self.metrics_retention = timedelta(days=90)

    def track_tenant_performance(self, tenant_bid: str, metrics: Dict):
        """Track performance metrics for specific tenant"""

        timestamp = datetime.utcnow()
        key = f"tenant_metrics:{tenant_bid}:{timestamp.strftime('%Y%m%d%H%M')}"

        # Store metrics with expiration
        self.redis_client.hset(key, mapping=metrics)
        self.redis_client.expire(key, int(self.metrics_retention.total_seconds()))

        # Update rolling aggregates
        self._update_rolling_aggregates(tenant_bid, metrics, timestamp)

    def _update_rolling_aggregates(self, tenant_bid: str, metrics: Dict, timestamp: datetime):
        """Update rolling performance aggregates"""

        windows = {
            '5m': timedelta(minutes=5),
            '1h': timedelta(hours=1),
            '1d': timedelta(days=1)
        }

        for window_name, window_duration in windows.items():
            window_key = f"tenant_agg:{tenant_bid}:{window_name}"

            # Get current window data
            current_data = self.redis_client.hgetall(window_key)
            if current_data:
                current_data = {k.decode(): float(v.decode()) for k, v in current_data.items()}
            else:
                current_data = {}

            # Update aggregates
            for metric_name, value in metrics.items():
                if isinstance(value, (int, float)):
                    # Simple moving average
                    current_avg = current_data.get(f"{metric_name}_avg", 0)
                    count = current_data.get(f"{metric_name}_count", 0)

                    new_count = count + 1
                    new_avg = (current_avg * count + value) / new_count

                    current_data[f"{metric_name}_avg"] = new_avg
                    current_data[f"{metric_name}_count"] = new_count
                    current_data[f"{metric_name}_max"] = max(
                        current_data.get(f"{metric_name}_max", 0), value
                    )
                    current_data[f"{metric_name}_min"] = min(
                        current_data.get(f"{metric_name}_min", float('inf')), value
                    )

            # Store updated aggregates
            self.redis_client.hset(window_key, mapping=current_data)
            self.redis_client.expire(window_key, int(window_duration.total_seconds() * 2))

    def get_tenant_performance_report(self, tenant_bid: str,
                                    window: str = '1h') -> Dict:
        """Generate performance report for tenant"""

        window_key = f"tenant_agg:{tenant_bid}:{window}"
        data = self.redis_client.hgetall(window_key)

        if not data:
            return {"error": "No performance data available"}

        # Convert to proper format
        performance_data = {k.decode(): float(v.decode()) for k, v in data.items()}

        # Calculate SLA compliance
        sla_compliance = self._calculate_sla_compliance(tenant_bid, performance_data)

        return {
            "tenant_bid": tenant_bid,
            "window": window,
            "timestamp": datetime.utcnow().isoformat(),
            "performance_metrics": performance_data,
            "sla_compliance": sla_compliance,
            "health_score": self._calculate_health_score(performance_data)
        }

    def _calculate_sla_compliance(self, tenant_bid: str, metrics: Dict) -> Dict:
        """Calculate SLA compliance scores"""

        # Define SLA thresholds
        thresholds = {
            "availability": 99.9,  # 99.9% uptime
            "response_time_95": 2.0,  # 2 seconds for 95th percentile
            "error_rate": 1.0  # Less than 1% error rate
        }

        compliance = {}

        # Availability compliance
        uptime_pct = metrics.get("uptime_avg", 0) * 100
        compliance["availability"] = {
            "score": min(100, uptime_pct),
            "threshold": thresholds["availability"],
            "compliant": uptime_pct >= thresholds["availability"]
        }

        # Response time compliance
        response_time_95 = metrics.get("response_time_95_avg", float('inf'))
        compliance["response_time"] = {
            "score": max(0, 100 - ((response_time_95 - thresholds["response_time_95"]) * 50)),
            "threshold": thresholds["response_time_95"],
            "compliant": response_time_95 <= thresholds["response_time_95"]
        }

        # Error rate compliance
        error_rate = metrics.get("error_rate_avg", 100)
        compliance["error_rate"] = {
            "score": max(0, 100 - (error_rate * 10)),
            "threshold": thresholds["error_rate"],
            "compliant": error_rate <= thresholds["error_rate"]
        }

        return compliance

    def _calculate_health_score(self, metrics: Dict) -> float:
        """Calculate overall health score for tenant"""

        weights = {
            "uptime": 0.4,
            "response_time": 0.3,
            "error_rate": 0.2,
            "resource_utilization": 0.1
        }

        scores = {
            "uptime": min(100, metrics.get("uptime_avg", 0) * 100),
            "response_time": max(0, 100 - (metrics.get("response_time_95_avg", 0) * 50)),
            "error_rate": max(0, 100 - (metrics.get("error_rate_avg", 0) * 10)),
            "resource_utilization": max(0, 100 - max(
                metrics.get("cpu_usage_avg", 0),
                metrics.get("memory_usage_avg", 0)
            ))
        }

        weighted_score = sum(scores[metric] * weights[metric] for metric in scores)
        return round(weighted_score, 2)
```

## 6. Implementation Roadmap

### Phase 1: Core Monitoring Infrastructure (Weeks 1-3)
- Deploy Prometheus and Grafana
- Set up basic application metrics
- Configure log aggregation with ELK stack
- Implement basic alerting rules

### Phase 2: Advanced Observability (Weeks 4-6)
- Deploy distributed tracing with Jaeger
- Implement custom business metrics
- Set up tenant-specific monitoring
- Create comprehensive dashboards

### Phase 3: Alerting and Automation (Weeks 7-9)
- Configure AlertManager with escalation rules
- Implement incident management system
- Set up automated incident response
- Create SLA monitoring dashboards

### Phase 4: Performance and Security Monitoring (Weeks 10-12)
- Implement performance profiling
- Set up security monitoring and SIEM
- Create capacity planning dashboards
- Implement cost monitoring

### Phase 5: Optimization and Documentation (Weeks 13-16)
- Performance optimization based on monitoring data
- Create operational runbooks
- Set up monitoring for multi-region deployments
- Implement predictive alerting

This comprehensive monitoring and operations design ensures that the AI-Shifu SaaS platform maintains high availability, performance, and security while providing detailed visibility into system behavior and tenant-specific metrics.
