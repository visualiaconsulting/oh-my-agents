# Shared, side-effect-free Python discovery for Windows entry points.
function Find-ProjectPython {
    foreach ($candidate in @(
        @{ Executable = 'py'; Prefix = @('-3') },
        @{ Executable = 'python3'; Prefix = @() },
        @{ Executable = 'python'; Prefix = @() }
    )) {
        try {
            $command = Get-Command $candidate.Executable -ErrorAction Stop
            $executable = $command.Source
            $prefix = @($candidate.Prefix)
            $version = & $executable @prefix -c 'import sys; print(sys.version_info.major, sys.version_info.minor)' 2>$null
            if ($LASTEXITCODE -eq 0 -and "$version" -match '^(\d+) (\d+)$') {
                if ([int]$Matches[1] -gt 3 -or ([int]$Matches[1] -eq 3 -and [int]$Matches[2] -ge 9)) {
                    return [PSCustomObject]@{ Executable = $executable; Prefix = $prefix }
                }
            }
        } catch {
            continue
        }
    }
    throw 'Python 3.9+ was not found. Install Python from https://python.org and add it to PATH.'
}
