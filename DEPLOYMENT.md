# 部署指南

## GitHub Actions 自动部署

本项目使用 GitHub Actions 实现 CI/CD 自动部署。

### 架构

```
Push/Tag → CI (Test + Lint + Build) → Build Docker Image → Push to GHCR → Deploy to Server
```

### 工作流

#### 1. CI 工作流 (`.github/workflows/ci.yml`)
- **触发条件**: push to main/develop, PR to main
- **执行内容**:
  - 运行单元测试
  - 代码检查 (Ruff + MyPy)
  - 构建测试 Docker 镜像
  - 上传覆盖率报告

#### 2. Deploy 工作流 (`.github/workflows/deploy.yml`)
- **触发条件**: 
  - push to main
  - 创建 tag (v*)
  - 手动触发
- **执行内容**:
  - 构建 Docker 镜像
  - 推送到 GitHub Container Registry
  - SSH 到服务器执行部署
  - 健康检查

## 配置 Secrets

在 GitHub 仓库设置中添加以下 Secrets:

### 必需的 Secrets

| Secret | 说明 |
|--------|------|
| `DEPLOY_HOST` | 部署服务器 IP/域名 |
| `DEPLOY_USER` | SSH 用户名 |
| `DEPLOY_KEY` | SSH 私钥 |

### API Keys (可选)

| Secret | 说明 |
|--------|------|
| `OPENAI_API_KEY` | OpenAI API 密钥 |
| `ANTHROPIC_API_KEY` | Anthropic API 密钥 |

## 服务器准备

### 1. 安装 Docker

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
```

### 2. 创建部署目录

```bash
sudo mkdir -p /opt/coderag-agent
sudo chown $USER:$USER /opt/coderag-agent
cd /opt/coderag-agent
```

### 3. 创建环境文件

```bash
cat > .env << EOF
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here
EOF
```

### 4. 创建 docker-compose.yml

将项目中的 `docker-compose.yml` 复制到服务器。

### 5. 配置 SSH

将 GitHub Actions 使用的 SSH 公钥添加到服务器的 `~/.ssh/authorized_keys`。

## 部署方式

### 自动部署

推送到 `main` 分支或创建 tag 自动触发:

```bash
# 推送到 main
git push origin main

# 创建 release
git tag v1.0.0
git push origin v1.0.0
```

### 手动部署

在 GitHub Actions 页面点击 "Deploy" 工作流 → "Run workflow"。

## 本地测试部署

### 1. 构建镜像

```bash
docker build -t coderag-agent:local .
```

### 2. 运行容器

```bash
docker run -d \
  --name coderag-agent \
  -p 7860:7860 \
  -p 8000:8000 \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  -v $(pwd)/chroma_db:/app/chroma_db \
  coderag-agent:local
```

### 3. 访问服务

- Web UI: http://localhost:7860
- API: http://localhost:8000

## 监控和日志

### 查看日志

```bash
docker logs -f coderag-agent
```

### 健康检查

```bash
curl http://localhost:8000/health
```

## 回滚

```bash
# 查看历史镜像
docker images | grep coderag-agent

# 停止当前容器
docker stop coderag-agent

# 使用旧镜像启动
docker run -d --name coderag-agent ... coderag-agent:previous_version
```

## 生产环境建议

1. **使用 HTTPS**: 配置 Nginx 反向代理 + Let's Encrypt
2. **资源限制**: 在 docker-compose.yml 中设置 CPU/内存限制
3. **日志轮转**: 配置 Docker 日志驱动
4. **备份策略**: 定期备份 chroma_db 数据
5. **监控告警**: 接入 Prometheus/Grafana 或其他监控方案
