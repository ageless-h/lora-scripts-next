$Env:HF_HOME = "huggingface"
$Env:PYTHONUTF8 = "1"
$Env:MIKAZUKI_PORT = "28000"

# 自动检查并初始化所有 submodule（含 Anima 后端 vendor/sd-scripts）
$submoduleMarker = "vendor\sd-scripts\anima_train_network.py"
if (-not (Test-Path $submoduleMarker)) {
    Write-Host -ForegroundColor Cyan "首次运行：正在初始化必要组件，请稍候..."
    git submodule update --init --recursive
    if ($LASTEXITCODE -ne 0) {
        Write-Host -ForegroundColor Red "组件初始化失败，请检查网络连接后重新运行。"
        Read-Host "按 Enter 退出"
        exit 1
    }
    Write-Host -ForegroundColor Green "初始化完成，继续启动..."
}

if (Test-Path -Path "venv\Scripts\activate") {
    Write-Host -ForegroundColor green "Activating virtual environment..."
    .\venv\Scripts\activate
}
elseif (Test-Path -Path "python\python.exe") {
    Write-Host -ForegroundColor green "Using python from python folder..."
    $py_path = (Get-Item "python").FullName
    $env:PATH = "$py_path;$env:PATH"
}
else {
    Write-Host -ForegroundColor Blue "No virtual environment found, using system python..."
}

python gui.py