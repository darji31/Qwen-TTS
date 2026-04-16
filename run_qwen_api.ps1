$ErrorActionPreference = "Stop"

$baseUrl = "http://127.0.0.1:8000"
$predictUrl = "$baseUrl/api/predict"
$useXVectorOnly = $true
$referenceText = if ($useXVectorOnly) { $null } else { "reference tone generated locally" }

function To-DataUrl {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Mime
    )
    $resolved = (Resolve-Path $Path).Path
    $bytes = [System.IO.File]::ReadAllBytes($resolved)
    $b64 = [System.Convert]::ToBase64String($bytes)
    return "data:$Mime;base64,$b64"
}

function New-GradioUploadObject {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Mime
    )
    $resolved = (Resolve-Path $Path).Path
    $fileInfo = Get-Item $resolved
    return @{
        name      = $fileInfo.Name
        orig_name = $fileInfo.Name
        size      = [int64]$fileInfo.Length
        is_file   = $false
        data      = (To-DataUrl -Path $resolved -Mime $Mime)
    }
}

function Get-GradioFnIndices {
    param([Parameter(Mandatory = $true)][string]$ConfigUrl)
    $config = Invoke-RestMethod -Method Get -Uri $ConfigUrl
    $idToType = @{}
    foreach ($component in $config.components) {
        $idToType[[int]$component.id] = [string]$component.type
    }
    $deps = @($config.dependencies)

    function Find-FnIndex([string[]]$expectedTypes) {
        for ($i = 0; $i -lt $deps.Count; $i++) {
            $actualTypes = @()
            foreach ($inputId in @($deps[$i].inputs)) {
                $actualTypes += $idToType[[int]$inputId]
            }
            if (($actualTypes -join ",") -eq ($expectedTypes -join ",")) {
                return $i
            }
        }
        return $null
    }

    $saveFnIndex = Find-FnIndex @("audio", "textbox", "checkbox")
    $genFnIndex = Find-FnIndex @("file", "textbox", "dropdown")
    if ($null -eq $saveFnIndex -or $null -eq $genFnIndex) {
        throw "Could not resolve Gradio fn_index values from /config."
    }

    return @{
        Save = $saveFnIndex
        Gen  = $genFnIndex
    }
}

function Save-ArtifactFromGradioValue {
    param(
        [Parameter(Mandatory = $true)]$Value,
        [Parameter(Mandatory = $true)][string]$OutFile
    )
    $source = if ($Value -is [string]) { $Value } else { $Value.name }
    if (-not $source) {
        throw "Gradio response does not include a valid artifact path or URL."
    }

    if (Test-Path $source) {
        Copy-Item -LiteralPath $source -Destination $OutFile -Force
        return
    }

    if ($source -match "^https?://") {
        Invoke-WebRequest -Uri $source -OutFile $OutFile
        return
    }

    throw "Unsupported artifact source: $source"
}

$fn = Get-GradioFnIndices -ConfigUrl "$baseUrl/config"

# 1) Create .qvp
$saveBody = @{
    fn_index = $fn.Save
    data     = @(
        (New-GradioUploadObject -Path ".\ref.wav" -Mime "audio/wav"),
        $referenceText,
        $useXVectorOnly
    )
} | ConvertTo-Json -Depth 12

$saveResp = Invoke-RestMethod -Method Post -Uri $predictUrl -ContentType "application/json" -Body $saveBody
$saveStatus = $saveResp.data[1]
Write-Host "Save status: $saveStatus"
Save-ArtifactFromGradioValue -Value $saveResp.data[0] -OutFile ".\voice.qvp"
Write-Host "Saved .\voice.qvp"

# 2) Generate from .qvp
$genBody = @{
    fn_index = $fn.Gen
    data     = @(
        (New-GradioUploadObject -Path ".\voice.qvp" -Mime "application/octet-stream"),
        "Hello, this is generated from saved prompt.",
        "English"
    )
} | ConvertTo-Json -Depth 12

$genResp = Invoke-RestMethod -Method Post -Uri $predictUrl -ContentType "application/json" -Body $genBody
$genStatus = $genResp.data[1]
Write-Host "Gen status: $genStatus"
if ($null -eq $genResp.data[0]) {
    throw "Generation failed and returned no audio artifact. Status: $genStatus"
}
Save-ArtifactFromGradioValue -Value $genResp.data[0] -OutFile ".\output.wav"
Write-Host "Saved .\output.wav"
