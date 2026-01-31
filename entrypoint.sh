#!/bin/bash
# Entrypoint script for Django application in Docker

set -e

echo "======================================"
echo "F&B POS HO System - Starting..."
echo "======================================"

# Wait for database to be ready
echo "Waiting for PostgreSQL..."
while ! nc -z $DB_HOST $DB_PORT; do
  sleep 0.5
done
echo "✓ PostgreSQL is ready!"

# Wait for Redis to be ready
echo "Waiting for Redis..."
while ! nc -z redis 6379; do
  sleep 0.5
done
echo "✓ Redis is ready!"

# Run database migrations
echo "Running database migrations..."
python manage.py migrate --noinput

# Create superuser if doesn't exist
echo "Creating superuser..."
python manage.py shell << END
from core.models import User
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@yogyagroup.com', 'admin123')
    print('✓ Superuser created: admin / admin123')
else:
    print('✓ Superuser already exists')
END

# Generate sample data if database is empty
echo "Checking for sample data..."
python manage.py shell << END
from core.models import Company
if Company.objects.count() == 0:
    print('Generating sample data...')
    import subprocess
    subprocess.run(['python', 'manage.py', 'generate_sample_data'])
    print('✓ Sample data generated')
else:
    print('✓ Sample data already exists')
END

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "======================================"
echo "✓ Initialization complete!"
echo "======================================"

# Execute the command passed to docker run
exec "$@"
