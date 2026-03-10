#!/usr/bin/env pwsh
# DEPLOYMENT READINESS CHECK - Safe Ingestion Engine CI/CD
# Run this before git push origin main

Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║     PRODUCTION DEPLOYMENT READINESS CHECK                 ║" -ForegroundColor Green
Write-Host "║     Safe Ingestion Engine - Docker CI/CD Pipeline         ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""

$allGood = $true

# ============================================================================
# CHECK 1: Core Files
# ============================================================================
Write-Host "✓ CHECK 1: CORE FILES" -ForegroundColor Cyan
$coreFiles = @(
    ".github/workflows/docker-ci.yml",
    "docker-compose.yml",
    "Dockerfile",
    "verify-deploy.ps1",
    "FINAL_SETUP_INSTRUCTIONS.md",
    "SECRETS_REFERENCE.md",
    "k8s-deployment.yaml",
    "INDEX.md",
    "00_START_HERE.md"
)

foreach ($file in $coreFiles) {
    if (Test-Path $file) {
        $size = (Get-Item $file).Length / 1KB
        Write-Host "  ✅ $file ($([Math]::Round($size, 1)) KB)" -ForegroundColor Green
    } else {
        Write-Host "  ❌ $file (MISSING)" -ForegroundColor Red
        $allGood = $false
    }
}

# ============================================================================
# CHECK 2: Workflow Secret Names
# ============================================================================
Write-Host "`n✓ CHECK 2: WORKFLOW SECRETS (Correct Names)" -ForegroundColor Cyan
$workflowContent = Get-Content ".github/workflows/docker-ci.yml" -Raw

$requiredSecrets = @("DOCKERHUB_USERNAME", "DOCKERHUB_TOKEN")
foreach ($secret in $requiredSecrets) {
    if ($workflowContent -match $secret) {
        Write-Host "  ✅ Secret reference found: $secret" -ForegroundColor Green
    } else {
        Write-Host "  ❌ Secret reference missing: $secret" -ForegroundColor Red
        $allGood = $false
    }
}

# ============================================================================
# CHECK 3: Pipeline Stages
# ============================================================================
Write-Host "`n✓ CHECK 3: PIPELINE STAGES (9 Required)" -ForegroundColor Cyan
$stages = @(
    "name: Lint & Type Check",
    "name: Security Scan",
    "name: Tests",
    "name: Docker Build & Cache",
    "name: Docker Compose Integration Test",
    "name: Docker Scout Security Scan",
    "name: Trivy Container Scan",
    "name: Build & Publish to Docker Hub",
    "name: Pipeline Summary"
)

foreach ($stage in $stages) {
    if ($workflowContent -match [regex]::Escape($stage)) {
        Write-Host "  ✅ $stage" -ForegroundColor Green
    } else {
        Write-Host "  ❌ $stage (MISSING)" -ForegroundColor Red
        $allGood = $false
    }
}

# ============================================================================
# CHECK 4: Docker Build Configuration
# ============================================================================
Write-Host "`n✓ CHECK 4: DOCKER BUILD CONFIGURATION" -ForegroundColor Cyan
$dockerChecks = @(
    @{ Pattern = "linux/amd64,linux/arm64"; Name = "Multi-platform (amd64 + arm64)" },
    @{ Pattern = "cache-from: type=gha"; Name = "GitHub Actions Cache" },
    @{ Pattern = "cache-to: type=gha"; Name = "Cache Export" }
)

foreach ($check in $dockerChecks) {
    if ($workflowContent -match $check.Pattern) {
        Write-Host "  ✅ $($check.Name)" -ForegroundColor Green
    } else {
        Write-Host "  ❌ $($check.Name) (MISSING)" -ForegroundColor Red
        $allGood = $false
    }
}

# ============================================================================
# CHECK 5: Security Scanning
# ============================================================================
Write-Host "`n✓ CHECK 5: SECURITY SCANNING" -ForegroundColor Cyan
$securityChecks = @(
    @{ Pattern = "docker/scout-action"; Name = "Docker Scout" },
    @{ Pattern = "aquasecurity/trivy-action"; Name = "Trivy" },
    @{ Pattern = "bandit"; Name = "Bandit (Code Security)" },
    @{ Pattern = "pip-audit"; Name = "pip-audit (Dependencies)" }
)

foreach ($check in $securityChecks) {
    if ($workflowContent -match $check.Pattern) {
        Write-Host "  ✅ $($check.Name)" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  $($check.Name) (not found)" -ForegroundColor Yellow
    }
}

# ============================================================================
# CHECK 6: Integration Testing
# ============================================================================
Write-Host "`n✓ CHECK 6: INTEGRATION TESTING" -ForegroundColor Cyan
$testChecks = @(
    @{ Pattern = "docker compose up"; Name = "Docker Compose Stack" },
    @{ Pattern = "/health"; Name = "Health Endpoint Test" },
    @{ Pattern = "/scan"; Name = "Scan Endpoint Test" }
)

foreach ($check in $testChecks) {
    if ($workflowContent -match $check.Pattern) {
        Write-Host "  ✅ $($check.Name)" -ForegroundColor Green
    } else {
        Write-Host "  ❌ $($check.Name) (MISSING)" -ForegroundColor Red
        $allGood = $false
    }
}

# ============================================================================
# CHECK 7: Documentation
# ============================================================================
Write-Host "`n✓ CHECK 7: DOCUMENTATION" -ForegroundColor Cyan
$docFiles = @(
    "00_START_HERE.md",
    "INDEX.md",
    "FINAL_SETUP_INSTRUCTIONS.md",
    "SECRETS_REFERENCE.md",
    "QUICK_REFERENCE.md",
    "GITHUB_ACTIONS_SETUP.md",
    "DEPLOYMENT.md",
    "CI_CD_SUMMARY.md"
)

$docCount = 0
foreach ($doc in $docFiles) {
    if (Test-Path $doc) {
        $docCount++
        Write-Host "  ✅ $doc" -ForegroundColor Green
    }
}
Write-Host "  Summary: $docCount/$($docFiles.Count) documentation files" -ForegroundColor Green

# ============================================================================
# CHECK 8: Git Status
# ============================================================================
Write-Host "`n✓ CHECK 8: GIT STATUS" -ForegroundColor Cyan
$gitStatus = git status --porcelain 2>$null
if ($gitStatus) {
    $changeCount = @($gitStatus).Count
    Write-Host "  ⚠️  $changeCount files with uncommitted changes" -ForegroundColor Yellow
} else {
    Write-Host "  ✅ All changes committed" -ForegroundColor Green
}

$branch = git rev-parse --abbrev-ref HEAD 2>$null
if ($branch -eq "main") {
    Write-Host "  ✅ On main branch: ready to push" -ForegroundColor Green
} elseif ($branch) {
    Write-Host "  ⚠️  On branch: $branch (should push from main)" -ForegroundColor Yellow
} else {
    Write-Host "  ❌ Could not determine branch" -ForegroundColor Red
}

# ============================================================================
# CHECK 9: FINAL STATUS
# ============================================================================
Write-Host "`n" -ForegroundColor Green
if ($allGood) {
    Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Green
    Write-Host "║                                                            ║" -ForegroundColor Green
    Write-Host "║          🟢 DEPLOYMENT READINESS: CONFIRMED               ║" -ForegroundColor Green
    Write-Host "║                                                            ║" -ForegroundColor Green
    Write-Host "║  All critical files, secrets, and pipeline stages ready   ║" -ForegroundColor Green
    Write-Host "║  Next: Add GitHub Secrets → git push origin main          ║" -ForegroundColor Green
    Write-Host "║                                                            ║" -ForegroundColor Green
    Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Green
    Write-Host ""
    Write-Host "DEPLOYMENT COMMAND:" -ForegroundColor Magenta
    Write-Host "  git add ." -ForegroundColor Cyan
    Write-Host "  git commit -m 'Production ready: 32 files, corrected secrets, verification'" -ForegroundColor Cyan
    Write-Host "  git push origin main" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "THEN:" -ForegroundColor Magenta
    Write-Host "  1. Monitor: https://github.com/Elmahrosa/safe-ingestion-engine/actions" -ForegroundColor Yellow
    Write-Host "  2. Wait: ~40-50 minutes for full pipeline" -ForegroundColor Yellow
    Write-Host "  3. Verify: Image on ghcr.io/elmahrosa/safe-ingestion-engine:latest" -ForegroundColor Yellow
} else {
    Write-Host "🔴 DEPLOYMENT READINESS: FAILED" -ForegroundColor Red
    Write-Host ""
    Write-Host "Fix issues above before pushing to main" -ForegroundColor Red
}

Write-Host ""
