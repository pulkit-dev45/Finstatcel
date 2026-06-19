web: gunicorn statementConverter.wsgi --timeout 180
release: python manage.py migrate && python manage.py collectstatic --noinput
