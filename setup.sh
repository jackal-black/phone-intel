#!/usr/bin/env bash
# ═══════════════════════════════════════════════
# Phone Monitor — 一键部署脚本
# ═══════════════════════════════════════════════
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "📦 Phone Monitor 部署开始"
echo "──────────────────────────────"

# ── 1. 检查 Python ──
echo "🔍 检查 Python..."
if ! command -v python3 &>/dev/null; then
    echo "❌ 未找到 python3，请先安装 Python 3.10+"
    exit 1
fi
echo "   ✅ $(python3 --version)"

# ── 2. 创建虚拟环境 ──
if [ ! -d "venv" ]; then
    echo "🔧 创建虚拟环境..."
    python3 -m venv venv
fi
source venv/bin/activate

# ── 3. 安装依赖 ──
echo "📥 安装依赖..."
pip install -q -r requirements.txt
echo "   ✅ 依赖安装完成"

# ── 4. 配置 .env ──
if [ ! -f ".env" ]; then
    echo "📝 创建 .env 配置文件（请编辑填写你的 API Key）..."
    cp .env.example .env
    echo "   ⚠️  请编辑 .env 文件，填入你的 API Key："
    echo "      vi .env"
    echo "      或"
    echo "      nano .env"
else
    echo "   ✅ .env 已存在"
fi

# ── 5. 首次运行测试 ──
echo ""
echo "🚀 是否要立即运行测试？（仅打印，不推送）"
read -r -p "   [Y/n] " reply
reply=${reply:-Y}
if [[ "$reply" =~ ^[Yy] ]]; then
    echo ""
    echo "▶️  运行测试模式..."
    DRY_RUN=true python main.py
fi

# ── 6. 设置定时任务 ──
echo ""
echo "⏰ 是否设置每日定时任务（每天 09:00 自动运行）？"
read -r -p "   [y/N] " reply_cron
reply_cron=${reply_cron:-N}
if [[ "$reply_cron" =~ ^[Yy] ]]; then
    CRON_JOB="0 9 * * * cd $SCRIPT_DIR && $SCRIPT_DIR/venv/bin/python $SCRIPT_DIR/main.py >> $SCRIPT_DIR/cron.log 2>&1"
    # 检查是否已存在
    if crontab -l 2>/dev/null | grep -q "$SCRIPT_DIR/main.py"; then
        echo "   ⚠️  定时任务已存在，跳过"
    else
        (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
        echo "   ✅ 定时任务已添加（每天 09:00）"
        echo "   查看: crontab -l"
        echo "   日志: tail -f cron.log"
    fi
fi

echo ""
echo "✅ Phone Monitor 部署完成！"
echo "──────────────────────────────"
echo "运行方式:"
echo "  测试模式:   cd $SCRIPT_DIR && DRY_RUN=true python main.py"
echo "  正式运行:   cd $SCRIPT_DIR && python main.py"
echo "  查看日志:   tail -f cron.log"
