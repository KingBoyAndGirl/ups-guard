#!/usr/bin/env pwsh
#
# 懒猫微服自动化部署脚本 | Automated Lazycat Deployment Script
#
# 使用方法: .\deploy-to-lazycat.ps1 [-Verbose] [-AutoInstall]
#

param(
    [switch]$Verbose,
    [switch]$AutoInstall,
    [switch]$Help
)

if ($Help) {
    Write-Host @"
懒猫微服自动化部署脚本

使用方法: .\deploy-to-lazycat.ps1 [选项]

选项:
  -Verbose        显示详细输出
  -AutoInstall    自动安装（不提示）
  -Help           显示此帮助信息

前置要求:
  - Docker Desktop 已安装并运行
  - lzc-cli 已安装并登录
  - Docker Hub 账号
  - Node.js 和 npm 已安装

配置:
  编辑 .env 文件设置 DOCKERHUB_USERNAME
"@
    exit 0
}

$ErrorActionPreference = "Stop"

# 脚本目录
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Join-Path $ScriptDir "..\..\" | Resolve-Path

# 打印函数
function Print-Step {
    param($Step, $Message)
    Write-Host "[$Step/6] $Message" -ForegroundColor Green
}

function Print-Error {
    param($Message)
    Write-Host "❌ 错误: $Message" -ForegroundColor Red
}

function Print-Success {
    param($Message)
    Write-Host "✅ $Message" -ForegroundColor Green
}

# 加载配置
$EnvFile = Join-Path $ScriptDir ".env"
# 需要跳过的变量名（与脚本参数冲突）
$SkipVars = @("Verbose", "AutoInstall", "Help", "AUTO_INSTALL", "VERBOSE")

if (Test-Path $EnvFile) {
    $envVars = @{}
    Get-Content $EnvFile -Encoding UTF8 | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()

            # 检查是否以引号开头
            if ($value -match '^"') {
                # 带引号的值：提取引号内的完整内容（支持内部包含 #）
                if ($value -match '^"(.*)"') {
                    $value = $matches[1]
                }
            } elseif ($value -match "^'") {
                # 单引号
                if ($value -match "^'(.*)'") {
                    $value = $matches[1]
                }
            } else {
                # 不带引号的值：移除行尾注释
                $commentIndex = $value.IndexOf('#')
                if ($commentIndex -ge 0) {
                    $value = $value.Substring(0, $commentIndex).Trim()
                }
            }
            $envVars[$name] = $value
        }
    }
    # 设置变量到脚本作用域
    foreach ($key in $envVars.Keys) {
        if ($key -notin $SkipVars) {
            Set-Variable -Name $key -Value $envVars[$key] -Scope Script
        } else {
            # 特殊处理: 如果命令行没有指定，则使用 .env 中的值
            if ($key -eq "AUTO_INSTALL" -and -not $AutoInstall) {
                if ($envVars[$key] -eq "true") { $script:AutoInstall = $true }
            }
            if ($key -eq "VERBOSE" -and -not $Verbose) {
                if ($envVars[$key] -eq "true") { $script:Verbose = $true }
            }
        }
    }
} else {
    Print-Error ".env 文件不存在，请从 .env.example 复制并配置"
    exit 1
}

# 检查必需配置
if ([string]::IsNullOrEmpty($DOCKERHUB_USERNAME)) {
    Print-Error "请在 .env 文件中设置您的 DOCKERHUB_USERNAME"
    exit 1
}

# 从 lzc-manifest.yml 提取版本号
$manifestPath = Join-Path $ScriptDir "lzc-manifest.yml"
if (Test-Path $manifestPath) {
    $manifestContent = Get-Content $manifestPath -Encoding UTF8 -Raw
    if ($manifestContent -match '(?m)^version:\s*(.+)$') {
        $IMAGE_TAG = $matches[1].Trim()
        Write-Host "从 lzc-manifest.yml 提取版本号: $IMAGE_TAG" -ForegroundColor Cyan
    } else {
        Print-Error "无法从 lzc-manifest.yml 提取版本号"
        exit 1
    }
} else {
    Print-Error "lzc-manifest.yml 不存在"
    exit 1
}

# 设置变量
if ([string]::IsNullOrEmpty($LOCAL_IMAGE_NAME)) { $LOCAL_IMAGE_NAME = "cloud.lazycat.app.ups-guard" }
if ([string]::IsNullOrEmpty($DOCKERHUB_REPOSITORY)) { $DOCKERHUB_REPOSITORY = "ups-guard" }

$LOCAL_IMAGE = "${LOCAL_IMAGE_NAME}:${IMAGE_TAG}"
$DOCKERHUB_IMAGE = "${DOCKERHUB_USERNAME}/${DOCKERHUB_REPOSITORY}:${IMAGE_TAG}"


Write-Host ""
Write-Host "========================================" -ForegroundColor Blue
Write-Host "  UPS Guard 懒猫微服部署" -ForegroundColor Blue
Write-Host "  Docker Hub: ${DOCKERHUB_IMAGE}" -ForegroundColor Blue
Write-Host "========================================" -ForegroundColor Blue
Write-Host ""

try {
    # Step 1: 构建前端
    Print-Step 1 "构建前端..."
    Push-Location (Join-Path $ProjectRoot "frontend")
    if ($Verbose) {
        npm install
        npm run build
    } else {
        npm install | Out-Null
        npm run build | Out-Null
    }
    Pop-Location
    Print-Success "前端构建完成"

    # Step 2: 构建 Docker 镜像
    Print-Step 2 "构建 Docker 镜像..."
    Push-Location $ScriptDir
    if ($Verbose) {
        docker build -t $LOCAL_IMAGE -f Dockerfile $ProjectRoot
    } else {
        docker build -t $LOCAL_IMAGE -f Dockerfile $ProjectRoot | Out-Null
    }
    Pop-Location
    Print-Success "Docker 镜像构建完成: $LOCAL_IMAGE"

    # Step 3: 登录并推送到 Docker Hub
    Print-Step 3 "推送到 Docker Hub..."

    # 检查是否已登录
    $dockerInfo = docker info 2>&1 | Out-String
    if ($dockerInfo -notmatch "Username") {
        Write-Host "请登录 Docker Hub (输入用户名和密码/PAT):"
        docker login
    }

    # 打标签
    docker tag $LOCAL_IMAGE $DOCKERHUB_IMAGE
    Print-Success "镜像已标记: $DOCKERHUB_IMAGE"

    # 推送
    Write-Host "正在推送到 Docker Hub..."
    if ($Verbose) {
        docker push $DOCKERHUB_IMAGE
    } else {
        docker push $DOCKERHUB_IMAGE | Select-String -Pattern "(Pushing|Pushed|digest:)"
    }
    Print-Success "已推送到 Docker Hub"

    # Step 4: 复制到懒猫 Registry 并自动更新 manifest
    Print-Step 4 "复制到懒猫 Registry 并更新 manifest..."
    Write-Host "使用 lzc-cli 从 Docker Hub 复制..."

    # 捕获 lzc-cli 输出
    $output = lzc-cli appstore copy-image $DOCKERHUB_IMAGE 2>&1 | Out-String
    Write-Host $output
    
    # 提取 registry 镜像地址
    if ($output -match '(registry\.lazycat\.cloud/[^\s]+)') {
        $registryImage = $matches[1]
        Print-Success "已复制到懒猫 Registry: $registryImage"

        # 只更新 lzc-manifest.yml 中的 image 字段
        Write-Host "正在更新 lzc-manifest.yml 的 image 字段..."
        $manifestPath = Join-Path $ScriptDir "lzc-manifest.yml"
        $content = Get-Content $manifestPath -Encoding UTF8 -Raw
        $content = $content -replace 'image:.*', "image: $registryImage"

        # 写入文件（使用 UTF-8 无 BOM）
        $utf8NoBom = New-Object System.Text.UTF8Encoding $false
        [System.IO.File]::WriteAllText($manifestPath, $content, $utf8NoBom)

        Print-Success "已更新 image: $registryImage"
    } else {
        Print-Error "无法提取 registry 镜像地址，请检查 lzc-cli 输出"
        exit 1
    }
    
    Write-Host ""

    # Step 5: 构建 LPK 包
    Print-Step 5 "构建 LPK 包..."
    Push-Location $ScriptDir

    # 确保目录存在
    New-Item -ItemType Directory -Force -Path "content" | Out-Null
    New-Item -ItemType Directory -Force -Path "lpk" | Out-Null

    # 构建
    if ($Verbose) {
        lzc-cli project build
    } else {
        lzc-cli project build | Select-String -Pattern "(Building|Success|Error)"
    }

    $LPK_FILE = Get-ChildItem -Path "lpk\*.lpk" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($LPK_FILE) {
        Print-Success "LPK 包已创建: $($LPK_FILE.FullName)"
    } else {
        Print-Error "LPK 包创建失败"
        exit 1
    }
    Pop-Location

    # Step 6: 安装到设备 (可选)
    Print-Step 6 "安装到设备..."

    if ($AutoInstall) {
        lzc-cli app install $LPK_FILE.FullName
        Print-Success "应用已安装到设备"
    } else {
        Write-Host ""
        $response = Read-Host "是否要安装到设备? (y/N)"
        if ($response -match '^[Yy]$') {
            lzc-cli app install $LPK_FILE.FullName
            Print-Success "应用已安装到设备"
        } else {
            Write-Host "跳过安装。可以稍后手动安装:"
            Write-Host "  lzc-cli app install $($LPK_FILE.FullName)"
        }
    }

    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  ✅ 部署完成！" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "接下来的步骤:"
    Write-Host "1. 验证 lzc-manifest.yml 中的镜像字段是否已更新"
    Write-Host "2. 访问设备 Web 界面验证应用是否正在运行"
    Write-Host "3. 查看日志: lzc-cli app logs cloud.lazycat.app.ups-guard"
    Write-Host ""

} catch {
    Print-Error $_.Exception.Message
    exit 1
}
