Get-Content "$PSScriptRoot/config/cli.txt", "$PSScriptRoot/config/gui.txt" | Where-Object { $_ -match '#scoop' } | ForEach-Object { (-split $_)[0] } | ForEach-Object { scoop install $_ }
