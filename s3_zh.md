---
displayed_sidebar: Chinese
---

# 使用 S3 进行存算分离

<SharedDataIntro />

## 架构

![存算分离架构](../../assets/share_data_arch.png)

## 部署一个存算分离的 StarRocks 集群

部署存算分离模式的 StarRocks 集群与部署存算一体集群相似。唯一的区别是在存算分离集群中需要部署 CN 而不是 BE。本节只列出了在部署存算分离 StarRocks 集群时，需要在 FE 和 CN 的配置文件 **fe.conf** 和 **cn.conf** 中添加的额外 FE 和 CN 配置项。有关部署 StarRocks 集群的详细说明，请参见 [部署 StarRocks](../../deployment/deploy_manually.md)。

> **注意**
>
> 在下一节的文档中为共享存储配置集群之前，请勿启动集群。

## 为存算分离 StarRocks 配置 FE 节点

在启动集群前请先配置 FE 和 CN。下面提供了示例配置，然后提供了每个参数的详绀信息。

### S3 的示例 FE 配置

这些是每个 FE 节点上 `fe.conf` 文件的存算分离添加示例。示例根据使用的 AWS 身份验证方法的不同而不同。

#### 默认身份验证凭证

```Properties
run_mode = shared_data
cloud_native_meta_port = <meta_port>
cloud_native_storage_type = S3

# 例如, testbucket/subpath
aws_s3_path = <s3_path>

# 例如, us-west-2
aws_s3_region = <region>

# 例如, https://s3.us-west-2.amazonaws.com
aws_s3_endpoint = <endpoint_url>

aws_s3_use_aws_sdk_default_behavior = true

# 如果您不希望使用上述详细信息在对象存储中创建默认存储，请将此设置为 false
enable_load_volume_from_conf = true
```

#### 基于 IAM 用户的凭证

```Properties
run_mode = shared_data
cloud_native_meta_port = <meta_port>
cloud_native_storage_type = S3

# 例如, testbucket/subpath
aws_s3_path = <s3_path>

# 例如, us-west-2
aws_s3_region = <region>

# S3 对象读/写的凭证
aws_s3_access_key = <access_key>
aws_s3_secret_key = <secret_key>

# 如果您不希望使用上述详细信息在对象存储中创建默认存储，请将此设置为 false
enable_load_volume_from_conf = true
```

#### 实例配置文件

```Properties
run_mode = shared_data
cloud_native_meta_port = <meta_port>
cloud_native_storage_type = S3

# 例如, testbucket/subpath
aws_s3_path = <s3_path>

# 例如, us-west-2
aws_s3_region = <region>

# 例如, https://s3.us-west-2.amazonaws.com
aws_s3_endpoint = <endpoint_url>

aws_s3_use_instance_profile = true

# 如果您不希望使用上述详细信息在对象存储中创建默认存储，请将此设置为 false
enable_load_volume_from_conf = true
```

#### 假定角色

```Properties
run_mode = shared_data
cloud_native_meta_port = <meta_port>
cloud_native_storage_type = S3

# 例如, testbucket/subpath
aws_s3_path = <s3_path>

# 例如, us-west-2
aws_s3_region = <region>

# 例如, https://s3.us-west-2.amazonaws.com
aws_s3_endpoint = <endpoint_url>

aws_s3_use_instance_profile = true
aws_s3_iam_role_arn = <role_arn>

# 如果您不希望使用上述详细信息在对象存储中创建默认存储，请将此设置为 false
enable_load_volume_from_conf = true
```

#### 外部账户的假定角色

```Properties
run_mode = shared_data
cloud_native_meta_port = <meta_port>
cloud_native_storage_type = S3

# 例如, testbucket/subpath
aws_s3_path = <s3_path>

# 例如, us-west-2
aws_s3_region = <region>

# 例如, https://s3.us-west-2.amazonaws.com
aws_s3_endpoint = <endpoint_url>

aws_s3_use_instance_profile = true
aws_s3_iam_role_arn = <role_arn>
aws_s3_external_id = <external_id>

# 如果您不希望使用上述详细信息在对象存储中创建默认存储，请将此设置为 false
enable_load_volume_from_conf = true
```

### 与 S3 相关的所有 FE 参数

#### run_mode

StarRocks 集群的运行模式。有效值：

- `shared_data`
- `shared_nothing`（默认）。

> **注意**
>
> 不能同时为 StarRocks 集群采用 `shared_data` 和 `shared_nothing` 模式。不支持混合部署。
>
> 集群部署后，请勿更改 `run_mode`，否则集群无法重启。不支持从存算一体集群转换为存算分离集群，反之亦然。

#### cloud_native_meta_port

云原生元服务 RPC 端口。

- 默认值：`6090`

#### enable_load_volume_from_conf

是否允许 StarRocks 使用 FE 配置文件中指定的对象存储相关属性创建默认存储卷。有效值：

- `true`（默认）如果在创建新的存算分离集群时将此项指定为 `true`，StarRocks 会使用 FE 配置文件中的对象存储相关属性创建内置存储卷 `builtin_storage_volume`，并将其设置为默认存储卷。但是，如果您未指定对象存储相关属性，StarRocks 无法启动。
- `false` 如果在创建新的存算分离集群时将此项指定为 `false`，StarRocks 将直接启动而不创建内置存储卷。您必须手动创建存储卷并将其设置为默认存储卷，然后才能在 StarRocks 中创建任何对象。更多信息，请参见 [创建默认存储卷](#use-your-shared-data-starrocks-cluster)。

从 v3.1.0 版本开始支持。

> **警告**
>
> 我们强烈建议您在将现有存算分离集群从 v3.0 版本升级时将此项保留为 `true`。如果您将此项指定为 `false`，那么升级前创建的数据库和表将变为只读，您将无法加载数据到它们中。

#### cloud_native_storage_type

您使用的对象存储类型。在存算分离模式下，StarRocks 支持将数据存储在 Azure Blob（从 v3.1.1 版本开始支持）和与 S3 协议兼容的对象存储（如 AWS S3、Google GCP 和 MinIO）中。有效值：

- `S3`（默认）
- `AZBLOB`.

#### aws_s3_path

用于存储数据的 S3 路径。它由您的 S3 存储桶的名称和其下的子路径（如果有）组成，例如 `testbucket/subpath`。

#### aws_s3_endpoint

用于访问 S3 存储桶的端点，例如 `https://s3.us-west-2.amazonaws.com`。

#### aws_s3_region

您的 S3 存储桶所在的区域，例如 `us-west-2`。

#### aws_s3_use_aws_sdk_default_behavior

是否使用 [AWS SDK 默认凭证提供者链](https://docs.aws.amazon.com/AWSJavaSDK/latest/javadoc/com/amazonaws/auth/DefaultAWSCredentialsProviderChain.html)。有效值：

- `true`
- `false`（默认）。

#### aws_s3_use_instance_profile

是否使用实例配置文件和假定角色作为访问 S3 的凭证方法。有效值：

- `true`
- `false`（默认）。

如果您使用基于 IAM 用户的凭证（访问密钥和密钥）访问 S3，则必须将此项指定为 `false`，并指定 `aws_s3_access_key` 和 `aws_s3_secret_key`。

如果您使用实例配置文件访问 S3，则必须将此项指定为 `true`。

如果您使用假定角色访问 S3，则必须将此项指定为 `true`，并指定 `aws_s3_iam_role_arn`。

如果您使用外部 AWS 账户，则还必须指定 `aws_s3_external_id`。

#### aws_s3_access_key

用于访问 S3 存储桶的访问密钥 ID。

#### aws_s3_secret_key

用于访问 S3 存储桶的密钥。

#### aws_s3_iam_role_arn

在您的 S3 存储桶中拥有数据文件权限的 IAM 角色的 ARN。

#### aws_s3_external_id

用于跨账户访问 S3 存储桶的外部 AWS 账户的外部 ID。

> **注意**
>
> 只有与凭证相关的配置项在创建存算分离 StarRocks 集群后可以修改。如果您更改了原始存储路径相关的配置项，则更改前创建的数据库和表将变为只读，您将无法加载数据到它们中。

如果您希望在集群创建后手动创建默认存储卷，只需添加以下配置项：

```Properties
run_mode = shared_data
cloud_native_meta_port = <meta_port>
enable_load_volume_from_conf = false
```

## 为存算分离 StarRocks 配置 CN 节点
<SharedDataCNconf />

## 使用您的存算分离 StarRocks 集群

<SharedDataUseIntro />

下面的示例为 AWS S3 存储桶 `defaultbucket` 创建一个存储卷 `def_volume`，使用基于 IAM 用户的凭证（访问密钥和密钥），启用 [分区前缀](../../sql-reference/sql-statements/Administration/CREATE_STORAGE_VOLUME.md#partitioned-prefix) 功能，并将其设置为默认存储卷：

```SQL
CREATE STORAGE VOLUME def_volume
TYPE = S3
LOCATIONS = ("s3://defaultbucket")
PROPERTIES
(
    "enabled" = "true",
    "aws.s3.region" = "us-west-2",
    "aws.s3.endpoint" = "https://s3.us-west-2.amazonaws.com",
    "aws.s3.use_aws_sdk_default_behavior" = "false",
    "aws.s3.use_instance_profile" = "false",
    "aws.s3.access_key" = "xxxxxxxxxx",
    "aws.s3.secret_key" = "yyyyyyyyyy",
    "aws.s3.enable_partitioned_prefix" = "true"
);

SET def_volume AS DEFAULT STORAGE VOLUME;
```

<SharedDataUse />
