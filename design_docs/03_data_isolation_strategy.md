# 数据隔离策略详细设计文档

## 1. 概述

### 1.1 数据隔离目标

为AI-Shifu SaaS平台设计完善的数据隔离策略，确保租户间数据完全隔离，防止数据泄露，同时保持系统性能和开发效率。

### 1.2 隔离级别要求

**安全性要求**
- 租户间数据完全物理或逻辑隔离
- 防止跨租户数据访问和泄露
- 支持数据合规性要求（GDPR、SOC2）

**性能要求**
- 查询性能不受租户数量影响
- 支持高并发多租户访问
- 缓存和索引优化

**运维要求**
- 统一的数据库管理
- 简化的备份和恢复
- 便于监控和调试

## 2. 隔离方案对比

### 2.1 三种隔离方案对比

| 特性 | Database-per-Tenant | Schema-per-Tenant | Row-Level Security |
|------|-------------------|-------------------|-------------------|
| **数据隔离级别** | 完全物理隔离 | 逻辑隔离 | 应用层隔离 |
| **安全性** | 最高 | 高 | 中高 |
| **性能** | 优秀 (独立优化) | 良好 | 优秀 (共享索引) |
| **成本** | 高 | 中等 | 低 |
| **运维复杂度** | 高 | 中等 | 低 |
| **扩展性** | 优秀 | 良好 | 优秀 |
| **跨租户分析** | 复杂 | 中等 | 简单 |
| **备份恢复** | 复杂 | 中等 | 简单 |

### 2.2 推荐方案选择

**混合隔离策略**：根据租户级别采用不同隔离方案
- **企业级租户**: Database-per-Tenant (完全隔离)
- **标准租户**: Row-Level Security (行级隔离)
- **免费/试用租户**: Row-Level Security (行级隔离)

## 3. Row-Level Security 详细设计

### 3.1 核心设计原理

**租户上下文注入**
```python
class TenantContext:
    def __init__(self):
        self._tenant_bid = None

    def set_tenant(self, tenant_bid: str):
        self._tenant_bid = tenant_bid

    def get_tenant(self) -> str:
        if not self._tenant_bid:
            raise TenantContextError("No tenant context set")
        return self._tenant_bid

    def clear(self):
        self._tenant_bid = None

# 全局租户上下文
tenant_context = TenantContext()
```

### 3.2 数据库模型改造

**现有表结构改造示例**
```sql
-- 用户表改造
ALTER TABLE user_info
ADD COLUMN tenant_bid VARCHAR(32) NOT NULL DEFAULT '' AFTER id,
ADD INDEX idx_tenant_bid (tenant_bid);

-- 订单表改造
ALTER TABLE order_orders
ADD COLUMN tenant_bid VARCHAR(32) NOT NULL DEFAULT '' AFTER id,
ADD INDEX idx_tenant_bid (tenant_bid);

-- Shifu表改造
ALTER TABLE shifu_draft_shifus
ADD COLUMN tenant_bid VARCHAR(32) NOT NULL DEFAULT '' AFTER id,
ADD INDEX idx_tenant_bid (tenant_bid);

-- 学习会话表改造
ALTER TABLE study_sessions
ADD COLUMN tenant_bid VARCHAR(32) NOT NULL DEFAULT '' AFTER id,
ADD INDEX idx_tenant_bid (tenant_bid);
```

**复合索引优化**
```sql
-- 为常用查询添加复合索引
ALTER TABLE user_info
ADD INDEX idx_tenant_email (tenant_bid, email),
ADD INDEX idx_tenant_status (tenant_bid, user_state);

ALTER TABLE order_orders
ADD INDEX idx_tenant_user (tenant_bid, user_bid),
ADD INDEX idx_tenant_status (tenant_bid, status);

ALTER TABLE shifu_draft_shifus
ADD INDEX idx_tenant_creator (tenant_bid, created_user_bid),
ADD INDEX idx_tenant_updated (tenant_bid, updated_at);
```

### 3.3 应用层隔离实现

**SQLAlchemy 模型基类**
```python
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy import Column, String, event
from sqlalchemy.orm import Query

class TenantMixin:
    """租户混入类，为所有业务表添加租户隔离"""

    @declared_attr
    def tenant_bid(cls):
        return Column(String(32), nullable=False, default='', index=True)

    @classmethod
    def __declare_last__(cls):
        """在模型声明完成后设置事件监听器"""
        event.listen(cls.__table__, 'before_create', cls._add_tenant_check_constraint)

    @staticmethod
    def _add_tenant_check_constraint(table, connection, **kwargs):
        """添加租户字段非空约束"""
        # MySQL不支持CHECK约束，在应用层控制
        pass

class TenantAwareQuery(Query):
    """租户感知的查询类"""

    def __new__(cls, entities, session=None):
        if session is None:
            from flask import g
            session = g.db_session

        query = Query.__new__(cls, entities, session)
        return query._filter_by_tenant()

    def _filter_by_tenant(self):
        """自动添加租户过滤条件"""
        tenant_bid = tenant_context.get_tenant()

        for entity in self.column_descriptions:
            model_class = entity['type']
            if hasattr(model_class, 'tenant_bid'):
                return self.filter(model_class.tenant_bid == tenant_bid)

        return self

# 业务模型示例
class User(db.Model, TenantMixin):
    __tablename__ = "user_info"
    query_class = TenantAwareQuery

    id = Column(BIGINT, primary_key=True, autoincrement=True)
    user_id = Column(String(36), nullable=False, index=True)
    username = Column(String(255), nullable=False, default="")
    email = Column(String(255), nullable=False, default="")
    # ... 其他字段
```

**中间件实现租户上下文注入**
```python
class TenantMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] == 'http':
            # 从请求中提取租户信息
            tenant_bid = await self._extract_tenant_from_request(scope)

            # 设置租户上下文
            tenant_context.set_tenant(tenant_bid)

            try:
                await self.app(scope, receive, send)
            finally:
                # 清理租户上下文
                tenant_context.clear()
        else:
            await self.app(scope, receive, send)

    async def _extract_tenant_from_request(self, scope) -> str:
        # 1. 从JWT token中提取
        headers = dict(scope.get('headers', []))
        auth_header = headers.get(b'authorization', b'').decode()

        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
            try:
                payload = jwt.decode(token, verify=False)  # 这里应该验证签名
                return payload.get('tenant_bid', '')
            except:
                pass

        # 2. 从域名中提取
        host = headers.get(b'host', b'').decode()
        tenant = await self._resolve_tenant_by_domain(host)
        if tenant:
            return tenant.tenant_bid

        # 3. 从查询参数中提取
        query_string = scope.get('query_string', b'').decode()
        params = parse_qs(query_string)
        tenant_param = params.get('tenant', [''])[0]
        if tenant_param:
            return tenant_param

        raise TenantNotFoundError("Cannot determine tenant from request")
```

### 3.4 Repository 层租户隔离

```python
class BaseTenantRepository:
    """租户感知的基础Repository"""

    def __init__(self, model_class, session):
        self.model_class = model_class
        self.session = session

    def _get_base_query(self):
        """获取带租户过滤的基础查询"""
        tenant_bid = tenant_context.get_tenant()
        return self.session.query(self.model_class).filter(
            self.model_class.tenant_bid == tenant_bid
        )

    async def create(self, entity):
        """创建实体，自动注入租户ID"""
        entity.tenant_bid = tenant_context.get_tenant()
        self.session.add(entity)
        await self.session.commit()
        return entity

    async def get_by_id(self, entity_id):
        """根据ID获取实体"""
        return await self._get_base_query().filter(
            self.model_class.id == entity_id
        ).first()

    async def get_by_bid(self, business_id):
        """根据业务ID获取实体"""
        return await self._get_base_query().filter(
            self.model_class.get_bid_column() == business_id
        ).first()

    async def list_all(self, offset=0, limit=100):
        """列出当前租户的所有实体"""
        return await self._get_base_query().offset(offset).limit(limit).all()

    async def update(self, entity):
        """更新实体，验证租户归属"""
        current_tenant = tenant_context.get_tenant()
        if entity.tenant_bid != current_tenant:
            raise TenantMismatchError(f"Entity belongs to different tenant")

        await self.session.commit()
        return entity

    async def delete(self, entity_id):
        """删除实体"""
        entity = await self.get_by_id(entity_id)
        if entity:
            if hasattr(entity, 'deleted'):
                # 软删除
                entity.deleted = 1
            else:
                # 硬删除
                self.session.delete(entity)

            await self.session.commit()

        return entity

class UserRepository(BaseTenantRepository):
    def __init__(self, session):
        super().__init__(User, session)

    async def get_by_email(self, email: str):
        """根据邮箱获取用户（租户内唯一）"""
        return await self._get_base_query().filter(
            User.email == email
        ).first()

    async def get_active_users(self):
        """获取活跃用户"""
        return await self._get_base_query().filter(
            User.user_state == 1,
            User.deleted == 0
        ).all()
```

### 3.5 服务层租户验证

```python
class BaseTenantService:
    """租户感知的基础服务类"""

    def __init__(self, repository):
        self.repository = repository

    async def ensure_tenant_access(self, entity_bid: str, action: str = 'read'):
        """确保当前租户有权限访问指定实体"""
        entity = await self.repository.get_by_bid(entity_bid)
        if not entity:
            raise EntityNotFoundError(f"Entity {entity_bid} not found")

        current_tenant = tenant_context.get_tenant()
        if entity.tenant_bid != current_tenant:
            raise PermissionDeniedError(
                f"Tenant {current_tenant} has no {action} access to entity {entity_bid}"
            )

        return entity

    async def create_with_tenant(self, data: dict):
        """创建实体并自动设置租户"""
        entity = self.repository.model_class(**data)
        entity.tenant_bid = tenant_context.get_tenant()

        return await self.repository.create(entity)

class ShifuService(BaseTenantService):
    def __init__(self, shifu_repository):
        super().__init__(shifu_repository)

    async def create_shifu(self, shifu_data: dict):
        """创建Shifu，确保租户隔离"""
        # 验证租户配额
        await self._check_shifu_quota()

        # 创建Shifu
        shifu = await self.create_with_tenant(shifu_data)

        return shifu

    async def get_shifu(self, shifu_bid: str):
        """获取Shifu，自动验证租户权限"""
        return await self.ensure_tenant_access(shifu_bid, 'read')

    async def update_shifu(self, shifu_bid: str, update_data: dict):
        """更新Shifu"""
        shifu = await self.ensure_tenant_access(shifu_bid, 'write')

        for key, value in update_data.items():
            if hasattr(shifu, key):
                setattr(shifu, key, value)

        return await self.repository.update(shifu)

    async def _check_shifu_quota(self):
        """检查租户Shifu配额"""
        tenant_bid = tenant_context.get_tenant()
        tenant = await self.tenant_service.get_tenant(tenant_bid)

        current_count = await self.repository.count_active_shifus()
        if current_count >= tenant.max_shifus:
            raise QuotaExceededError(
                f"Shifu quota exceeded. Max: {tenant.max_shifus}, Current: {current_count}"
            )
```

## 4. Database-per-Tenant 设计

### 4.1 数据库路由系统

```python
class DatabaseRouter:
    """数据库路由器"""

    def __init__(self):
        self.connection_pools = {}
        self.tenant_database_mapping = {}

    async def get_database_for_tenant(self, tenant_bid: str) -> DatabaseInfo:
        """获取租户的数据库信息"""
        if tenant_bid in self.tenant_database_mapping:
            return self.tenant_database_mapping[tenant_bid]

        # 从配置服务获取数据库映射
        db_info = await self.load_tenant_database_mapping(tenant_bid)
        if not db_info:
            # 大租户可能需要创建独立数据库
            db_info = await self.create_tenant_database(tenant_bid)

        self.tenant_database_mapping[tenant_bid] = db_info
        return db_info

    async def get_connection(self, tenant_bid: str):
        """获取租户数据库连接"""
        db_info = await self.get_database_for_tenant(tenant_bid)

        if db_info.database_name not in self.connection_pools:
            # 创建连接池
            pool = await self.create_connection_pool(db_info)
            self.connection_pools[db_info.database_name] = pool

        return self.connection_pools[db_info.database_name].acquire()

    async def create_tenant_database(self, tenant_bid: str) -> DatabaseInfo:
        """为租户创建独立数据库"""
        # 选择合适的数据库实例
        db_instance = await self.select_database_instance(tenant_bid)

        # 生成数据库名称
        database_name = f"ai_shifu_{tenant_bid}"

        # 创建数据库
        admin_conn = await db_instance.get_admin_connection()
        await admin_conn.execute(f"CREATE DATABASE {database_name}")

        # 创建数据库用户
        username = f"user_{tenant_bid}"
        password = self.generate_secure_password()

        await admin_conn.execute(f"""
            CREATE USER '{username}'@'%' IDENTIFIED BY '{password}'
        """)

        await admin_conn.execute(f"""
            GRANT ALL PRIVILEGES ON {database_name}.* TO '{username}'@'%'
        """)

        # 初始化数据库结构
        await self.initialize_database_schema(database_name, username, password)

        # 保存数据库映射信息
        db_info = DatabaseInfo(
            tenant_bid=tenant_bid,
            host=db_instance.host,
            port=db_instance.port,
            database_name=database_name,
            username=username,
            password=password
        )

        await self.save_tenant_database_mapping(db_info)

        return db_info

@dataclass
class DatabaseInfo:
    tenant_bid: str
    host: str
    port: int
    database_name: str
    username: str
    password: str
    max_connections: int = 50

    def get_connection_string(self):
        return f"mysql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database_name}"
```

### 4.2 动态Session管理

```python
class TenantAwareSessionManager:
    """租户感知的Session管理器"""

    def __init__(self, database_router: DatabaseRouter):
        self.database_router = database_router
        self.session_factories = {}

    async def get_session(self, tenant_bid: str):
        """获取租户专用的数据库Session"""
        if tenant_bid not in self.session_factories:
            # 创建租户专用的SessionFactory
            db_info = await self.database_router.get_database_for_tenant(tenant_bid)
            engine = create_async_engine(db_info.get_connection_string())

            session_factory = sessionmaker(
                bind=engine,
                class_=AsyncSession,
                expire_on_commit=False
            )

            self.session_factories[tenant_bid] = session_factory

        return self.session_factories[tenant_bid]()

    async def execute_on_tenant_db(self, tenant_bid: str, operation):
        """在租户数据库上执行操作"""
        session = await self.get_session(tenant_bid)
        try:
            result = await operation(session)
            await session.commit()
            return result
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()

# 使用示例
class MultiTenantUserRepository:
    def __init__(self, session_manager: TenantAwareSessionManager):
        self.session_manager = session_manager

    async def create_user(self, tenant_bid: str, user_data: dict):
        async def _create_operation(session):
            user = User(**user_data)
            session.add(user)
            return user

        return await self.session_manager.execute_on_tenant_db(
            tenant_bid, _create_operation
        )

    async def get_user_by_email(self, tenant_bid: str, email: str):
        async def _query_operation(session):
            return await session.query(User).filter(User.email == email).first()

        return await self.session_manager.execute_on_tenant_db(
            tenant_bid, _query_operation
        )
```

## 5. 缓存隔离策略

### 5.1 Redis 租户隔离

```python
class TenantAwareCache:
    """租户感知的缓存服务"""

    def __init__(self, redis_client):
        self.redis = redis_client
        self.key_prefix = "ai-shifu"

    def _build_key(self, key: str, tenant_bid: str = None) -> str:
        """构建租户隔离的缓存key"""
        if tenant_bid is None:
            tenant_bid = tenant_context.get_tenant()

        return f"{self.key_prefix}:tenant:{tenant_bid}:{key}"

    async def get(self, key: str, tenant_bid: str = None):
        """获取缓存值"""
        cache_key = self._build_key(key, tenant_bid)
        value = await self.redis.get(cache_key)

        if value:
            return json.loads(value)
        return None

    async def set(self, key: str, value, expire: int = 3600, tenant_bid: str = None):
        """设置缓存值"""
        cache_key = self._build_key(key, tenant_bid)
        serialized_value = json.dumps(value, default=str)

        await self.redis.setex(cache_key, expire, serialized_value)

    async def delete(self, key: str, tenant_bid: str = None):
        """删除缓存"""
        cache_key = self._build_key(key, tenant_bid)
        await self.redis.delete(cache_key)

    async def clear_tenant_cache(self, tenant_bid: str):
        """清空租户所有缓存"""
        pattern = f"{self.key_prefix}:tenant:{tenant_bid}:*"
        keys = await self.redis.keys(pattern)

        if keys:
            await self.redis.delete(*keys)

    async def get_tenant_cache_stats(self, tenant_bid: str):
        """获取租户缓存统计"""
        pattern = f"{self.key_prefix}:tenant:{tenant_bid}:*"
        keys = await self.redis.keys(pattern)

        total_memory = 0
        for key in keys:
            memory_usage = await self.redis.memory_usage(key)
            total_memory += memory_usage if memory_usage else 0

        return {
            'key_count': len(keys),
            'total_memory_bytes': total_memory,
            'tenant_bid': tenant_bid
        }

# 分布式缓存锁
class TenantAwareDistributedLock:
    """租户感知的分布式锁"""

    def __init__(self, redis_client, cache_service: TenantAwareCache):
        self.redis = redis_client
        self.cache = cache_service

    async def acquire(self, resource: str, timeout: int = 10, tenant_bid: str = None):
        """获取分布式锁"""
        lock_key = self.cache._build_key(f"lock:{resource}", tenant_bid)
        identifier = str(uuid.uuid4())

        end_time = time.time() + timeout

        while time.time() < end_time:
            # 尝试获取锁
            if await self.redis.set(lock_key, identifier, nx=True, ex=timeout):
                return identifier

            # 等待一段时间后重试
            await asyncio.sleep(0.1)

        return None

    async def release(self, resource: str, identifier: str, tenant_bid: str = None):
        """释放分布式锁"""
        lock_key = self.cache._build_key(f"lock:{resource}", tenant_bid)

        # 使用Lua脚本确保原子性
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """

        return await self.redis.eval(lua_script, 1, lock_key, identifier)
```

### 5.2 应用层缓存装饰器

```python
def tenant_cache(expire: int = 3600, key_pattern: str = None):
    """租户缓存装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 构建缓存key
            if key_pattern:
                cache_key = key_pattern.format(*args, **kwargs)
            else:
                # 默认使用函数名和参数构建key
                cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"

            # 尝试从缓存获取
            cached_result = await cache_service.get(cache_key)
            if cached_result is not None:
                return cached_result

            # 执行函数并缓存结果
            result = await func(*args, **kwargs)
            await cache_service.set(cache_key, result, expire)

            return result

        return wrapper
    return decorator

# 使用示例
class ShifuService:
    @tenant_cache(expire=1800, key_pattern="shifu:{}")
    async def get_shifu(self, shifu_bid: str):
        """获取Shifu，带缓存"""
        return await self.shifu_repository.get_by_bid(shifu_bid)

    @tenant_cache(expire=300, key_pattern="shifu_list:{}:{}")
    async def list_shifus(self, page: int = 1, limit: int = 20):
        """获取Shifu列表，带缓存"""
        offset = (page - 1) * limit
        return await self.shifu_repository.list_all(offset, limit)
```

## 6. 文件存储隔离

### 6.1 对象存储隔离策略

```python
class TenantAwareFileStorage:
    """租户感知的文件存储服务"""

    def __init__(self, s3_client, bucket_name: str):
        self.s3 = s3_client
        self.bucket_name = bucket_name

    def _build_object_key(self, file_path: str, tenant_bid: str = None) -> str:
        """构建租户隔离的对象key"""
        if tenant_bid is None:
            tenant_bid = tenant_context.get_tenant()

        # 确保路径以租户ID开头
        return f"tenants/{tenant_bid}/{file_path.lstrip('/')}"

    async def upload_file(self, file_path: str, file_content: bytes,
                         content_type: str = None, metadata: dict = None):
        """上传文件到租户目录"""
        object_key = self._build_object_key(file_path)

        upload_args = {
            'Bucket': self.bucket_name,
            'Key': object_key,
            'Body': file_content
        }

        if content_type:
            upload_args['ContentType'] = content_type

        if metadata:
            upload_args['Metadata'] = metadata

        # 添加租户标识到metadata
        upload_args.setdefault('Metadata', {})['tenant_bid'] = tenant_context.get_tenant()

        await self.s3.put_object(**upload_args)

        return {
            'object_key': object_key,
            'url': f"https://{self.bucket_name}.s3.amazonaws.com/{object_key}",
            'tenant_bid': tenant_context.get_tenant()
        }

    async def download_file(self, file_path: str) -> bytes:
        """下载文件，自动验证租户权限"""
        object_key = self._build_object_key(file_path)

        try:
            response = await self.s3.get_object(
                Bucket=self.bucket_name,
                Key=object_key
            )

            # 验证文件所属租户
            metadata = response.get('Metadata', {})
            file_tenant = metadata.get('tenant_bid')
            current_tenant = tenant_context.get_tenant()

            if file_tenant and file_tenant != current_tenant:
                raise PermissionDeniedError("Access denied to file from different tenant")

            return await response['Body'].read()

        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                raise FileNotFoundError(f"File not found: {file_path}")
            raise

    async def delete_file(self, file_path: str):
        """删除文件"""
        object_key = self._build_object_key(file_path)

        await self.s3.delete_object(
            Bucket=self.bucket_name,
            Key=object_key
        )

    async def list_files(self, prefix: str = "", max_keys: int = 1000):
        """列出租户目录下的文件"""
        tenant_prefix = self._build_object_key(prefix)

        response = await self.s3.list_objects_v2(
            Bucket=self.bucket_name,
            Prefix=tenant_prefix,
            MaxKeys=max_keys
        )

        files = []
        for obj in response.get('Contents', []):
            # 移除租户前缀，返回相对路径
            relative_path = obj['Key'][len(f"tenants/{tenant_context.get_tenant()}/"):]

            files.append({
                'key': relative_path,
                'size': obj['Size'],
                'last_modified': obj['LastModified'],
                'etag': obj['ETag']
            })

        return files

    async def get_tenant_storage_usage(self, tenant_bid: str) -> dict:
        """获取租户存储使用情况"""
        prefix = f"tenants/{tenant_bid}/"

        total_size = 0
        file_count = 0

        paginator = self.s3.get_paginator('list_objects_v2')

        async for page in paginator.paginate(
            Bucket=self.bucket_name,
            Prefix=prefix
        ):
            for obj in page.get('Contents', []):
                total_size += obj['Size']
                file_count += 1

        return {
            'tenant_bid': tenant_bid,
            'total_size_bytes': total_size,
            'total_size_gb': round(total_size / (1024**3), 2),
            'file_count': file_count
        }

# CDN URL生成服务
class TenantAwareCDNService:
    """租户感知的CDN服务"""

    def __init__(self, cdn_domain: str, signing_key: str = None):
        self.cdn_domain = cdn_domain
        self.signing_key = signing_key

    def generate_public_url(self, file_path: str, tenant_bid: str = None) -> str:
        """生成公开访问URL"""
        if tenant_bid is None:
            tenant_bid = tenant_context.get_tenant()

        object_key = f"tenants/{tenant_bid}/{file_path.lstrip('/')}"
        return f"https://{self.cdn_domain}/{object_key}"

    def generate_signed_url(self, file_path: str, expires_in: int = 3600,
                           tenant_bid: str = None) -> str:
        """生成签名URL（私有文件访问）"""
        if not self.signing_key:
            raise ConfigurationError("CDN signing key not configured")

        if tenant_bid is None:
            tenant_bid = tenant_context.get_tenant()

        object_key = f"tenants/{tenant_bid}/{file_path.lstrip('/')}"
        expires_at = int(time.time()) + expires_in

        # 生成签名
        string_to_sign = f"{object_key}:{expires_at}"
        signature = hmac.new(
            self.signing_key.encode(),
            string_to_sign.encode(),
            hashlib.sha256
        ).hexdigest()

        return f"https://{self.cdn_domain}/{object_key}?expires={expires_at}&signature={signature}"
```

## 7. 跨租户功能支持

### 7.1 平台级数据聚合

```python
class CrossTenantAnalyticsService:
    """跨租户数据分析服务"""

    def __init__(self, database_router: DatabaseRouter = None):
        self.db_router = database_router
        self.platform_db = None  # 平台级数据库连接

    async def get_platform_metrics(self) -> dict:
        """获取平台级指标"""
        if self.db_router:
            # Database-per-Tenant模式：需要跨库查询
            return await self._get_metrics_multi_db()
        else:
            # Row-Level Security模式：直接聚合查询
            return await self._get_metrics_single_db()

    async def _get_metrics_single_db(self) -> dict:
        """单数据库模式的指标聚合"""
        # 临时清除租户上下文，进行平台级查询
        original_tenant = tenant_context._tenant_bid
        tenant_context.clear()

        try:
            # 使用原生SQL进行聚合查询
            metrics = await self.platform_db.fetch_one("""
                SELECT
                    COUNT(DISTINCT tenant_bid) as total_tenants,
                    COUNT(DISTINCT CASE WHEN user_state = 1 THEN user_id END) as active_users,
                    COUNT(DISTINCT shifu_bid) as total_shifus,
                    COUNT(order_bid) as total_orders,
                    SUM(CASE WHEN status = 502 THEN paid_price ELSE 0 END) as total_revenue
                FROM user_info u
                LEFT JOIN shifu_published_shifus s ON u.tenant_bid = s.tenant_bid
                LEFT JOIN order_orders o ON u.tenant_bid = o.tenant_bid
                WHERE u.deleted = 0
            """)

            return metrics

        finally:
            # 恢复租户上下文
            if original_tenant:
                tenant_context.set_tenant(original_tenant)

    async def _get_metrics_multi_db(self) -> dict:
        """多数据库模式的指标聚合"""
        # 获取所有活跃租户
        active_tenants = await self.get_active_tenants()

        # 并行查询所有租户数据库
        tasks = [
            self._get_tenant_metrics(tenant.tenant_bid)
            for tenant in active_tenants
        ]

        tenant_metrics = await asyncio.gather(*tasks, return_exceptions=True)

        # 聚合结果
        total_metrics = {
            'total_tenants': len(active_tenants),
            'active_users': 0,
            'total_shifus': 0,
            'total_orders': 0,
            'total_revenue': 0
        }

        for metrics in tenant_metrics:
            if isinstance(metrics, dict):
                total_metrics['active_users'] += metrics.get('active_users', 0)
                total_metrics['total_shifus'] += metrics.get('total_shifus', 0)
                total_metrics['total_orders'] += metrics.get('total_orders', 0)
                total_metrics['total_revenue'] += metrics.get('total_revenue', 0)

        return total_metrics

    async def _get_tenant_metrics(self, tenant_bid: str) -> dict:
        """获取单个租户的指标"""
        session = await self.db_router.get_session(tenant_bid)

        try:
            result = await session.execute("""
                SELECT
                    COUNT(DISTINCT CASE WHEN user_state = 1 THEN user_id END) as active_users,
                    (SELECT COUNT(*) FROM shifu_published_shifus WHERE deleted = 0) as total_shifus,
                    (SELECT COUNT(*) FROM order_orders WHERE deleted = 0) as total_orders,
                    (SELECT SUM(CASE WHEN status = 502 THEN paid_price ELSE 0 END)
                     FROM order_orders WHERE deleted = 0) as total_revenue
                FROM user_info
                WHERE deleted = 0
            """)

            return dict(result.fetchone())

        except Exception as e:
            logger.error(f"Failed to get metrics for tenant {tenant_bid}: {e}")
            return {}
        finally:
            await session.close()
```

### 7.2 数据迁移和同步

```python
class TenantDataMigrationService:
    """租户数据迁移服务"""

    async def migrate_tenant_to_dedicated_db(self, tenant_bid: str) -> dict:
        """将租户从共享数据库迁移到独立数据库"""

        # 1. 创建独立数据库
        target_db_info = await self.database_router.create_tenant_database(tenant_bid)

        try:
            # 2. 导出租户数据
            export_file = await self._export_tenant_data(tenant_bid)

            # 3. 导入到目标数据库
            await self._import_tenant_data(target_db_info, export_file)

            # 4. 验证数据完整性
            validation_result = await self._validate_migration(tenant_bid, target_db_info)
            if not validation_result['success']:
                raise MigrationValidationError(f"Migration validation failed: {validation_result['errors']}")

            # 5. 更新路由配置
            await self._update_tenant_routing(tenant_bid, target_db_info)

            # 6. 清理源数据（软删除）
            await self._cleanup_source_data(tenant_bid)

            return {
                'success': True,
                'tenant_bid': tenant_bid,
                'target_database': target_db_info.database_name,
                'migrated_records': validation_result['record_counts']
            }

        except Exception as e:
            # 回滚：删除目标数据库
            await self._cleanup_failed_migration(target_db_info)
            raise MigrationError(f"Migration failed for tenant {tenant_bid}: {e}")

    async def _export_tenant_data(self, tenant_bid: str) -> str:
        """导出租户数据"""
        export_file = f"/tmp/tenant_export_{tenant_bid}_{int(time.time())}.sql"

        # 获取需要迁移的表列表
        tables_to_export = await self._get_tenant_tables()

        # 构建mysqldump命令
        dump_args = [
            'mysqldump',
            '--single-transaction',
            '--routines',
            '--triggers',
            '--where', f"tenant_bid='{tenant_bid}'",
            self.source_db_config['database']
        ]
        dump_args.extend(tables_to_export)

        # 执行导出
        process = await asyncio.create_subprocess_exec(
            *dump_args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise ExportError(f"mysqldump failed: {stderr.decode()}")

        # 保存到文件
        with open(export_file, 'wb') as f:
            f.write(stdout)

        return export_file

    async def _validate_migration(self, tenant_bid: str, target_db_info: DatabaseInfo) -> dict:
        """验证迁移数据完整性"""
        validation_errors = []
        record_counts = {}

        # 获取源数据库记录数
        source_counts = await self._get_tenant_record_counts(tenant_bid, self.source_db)

        # 获取目标数据库记录数
        target_session = await self.db_router.get_session_by_db_info(target_db_info)
        target_counts = await self._get_record_counts(target_session)

        # 比较记录数
        for table, source_count in source_counts.items():
            target_count = target_counts.get(table, 0)
            record_counts[table] = {
                'source': source_count,
                'target': target_count,
                'match': source_count == target_count
            }

            if source_count != target_count:
                validation_errors.append(
                    f"Record count mismatch in table {table}: source={source_count}, target={target_count}"
                )

        # 验证关键数据完整性
        critical_validations = await self._run_critical_validations(tenant_bid, target_db_info)
        validation_errors.extend(critical_validations)

        return {
            'success': len(validation_errors) == 0,
            'errors': validation_errors,
            'record_counts': record_counts
        }
```

## 8. 性能优化策略

### 8.1 查询优化

```python
class TenantAwareQueryOptimizer:
    """租户感知的查询优化器"""

    @staticmethod
    def optimize_tenant_query(query, model_class):
        """优化租户查询"""
        # 1. 确保租户过滤条件在最前面
        tenant_bid = tenant_context.get_tenant()
        query = query.filter(model_class.tenant_bid == tenant_bid)

        # 2. 添加合适的索引提示
        if hasattr(model_class, '__table__'):
            # 使用租户相关的索引
            query = query.execution_options(
                mysql_use_index=['idx_tenant_bid', 'idx_tenant_status']
            )

        return query

    @staticmethod
    def build_optimized_filters(filters: dict, model_class):
        """构建优化的过滤条件"""
        conditions = []

        # 租户过滤始终是第一个条件
        tenant_bid = tenant_context.get_tenant()
        conditions.append(model_class.tenant_bid == tenant_bid)

        # 按选择性排序其他过滤条件
        high_selectivity = []  # 高选择性条件
        low_selectivity = []   # 低选择性条件

        for field, value in filters.items():
            if hasattr(model_class, field):
                column = getattr(model_class, field)
                condition = column == value

                # 根据字段类型和索引情况判断选择性
                if field in ['id', 'email', 'unique_identifier']:
                    high_selectivity.append(condition)
                else:
                    low_selectivity.append(condition)

        # 高选择性条件优先
        conditions.extend(high_selectivity)
        conditions.extend(low_selectivity)

        return conditions

class PerformanceMetrics:
    """性能指标收集"""

    def __init__(self):
        self.metrics = defaultdict(list)

    async def track_query_performance(self, tenant_bid: str, table_name: str,
                                    query_type: str, duration: float, record_count: int):
        """跟踪查询性能"""
        metric = {
            'tenant_bid': tenant_bid,
            'table_name': table_name,
            'query_type': query_type,  # select, insert, update, delete
            'duration_ms': duration * 1000,
            'record_count': record_count,
            'timestamp': datetime.utcnow()
        }

        # 发送到监控系统
        await self._send_to_monitoring_system(metric)

        # 检查性能阈值
        if duration > 1.0:  # 超过1秒的慢查询
            await self._handle_slow_query(metric)

    async def _handle_slow_query(self, metric: dict):
        """处理慢查询"""
        logger.warning(f"Slow query detected: {metric}")

        # 发送告警
        await self.send_alert(
            f"Slow query detected in tenant {metric['tenant_bid']}: "
            f"{metric['table_name']}.{metric['query_type']} took {metric['duration_ms']:.2f}ms"
        )

        # 可以触发自动优化建议
        await self._suggest_optimization(metric)
```

### 8.2 连接池管理

```python
class TenantAwareConnectionPool:
    """租户感知的连接池管理"""

    def __init__(self):
        self.pools = {}
        self.pool_stats = defaultdict(lambda: {
            'active_connections': 0,
            'total_requests': 0,
            'avg_response_time': 0
        })

    async def get_pool_for_tenant(self, tenant_bid: str):
        """获取租户的连接池"""
        if tenant_bid not in self.pools:
            # 根据租户级别配置不同的连接池
            tenant_info = await self.get_tenant_info(tenant_bid)
            pool_config = self._get_pool_config(tenant_info.subscription_plan)

            self.pools[tenant_bid] = await self._create_pool(tenant_bid, pool_config)

        return self.pools[tenant_bid]

    def _get_pool_config(self, subscription_plan: str) -> dict:
        """根据订阅计划获取连接池配置"""
        configs = {
            'starter': {
                'min_size': 2,
                'max_size': 10,
                'max_queries': 50000,
                'max_inactive_time': 300
            },
            'professional': {
                'min_size': 5,
                'max_size': 25,
                'max_queries': 100000,
                'max_inactive_time': 600
            },
            'enterprise': {
                'min_size': 10,
                'max_size': 50,
                'max_queries': 200000,
                'max_inactive_time': 1200
            }
        }

        return configs.get(subscription_plan, configs['starter'])

    async def monitor_pool_health(self):
        """监控连接池健康状态"""
        for tenant_bid, pool in self.pools.items():
            stats = {
                'tenant_bid': tenant_bid,
                'size': pool.get_size(),
                'free_size': pool.get_free_size(),
                'max_size': pool.get_max_size(),
                'utilization': (pool.get_size() - pool.get_free_size()) / pool.get_max_size()
            }

            # 记录监控指标
            await self.metrics_service.record('connection_pool_stats', stats)

            # 检查池利用率
            if stats['utilization'] > 0.8:
                logger.warning(f"High connection pool utilization for tenant {tenant_bid}: {stats['utilization']:.2%}")

            # 检查是否需要扩容
            if stats['utilization'] > 0.9 and stats['size'] < stats['max_size']:
                await self._expand_pool(tenant_bid, pool)

    async def _expand_pool(self, tenant_bid: str, pool):
        """动态扩容连接池"""
        current_size = pool.get_size()
        max_size = pool.get_max_size()

        # 扩容20%或最多到最大值
        new_size = min(int(current_size * 1.2), max_size)

        logger.info(f"Expanding connection pool for tenant {tenant_bid} from {current_size} to {new_size}")

        # 这里需要根据具体的连接池实现来扩容
        # await pool.resize(new_size)
```

这个数据隔离策略设计提供了完整的多租户数据隔离解决方案，支持不同隔离级别的选择，具备良好的性能和安全性保证。
