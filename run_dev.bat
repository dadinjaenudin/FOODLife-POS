@echo off
REM Set development environment variables
set USE_SQLITE=True
set USE_LOCMEM_CACHE=True
set USE_INMEMORY_CHANNEL=True
set DEBUG=True

REM Run Django development server
python manage.py runserver
