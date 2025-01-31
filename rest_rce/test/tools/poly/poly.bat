@echo off

:: calculate x^n
if "%1" == "" GOTO error
ECHO Calculating exp
SET x=%1
ECHO Received parameter x=%x%
SET n=2
if "%2" == "" (ECHO Using default exponent 2) else (goto setexponent)
:calculate
SET result=1
FOR /L %%i IN (1,1,%n%) DO SET /A result*=x
ECHO Result: %result%
ECHO %result% > result
GOTO end

:setexponent
SET n=%2
ECHO Received parameter n=%n%
GOTO calculate

:error
ECHO Usage: poly.bat x [n]

:end
