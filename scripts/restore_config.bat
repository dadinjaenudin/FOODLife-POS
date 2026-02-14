@echo off
REM Restore POS config tables from backup
REM Usage:
REM   restore_config.bat                          (auto-detect latest backup)
REM   restore_config.bat path\to\backup.sql       (specify backup file)

cd /d "%~dp0.."
python scripts/restore_config_tables.py %*
pause
