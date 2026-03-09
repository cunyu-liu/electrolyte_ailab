#!/bin/bash

# AI Battery Lab Git 推送脚本
# 使用方法: ./git-push.sh "提交信息"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目路径
PROJECT_PATH="/Users/liucunyu/Documents/all_code/thu_2025/claudecode/ai-battery-lab"
BRANCH_NAME="lcy"

echo -e "${BLUE}🚀 AI Battery Lab Git 推送脚本${NC}"
echo -e "${YELLOW}=============================${NC}"

# 检查是否在正确的目录
if [ "$(pwd)" != "$PROJECT_PATH" ]; then
    echo -e "${RED}❌ 当前目录不正确${NC}"
    echo -e "${YELLOW}正在切换到项目目录...${NC}"
    cd "$PROJECT_PATH"
fi

echo -e "${GREEN}✅ 当前目录: $(pwd)${NC}"

# 检查Git状态
echo -e "${BLUE}📋 检查Git状态...${NC}"
git status

# 显示修改的文件
echo -e "${BLUE}📝 修改的文件:${NC}"
git diff --name-only --cached

# 如果没有提供提交信息，询问用户
if [ -z "$1" ]; then
    echo -e "${YELLOW}⚠️  未提供提交信息${NC}"
    echo -e "${YELLOW}请输入提交信息:${NC}"
    read -r COMMIT_MESSAGE
else
    COMMIT_MESSAGE="$1"
fi

if [ -z "$COMMIT_MESSAGE" ]; then
    echo -e "${RED}❌ 提交信息不能为空${NC}"
    exit 1
fi

# 添加所有文件
echo -e "${BLUE}➕ 添加文件到暂存区...${NC}"
git add .

# 检查是否有文件需要提交
if git diff --cached --quiet; then
    echo -e "${YELLOW}⚠️  没有文件需要提交${NC}"
fi

# 提交代码
echo -e "${BLUE}💾 提交代码...${NC}"
git commit -m "$COMMIT_MESSAGE"

git remote set-url origin https://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@github.com/AI4Battery/electrolyte_lab.git

# 推送到远程仓库
echo -e "${BLUE}📤 推送到远程仓库 ($BRANCH_NAME 分支)...${NC}"
if git push origin "$BRANCH_NAME"; then
    echo -e "${GREEN}✅ 推送成功!${NC}"
    echo -e "${GREEN}🎉 代码已成功推送到 $BRANCH_NAME 分支${NC}"
else
    echo -e "${RED}❌ 推送失败${NC}"
    echo -e "${YELLOW}可能的原因:${NC}"
    echo -e "1. GitHub认证问题"
    echo -e "2. 网络连接问题"
    echo -e "3. 需要先拉取远程代码 (git pull origin $BRANCH_NAME)"
    echo -e ""
    echo -e "${BLUE}💡 建议查看 GIT_WORKFLOW.md 文件获取详细帮助${NC}"
    exit 1
fi

echo -e "${BLUE}=============================${NC}"
echo -e "${GREEN}🎊 操作完成!${NC}"