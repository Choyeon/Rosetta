$routes = @(
    @{ path = "/"; name = "02-home" },
    @{ path = "/posts"; name = "03-posts" },
    @{ path = "/categories"; name = "04-categories" },
    @{ path = "/archive"; name = "05-archive" },
    @{ path = "/login"; name = "06-login" },
    @{ path = "/register"; name = "07-register" },
    @{ path = "/oobe"; name = "08-oobe" },
    @{ path = "/admin"; name = "09-admin" }
)

$baseUrl = "http://localhost:3000"
$shotDir = "D:\WebProjects\Rosetta\e2e-screenshots"
$results = @()

foreach ($route in $routes) {
    $url = $baseUrl + $route.path
    Write-Host "========================================"
    Write-Host "访问: $url"
    Write-Host "========================================"
    
    agent-browser open $url 2>&1 | Out-Null
    Start-Sleep -Milliseconds 5000
    
    $title = agent-browser get title 2>&1
    Write-Host "标题: $title"
    
    $shotFile = agent-browser screenshot --screenshot-dir $shotDir 2>&1
    $shotPath = ($shotFile -split "saved to ")[-1].Trim()
    $newPath = Join-Path $shotDir ($route.name + ".png")
    if (Test-Path $shotPath) {
        Move-Item -Path $shotPath -Destination $newPath -Force
        Write-Host "截图: $newPath"
    }
    
    $script = @'
(function() {
  var body = document.body ? document.body.innerText : "";
  var is500 = body.includes("500") || 
              body.includes("Internal Server Error") ||
              document.title.includes("500") ||
              body.includes("Nuxt Server Error");
  var errorCount = 0;
  var warnCount = 0;
  try {
    if (window.__consoleErrors) errorCount = window.__consoleErrors.length;
    if (window.__consoleWarns) warnCount = window.__consoleWarns.length;
  } catch(e) {}
  return JSON.stringify({
    title: document.title,
    url: window.location.href,
    is500: is500,
    errorCount: errorCount,
    warnCount: warnCount,
    bodyHasError: body.substring(0, 500).includes("Error") && !body.includes("Blog"),
    preview: body.substring(0, 200)
  });
})()
'@
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($script)
    $base64 = [System.Convert]::ToBase64String($bytes)
    $pageInfo = agent-browser eval -b $base64 2>&1 | ConvertFrom-Json
    
    $netStatus = "200"
    $netRequests = agent-browser network requests 2>&1
    foreach ($req in $netRequests) {
        if ($req -match "\(Document\)\s+(\d+)") {
            $netStatus = $Matches[1]
            break
        }
    }
    if ($netStatus -eq "500") { $pageInfo.is500 = $true }
    
    Write-Host "500错误: $($pageInfo.is500)"
    Write-Host "状态码(文档): $netStatus"
    Write-Host ""
    
    $results += @{
        route = $route.path
        title = $title
        is500 = $pageInfo.is500
        docStatus = $netStatus
        errorCount = $pageInfo.errorCount
        warnCount = $pageInfo.warnCount
        note = if ($pageInfo.is500) { "页面返回500错误" } elseif ($netStatus -ne "200") { "文档状态: $netStatus" } else { "" }
    }
}

Write-Host "========================================"
Write-Host "测试完成，结果汇总:"
Write-Host "========================================"
$results | ConvertTo-Json -Depth 10 | Out-File -FilePath "D:\WebProjects\Rosetta\e2e-results.json" -Encoding UTF8
$results | ConvertTo-Json -Depth 10
