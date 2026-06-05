#!/bin/bash
set -e

SERVER="http://10.58.101.69"
DEST="$HOME/.claude/skills/mimo"

echo "📦 正在安装 /mimo skill..."

mkdir -p "$DEST"
curl -fsSL "$SERVER/skill/mimo-skill.tar.gz" | tar xz -C "$DEST"

echo "📥 安装依赖..."
cd "$DEST/skill" && npm install --silent 2>/dev/null

echo ""
echo "✅ /mimo skill 安装成功！"
echo "   安装路径: $DEST"
echo ""
echo "💡 使用方式："
echo "   在 Claude Code 中输入 /mimo       启动 AB 评测"
echo "   在评测终端中输入   /mimo submit   提交评测结果"
