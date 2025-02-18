@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

set "source=D:\百度同步盘\BaiduSyncdisk\ACA Builder"

rem 使用 wmic 获取当前日期，格式为 YYYYMMDD
for /f "tokens=2 delims==" %%a in ('wmic os get localdatetime /value') do (
    set "fulldate=%%a"
)
set "year=!fulldate:~2,2!"
set "month=!fulldate:~4,2!"
set "day=!fulldate:~6,2!"

set "date_suffix=!year!!month!!day!"

set "destination=D:\过程文档\ACA Release\ACA Builder_!date_suffix!\src"
set "parent_destination=D:\过程文档\ACA Release\ACA Builder_!date_suffix!"
set "base_zipname=!parent_destination!\ACA_Builder_!date_suffix!"
set "zipfile=!base_zipname!.zip"
set "temp_dir=!parent_destination!\ACA Builder"

rem 清除目标目录中的所有文件和文件夹
if exist "!destination!" (
    rd /s /q "!destination!"
)
rem 重新创建目标目录及其父目录
mkdir -p "!destination!"

rem 拷贝文件，排除指定目录、所有 .blend 后缀的文件、aca_log.txt、.gitignore 以及 package.bat 文件
robocopy "!source!" "!destination!" /E /XF *.blend aca_log.txt .gitignore package.bat /XD __pycache__ .vscode .git

rem 显示拷贝结果
if %errorlevel% leq 3 (
    echo 拷贝成功。
) else (
    echo 拷贝过程中出现错误。
    goto end
)

rem 拷贝 template\acaAssets.blend 文件到与 zip 文件同一级目录
set "specific_file=!source!\template\acaAssets.blend"
if exist "!specific_file!" (
    copy "!specific_file!" "!parent_destination!"
    echo 已将 template\acaAssets.blend 拷贝到与 zip 文件同一级目录。
) else (
    echo template\acaAssets.blend 文件不存在，无法拷贝。
)

rem 创建临时 ACA Builder 目录
if exist "!temp_dir!" (
    rd /s /q "!temp_dir!"
)
mkdir "!temp_dir!"

rem 将目标目录内容复制到临时 ACA Builder 目录
xcopy "!destination!\*" "!temp_dir!" /E /I /H

rem 检查压缩包是否存在，若存在则添加序号
set "counter=1"
:check_zip_exists
if exist "!zipfile!" (
    set "zipfile=!base_zipname!_!counter!.zip"
    set /a counter+=1
    goto check_zip_exists
)

rem 生成目标目录的压缩包，将压缩目录改为父目录，并指定包含 ACA Builder 目录
powershell -Command "Add-Type -AssemblyName System.IO.Compression.FileSystem; $zip = [System.IO.Compression.ZipFile]::Open('%zipfile%', 'Create'); $sourceDir = '%parent_destination%\ACA Builder'; $entries = [System.IO.Directory]::EnumerateFileSystemEntries($sourceDir, '*', 'AllDirectories'); foreach ($entry in $entries) { if ([System.IO.File]::Exists($entry)) { $entryName = $entry.Substring($sourceDir.Length + 1); [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip, $entry, 'ACA Builder\'+$entryName); } } $zip.Dispose();"

echo 压缩包已生成：!zipfile!

rem 删除临时目录
if exist "!temp_dir!" (
    rd /s /q "!temp_dir!"
)

:end
endlocal