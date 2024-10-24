---
displayed_sidebar: English
---

# 使用 GCS 部署 StarRocks

import SharedDataIntro from '../../assets/commonMarkdown/sharedDataIntro.md'
import SharedDataCNconf from '../../assets/commonMarkdown/sharedDataCNconf.md'
import SharedDataUseIntro from '../../assets/commonMarkdown/sharedDataUseIntro.md'
import SharedDataUse from '../../assets/commonMarkdown/sharedDataUse.md'

<SharedDataIntro />

## 架构

![存算分离架构](../../assets/share_data_arch.png)

## 部署一个存算分离模式的 StarRocks 集群

部署一个存算分离模式的 StarRocks 集群与部署一个存算一体集群类似。唯一的区别是你需要在存算分离集群中部署 CN 而不是 BE。本节仅列出在部署存算分离模式的 StarRocks 集群时，你需要在 FE 和 CN 的配置文件 **fe.conf** 和 **cn.conf** 中添加的额外 FE 和 CN 配置项。有关部署 StarRocks 集群的详细说明，请参见[部署 StarRocks](../../deployment/deploy_manually.md)。

> **注意**
>
> 请在下一节配置完共享存储后再启动集群。

## 为存算分离模式的 StarRocks 配置 FE 节点

在启动集群前，请先配置 FE 和 CN。下面提供了一个配置示例，然后提供了每个参数的详细说明。

### GCS 的 FE 示例配置

示例中的存算分离模式添加配置可以加到每个 FE 节点的 `fe.conf` 文件中。因为 GCS 存储是通过 [Cloud Storage XML API](https://cloud.google.com/storage/docs/xml-api/overview) 访问的，所以参数使用了前缀 `aws_s3`。

  ```Properties
  run_mode = shared_data
  cloud_native_meta_port = <meta_port>
  cloud_native_storage_type = S3

  # 例如，testbucket/subpath
  aws_s3_path = <s3_path>

  # 例如：us-east1
  aws_s3_region = <region>

  # 例如：https://storage.googleapis.com
  aws_s3_endpoint = <endpoint_url>

  aws_s3_access_key = <HMAC access_key>
  aws_s3_secret_key = <HMAC secret_key>
  ```

### 与 GCS 共享存储相关的所有 FE 参数

#### run_mode

StarRocks 集群的运行模式。有效值：

- `shared_data`
- `shared_nothing` (默认值)。

> **注意**
>
> 你不能同时为 StarRocks 集群采用 `shared_data` 和 `shared_nothing` 模式。不支持混合部署。
>
> 部署后不要更改 `run_mode`，否则集群将无法重启。不支持从存算一体集群到存算分离集群或反之的转换。

#### cloud_native_meta_port

云原生元服务 RPC 端口。

- 默认值：`6090`

#### enable_load_volume_from_conf

是否允许 StarRocks 使用 FE 配置文件中指定的对象存储相关属性创建默认存储卷。有效值：

- `true` (默认值) 如果在创建新的存算分离集群时将此项指定为 `true`，StarRocks 将使用 FE 配置文件中的对象存储相关属性创建内置存储卷 `builtin_storage_volume` 并将其设置为默认存储卷。然而，如果你没有指定对象存储相关属性，StarRocks 将无法启动。
- `false` 如果在创建新的存算分离集群时将此项指定为 `false`，StarRocks 将直接启动，而不创建内置存储卷。你必须手动创建一个存储卷并将其设置为默认存储卷，然后才能在 StarRocks 中创建任何对象。有关更多信息，请参见[创建默认存储卷](#use-your-shared-data-starrocks-cluster)。

从 v3.1.0 开始支持。

> **警告**
>
> 我们强烈建议你在将现有存算分离集群从 v3.0 升级时将此项保留为 `true`。如果你将此项指定为 `false`，那么升级前创建的数据库和表将变为只读，你将无法加载数据到它们中。

#### cloud_native_storage_type

你使用的对象存储类型。在存算分离模式下，StarRocks 支持将数据存储在 Azure Blob（从 v3.1.1 版本开始支持）和与 S3 协议兼容的对象存储（如 AWS S3、Google GCS 和 MinIO）中。有效值：

- `S3` (默认值)
- `AZBLOB`。

#### aws_s3_path

用于存储数据的 S3 路径。它由你的 S3 存储桶的名称和其下的子路径（如果有的话）组成，例如，`testbucket/subpath`。

#### aws_s3_endpoint

用于访问你的 S3 存储桶的端点，例如，`https://storage.googleapis.com/`

#### aws_s3_region

你的 S3 存储桶所在的区域，例如，`us-west-2`。

#### aws_s3_use_instance_profile

是否使用实例配置文件和假定角色作为访问 GCS 的凭证方法。有效值：

- `true`
- `false` (默认值)。

如果你使用基于 IAM 用户的凭证（访问密钥和密钥）来访问 GCS，你必须将此项指定为 `false`，并指定 `aws_s3_access_key` 和 `aws_s3_secret_key`。

如果你使用实例配置文件来访问 GCS，你必须将此项指定为 `true`。

如果你使用假定角色来访问 GCS，你必须将此项指定为 `true`，并指定 `aws_s3_iam_role_arn`。

如果你使用外部 AWS 账户，你还必须指定 `aws_s3_external_id`。

#### aws_s3_access_key

用于访问你的 GCS 存储桶的 HMAC 访问密钥 ID。

#### aws_s3_secret_key

用于访问你的 GCS 存储桶的 HMAC 密钥访问密钥。

#### aws_s3_iam_role_arn

在你的 GCS 存储桶中存储数据文件的 IAM 角色的 ARN。

#### aws_s3_external_id

用于跨账户访问你的 GCS 存储桶的 AWS 账户的外部 ID。

> **注意**
>
> 仅可在创建存算分离模式的 StarRocks 集群后修改与凭证相关的配置项。如果你更改了原始的存储路径相关配置项，那么更改前创建的数据库和表将变为只读，你将无法加载数据到它们中。

如果你希望在集群创建后手动创建默认存储卷，你只需添加以下配置项：

```Properties
run_mode = shared_data
cloud_native_meta_port = <meta_port>
enable_load_volume_from_conf = false
```

## 为存算分离模式的 StarRocks 配置 CN 节点

<SharedDataCNconf />

## 使用你的存算分离模式 StarRocks 集群

<SharedDataUseIntro />

以下示例为 GCS 存储桶 `defaultbucket` 创建了一个存储卷 `def_volume`，使用 HMAC 访问密钥和密钥，启用了 [分区前缀](../../sql-reference/sql-statements/Administration/CREATE_STORAGE_VOLUME.md#partitioned-prefix) 功能，并将其设置为默认存储卷：

```SQL
CREATE STORAGE VOLUME def_volume
TYPE = S3
LOCATIONS = ("s3://defaultbucket")
PROPERTIES
(
    "enabled" = "true",
    "aws.s3.region" = "us-east1",
    "aws.s3.endpoint" = "https://storage.googleapis.com",
    "aws.s3.access_key" = "<HMAC access key>",
    "aws.s3.secret_key" = "<HMAC secret key>",
    "aws.s3.enable_partitioned_prefix" = "true"
);

SET def_volume AS DEFAULT STORAGE VOLUME;
```

<SharedDataUse />