#!/bin/bash
#
# 懒猫微服自动化部署脚本 | Automated Lazycat Deployment Script
#
# 使用方法: ./deploy-to-lazycat.sh [-v|--verbose] [-a|--auto-install] [-h|--help]
#

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# 默认参数
VERBOSE=false
AUTO_INSTALL=false

# 打印函数
print_step() {
    echo -e "${GREEN}[$1/6] $2${NC}"
}

print_error() {
    echo -e "${RED}❌ 错误: $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

# 帮助信息
show_help() {
    cat << EOF
懒猫微服自动化部署脚本

使用方法: ./deploy-to-lazycat.sh [选项]

选项:
  -v, --verbose       显示详细输出
  -a, --auto-install  自动安装（不提示）
  -h, --help          显示此帮助信息

前置要求:
  - Docker 已安装并运行
  - lzc-cli 已安装并登录
  - Docker Hub 账号
  - Node.js 和 npm 已安装

配置:
  编辑 .env 文件设置 DOCKERHUB_USERNAME
EOF
    exit 0
}

# 解析参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -a|--auto-install)
            AUTO_INSTALL=true
            shift
            ;;
        -h|--help)
            show_help
            ;;
        *)
            echo "未知参数: $1"
            show_help
            ;;
    esac
done

# 加载配置
ENV_FILE="$SCRIPT_DIR/.env"
if [[ -f "$ENV_FILE" ]]; then
    while IFS= read -r line || [[ -n "$line" ]]; do
        # 跳过注释和空行
        [[ "$line" =~ ^[[:space:]]*# ]] && continue
        [[ -z "$line" ]] && continue

        # 解析 KEY=VALUE
        if [[ "$line" =~ ^[[:space:]]*([^#][^=]+)=(.*)$ ]]; then
            key="${BASH_REMATCH[1]}"
            value="${BASH_REMATCH[2]}"

            # 移除行尾注释（如果值不是引号包裹的）
            if [[ ! "$value" =~ ^\" ]] && [[ ! "$value" =~ ^\' ]]; then
                value="${value%%#*}"
            fi

            # 移除引号
            value="${value%\"}"
            value="${value#\"}"
            value="${value%\'}"
            value="${value#\'}"

            # 去除首尾空格
            key="$(echo "$key" | xargs)"
            value="$(echo "$value" | xargs)"

            # 导出变量（跳过与脚本参数冲突的）
            if [[ "$key" != "VERBOSE" ]] && [[ "$key" != "AUTO_INSTALL" ]]; then
                export "$key=$value"
            else
                # 特殊处理
                if [[ "$key" == "AUTO_INSTALL" ]] && [[ "$AUTO_INSTALL" == "false" ]] && [[ "$value" == "true" ]]; then
                    AUTO_INSTALL=true
                fi
                if [[ "$key" == "VERBOSE" ]] && [[ "$VERBOSE" == "false" ]] && [[ "$value" == "true" ]]; then
                    VERBOSE=true
                fi
            fi
        fi
    done < "$ENV_FILE"
else
    print_error ".env 文件不存在，请创建并配置"
    exit 1
fi

# 检查必需配置
if [[ -z "$DOCKERHUB_USERNAME" ]]; then
    print_error "请在 .env 文件中设置您的 DOCKERHUB_USERNAME"
    exit 1
fi

# 从 lzc-manifest.yml 提取版本号
MANIFEST_PATH="$SCRIPT_DIR/lzc-manifest.yml"
if [[ -f "$MANIFEST_PATH" ]]; then
    IMAGE_TAG=$(grep -E '^version:' "$MANIFEST_PATH" | sed 's/version:[[:space:]]*//' | tr -d '[:space:]')
    if [[ -n "$IMAGE_TAG" ]]; then
        echo -e "${CYAN}从 lzc-manifest.yml 提取版本号: $IMAGE_TAG${NC}"
    else
        print_error "无法从 lzc-manifest.yml 提取版本号"
        exit 1
    fi
else
    print_error "lzc-manifest.yml 不存在"
    exit 1
fi

# 设置变量
LOCAL_IMAGE_NAME="${LOCAL_IMAGE_NAME:-cloud.lazycat.app.ups-guard}"
DOCKERHUB_REPOSITORY="${DOCKERHUB_REPOSITORY:-ups-guard}"

LOCAL_IMAGE="${LOCAL_IMAGE_NAME}:${IMAGE_TAG}"
DOCKERHUB_IMAGE="${DOCKERHUB_USERNAME}/${DOCKERHUB_REPOSITORY}:${IMAGE_TAG}"

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  UPS Guard 懒猫微服部署${NC}"
echo -e "${BLUE}  Docker Hub: ${DOCKERHUB_IMAGE}${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Step 1: 构建前端
print_step 1 "构建前端..."
cd "$PROJECT_ROOT/frontend"
if [[ "$VERBOSE" == "true" ]]; then
    npm install
    npm run build
else
    npm install > /dev/null 2>&1
    npm run build > /dev/null 2>&1
fi
print_success "前端构建完成"

# Step 2: 构建 Docker 镜像
print_step 2 "构建 Docker 镜像..."
cd "$SCRIPT_DIR"
if [[ "$VERBOSE" == "true" ]]; then
    docker build -t "$LOCAL_IMAGE" -f Dockerfile "$PROJECT_ROOT"
else
    docker build -t "$LOCAL_IMAGE" -f Dockerfile "$PROJECT_ROOT" > /dev/null 2>&1
fi
print_success "Docker 镜像构建完成: $LOCAL_IMAGE"

# Step 3: 登录并推送到 Docker Hub
print_step 3 "推送到 Docker Hub..."

# 检查是否已登录
if ! docker info 2>/dev/null | grep -q "Username"; then
    echo "请登录 Docker Hub (输入用户名和密码/PAT):"
    docker login
fi

# 打标签
docker tag "$LOCAL_IMAGE" "$DOCKERHUB_IMAGE"
print_success "镜像已标记: $DOCKERHUB_IMAGE"

# 推送
echo "正在推送到 Docker Hub..."
if [[ "$VERBOSE" == "true" ]]; then
    docker push "$DOCKERHUB_IMAGE"
else
    docker push "$DOCKERHUB_IMAGE" 2>&1 | grep -E "(Pushing|Pushed|digest:)" || true
fi
print_success "已推送到 Docker Hub"

# Step 4: 复制到懒猫 Registry 并自动更新 manifest
print_step 4 "复制到懒猫 Registry 并更新 manifest..."
echo "使用 lzc-cli 从 Docker Hub 复制..."

# 捕获 lzc-cli 输出
OUTPUT=$(lzc-cli appstore copy-image "$DOCKERHUB_IMAGE" 2>&1)
echo "$OUTPUT"

# 提取 registry 镜像地址
REGISTRY_IMAGE=$(echo "$OUTPUT" | grep -oE 'registry\.lazycat\.cloud/[^[:space:]]+' | head -1)
if [[ -n "$REGISTRY_IMAGE" ]]; then
    print_success "已复制到懒猫 Registry: $REGISTRY_IMAGE"

    # 只更新 lzc-manifest.yml 中的 image 字段
    echo "正在更新 lzc-manifest.yml 的 image 字段..."
    sed -i.bak "s|image:.*|image: $REGISTRY_IMAGE|" "$MANIFEST_PATH"
    rm -f "${MANIFEST_PATH}.bak"

    print_success "已更新 image: $REGISTRY_IMAGE"
else
    print_error "无法提取 registry 镜像地址，请检查 lzc-cli 输出"
    exit 1
fi

echo ""

# Step 5: 构建 LPK 包
print_step 5 "构建 LPK 包..."
cd "$SCRIPT_DIR"

# 确保目录存在
mkdir -p content lpk

# 构建
if [[ "$VERBOSE" == "true" ]]; then
    lzc-cli project build
else
    lzc-cli project build 2>&1 | grep -E "(Building|Success|Error)" || true
fi

LPK_FILE=$(ls -t lpk/*.lpk 2>/dev/null | head -1)
if [[ -n "$LPK_FILE" ]]; then
    print_success "LPK 包已创建: $SCRIPT_DIR/$LPK_FILE"
else
    print_error "LPK 包创建失败"
    exit 1
fi

# Step 6: 安装到设备 (可选)
print_step 6 "安装到设备..."

if [[ "$AUTO_INSTALL" == "true" ]]; then
    lzc-cli app install "$LPK_FILE"
    print_success "应用已安装到设备"
else
    echo ""
    read -p "是否要安装到设备? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        lzc-cli app install "$LPK_FILE"
        print_success "应用已安装到设备"
    else
        echo "跳过安装。可以稍后手动安装:"
        echo "  lzc-cli app install $SCRIPT_DIR/$LPK_FILE"
    fi
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  ✅ 部署完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "接下来的步骤:"
echo "1. 验证 lzc-manifest.yml 中的镜像字段是否已更新"
echo "2. 访问设备 Web 界面验证应用是否正在运行"
echo "3. 查看日志: lzc-cli app logs cloud.lazycat.app.ups-guard"
echo ""

