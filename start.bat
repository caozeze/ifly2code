@echo off
REM 讯飞星辰MaaS代理GUI应用启动脚本 (Windows)

echo ============================================
echo   讯飞星辰 MaaS 代理服务
echo ============================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未检测到Python环境
    echo 请先安装Python 3.8或更高版本
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM 检查依赖是否安装
python -c "import PyQt5" >nul 2>&1
if errorlevel 1 (
    echo 首次运行，正在安装依赖...
    pip install -r requirements.txt
    echo.
)

echo 正在启动应用...
echo.

python main.py

pause
