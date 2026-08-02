@echo off
setlocal enabledelayedexpansion

pushd "%~dp0..\.."

set "DIRTY="
for /f "delims=" %%i in ('git status --porcelain 2^>nul') do set "DIRTY=1"

if defined DIRTY (
    echo ERROR: working tree is dirty ^(uncommitted or untracked changes^). Commit or stash before releasing.
    popd
    exit /b 1
)

git clone https://github.com/GrowVolution/WebFluid tmp
cd tmp
pip install -r requirements.txt
python -m build
twine upload dist/*
cd stubs
python -m build
twine upload dist/*
cd ..\..
rd /s /q tmp

popd
endlocal