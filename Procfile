web: gunicorn statementConverter.wsgi --bind 0.0.0.0:$PORT --workers 4
release: python manage.py migrate && python manage.py collectstatic --noinput
