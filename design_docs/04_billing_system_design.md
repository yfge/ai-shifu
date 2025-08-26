# 计费系统详细设计文档

## 1. 概述

### 1.1 系统目标

设计一个灵活、可扩展的计费系统，支持多种订阅模式、使用量计费、配额管理和自动化计费流程。

### 1.2 核心功能

- 订阅计划管理
- 使用量跟踪和计量
- 自动化账单生成
- 支付集成（Stripe）
- 配额管理和限制
- 计费分析和报告

### 1.3 计费模型

**订阅计费**
- 固定月费/年费
- 分层定价
- 免费试用期

**使用量计费**
- API调用次数
- 存储容量使用
- 活跃用户数
- 数据传输量

**混合计费**
- 基础订阅费 + 超额使用费
- 预付费 + 后付费组合

## 2. 系统架构

### 2.1 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                    Billing Frontend                        │
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │ Subscription    │  │   Usage         │                  │
│  │  Management     │  │  Dashboard      │                  │
│  └─────────────────┘  └─────────────────┘                  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   Billing API Gateway                      │
├─────────────────────────────────────────────────────────────┤
│  Subscription │ Usage Tracking │ Invoice │ Payment Gateway │
├─────────────────────────────────────────────────────────────┤
│              Billing Core Services                         │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐ │
│  │Subscription │ │   Usage     │ │      Payment        │ │
│  │  Service    │ │  Metering   │ │    Processing       │ │
│  └─────────────┘ └─────────────┘ └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                External Payment Providers                  │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────────────────┐ │
│  │ Stripe  │ │PayPal   │ │ Alipay  │ │      Others       │ │
│  │         │ │         │ │         │ │                   │ │
│  └─────────┘ └─────────┘ └─────────┘ └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 核心服务组件

**Subscription Service**: 订阅管理
- 订阅计划创建和管理
- 用户订阅生命周期
- 升级/降级处理
- 试用期管理

**Usage Metering Service**: 使用量计量
- 实时使用量跟踪
- 批量使用量聚合
- 配额检查和限制
- 使用量报告生成

**Invoice Service**: 发票管理
- 自动发票生成
- 发票模板管理
- 税费计算
- 发票分发

**Payment Processing Service**: 支付处理
- 支付方式管理
- 支付流程编排
- 支付状态同步
- 退款处理

## 3. 数据模型设计

### 3.1 订阅计划 (SubscriptionPlan)

```sql
CREATE TABLE saas_subscription_plans (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    plan_bid VARCHAR(32) NOT NULL UNIQUE,
    plan_id VARCHAR(50) NOT NULL UNIQUE,

    -- Plan Details
    name VARCHAR(100) NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,

    -- Pricing
    base_price DECIMAL(10, 2) NOT NULL DEFAULT 0,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    billing_cycle ENUM('monthly', 'yearly', 'quarterly') NOT NULL DEFAULT 'monthly',

    -- Trial Configuration
    trial_period_days INT DEFAULT 0,
    trial_price DECIMAL(10, 2) DEFAULT 0,

    -- Limits and Quotas
    quotas JSON NOT NULL, -- {"users": 100, "api_calls": 10000, "storage_gb": 10}

    -- Features
    features JSON NOT NULL, -- ["sso", "api_access", "advanced_analytics"]

    -- Usage-based Pricing
    usage_pricing JSON, -- {"api_calls": {"included": 1000, "overage_price": 0.01}}

    -- Plan Status
    is_active BOOLEAN DEFAULT TRUE,
    is_public BOOLEAN DEFAULT TRUE, -- 是否对外显示
    sort_order INT DEFAULT 0,

    -- Metadata
    stripe_price_id VARCHAR(100), -- Stripe价格ID
    metadata JSON,

    -- Standard Fields
    deleted SMALLINT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_user_bid VARCHAR(32) DEFAULT '',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    updated_user_bid VARCHAR(32) DEFAULT '',

    INDEX idx_plan_id (plan_id),
    INDEX idx_active (is_active),
    INDEX idx_public (is_public),
    INDEX idx_currency (currency)
);
```

### 3.2 订阅关系 (Subscription)

```sql
CREATE TABLE saas_subscriptions (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    subscription_bid VARCHAR(32) NOT NULL UNIQUE,
    tenant_bid VARCHAR(32) NOT NULL,

    -- Plan Reference
    plan_bid VARCHAR(32) NOT NULL,
    plan_snapshot JSON, -- 订阅时的计划快照

    -- Billing Information
    billing_cycle ENUM('monthly', 'yearly', 'quarterly') NOT NULL,
    base_amount DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',

    -- Subscription Lifecycle
    status ENUM('trialing', 'active', 'past_due', 'canceled', 'unpaid', 'incomplete') NOT NULL,

    -- Period Management
    current_period_start DATETIME NOT NULL,
    current_period_end DATETIME NOT NULL,
    trial_start DATETIME,
    trial_end DATETIME,

    -- Cancellation
    cancel_at_period_end BOOLEAN DEFAULT FALSE,
    canceled_at DATETIME,
    ended_at DATETIME,

    -- Payment Integration
    stripe_subscription_id VARCHAR(100),
    stripe_customer_id VARCHAR(100),

    -- Usage Limits (current period)
    usage_limits JSON, -- {"api_calls": 10000, "storage_gb": 50}
    usage_reset_at DATETIME, -- 使用量重置时间

    -- Standard Fields
    deleted SMALLINT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_tenant_bid (tenant_bid),
    INDEX idx_plan_bid (plan_bid),
    INDEX idx_status (status),
    INDEX idx_period_end (current_period_end),
    INDEX idx_stripe_subscription (stripe_subscription_id),
    UNIQUE KEY uk_tenant_active (tenant_bid, status) -- 确保租户只有一个活跃订阅
);
```

### 3.3 使用量记录 (UsageRecord)

```sql
CREATE TABLE saas_usage_records (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    usage_bid VARCHAR(32) NOT NULL UNIQUE,
    tenant_bid VARCHAR(32) NOT NULL,
    subscription_bid VARCHAR(32) NOT NULL,

    -- Usage Details
    metric_name VARCHAR(50) NOT NULL, -- api_calls, storage_gb, active_users
    metric_value DECIMAL(15, 6) NOT NULL, -- 支持小数，如存储GB
    unit VARCHAR(20) NOT NULL, -- count, gb, mb, hours

    -- Aggregation Period
    period_type ENUM('hour', 'day', 'month') NOT NULL,
    period_start DATETIME NOT NULL,
    period_end DATETIME NOT NULL,

    -- Metadata
    source VARCHAR(50), -- api, background_job, import
    resource_id VARCHAR(100), -- 关联资源ID
    user_bid VARCHAR(32), -- 使用者

    -- Billing Context
    billable BOOLEAN DEFAULT TRUE,
    unit_price DECIMAL(10, 6), -- 单价
    total_cost DECIMAL(10, 2), -- 总费用

    -- Processing Status
    processed BOOLEAN DEFAULT FALSE,
    processed_at DATETIME,
    invoice_bid VARCHAR(32), -- 关联发票

    -- Standard Fields
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_tenant_metric (tenant_bid, metric_name),
    INDEX idx_subscription_bid (subscription_bid),
    INDEX idx_period (period_start, period_end),
    INDEX idx_processed (processed),
    INDEX idx_billable (billable),
    INDEX idx_created_at (created_at)
);
```

### 3.4 发票 (Invoice)

```sql
CREATE TABLE saas_invoices (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    invoice_bid VARCHAR(32) NOT NULL UNIQUE,
    tenant_bid VARCHAR(32) NOT NULL,
    subscription_bid VARCHAR(32) NOT NULL,

    -- Invoice Details
    invoice_number VARCHAR(50) NOT NULL UNIQUE,
    invoice_date DATE NOT NULL,
    due_date DATE NOT NULL,

    -- Amount Breakdown
    subtotal DECIMAL(10, 2) NOT NULL DEFAULT 0,
    tax_amount DECIMAL(10, 2) NOT NULL DEFAULT 0,
    discount_amount DECIMAL(10, 2) NOT NULL DEFAULT 0,
    total_amount DECIMAL(10, 2) NOT NULL DEFAULT 0,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',

    -- Billing Period
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,

    -- Status
    status ENUM('draft', 'open', 'paid', 'past_due', 'canceled', 'uncollectible') NOT NULL DEFAULT 'draft',

    -- Payment Information
    paid_at DATETIME,
    payment_method VARCHAR(50),
    transaction_id VARCHAR(100),

    -- Integration
    stripe_invoice_id VARCHAR(100),

    -- Content
    line_items JSON, -- 发票明细
    notes TEXT,

    -- Standard Fields
    deleted SMALLINT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_tenant_bid (tenant_bid),
    INDEX idx_subscription_bid (subscription_bid),
    INDEX idx_invoice_number (invoice_number),
    INDEX idx_status (status),
    INDEX idx_due_date (due_date),
    INDEX idx_period (period_start, period_end)
);
```

### 3.5 支付记录 (Payment)

```sql
CREATE TABLE saas_payments (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    payment_bid VARCHAR(32) NOT NULL UNIQUE,
    tenant_bid VARCHAR(32) NOT NULL,

    -- Payment Context
    invoice_bid VARCHAR(32),
    subscription_bid VARCHAR(32),

    -- Payment Details
    amount DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    payment_method VARCHAR(50) NOT NULL, -- card, bank_transfer, alipay

    -- Status
    status ENUM('pending', 'processing', 'succeeded', 'failed', 'canceled', 'refunded') NOT NULL,

    -- Integration Data
    stripe_payment_intent_id VARCHAR(100),
    stripe_charge_id VARCHAR(100),
    external_transaction_id VARCHAR(100),

    -- Failure Information
    failure_code VARCHAR(50),
    failure_message TEXT,

    -- Timestamps
    initiated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME,
    failed_at DATETIME,

    -- Metadata
    metadata JSON,

    -- Standard Fields
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_tenant_bid (tenant_bid),
    INDEX idx_invoice_bid (invoice_bid),
    INDEX idx_subscription_bid (subscription_bid),
    INDEX idx_status (status),
    INDEX idx_stripe_payment_intent (stripe_payment_intent_id)
);
```

## 4. 订阅管理服务

### 4.1 订阅生命周期管理

```python
class SubscriptionService:
    def __init__(self, stripe_service, usage_service, invoice_service):
        self.stripe = stripe_service
        self.usage_service = usage_service
        self.invoice_service = invoice_service

    async def create_subscription(self, tenant_bid: str, plan_id: str,
                                payment_method_id: str = None, trial: bool = True):
        """创建新订阅"""
        # 1. 获取订阅计划
        plan = await self.get_subscription_plan(plan_id)
        if not plan or not plan.is_active:
            raise PlanNotFoundError(f"Plan {plan_id} not found or inactive")

        # 2. 检查租户是否已有活跃订阅
        existing_subscription = await self.get_active_subscription(tenant_bid)
        if existing_subscription:
            raise ActiveSubscriptionExistsError("Tenant already has an active subscription")

        # 3. 创建Stripe客户和订阅
        tenant = await self.tenant_service.get_tenant(tenant_bid)
        stripe_customer = await self.stripe.create_customer(
            email=tenant.billing_email,
            name=tenant.name,
            metadata={'tenant_bid': tenant_bid}
        )

        # 4. 设置试用期
        trial_end = None
        if trial and plan.trial_period_days > 0:
            trial_end = datetime.utcnow() + timedelta(days=plan.trial_period_days)

        # 5. 创建Stripe订阅
        stripe_subscription = await self.stripe.create_subscription(
            customer_id=stripe_customer.id,
            price_id=plan.stripe_price_id,
            payment_method_id=payment_method_id,
            trial_end=trial_end
        )

        # 6. 创建本地订阅记录
        subscription = Subscription(
            subscription_bid=generate_uuid(),
            tenant_bid=tenant_bid,
            plan_bid=plan.plan_bid,
            plan_snapshot=plan.to_dict(),
            billing_cycle=plan.billing_cycle,
            base_amount=plan.base_price,
            currency=plan.currency,
            status='trialing' if trial_end else 'active',
            current_period_start=datetime.utcnow(),
            current_period_end=self.calculate_period_end(datetime.utcnow(), plan.billing_cycle),
            trial_start=datetime.utcnow() if trial_end else None,
            trial_end=trial_end,
            stripe_subscription_id=stripe_subscription.id,
            stripe_customer_id=stripe_customer.id,
            usage_limits=plan.quotas.copy()
        )

        await self.subscription_repository.create(subscription)

        # 7. 初始化使用量跟踪
        await self.usage_service.initialize_usage_tracking(subscription.subscription_bid)

        return subscription

    async def upgrade_subscription(self, tenant_bid: str, new_plan_id: str):
        """升级订阅"""
        # 1. 获取当前订阅
        current_subscription = await self.get_active_subscription(tenant_bid)
        if not current_subscription:
            raise NoActiveSubscriptionError("No active subscription found")

        # 2. 获取新计划
        new_plan = await self.get_subscription_plan(new_plan_id)
        current_plan_price = current_subscription.base_amount

        if new_plan.base_price <= current_plan_price:
            raise InvalidUpgradeError("New plan must be higher tier than current plan")

        # 3. 计算按比例退费/补费
        proration_amount = await self.calculate_proration(
            current_subscription, new_plan
        )

        # 4. 更新Stripe订阅
        await self.stripe.modify_subscription(
            current_subscription.stripe_subscription_id,
            price_id=new_plan.stripe_price_id,
            proration_behavior='always_invoice'
        )

        # 5. 更新本地订阅记录
        current_subscription.plan_bid = new_plan.plan_bid
        current_subscription.plan_snapshot = new_plan.to_dict()
        current_subscription.base_amount = new_plan.base_price
        current_subscription.usage_limits = new_plan.quotas.copy()

        await self.subscription_repository.update(current_subscription)

        # 6. 记录变更历史
        await self.record_subscription_change(
            current_subscription.subscription_bid,
            'upgrade',
            {'old_plan_id': current_subscription.plan_snapshot['plan_id'], 'new_plan_id': new_plan_id}
        )

        return current_subscription

    async def cancel_subscription(self, tenant_bid: str, immediate: bool = False):
        """取消订阅"""
        subscription = await self.get_active_subscription(tenant_bid)
        if not subscription:
            raise NoActiveSubscriptionError("No active subscription found")

        if immediate:
            # 立即取消
            await self.stripe.cancel_subscription_immediately(
                subscription.stripe_subscription_id
            )

            subscription.status = 'canceled'
            subscription.canceled_at = datetime.utcnow()
            subscription.ended_at = datetime.utcnow()
        else:
            # 期末取消
            await self.stripe.cancel_subscription_at_period_end(
                subscription.stripe_subscription_id
            )

            subscription.cancel_at_period_end = True
            subscription.canceled_at = datetime.utcnow()

        await self.subscription_repository.update(subscription)

        return subscription

    def calculate_period_end(self, start_date: datetime, billing_cycle: str) -> datetime:
        """计算计费周期结束时间"""
        if billing_cycle == 'monthly':
            return start_date + timedelta(days=30)
        elif billing_cycle == 'yearly':
            return start_date + timedelta(days=365)
        elif billing_cycle == 'quarterly':
            return start_date + timedelta(days=90)
        else:
            raise ValueError(f"Invalid billing cycle: {billing_cycle}")
```

### 4.2 使用量跟踪服务

```python
class UsageTrackingService:
    def __init__(self, redis_client, usage_repository):
        self.redis = redis_client
        self.usage_repo = usage_repository
        self.batch_size = 100
        self.flush_interval = 300  # 5分钟

    async def track_usage(self, tenant_bid: str, metric_name: str,
                         value: float = 1, metadata: dict = None):
        """跟踪使用量"""
        # 1. 实时增量计数
        current_hour = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        cache_key = f"usage:{tenant_bid}:{metric_name}:{current_hour.isoformat()}"

        # 使用Redis原子操作
        pipe = self.redis.pipeline()
        pipe.hincrbyfloat(cache_key, 'value', value)
        pipe.hset(cache_key, 'last_updated', datetime.utcnow().isoformat())
        pipe.expire(cache_key, 86400)  # 24小时过期

        if metadata:
            pipe.hset(cache_key, 'metadata', json.dumps(metadata))

        await pipe.execute()

        # 2. 检查配额限制
        await self.check_quota_limit(tenant_bid, metric_name)

        # 3. 异步批量持久化
        await self.schedule_batch_persistence(tenant_bid, metric_name)

    async def check_quota_limit(self, tenant_bid: str, metric_name: str):
        """检查配额限制"""
        # 获取当前使用量
        current_usage = await self.get_current_period_usage(tenant_bid, metric_name)

        # 获取配额限制
        subscription = await self.subscription_service.get_active_subscription(tenant_bid)
        if not subscription:
            return  # 无订阅时不限制

        quota_limit = subscription.usage_limits.get(metric_name)
        if not quota_limit:
            return  # 无限制

        # 检查是否超额
        if current_usage >= quota_limit:
            await self.handle_quota_exceeded(tenant_bid, metric_name, current_usage, quota_limit)
        elif current_usage >= quota_limit * 0.8:  # 80%告警
            await self.send_quota_warning(tenant_bid, metric_name, current_usage, quota_limit)

    async def get_current_period_usage(self, tenant_bid: str, metric_name: str) -> float:
        """获取当前计费周期使用量"""
        subscription = await self.subscription_service.get_active_subscription(tenant_bid)
        if not subscription:
            return 0

        # 从当前周期开始时间聚合使用量
        period_start = subscription.current_period_start
        period_end = datetime.utcnow()

        # 先从Redis获取实时数据
        redis_usage = await self._get_redis_usage(tenant_bid, metric_name, period_start, period_end)

        # 再从数据库获取已持久化的数据
        db_usage = await self.usage_repo.get_usage_sum(
            tenant_bid, metric_name, period_start, period_end
        )

        return redis_usage + db_usage

    async def _get_redis_usage(self, tenant_bid: str, metric_name: str,
                              start_time: datetime, end_time: datetime) -> float:
        """从Redis获取实时使用量"""
        total_usage = 0
        current_time = start_time.replace(minute=0, second=0, microsecond=0)

        while current_time <= end_time:
            cache_key = f"usage:{tenant_bid}:{metric_name}:{current_time.isoformat()}"
            value = await self.redis.hget(cache_key, 'value')

            if value:
                total_usage += float(value)

            current_time += timedelta(hours=1)

        return total_usage

    async def batch_persist_usage(self):
        """批量持久化使用量数据"""
        # 获取所有待持久化的使用量数据
        pattern = "usage:*:*:*"
        keys = await self.redis.keys(pattern)

        usage_records = []

        for key in keys:
            # 解析key: usage:tenant_bid:metric_name:timestamp
            parts = key.split(':')
            if len(parts) != 4:
                continue

            tenant_bid = parts[1]
            metric_name = parts[2]
            hour_timestamp = datetime.fromisoformat(parts[3])

            # 获取使用量数据
            usage_data = await self.redis.hgetall(key)
            if not usage_data.get('value'):
                continue

            # 创建使用量记录
            usage_record = UsageRecord(
                usage_bid=generate_uuid(),
                tenant_bid=tenant_bid,
                metric_name=metric_name,
                metric_value=float(usage_data['value']),
                unit='count',  # 根据metric_name确定单位
                period_type='hour',
                period_start=hour_timestamp,
                period_end=hour_timestamp + timedelta(hours=1),
                source='api',
                billable=True
            )

            usage_records.append(usage_record)

            # 删除Redis中的数据
            await self.redis.delete(key)

        # 批量保存到数据库
        if usage_records:
            await self.usage_repo.bulk_create(usage_records)
            logger.info(f"Persisted {len(usage_records)} usage records")

    async def aggregate_daily_usage(self):
        """聚合每日使用量"""
        yesterday = datetime.utcnow().date() - timedelta(days=1)

        # 获取所有租户的小时使用量
        hourly_records = await self.usage_repo.get_hourly_records_by_date(yesterday)

        # 按租户和指标聚合
        daily_aggregations = {}

        for record in hourly_records:
            key = (record.tenant_bid, record.metric_name)
            if key not in daily_aggregations:
                daily_aggregations[key] = {
                    'tenant_bid': record.tenant_bid,
                    'metric_name': record.metric_name,
                    'total_value': 0,
                    'unit': record.unit
                }

            daily_aggregations[key]['total_value'] += record.metric_value

        # 创建每日聚合记录
        daily_records = []
        for key, agg_data in daily_aggregations.items():
            daily_record = UsageRecord(
                usage_bid=generate_uuid(),
                tenant_bid=agg_data['tenant_bid'],
                metric_name=agg_data['metric_name'],
                metric_value=agg_data['total_value'],
                unit=agg_data['unit'],
                period_type='day',
                period_start=datetime.combine(yesterday, datetime.min.time()),
                period_end=datetime.combine(yesterday, datetime.max.time()),
                source='aggregation',
                billable=True
            )
            daily_records.append(daily_record)

        # 保存每日记录
        if daily_records:
            await self.usage_repo.bulk_create(daily_records)
            logger.info(f"Created {len(daily_records)} daily usage aggregations for {yesterday}")
```

### 4.3 发票生成服务

```python
class InvoiceService:
    def __init__(self, subscription_service, usage_service, tax_service):
        self.subscription_service = subscription_service
        self.usage_service = usage_service
        self.tax_service = tax_service

    async def generate_monthly_invoices(self, target_date: date = None):
        """生成月度发票"""
        if target_date is None:
            target_date = datetime.utcnow().date().replace(day=1)  # 当月第一天

        # 获取需要计费的订阅
        subscriptions = await self.get_billable_subscriptions(target_date)

        invoices_created = []

        for subscription in subscriptions:
            try:
                invoice = await self.generate_subscription_invoice(subscription, target_date)
                invoices_created.append(invoice)
            except Exception as e:
                logger.error(f"Failed to generate invoice for subscription {subscription.subscription_bid}: {e}")

        logger.info(f"Generated {len(invoices_created)} invoices for {target_date}")
        return invoices_created

    async def generate_subscription_invoice(self, subscription: Subscription, billing_date: date):
        """为订阅生成发票"""
        # 1. 计算计费周期
        period_start, period_end = self.calculate_billing_period(subscription, billing_date)

        # 2. 检查是否已有发票
        existing_invoice = await self.invoice_repo.get_by_subscription_and_period(
            subscription.subscription_bid, period_start, period_end
        )

        if existing_invoice:
            return existing_invoice

        # 3. 计算基础费用
        base_amount = subscription.base_amount

        # 4. 计算使用量费用
        usage_charges = await self.calculate_usage_charges(subscription, period_start, period_end)

        # 5. 构建发票明细
        line_items = []

        # 基础订阅费用
        line_items.append({
            'type': 'subscription',
            'description': f"{subscription.plan_snapshot['display_name']} ({period_start.strftime('%Y-%m-%d')} - {period_end.strftime('%Y-%m-%d')})",
            'quantity': 1,
            'unit_price': float(base_amount),
            'total': float(base_amount)
        })

        # 使用量费用
        for metric_name, charge_info in usage_charges.items():
            if charge_info['overage_amount'] > 0:
                line_items.append({
                    'type': 'usage',
                    'description': f"{charge_info['display_name']} overage",
                    'quantity': charge_info['overage_quantity'],
                    'unit_price': charge_info['unit_price'],
                    'total': charge_info['overage_amount']
                })

        # 6. 计算小计和税费
        subtotal = sum(item['total'] for item in line_items)
        tax_amount = await self.tax_service.calculate_tax(subscription.tenant_bid, subtotal)
        total_amount = subtotal + tax_amount

        # 7. 创建发票
        invoice = Invoice(
            invoice_bid=generate_uuid(),
            tenant_bid=subscription.tenant_bid,
            subscription_bid=subscription.subscription_bid,
            invoice_number=await self.generate_invoice_number(),
            invoice_date=billing_date,
            due_date=billing_date + timedelta(days=30),
            subtotal=subtotal,
            tax_amount=tax_amount,
            total_amount=total_amount,
            currency=subscription.currency,
            period_start=period_start,
            period_end=period_end,
            status='open',
            line_items=line_items
        )

        await self.invoice_repo.create(invoice)

        # 8. 创建Stripe发票
        await self.create_stripe_invoice(invoice)

        return invoice

    async def calculate_usage_charges(self, subscription: Subscription,
                                    period_start: date, period_end: date) -> dict:
        """计算使用量费用"""
        charges = {}

        # 获取计划的使用量定价配置
        usage_pricing = subscription.plan_snapshot.get('usage_pricing', {})

        for metric_name, pricing_config in usage_pricing.items():
            # 获取实际使用量
            actual_usage = await self.usage_service.get_period_usage(
                subscription.tenant_bid, metric_name, period_start, period_end
            )

            # 计算超额使用量
            included_quantity = pricing_config.get('included', 0)
            overage_quantity = max(0, actual_usage - included_quantity)

            # 计算超额费用
            unit_price = pricing_config.get('overage_price', 0)
            overage_amount = overage_quantity * unit_price

            charges[metric_name] = {
                'display_name': pricing_config.get('display_name', metric_name),
                'actual_usage': actual_usage,
                'included_quantity': included_quantity,
                'overage_quantity': overage_quantity,
                'unit_price': unit_price,
                'overage_amount': overage_amount
            }

        return charges
```

### 4.4 支付处理服务

```python
class PaymentProcessingService:
    def __init__(self, stripe_service):
        self.stripe = stripe_service

    async def process_invoice_payment(self, invoice_bid: str, payment_method_id: str = None):
        """处理发票支付"""
        # 1. 获取发票
        invoice = await self.invoice_repo.get_by_bid(invoice_bid)
        if not invoice:
            raise InvoiceNotFoundError(f"Invoice {invoice_bid} not found")

        if invoice.status != 'open':
            raise InvalidInvoiceStatusError(f"Invoice {invoice_bid} is not open for payment")

        # 2. 获取订阅信息
        subscription = await self.subscription_service.get_subscription(invoice.subscription_bid)

        # 3. 创建支付记录
        payment = Payment(
            payment_bid=generate_uuid(),
            tenant_bid=invoice.tenant_bid,
            invoice_bid=invoice.invoice_bid,
            subscription_bid=invoice.subscription_bid,
            amount=invoice.total_amount,
            currency=invoice.currency,
            status='pending'
        )

        await self.payment_repo.create(payment)

        try:
            # 4. 创建Stripe PaymentIntent
            payment_intent = await self.stripe.create_payment_intent(
                amount=int(invoice.total_amount * 100),  # 转换为分
                currency=invoice.currency,
                customer_id=subscription.stripe_customer_id,
                payment_method_id=payment_method_id,
                metadata={
                    'invoice_bid': invoice.invoice_bid,
                    'tenant_bid': invoice.tenant_bid
                }
            )

            # 5. 更新支付记录
            payment.stripe_payment_intent_id = payment_intent.id
            payment.status = 'processing'
            await self.payment_repo.update(payment)

            # 6. 如果有默认支付方式，尝试自动确认
            if payment_method_id:
                confirmed_intent = await self.stripe.confirm_payment_intent(
                    payment_intent.id
                )

                if confirmed_intent.status == 'succeeded':
                    await self.handle_payment_success(payment, confirmed_intent)
                elif confirmed_intent.status == 'requires_action':
                    # 需要3D验证等额外操作
                    return {
                        'status': 'requires_action',
                        'client_secret': confirmed_intent.client_secret,
                        'payment_bid': payment.payment_bid
                    }

            return {
                'status': 'processing',
                'client_secret': payment_intent.client_secret,
                'payment_bid': payment.payment_bid
            }

        except Exception as e:
            # 支付失败
            payment.status = 'failed'
            payment.failure_message = str(e)
            payment.failed_at = datetime.utcnow()
            await self.payment_repo.update(payment)

            raise PaymentProcessingError(f"Payment processing failed: {e}")

    async def handle_stripe_webhook(self, event_type: str, event_data: dict):
        """处理Stripe Webhook事件"""
        if event_type == 'payment_intent.succeeded':
            await self.handle_payment_intent_succeeded(event_data)
        elif event_type == 'payment_intent.payment_failed':
            await self.handle_payment_intent_failed(event_data)
        elif event_type == 'invoice.payment_succeeded':
            await self.handle_invoice_payment_succeeded(event_data)
        elif event_type == 'customer.subscription.updated':
            await self.handle_subscription_updated(event_data)
        # ... 其他事件处理

    async def handle_payment_intent_succeeded(self, payment_intent_data: dict):
        """处理支付成功事件"""
        payment_intent_id = payment_intent_data['id']

        # 查找对应的支付记录
        payment = await self.payment_repo.get_by_stripe_payment_intent_id(payment_intent_id)
        if not payment:
            logger.warning(f"Payment not found for PaymentIntent {payment_intent_id}")
            return

        await self.handle_payment_success(payment, payment_intent_data)

    async def handle_payment_success(self, payment: Payment, payment_intent_data: dict):
        """处理支付成功"""
        # 1. 更新支付记录
        payment.status = 'succeeded'
        payment.completed_at = datetime.utcnow()
        payment.stripe_charge_id = payment_intent_data.get('latest_charge')
        await self.payment_repo.update(payment)

        # 2. 更新发票状态
        if payment.invoice_bid:
            invoice = await self.invoice_repo.get_by_bid(payment.invoice_bid)
            invoice.status = 'paid'
            invoice.paid_at = datetime.utcnow()
            invoice.payment_method = payment_intent_data.get('payment_method', {}).get('type')
            invoice.transaction_id = payment.stripe_charge_id

            await self.invoice_repo.update(invoice)

        # 3. 更新订阅状态（如果需要）
        if payment.subscription_bid:
            subscription = await self.subscription_service.get_subscription(payment.subscription_bid)
            if subscription.status == 'past_due':
                subscription.status = 'active'
                await self.subscription_service.update_subscription(subscription)

        # 4. 发送支付成功通知
        await self.notification_service.send_payment_success_notification(
            payment.tenant_bid, payment.amount, invoice.invoice_number if invoice else None
        )
```

## 5. 配额管理和限制

### 5.1 实时配额检查

```python
class QuotaEnforcementService:
    def __init__(self, usage_service, subscription_service, cache_service):
        self.usage_service = usage_service
        self.subscription_service = subscription_service
        self.cache = cache_service

    async def check_quota(self, tenant_bid: str, metric_name: str,
                         requested_amount: float = 1) -> QuotaCheckResult:
        """检查配额是否允许请求"""
        # 1. 获取配额限制
        quota_limit = await self.get_quota_limit(tenant_bid, metric_name)
        if quota_limit is None:
            # 无限制
            return QuotaCheckResult(allowed=True, unlimited=True)

        # 2. 获取当前使用量
        current_usage = await self.usage_service.get_current_period_usage(tenant_bid, metric_name)

        # 3. 检查是否会超额
        projected_usage = current_usage + requested_amount

        if projected_usage <= quota_limit:
            return QuotaCheckResult(
                allowed=True,
                current_usage=current_usage,
                quota_limit=quota_limit,
                remaining=quota_limit - current_usage
            )
        else:
            return QuotaCheckResult(
                allowed=False,
                current_usage=current_usage,
                quota_limit=quota_limit,
                remaining=max(0, quota_limit - current_usage),
                exceeded_by=projected_usage - quota_limit
            )

    async def enforce_quota(self, tenant_bid: str, metric_name: str,
                          requested_amount: float = 1) -> bool:
        """强制执行配额检查"""
        quota_result = await self.check_quota(tenant_bid, metric_name, requested_amount)

        if not quota_result.allowed:
            # 发送配额超限通知
            await self.send_quota_exceeded_notification(tenant_bid, metric_name, quota_result)

            # 记录配额违规事件
            await self.log_quota_violation(tenant_bid, metric_name, quota_result)

            raise QuotaExceededError(
                f"Quota exceeded for {metric_name}. "
                f"Current: {quota_result.current_usage}, "
                f"Limit: {quota_result.quota_limit}, "
                f"Requested: {requested_amount}"
            )

        return True

    async def get_quota_limit(self, tenant_bid: str, metric_name: str) -> Optional[float]:
        """获取配额限制，带缓存"""
        cache_key = f"quota_limit:{tenant_bid}:{metric_name}"

        # 尝试从缓存获取
        cached_limit = await self.cache.get(cache_key)
        if cached_limit is not None:
            return cached_limit

        # 从订阅信息获取
        subscription = await self.subscription_service.get_active_subscription(tenant_bid)
        if not subscription:
            return None

        quota_limit = subscription.usage_limits.get(metric_name)

        # 缓存结果
        await self.cache.set(cache_key, quota_limit, expire=300)  # 5分钟缓存

        return quota_limit

    @dataclass
    class QuotaCheckResult:
        allowed: bool
        current_usage: float = 0
        quota_limit: Optional[float] = None
        remaining: float = 0
        exceeded_by: float = 0
        unlimited: bool = False
```

### 5.2 配额中间件

```python
class QuotaMiddleware:
    """API配额检查中间件"""

    def __init__(self, quota_service: QuotaEnforcementService):
        self.quota_service = quota_service

        # 配置不同API端点的配额类型
        self.endpoint_metrics = {
            '/api/v1/shifu/chat': 'api_calls',
            '/api/v1/shifu/create': 'shifu_operations',
            '/api/v1/files/upload': 'storage_operations',
        }

    async def __call__(self, request, call_next):
        # 获取当前租户
        tenant_bid = tenant_context.get_tenant()

        # 确定配额类型
        endpoint = request.url.path
        metric_name = self.endpoint_metrics.get(endpoint, 'api_calls')

        try:
            # 检查配额
            await self.quota_service.enforce_quota(tenant_bid, metric_name)

            # 执行请求
            response = await call_next(request)

            # 记录使用量
            await self.usage_service.track_usage(
                tenant_bid,
                metric_name,
                1,
                metadata={'endpoint': endpoint, 'method': request.method}
            )

            return response

        except QuotaExceededError as e:
            return JSONResponse(
                status_code=429,
                content={
                    'error': 'quota_exceeded',
                    'message': str(e),
                    'code': 4290
                }
            )
```

## 6. 分析和报告

### 6.1 计费分析服务

```python
class BillingAnalyticsService:
    async def get_revenue_metrics(self, start_date: date, end_date: date) -> dict:
        """获取收入指标"""
        # 1. 总收入
        total_revenue = await self.invoice_repo.get_total_revenue(start_date, end_date)

        # 2. MRR (Monthly Recurring Revenue)
        mrr = await self.calculate_mrr(end_date)

        # 3. ARR (Annual Recurring Revenue)
        arr = mrr * 12

        # 4. 按计划分组的收入
        revenue_by_plan = await self.invoice_repo.get_revenue_by_plan(start_date, end_date)

        # 5. 客户生命周期价值
        avg_ltv = await self.calculate_average_ltv()

        # 6. 流失率
        churn_rate = await self.calculate_churn_rate(start_date, end_date)

        return {
            'total_revenue': float(total_revenue),
            'mrr': float(mrr),
            'arr': float(arr),
            'revenue_by_plan': revenue_by_plan,
            'average_ltv': float(avg_ltv),
            'churn_rate': float(churn_rate),
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            }
        }

    async def get_usage_analytics(self, tenant_bid: str = None,
                                 start_date: date = None, end_date: date = None):
        """获取使用量分析"""
        if not start_date:
            start_date = date.today() - timedelta(days=30)
        if not end_date:
            end_date = date.today()

        # 按指标类型统计使用量
        usage_by_metric = await self.usage_repo.get_usage_by_metric(
            tenant_bid, start_date, end_date
        )

        # 使用量趋势
        usage_trend = await self.usage_repo.get_daily_usage_trend(
            tenant_bid, start_date, end_date
        )

        # 峰值使用时间
        peak_usage_hours = await self.usage_repo.get_peak_usage_hours(
            tenant_bid, start_date, end_date
        )

        return {
            'usage_by_metric': usage_by_metric,
            'usage_trend': usage_trend,
            'peak_usage_hours': peak_usage_hours,
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            }
        }

    async def generate_billing_report(self, tenant_bid: str, year: int, month: int):
        """生成租户计费报告"""
        # 计费周期
        period_start = date(year, month, 1)
        if month == 12:
            period_end = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            period_end = date(year, month + 1, 1) - timedelta(days=1)

        # 获取订阅信息
        subscription = await self.subscription_service.get_active_subscription(tenant_bid)

        # 获取使用量数据
        usage_data = await self.get_usage_analytics(tenant_bid, period_start, period_end)

        # 获取发票信息
        invoices = await self.invoice_repo.get_by_tenant_and_period(
            tenant_bid, period_start, period_end
        )

        # 生成报告
        report = {
            'tenant_bid': tenant_bid,
            'period': {
                'year': year,
                'month': month,
                'start': period_start.isoformat(),
                'end': period_end.isoformat()
            },
            'subscription': {
                'plan_name': subscription.plan_snapshot['display_name'],
                'billing_cycle': subscription.billing_cycle,
                'status': subscription.status
            },
            'usage_summary': usage_data['usage_by_metric'],
            'invoices': [
                {
                    'invoice_number': inv.invoice_number,
                    'amount': float(inv.total_amount),
                    'status': inv.status,
                    'due_date': inv.due_date.isoformat()
                }
                for inv in invoices
            ],
            'total_amount': sum(float(inv.total_amount) for inv in invoices)
        }

        return report
```

这个计费系统设计提供了完整的订阅管理、使用量跟踪、自动计费和支付处理功能，支持灵活的定价模式和企业级的计费需求。
