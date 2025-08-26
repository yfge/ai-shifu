# API 限流和资源管理详细设计文档

## 1. 概述

### 1.1 系统目标

设计多层级的API限流和资源管理系统，确保平台稳定性，防止滥用，并根据租户订阅级别提供差异化的服务质量。

### 1.2 核心功能

- 多层级限流机制
- 租户级别配额管理
- 动态限流规则调整
- 实时流量监控和告警
- 优雅降级和熔断机制
- 分布式限流支持

### 1.3 限流层级

```
Global Platform Limit (平台全局限制)
    ↓
Tenant Subscription Limit (租户订阅限制)
    ↓
User Rate Limit (用户频率限制)
    ↓
IP Rate Limit (IP地址限制)
    ↓
Endpoint Specific Limit (端点特定限制)
```

## 2. 系统架构

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                    API Gateway                              │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              Rate Limiting Middleware                  │ │
│  │  • Request Classification                              │ │
│  │  • Multi-layer Rate Checking                          │ │
│  │  • Response Generation                                 │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                Rate Limiting Services                       │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐ │
│  │   Token     │ │  Sliding    │ │      Circuit         │ │
│  │   Bucket    │ │  Window     │ │     Breaker          │ │
│  │  Service    │ │  Service    │ │     Service          │ │
│  └─────────────┘ └─────────────┘ └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   Storage Layer                             │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐ │
│  │    Redis    │ │  Database   │ │      Metrics          │ │
│  │   Cache     │ │   Config    │ │     Storage           │ │
│  └─────────────┘ └─────────────┘ └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 核心组件

**Rate Limiting Middleware**: 限流中间件
- 请求分类和路由
- 多层限流检查
- 响应生成和错误处理

**Token Bucket Service**: 令牌桶服务
- 令牌生成和消费
- 突发流量处理
- 分布式令牌桶实现

**Sliding Window Service**: 滑动窗口服务
- 精确的时间窗口限流
- 内存优化的数据结构
- 历史请求统计

**Circuit Breaker Service**: 熔断器服务
- 服务健康状态监控
- 自动熔断和恢复
- 降级策略执行

**Metrics Service**: 指标服务
- 实时流量统计
- 限流效果分析
- 告警和通知

## 3. 数据模型设计

### 3.1 限流规则配置 (RateLimitRule)

```sql
CREATE TABLE saas_rate_limit_rules (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    rule_bid VARCHAR(32) NOT NULL UNIQUE,

    -- Rule Scope
    scope_type ENUM('global', 'tenant', 'user', 'ip', 'endpoint') NOT NULL,
    scope_value VARCHAR(100), -- 作用域值，如tenant_bid, user_bid, IP地址等

    -- Resource Identification
    resource_type VARCHAR(50) NOT NULL, -- api_calls, storage_ops, compute_ops
    resource_pattern VARCHAR(200), -- API路径模式，支持通配符
    http_methods JSON, -- ["GET", "POST"] 或 null 表示所有方法

    -- Rate Limit Configuration
    algorithm ENUM('token_bucket', 'sliding_window', 'fixed_window') NOT NULL,
    limit_value BIGINT NOT NULL, -- 限制数量
    time_window_seconds INT NOT NULL, -- 时间窗口（秒）
    burst_capacity BIGINT, -- 突发容量（令牌桶）

    -- Priority and Status
    priority INT DEFAULT 100, -- 优先级，数字越小优先级越高
    is_enabled BOOLEAN DEFAULT TRUE,

    -- Conditional Rules
    conditions JSON, -- 额外条件，如用户角色、订阅类型等

    -- Actions
    action_on_limit ENUM('reject', 'throttle', 'queue') DEFAULT 'reject',
    throttle_factor DECIMAL(3,2), -- 限流因子（0-1）
    queue_timeout_ms INT, -- 队列超时时间

    -- Metadata
    description TEXT,
    tags JSON,

    -- Lifecycle
    effective_from DATETIME,
    effective_to DATETIME,

    -- Standard Fields
    deleted SMALLINT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_user_bid VARCHAR(32) DEFAULT '',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    updated_user_bid VARCHAR(32) DEFAULT '',

    INDEX idx_scope (scope_type, scope_value),
    INDEX idx_resource (resource_type, resource_pattern),
    INDEX idx_priority (priority),
    INDEX idx_enabled (is_enabled),
    INDEX idx_effective (effective_from, effective_to)
);
```

### 3.2 限流状态跟踪 (RateLimitState)

```sql
CREATE TABLE saas_rate_limit_states (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    state_bid VARCHAR(32) NOT NULL UNIQUE,

    -- Rule Reference
    rule_bid VARCHAR(32) NOT NULL,

    -- Scope Identification
    scope_key VARCHAR(200) NOT NULL, -- 组合键：scope_type:scope_value:resource

    -- Current State
    current_tokens BIGINT DEFAULT 0, -- 当前令牌数
    last_refill_time BIGINT, -- 最后补充时间（Unix时间戳毫秒）

    -- Window Data (for sliding window)
    window_data JSON, -- 滑动窗口数据

    -- Statistics
    total_requests BIGINT DEFAULT 0,
    blocked_requests BIGINT DEFAULT 0,
    last_request_time BIGINT,

    -- Metadata
    metadata JSON,

    -- TTL Management
    expires_at DATETIME,

    -- Standard Fields
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY uk_scope_key (scope_key),
    INDEX idx_rule_bid (rule_bid),
    INDEX idx_expires_at (expires_at)
);
```

### 3.3 限流事件日志 (RateLimitEvent)

```sql
CREATE TABLE saas_rate_limit_events (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    event_bid VARCHAR(32) NOT NULL UNIQUE,

    -- Event Classification
    event_type ENUM('request_allowed', 'request_blocked', 'rule_triggered', 'threshold_exceeded') NOT NULL,
    severity ENUM('info', 'warning', 'error', 'critical') DEFAULT 'info',

    -- Context
    tenant_bid VARCHAR(32),
    user_bid VARCHAR(32),
    ip_address VARCHAR(45),
    user_agent TEXT,

    -- Request Details
    endpoint VARCHAR(500),
    http_method VARCHAR(10),
    request_id VARCHAR(64),

    -- Rule Information
    rule_bid VARCHAR(32),
    rule_type VARCHAR(50),
    limit_value BIGINT,
    current_usage BIGINT,

    -- Response Details
    action_taken VARCHAR(50), -- blocked, throttled, queued
    response_code INT,
    response_time_ms INT,

    -- Metadata
    metadata JSON,

    -- Standard Fields
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_tenant_bid (tenant_bid),
    INDEX idx_user_bid (user_bid),
    INDEX idx_event_type (event_type),
    INDEX idx_rule_bid (rule_bid),
    INDEX idx_created_at (created_at),
    INDEX idx_severity (severity)
);
```

### 3.4 熔断器状态 (CircuitBreakerState)

```sql
CREATE TABLE saas_circuit_breaker_states (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    breaker_bid VARCHAR(32) NOT NULL UNIQUE,

    -- Service Identification
    service_name VARCHAR(100) NOT NULL,
    endpoint_pattern VARCHAR(200),
    tenant_bid VARCHAR(32), -- 租户级熔断器

    -- Current State
    state ENUM('closed', 'open', 'half_open') DEFAULT 'closed',

    -- Failure Tracking
    failure_count INT DEFAULT 0,
    success_count INT DEFAULT 0,
    total_requests INT DEFAULT 0,

    -- Thresholds
    failure_threshold INT DEFAULT 5, -- 失败阈值
    success_threshold INT DEFAULT 3, -- 恢复成功阈值
    timeout_duration_ms BIGINT DEFAULT 60000, -- 超时时间

    -- Timing
    last_failure_time BIGINT,
    next_attempt_time BIGINT,

    -- Window Management
    window_start_time BIGINT,
    window_duration_ms BIGINT DEFAULT 60000,

    -- Statistics
    total_failures BIGINT DEFAULT 0,
    total_successes BIGINT DEFAULT 0,

    -- Metadata
    metadata JSON,

    -- Standard Fields
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY uk_service_endpoint (service_name, endpoint_pattern, tenant_bid),
    INDEX idx_service_name (service_name),
    INDEX idx_state (state),
    INDEX idx_tenant_bid (tenant_bid)
);
```

## 4. 限流算法实现

### 4.1 令牌桶算法

```python
class TokenBucketRateLimiter:
    """分布式令牌桶限流器"""

    def __init__(self, redis_client, rule: RateLimitRule):
        self.redis = redis_client
        self.rule = rule
        self.capacity = rule.burst_capacity or rule.limit_value
        self.refill_rate = rule.limit_value / rule.time_window_seconds

    async def is_allowed(self, scope_key: str, tokens_requested: int = 1) -> RateLimitResult:
        """检查请求是否被允许"""
        current_time = time.time() * 1000  # 毫秒时间戳

        # 使用Lua脚本确保原子性
        lua_script = """
        local key = KEYS[1]
        local capacity = tonumber(ARGV[1])
        local refill_rate = tonumber(ARGV[2])
        local tokens_requested = tonumber(ARGV[3])
        local current_time = tonumber(ARGV[4])

        -- 获取当前状态
        local bucket_data = redis.call('HMGET', key, 'tokens', 'last_refill')
        local tokens = tonumber(bucket_data[1]) or capacity
        local last_refill = tonumber(bucket_data[2]) or current_time

        -- 计算需要补充的令牌数
        local time_passed = (current_time - last_refill) / 1000
        local tokens_to_add = math.floor(time_passed * refill_rate)
        tokens = math.min(capacity, tokens + tokens_to_add)

        -- 检查是否有足够的令牌
        if tokens >= tokens_requested then
            tokens = tokens - tokens_requested

            -- 更新状态
            redis.call('HMSET', key,
                'tokens', tokens,
                'last_refill', current_time,
                'total_requests', redis.call('HGET', key, 'total_requests') or 0 + 1
            )
            redis.call('EXPIRE', key, 3600) -- 1小时过期

            return {1, tokens} -- 允许请求，返回剩余令牌数
        else
            -- 更新统计
            redis.call('HMSET', key,
                'last_refill', current_time,
                'total_requests', redis.call('HGET', key, 'total_requests') or 0 + 1,
                'blocked_requests', redis.call('HGET', key, 'blocked_requests') or 0 + 1
            )
            redis.call('EXPIRE', key, 3600)

            return {0, tokens} -- 拒绝请求，返回当前令牌数
        end
        """

        result = await self.redis.eval(
            lua_script, 1,
            scope_key, self.capacity, self.refill_rate, tokens_requested, current_time
        )

        allowed = result[0] == 1
        remaining_tokens = result[1]

        # 计算重试时间
        retry_after = None
        if not allowed:
            tokens_needed = tokens_requested - remaining_tokens
            retry_after = int(tokens_needed / self.refill_rate) + 1

        return RateLimitResult(
            allowed=allowed,
            limit=self.rule.limit_value,
            remaining=remaining_tokens,
            reset_time=current_time + (self.rule.time_window_seconds * 1000),
            retry_after=retry_after
        )

@dataclass
class RateLimitResult:
    allowed: bool
    limit: int
    remaining: int
    reset_time: int  # Unix timestamp in milliseconds
    retry_after: Optional[int] = None  # Seconds to wait before retry
```

### 4.2 滑动窗口算法

```python
class SlidingWindowRateLimiter:
    """滑动窗口限流器"""

    def __init__(self, redis_client, rule: RateLimitRule):
        self.redis = redis_client
        self.rule = rule
        self.window_size = rule.time_window_seconds * 1000  # 转换为毫秒
        self.sub_window_count = min(rule.time_window_seconds, 60)  # 最多60个子窗口
        self.sub_window_size = self.window_size // self.sub_window_count

    async def is_allowed(self, scope_key: str, requests_count: int = 1) -> RateLimitResult:
        """检查请求是否被允许"""
        current_time = int(time.time() * 1000)
        window_start = current_time - self.window_size

        # 使用Lua脚本实现滑动窗口
        lua_script = """
        local key = KEYS[1]
        local window_start = tonumber(ARGV[1])
        local current_time = tonumber(ARGV[2])
        local sub_window_size = tonumber(ARGV[3])
        local limit = tonumber(ARGV[4])
        local requests_count = tonumber(ARGV[5])

        -- 清理过期的子窗口
        redis.call('ZREMRANGEBYSCORE', key, 0, window_start)

        -- 计算当前窗口内的请求总数
        local current_requests = redis.call('ZCARD', key)

        if current_requests + requests_count <= limit then
            -- 允许请求，添加到当前子窗口
            local sub_window = math.floor(current_time / sub_window_size) * sub_window_size
            redis.call('ZADD', key, current_time, current_time .. ':' .. math.random(1000000))
            redis.call('EXPIRE', key, 3600)

            return {1, current_requests + requests_count, limit - (current_requests + requests_count)}
        else
            -- 拒绝请求
            return {0, current_requests, limit - current_requests}
        end
        """

        result = await self.redis.eval(
            lua_script, 1,
            scope_key, window_start, current_time, self.sub_window_size,
            self.rule.limit_value, requests_count
        )

        allowed = result[0] == 1
        current_usage = result[1]
        remaining = result[2]

        # 计算窗口重置时间
        reset_time = current_time + self.window_size

        return RateLimitResult(
            allowed=allowed,
            limit=self.rule.limit_value,
            remaining=max(0, remaining),
            reset_time=reset_time,
            retry_after=self.sub_window_size // 1000 if not allowed else None
        )
```

### 4.3 限流管理器

```python
class RateLimitManager:
    """限流管理器 - 统一管理多种限流算法"""

    def __init__(self, redis_client, rule_repository):
        self.redis = redis_client
        self.rule_repo = rule_repository
        self.limiters = {}
        self.rule_cache = {}

    async def check_rate_limit(self, request_context: RequestContext) -> RateLimitResult:
        """检查请求的限流状态"""
        # 1. 获取适用的限流规则
        applicable_rules = await self.get_applicable_rules(request_context)

        # 2. 按优先级排序检查
        for rule in sorted(applicable_rules, key=lambda r: r.priority):
            # 生成作用域键
            scope_key = self.generate_scope_key(rule, request_context)

            # 获取限流器
            limiter = await self.get_limiter(rule)

            # 检查限流
            result = await limiter.is_allowed(scope_key)

            if not result.allowed:
                # 记录限流事件
                await self.log_rate_limit_event(rule, request_context, result, 'blocked')

                return result
            else:
                # 记录通过事件（可选，用于统计）
                await self.log_rate_limit_event(rule, request_context, result, 'allowed')

        # 所有规则检查通过
        return RateLimitResult(
            allowed=True,
            limit=float('inf'),
            remaining=float('inf'),
            reset_time=int(time.time() * 1000) + 3600000
        )

    async def get_applicable_rules(self, request_context: RequestContext) -> List[RateLimitRule]:
        """获取适用于当前请求的限流规则"""
        cache_key = f"rules:{request_context.tenant_bid}:{request_context.user_bid}:{request_context.endpoint}"

        # 尝试从缓存获取
        cached_rules = self.rule_cache.get(cache_key)
        if cached_rules and time.time() - cached_rules['timestamp'] < 300:  # 5分钟缓存
            return cached_rules['rules']

        rules = []

        # 1. 全局规则
        global_rules = await self.rule_repo.get_by_scope('global', None)
        rules.extend(self.filter_rules_by_context(global_rules, request_context))

        # 2. 租户规则
        tenant_rules = await self.rule_repo.get_by_scope('tenant', request_context.tenant_bid)
        rules.extend(self.filter_rules_by_context(tenant_rules, request_context))

        # 3. 用户规则
        if request_context.user_bid:
            user_rules = await self.rule_repo.get_by_scope('user', request_context.user_bid)
            rules.extend(self.filter_rules_by_context(user_rules, request_context))

        # 4. IP规则
        ip_rules = await self.rule_repo.get_by_scope('ip', request_context.ip_address)
        rules.extend(self.filter_rules_by_context(ip_rules, request_context))

        # 缓存结果
        self.rule_cache[cache_key] = {
            'rules': rules,
            'timestamp': time.time()
        }

        return rules

    def filter_rules_by_context(self, rules: List[RateLimitRule],
                               context: RequestContext) -> List[RateLimitRule]:
        """根据请求上下文过滤规则"""
        filtered_rules = []

        for rule in rules:
            # 检查是否启用
            if not rule.is_enabled:
                continue

            # 检查生效时间
            current_time = datetime.utcnow()
            if rule.effective_from and current_time < rule.effective_from:
                continue
            if rule.effective_to and current_time > rule.effective_to:
                continue

            # 检查端点模式匹配
            if rule.resource_pattern and not self.match_pattern(context.endpoint, rule.resource_pattern):
                continue

            # 检查HTTP方法
            if rule.http_methods and context.method not in rule.http_methods:
                continue

            # 检查条件
            if rule.conditions and not self.evaluate_conditions(rule.conditions, context):
                continue

            filtered_rules.append(rule)

        return filtered_rules

    def match_pattern(self, endpoint: str, pattern: str) -> bool:
        """检查端点是否匹配模式"""
        # 转换通配符模式为正则表达式
        regex_pattern = pattern.replace('*', '.*').replace('?', '.')
        return bool(re.match(f'^{regex_pattern}$', endpoint))

    def generate_scope_key(self, rule: RateLimitRule, context: RequestContext) -> str:
        """生成限流作用域键"""
        parts = [f"rl:{rule.rule_bid}"]

        if rule.scope_type == 'global':
            parts.append('global')
        elif rule.scope_type == 'tenant':
            parts.append(f"tenant:{context.tenant_bid}")
        elif rule.scope_type == 'user':
            parts.append(f"user:{context.user_bid}")
        elif rule.scope_type == 'ip':
            parts.append(f"ip:{context.ip_address}")

        if rule.resource_pattern:
            parts.append(f"resource:{rule.resource_pattern}")

        return ':'.join(parts)

    async def get_limiter(self, rule: RateLimitRule):
        """获取限流器实例"""
        cache_key = f"limiter:{rule.rule_bid}"

        if cache_key not in self.limiters:
            if rule.algorithm == 'token_bucket':
                self.limiters[cache_key] = TokenBucketRateLimiter(self.redis, rule)
            elif rule.algorithm == 'sliding_window':
                self.limiters[cache_key] = SlidingWindowRateLimiter(self.redis, rule)
            else:
                raise ValueError(f"Unsupported rate limiting algorithm: {rule.algorithm}")

        return self.limiters[cache_key]

@dataclass
class RequestContext:
    tenant_bid: str
    user_bid: Optional[str]
    ip_address: str
    endpoint: str
    method: str
    user_agent: Optional[str] = None
    subscription_plan: Optional[str] = None
    user_role: Optional[str] = None
```

## 5. 中间件和拦截器

### 5.1 限流中间件

```python
class RateLimitMiddleware:
    """限流中间件"""

    def __init__(self, rate_limit_manager: RateLimitManager):
        self.rate_limit_manager = rate_limit_manager

    async def __call__(self, request, call_next):
        # 构建请求上下文
        context = await self.build_request_context(request)

        # 执行限流检查
        rate_limit_result = await self.rate_limit_manager.check_rate_limit(context)

        if not rate_limit_result.allowed:
            # 返回限流响应
            return self.create_rate_limit_response(rate_limit_result)

        # 执行请求
        try:
            response = await call_next(request)

            # 在响应中添加限流头部
            self.add_rate_limit_headers(response, rate_limit_result)

            return response

        except Exception as e:
            # 记录异常，但不回退限流计数（已经消费了配额）
            logger.error(f"Request failed after rate limit check: {e}")
            raise

    async def build_request_context(self, request) -> RequestContext:
        """构建请求上下文"""
        # 从JWT或其他方式获取租户和用户信息
        tenant_bid = await self.extract_tenant_bid(request)
        user_bid = await self.extract_user_bid(request)

        # 获取客户端IP
        ip_address = self.get_client_ip(request)

        return RequestContext(
            tenant_bid=tenant_bid,
            user_bid=user_bid,
            ip_address=ip_address,
            endpoint=request.url.path,
            method=request.method,
            user_agent=request.headers.get('user-agent')
        )

    def create_rate_limit_response(self, result: RateLimitResult):
        """创建限流响应"""
        headers = {
            'X-RateLimit-Limit': str(result.limit),
            'X-RateLimit-Remaining': str(result.remaining),
            'X-RateLimit-Reset': str(result.reset_time // 1000),
        }

        if result.retry_after:
            headers['Retry-After'] = str(result.retry_after)

        return JSONResponse(
            status_code=429,
            content={
                'error': 'rate_limit_exceeded',
                'message': 'Too many requests',
                'code': 4290,
                'retry_after': result.retry_after
            },
            headers=headers
        )

    def add_rate_limit_headers(self, response, result: RateLimitResult):
        """添加限流相关的响应头"""
        response.headers['X-RateLimit-Limit'] = str(result.limit)
        response.headers['X-RateLimit-Remaining'] = str(result.remaining)
        response.headers['X-RateLimit-Reset'] = str(result.reset_time // 1000)
```

### 5.2 动态限流装饰器

```python
def rate_limit(scope: str = 'user', limit: int = 100, window: int = 3600,
               algorithm: str = 'token_bucket'):
    """动态限流装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 获取当前请求上下文
            context = get_current_request_context()

            # 创建动态规则
            rule = RateLimitRule(
                rule_bid=f"dynamic_{func.__name__}_{scope}",
                scope_type=scope,
                resource_type='api_calls',
                resource_pattern=f"function:{func.__name__}",
                algorithm=algorithm,
                limit_value=limit,
                time_window_seconds=window,
                is_enabled=True
            )

            # 执行限流检查
            limiter = get_limiter(rule)
            scope_key = generate_scope_key(rule, context)

            result = await limiter.is_allowed(scope_key)

            if not result.allowed:
                raise RateLimitExceededException(
                    f"Rate limit exceeded for {func.__name__}",
                    retry_after=result.retry_after
                )

            # 执行函数
            return await func(*args, **kwargs)

        return wrapper
    return decorator

# 使用示例
@rate_limit(scope='user', limit=10, window=60, algorithm='sliding_window')
async def create_shifu(tenant_bid: str, shifu_data: dict):
    """创建Shifu，限制每分钟10次"""
    return await shifu_service.create_shifu(tenant_bid, shifu_data)

@rate_limit(scope='tenant', limit=1000, window=3600, algorithm='token_bucket')
async def chat_with_shifu(tenant_bid: str, shifu_bid: str, message: str):
    """与Shifu对话，租户级别限制每小时1000次"""
    return await shifu_service.chat(tenant_bid, shifu_bid, message)
```

## 6. 熔断器实现

### 6.1 熔断器服务

```python
class CircuitBreakerService:
    """熔断器服务"""

    def __init__(self, redis_client, breaker_repository):
        self.redis = redis_client
        self.breaker_repo = breaker_repository
        self.breakers = {}

    async def execute(self, breaker_name: str, func: Callable,
                     *args, **kwargs):
        """通过熔断器执行函数"""
        breaker = await self.get_circuit_breaker(breaker_name)

        # 检查熔断器状态
        if await self.should_block_request(breaker):
            raise CircuitBreakerOpenException(
                f"Circuit breaker {breaker_name} is open"
            )

        try:
            # 执行函数
            result = await func(*args, **kwargs)

            # 记录成功
            await self.record_success(breaker)

            return result

        except Exception as e:
            # 记录失败
            await self.record_failure(breaker, e)

            raise

    async def should_block_request(self, breaker: CircuitBreakerState) -> bool:
        """检查是否应该阻断请求"""
        current_time = int(time.time() * 1000)

        if breaker.state == 'closed':
            return False
        elif breaker.state == 'open':
            if current_time >= breaker.next_attempt_time:
                # 尝试半开状态
                await self.transition_to_half_open(breaker)
                return False
            return True
        elif breaker.state == 'half_open':
            return False

    async def record_success(self, breaker: CircuitBreakerState):
        """记录成功调用"""
        current_time = int(time.time() * 1000)

        if breaker.state == 'half_open':
            breaker.success_count += 1

            if breaker.success_count >= breaker.success_threshold:
                # 转为关闭状态
                await self.transition_to_closed(breaker)

        elif breaker.state == 'closed':
            # 重置失败计数
            if current_time - breaker.window_start_time > breaker.window_duration_ms:
                breaker.failure_count = 0
                breaker.window_start_time = current_time

        breaker.total_successes += 1
        await self.update_breaker_state(breaker)

    async def record_failure(self, breaker: CircuitBreakerState, exception: Exception):
        """记录失败调用"""
        current_time = int(time.time() * 1000)

        if breaker.state == 'closed':
            breaker.failure_count += 1
            breaker.last_failure_time = current_time

            if breaker.failure_count >= breaker.failure_threshold:
                # 转为开启状态
                await self.transition_to_open(breaker)

        elif breaker.state == 'half_open':
            # 直接转为开启状态
            await self.transition_to_open(breaker)

        breaker.total_failures += 1
        await self.update_breaker_state(breaker)

    async def transition_to_open(self, breaker: CircuitBreakerState):
        """转换为开启状态"""
        breaker.state = 'open'
        breaker.next_attempt_time = int(time.time() * 1000) + breaker.timeout_duration_ms

        # 发送熔断告警
        await self.send_circuit_breaker_alert(breaker, 'opened')

    async def transition_to_half_open(self, breaker: CircuitBreakerState):
        """转换为半开状态"""
        breaker.state = 'half_open'
        breaker.success_count = 0

        logger.info(f"Circuit breaker {breaker.breaker_bid} transitioned to half-open")

    async def transition_to_closed(self, breaker: CircuitBreakerState):
        """转换为关闭状态"""
        breaker.state = 'closed'
        breaker.failure_count = 0
        breaker.success_count = 0
        breaker.window_start_time = int(time.time() * 1000)

        # 发送恢复通知
        await self.send_circuit_breaker_alert(breaker, 'closed')

        logger.info(f"Circuit breaker {breaker.breaker_bid} recovered to closed state")
```

### 6.2 熔断器装饰器

```python
def circuit_breaker(name: str, failure_threshold: int = 5,
                   timeout_duration: int = 60000, success_threshold: int = 3):
    """熔断器装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            breaker_service = get_circuit_breaker_service()

            # 获取或创建熔断器
            breaker_key = f"{name}:{func.__name__}"

            return await breaker_service.execute(
                breaker_key, func, *args, **kwargs
            )

        return wrapper
    return decorator

# 使用示例
@circuit_breaker(name='llm_service', failure_threshold=3, timeout_duration=30000)
async def call_llm_api(prompt: str, model: str) -> str:
    """调用LLM API，带熔断保护"""
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            'https://api.openai.com/v1/completions',
            json={'prompt': prompt, 'model': model}
        )
        response.raise_for_status()
        return response.json()
```

## 7. 监控和告警

### 7.1 实时指标收集

```python
class RateLimitMetricsService:
    """限流指标服务"""

    def __init__(self, metrics_client):
        self.metrics = metrics_client

    async def record_rate_limit_event(self, event_type: str, tags: dict, value: float = 1):
        """记录限流事件"""
        await self.metrics.increment(
            'rate_limit.events',
            value,
            tags={'event_type': event_type, **tags}
        )

    async def record_request_latency(self, endpoint: str, tenant_bid: str, latency_ms: float):
        """记录请求延迟"""
        await self.metrics.histogram(
            'request.latency',
            latency_ms,
            tags={'endpoint': endpoint, 'tenant': tenant_bid}
        )

    async def get_rate_limit_stats(self, tenant_bid: str = None,
                                  time_range: str = '1h') -> dict:
        """获取限流统计"""
        filters = []
        if tenant_bid:
            filters.append(f'tenant:{tenant_bid}')

        # 查询指标数据
        stats = await self.metrics.query([
            f'rate_limit.events{{event_type:blocked,{','.join(filters)}}}[{time_range}]',
            f'rate_limit.events{{event_type:allowed,{','.join(filters)}}}[{time_range}]',
        ])

        blocked_requests = sum(stats[0]['values']) if stats[0]['values'] else 0
        allowed_requests = sum(stats[1]['values']) if stats[1]['values'] else 0
        total_requests = blocked_requests + allowed_requests

        return {
            'total_requests': total_requests,
            'blocked_requests': blocked_requests,
            'allowed_requests': allowed_requests,
            'block_rate': blocked_requests / total_requests if total_requests > 0 else 0,
            'time_range': time_range
        }
```

### 7.2 告警配置

```python
class RateLimitAlertService:
    """限流告警服务"""

    def __init__(self, notification_service):
        self.notification = notification_service

        # 告警阈值配置
        self.alert_thresholds = {
            'high_block_rate': 0.1,  # 10%的请求被阻断
            'sudden_traffic_spike': 5.0,  # 流量突增5倍
            'circuit_breaker_open': 1,  # 熔断器开启
        }

    async def check_rate_limit_health(self):
        """检查限流系统健康状态"""
        # 检查全局阻断率
        global_stats = await self.metrics_service.get_rate_limit_stats(time_range='5m')

        if global_stats['block_rate'] > self.alert_thresholds['high_block_rate']:
            await self.send_alert(
                'high_global_block_rate',
                f"Global request block rate is {global_stats['block_rate']:.2%}",
                severity='warning',
                data=global_stats
            )

        # 检查租户级别异常
        tenant_stats = await self.get_tenant_rate_limit_stats()

        for tenant_bid, stats in tenant_stats.items():
            if stats['block_rate'] > self.alert_thresholds['high_block_rate']:
                await self.send_alert(
                    'high_tenant_block_rate',
                    f"Tenant {tenant_bid} request block rate is {stats['block_rate']:.2%}",
                    severity='warning',
                    data={'tenant_bid': tenant_bid, **stats}
                )

    async def send_alert(self, alert_type: str, message: str,
                        severity: str = 'info', data: dict = None):
        """发送告警"""
        alert = {
            'type': alert_type,
            'message': message,
            'severity': severity,
            'timestamp': datetime.utcnow().isoformat(),
            'data': data or {},
            'source': 'rate_limit_service'
        }

        # 发送到不同的通知渠道
        await self.notification.send_slack_alert(alert)

        if severity in ['error', 'critical']:
            await self.notification.send_email_alert(alert)
            await self.notification.send_sms_alert(alert)
```

## 8. 性能优化

### 8.1 缓存优化

```python
class OptimizedRateLimitCache:
    """优化的限流缓存"""

    def __init__(self, redis_client):
        self.redis = redis_client
        self.local_cache = {}
        self.cache_ttl = 60  # 本地缓存60秒

    async def get_with_fallback(self, key: str, fallback_func: Callable):
        """多层缓存获取"""
        # 1. 本地内存缓存
        local_data = self.local_cache.get(key)
        if local_data and time.time() - local_data['timestamp'] < self.cache_ttl:
            return local_data['value']

        # 2. Redis缓存
        redis_data = await self.redis.get(key)
        if redis_data:
            value = json.loads(redis_data)
            # 更新本地缓存
            self.local_cache[key] = {
                'value': value,
                'timestamp': time.time()
            }
            return value

        # 3. 回退到数据库
        value = await fallback_func()

        # 缓存到Redis和本地
        await self.redis.setex(key, 300, json.dumps(value))  # 5分钟
        self.local_cache[key] = {
            'value': value,
            'timestamp': time.time()
        }

        return value
```

### 8.2 批量操作优化

```python
class BatchRateLimitProcessor:
    """批量限流处理器"""

    def __init__(self, redis_client, batch_size: int = 100):
        self.redis = redis_client
        self.batch_size = batch_size
        self.pending_requests = []
        self.batch_timer = None

    async def add_request(self, request_context: RequestContext) -> RateLimitResult:
        """添加请求到批量处理队列"""
        future = asyncio.Future()
        self.pending_requests.append((request_context, future))

        # 如果达到批量大小或者是第一个请求，立即处理
        if len(self.pending_requests) >= self.batch_size or len(self.pending_requests) == 1:
            await self.process_batch()
        else:
            # 设置定时器，确保请求不会等待太长时间
            if not self.batch_timer:
                self.batch_timer = asyncio.create_task(
                    self.delayed_process_batch(0.1)  # 100ms延迟
                )

        return await future

    async def process_batch(self):
        """处理批量请求"""
        if not self.pending_requests:
            return

        batch = self.pending_requests[:self.batch_size]
        self.pending_requests = self.pending_requests[self.batch_size:]

        # 取消定时器
        if self.batch_timer:
            self.batch_timer.cancel()
            self.batch_timer = None

        # 批量处理
        try:
            results = await self.batch_check_rate_limits(batch)

            # 设置结果
            for i, (context, future) in enumerate(batch):
                if not future.done():
                    future.set_result(results[i])

        except Exception as e:
            # 设置异常
            for context, future in batch:
                if not future.done():
                    future.set_exception(e)

        # 如果还有待处理的请求，继续处理
        if self.pending_requests:
            await self.process_batch()

    async def batch_check_rate_limits(self, batch: List[Tuple[RequestContext, asyncio.Future]]) -> List[RateLimitResult]:
        """批量检查限流"""
        # 构建批量Redis命令
        pipe = self.redis.pipeline()

        for context, _ in batch:
            # 为每个请求添加检查命令
            scope_key = f"rl:user:{context.user_bid}:api_calls"
            # ... 添加限流检查的Lua脚本

        # 执行批量命令
        results = await pipe.execute()

        # 解析结果
        rate_limit_results = []
        for i, (context, _) in enumerate(batch):
            # 解析Redis结果
            result = results[i]
            rate_limit_results.append(
                RateLimitResult(
                    allowed=result[0] == 1,
                    limit=1000,
                    remaining=result[1],
                    reset_time=int(time.time() * 1000) + 3600000
                )
            )

        return rate_limit_results
```

这个API限流和资源管理设计提供了完整的多层级限流解决方案，支持多种限流算法，具备熔断保护、实时监控和动态配置能力，能够有效保护系统稳定性并提供差异化的服务质量。
