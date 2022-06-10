@echo off
REM echo "copy PMMFeatureEnablementCheck to c:\"
REM set PGMDIR="%SystemDrive%\PMMFeatureEnablementCheck"

REM if not exist %PGMDIR% (
	REM md %PGMDIR%
	REM start "copy" /WAIT xcopy /Y /Q /S /I PMMFeatureEnablementCheck %PGMDIR%
REM )

cd "bin"

Kysy_installation.exe

exit 0

