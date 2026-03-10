#!/bin/bash
# Quick Start Checklist - Safe Ingestion Engine CI/CD
# Run this to verify your setup is complete

set -e

echo "🔍 Checking Safe Ingestion Engine CI/CD Setup..."
echo ""

# Check 1: Workflow file exists
echo -n "✓ Workflow file (.github/workflows/docker-ci.yml) exists: "
if [ -f ".github/workflows/docker-ci.yml" ]; then
  echo "✅"
else
  echo "❌ MISSING"
  exit 1
fi

# Check 2: Documentation files exist
echo -n "✓ GITHUB_ACTIONS_SETUP.md exists: "
if [ -f "GITHUB_ACTIONS_SETUP.md" ]; then
  echo "✅"
else
  echo "❌ MISSING"
  exit 1
fi

echo -n "✓ DEPLOYMENT.md exists: "
if [ -f "DEPLOYMENT.md" ]; then
  echo "✅"
else
  echo "❌ MISSING"
  exit 1
fi

echo -n "✓ CI_CD_SUMMARY.md exists: "
if [ -f "CI_CD_SUMMARY.md" ]; then
  echo "✅"
else
  echo "❌ MISSING"
  exit 1
fi

# Check 3: Dockerfile exists
echo -n "✓ Dockerfile exists: "
if [ -f "Dockerfile" ]; then
  echo "✅"
else
  echo "❌ MISSING"
  exit 1
fi

# Check 4: docker-compose.yml exists
echo -n "✓ docker-compose.yml exists: "
if [ -f "docker-compose.yml" ]; then
  echo "✅"
else
  echo "❌ MISSING"
  exit 1
fi

# Check 5: .env.example exists
echo -n "✓ .env.example exists: "
if [ -f ".env.example" ]; then
  echo "✅"
else
  echo "❌ MISSING"
  exit 1
fi

# Check 6: .gitignore has .env
echo -n "✓ .env in .gitignore: "
if grep -q "^\.env$" .gitignore 2>/dev/null; then
  echo "✅"
else
  echo "⚠️  May need to add .env to .gitignore"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ All files are in place!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 NEXT STEPS:"
echo ""
echo "1️⃣  ADD GITHUB SECRETS"
echo "   Go to: https://github.com/Elmahrosa/safe-ingestion-engine/settings/secrets/actions"
echo "   Add these secrets:"
echo "   - DOCKER_USERNAME = your Docker Hub username"
echo "   - DOCKER_PASSWORD = your Docker Hub access token"
echo ""
echo "   (Not sure how? See GITHUB_ACTIONS_SETUP.md → Section 1-2)"
echo ""
echo "2️⃣  PUSH TO GITHUB"
echo "   $ git add .github/workflows/docker-ci.yml CI_CD_SUMMARY.md GITHUB_ACTIONS_SETUP.md DEPLOYMENT.md"
echo "   $ git commit -m 'ci: add enterprise Docker CI/CD pipeline'"
echo "   $ git push origin main"
echo ""
echo "3️⃣  MONITOR WORKFLOW"
echo "   Go to: https://github.com/Elmahrosa/safe-ingestion-engine/actions"
echo "   Watch the 'Docker CI/CD Pipeline' run"
echo ""
echo "4️⃣  DEPLOY IMAGE"
echo "   After workflow completes:"
echo "   $ docker pull yourusername/safe-ingestion-engine:latest"
echo "   $ docker compose up -d"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📚 DOCUMENTATION:"
echo "   • Quick setup: GITHUB_ACTIONS_SETUP.md"
echo "   • Deploy options: DEPLOYMENT.md"
echo "   • Feature overview: CI_CD_SUMMARY.md"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🚀 Status: READY TO DEPLOY"
echo ""
