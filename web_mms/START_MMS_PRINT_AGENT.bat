@echo off
setlocal
pushd "%~dp0print_agent"
call START_PRINT_AGENT.bat %*
popd
