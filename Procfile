web: gunicorn statementConverter.wsgi
release: python manage.py migrate && python manage.py collectstatic --noinput
